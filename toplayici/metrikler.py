# -*- coding: utf-8 -*-
"""Getiri ve risk metrikleri.

Hepsi saf fonksiyon: (tarih, fiyat) listesi girer, sayi cikar. Ag yok,
veritabani yok, bu yuzden testi kolay.

TEFAS fiyatlari zaten masraflar dusulmus ve temettu iceri yazilmis
haldedir (Turkiye'de fonlar temettu dagitmaz, birim fiyata eklenir).
Yani buradaki getiriler NET TOPLAM GETIRIDIR, ayrica duzeltme gerekmez.

Butun yuzdeler 100 ile carpilmis olarak doner: 12.5 = %12,5.
Veri yetmiyorsa None doner - uydurma deger uretilmez.
"""
from __future__ import annotations

import math
from datetime import date

# Kac ISLEM GUNU geriye bakilacagi. Takvim gunu degil: fon fiyatlaninca
# bir gozlem olusur, tatiller zaten seride yoktur.
PENCERE = {
    "gunluk": 1,
    "haftalik": 5,
    "aylik": 21,
    "uc_aylik": 63,
    "yillik": 252,
}

VOLATILITE_PENCERE = 60      # gunluk getiri sayisi (gosterilen "Oynaklik")

# RISK-AYARLI GETIRI ICIN AYRI PENCERE.
#
# Sharpe orani pay ve bolende AYNI ornegi kullanir. Once pay 252
# gozlemlik yillik getiri, bolen 60 gozlemlik oynaklik idi: bir yillik
# getiri uc aylik riske bolunuyordu. Bu standart bir Sharpe degil,
# pencereleri karistiran ozel bir orandi.
#
# Gosterilen "Oynaklik" sutunu 60 gunde KALIYOR — orasi bilerek guncel
# riski bildiriyor. Yalnizca risk-ayarli getiri ayni pencereyi kullanir.
YILLIK_VOLATILITE_PENCERE = 252
DUSUS_PENCERE = 252          # maks dusus icin bakilan gozlem sayisi
YIL_ISGUNU = 252


def getiri(seri, gun):
    """`gun` islem gunu onceye gore yuzde degisim.

    seri: [(tarih, fiyat), ...] eskiden yeniye sirali.
    """
    if len(seri) < gun + 1:
        return None
    onceki = seri[-1 - gun][1]
    simdiki = seri[-1][1]
    if onceki is None or simdiki is None or onceki <= 0:
        return None
    return (simdiki / onceki - 1.0) * 100.0


def yilbasindan_getiri(seri):
    """Onceki yilin son gozlemine gore yuzde degisim.

    Yilbasi getirisi icin dogru referans 1 Ocak degil, gecen yilin son
    islem gunudur; 1 Ocak tatil oldugu icin o gun fiyat yoktur.
    """
    if len(seri) < 2:
        return None
    son_tarih, son_fiyat = seri[-1]
    yil = son_tarih[:4]
    baz = None
    for tarih, fiyat in seri:
        if tarih[:4] < yil:
            baz = fiyat
        else:
            break
    if baz is None or baz <= 0 or son_fiyat is None:
        return None
    return (son_fiyat / baz - 1.0) * 100.0


AZAMI_BOSLUK_GUN = 10


def _gun_farki(a, b):
    """Iki ISO tarih arasindaki takvim gunu farki.

    TARIH KURULUMU DA try ICINDE OLMALI. Ilk yazimda yalnizca `int()`
    ayristirmasi sariliydi; `date(2026, 1, 62)` gibi gecersiz bir gun
    disarida ValueError atip BUTUN toplamayi cokertiyordu. Bozuk bir
    tarih tek bir fonun olcumunu bozabilir, akisi durduramaz.

    Ayristirilamayan tarihte 0 doner: bosluk BILINMIYOR demektir ve o
    getiri atlanmaz. Yanlis tarih yuzunden gercek veriyi silmek, bosluk
    filtresinin amacina aykiri olur.
    """
    try:
        ya, ma, da = (int(p) for p in a.split("-")[:3])
        yb, mb, db = (int(p) for p in b.split("-")[:3])
        return date(yb, mb, db).toordinal() - date(ya, ma, da).toordinal()
    except (AttributeError, TypeError, ValueError):
        return 0


def gunluk_getiriler(seri, azami_bosluk_gun=AZAMI_BOSLUK_GUN):
    """Ardisik gozlemler arasi oransal degisimler (yuzde degil, oran).

    ARDISIK GOZLEM, ARDISIK GUN DEMEK DEGIL.
    ========================================

    Once tarihe hic bakilmiyordu: iki ardisik KAYIT arasindaki degisim
    "gunluk getiri" sayiliyordu. Fiyatlanmayan bir fonun 216 gunluk
    degisimi tek bir gunluk getiri gibi islenip kok(252) ile
    yillklandiriliyordu.

    Olculdu (2026-09-11 yayimlanan veri): 60 gunluk pencerede 4 gunden
    buyuk bosluk olan 17 fon var (2446'da, %0,7) ve bosluklar 216 gune
    kadar cikiyor. Sonuc: KPS %284,58, PDR %182,58 oynaklik bildiriyordu
    — butun fonlarda ortanca %6,86 iken. Veri setindeki en yuksek deger
    %864,65 de buyuk olasilikla ayni artefakt.

    Nadir ama SIDDETLI ve tam olarak sakinlik sutununu bozuyor; o da
    uygulamanin olculerek guvenilir bulunan tek ekseni.

    Esik neden 10 gun: normal hafta sonu + tatil 4 gune kadar cikar,
    bayram tatilleri bunu 9 gune tasiyabilir. 10 gunun otesi "fon
    fiyatlanmamis" demektir; o araligi olceklendirmek yerine ATLIYORUZ.
    Olceklendirme (1/kok(gun)) bagimsiz artis varsayimi gerektirir ve
    askiya alinmis bir fon icin bu varsayim savunulamaz.

    SIFIR FIYAT -%100'LUK "GUNLUK GETIRI" URETMEMELI.
    ================================================

    `maks_dusus` icinde sifir fiyat gecersiz sayiliyordu ama BURADA
    yalnizca `onceki > 0` kontrol ediliyordu; `simdiki = 0` gecebiliyor
    ve -%100'luk bir gunluk getiri uretiyordu. Tek basina bu gozlem
    oynakligi ~%200'e cikariyor.

    Olculdu (KPS, yayimlanan veri): 2026-01-13'te 1,00 -> 2026-01-14'te
    0,00. Bosluk duzeltmesinden SONRA bile oynaklik %284,59 kaliyordu ve
    sebebi boslук degil bu tek gozlemdi.

    Sifir fiyat veri hatasi da tam kayip da olabilir; ikisi de "bugun
    %100 kaybetti" diye gunluk oynakliga yazilamaz. `maks_dusus` ile
    ayni kural: gozlem atlanir.
    """
    cikti = []
    for i in range(1, len(seri)):
        onceki = seri[i - 1][1]
        simdiki = seri[i][1]
        if not (onceki and onceki > 0):
            continue
        if simdiki is None or simdiki <= 0:
            continue
        if _gun_farki(seri[i - 1][0], seri[i][0]) > azami_bosluk_gun:
            continue
        cikti.append(simdiki / onceki - 1.0)
    return cikti


def volatilite(seri, pencere=VOLATILITE_PENCERE):
    """Yillklandirilmis oynaklik (%).

    Son `pencere` gunluk getirinin ORNEK standart sapmasi (n-1) alinir ve
    kok(252) ile yillklandirilir. Yeterli gozlem yoksa None.
    """
    g = gunluk_getiriler(seri)
    if len(g) < pencere:
        return None
    son = g[-pencere:]
    ort = sum(son) / len(son)
    varyans = sum((x - ort) ** 2 for x in son) / (len(son) - 1)
    return math.sqrt(varyans) * math.sqrt(YIL_ISGUNU) * 100.0


def maks_dusus(seri, pencere=DUSUS_PENCERE):
    """En buyuk tepe-dip kaybi (%), NEGATIF sayi olarak.

    -18.4 => zirveden dibe %18,4 kaybettirmis.

    SIFIR/NEGATIF FIYAT ATLANMAZ, METRIK GECERSIZ SAYILIR.
    ======================================================

    Once `fiyat <= 0` olan gozlemler `continue` ile ATLANIYORDU. Niyet
    bozuk veriden korunmakti ama sonuc en kotu durumu sessizce silmekti:

        maks_dusus([100, 0])      -> 0.0    (hic dusmemis!)
        maks_dusus([100, 50, 0])  -> -50.0  (sifira inis yok sayildi)

    Bu, risk puaninin %40'ini besleyen metrik. Cokmus bir fon "sakin"
    gorunuyordu.

    Sifir fiyat iki sey olabilir ve veriden AYIRT EDILEMEZ:
      (a) veri hatasi,
      (b) gercek tam kayip.
    Ikisinde de "dusus yok" YANLIS cevap. Bu yuzden artik None donuyor:
    metrik olculemedi demek, uydurmaktan iyidir. `GEREKLI` listesinde
    olmadigi icin fon tumden elenmez; risk puani yalnizca oynakliktan
    hesaplanir ve `eksen()` kalan agirligi yeniden normalize eder.
    """
    if len(seri) < 2:
        return None
    son = seri[-pencere:] if len(seri) > pencere else seri
    zirve = None
    en_kotu = 0.0
    for _, fiyat in son:
        if fiyat is None:
            continue
        if fiyat <= 0:
            # Gecersiz ya da tam kayip: hangisi oldugu bilinemez.
            return None
        if zirve is None or fiyat > zirve:
            zirve = fiyat
        dusus = (fiyat / zirve - 1.0) * 100.0
        if dusus < en_kotu:
            en_kotu = dusus
    return en_kotu if zirve is not None else None


def hesapla(seri):
    """Bir fonun butun metriklerini sozluk olarak dondurur."""
    m = {}
    for ad, gun in PENCERE.items():
        m[ad + "_getiri"] = getiri(seri, gun)
    m["yilbasindan_getiri"] = yilbasindan_getiri(seri)
    m["volatilite"] = volatilite(seri)
    # Risk-ayarli getiri PAYLA AYNI pencereyi kullanmali (bkz.
    # YILLIK_VOLATILITE_PENCERE). Gozlem yetmiyorsa None kalir ve
    # risk_ayarli da uretilmez — uydurma oran uretmekten iyidir.
    m["yillik_volatilite"] = volatilite(
        seri, pencere=YILLIK_VOLATILITE_PENCERE)
    m["maks_dusus"] = maks_dusus(seri)
    m["gozlem_sayisi"] = len(seri)
    m["ilk_tarih"] = seri[0][0] if seri else None
    m["son_tarih"] = seri[-1][0] if seri else None
    m["son_fiyat"] = seri[-1][1] if seri else None
    return m
