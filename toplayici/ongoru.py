# -*- coding: utf-8 -*-
"""Puanlamanin ONGORU GUCUNU olcer.

NEDEN BU MODUL VAR
==================

Uygulama fonlari puanlayip "kategori sirasi 1" diye gosteriyor. Bu bir
IDDIA: "bu fon digerlerinden iyi". Iddianin sinanmasi gerekir.

Sinandi (2488 fon, 2025-07..2026-08) ve sonuc su:

    bilesen           agirlik   ileri Spearman
    aylik getiri       0,35        0,07
    uc aylik getiri    0,25        0,05
    haftalik getiri    0,20        0,07
    volatilite         0,20        0,76   <-- TEK CALISAN BILESEN

    Ust %20'nin ileri getirisi vs alt %20:
        1 ay   %3,1  vs  %3,2
        3 ay   %9,2  vs  %9,4
        6 ay  %17,2  vs %19,1   <-- alt dilim DAHA IYI

Yani gecmis getiriye gore siralama gelecegi TUTMUYOR; oynaklik ise guclu
bicimde kaliciydi. "Bu fon oynak" demek gelecege dair gercek bir ifade,
"bu fon gecen ay iyi getirdi" degil.

Bu modul olcumu HER TOPLAMADA yeniden yapar - sabit bir sayi gomulmez,
cunku piyasa degisirse olcum de degismeli. Sonuc JSON'a yazilir ve
uygulamada siralamanin yaninda gosterilir.

YONTEM
======

Ileri yuruyus: her T aninda fonlar GECMIS penceredeki degere gore
siralanir, T+ufuk arasindaki GERCEK sonuca bakilir. Kategori icinde
yapilir - para piyasasi fonuyla hisse fonunu ayni sirada yaristirmak
zaten anlamsiz.

Olculen iki sey:
  * Spearman sira korelasyonu: siralama ne kadar korunuyor
  * Ust/alt %20 dilimlerin ileri sonucu: pratikte fark var mi

Ikincisi daha anlasilir: "ust sirayi secseydin ne kazanirdin".
"""
from __future__ import annotations

import math
from collections import defaultdict

import metrikler as _metrikler
import puanlama as _puanlama

# OLCULEN SEY, YAYIMLANAN SEY OLMALI.
# ====================================
#
# Bu modul bir donem HAM 63 gunluk getiriye gore siralama yapip onu
# sinadi. Ama uygulamanin ekranda gosterdigi `getiri_puani` o degil:
# 21/63/5 gunluk getirilerin KATEGORI ICI z-skorlarinin agirlikli
# bilesimi. Ayni sekilde risk ekseni %60 oynaklik + %40 maksimum dusus
# bilesimiyken sinama yalnizca ham oynakligi olcuyordu.
#
# Yani "0,71 kalici" cumlesi oynakligin kaliciligini gosteriyordu,
# kullaniciya gosterilen Sakinlik puanini DEGIL. Sinama gecse de
# gecmese de yanlis seyi sinamis oluyordu.
#
# Ustelik iki hesap yolu ayni bozuk girdiyi farkli yorumluyordu.
# Olculdu: tek sifir fiyat iceren, kalan butun fiyatlari 100 olan 64
# gozlemde canli `metrikler.volatilite` %0 donerken buradaki ayri
# kopya %199,97 donuyordu — cunku sifir fiyat ve buyuk tarih boslugu
# kurallari yalnizca canli yolda vardi.
#
# Artik her iki yol da `metrikler` + `puanlama` fonksiyonlarini
# CAGIRIYOR. Ham olcum de birakildi (`ham_*` anahtarlari) ki ikisi
# karsilastirilabilsin; ama yayimlanan basliktaki sayi uretimdeki
# puanin sayisidir.

# Siralamanin dayandigi gecmis pencere (islem gunu). Puanlamadaki en
# uzun getiri bileseni uc aylik oldugu icin 63 gun; 63 gunluk getiri
# 64 gozlem ister.
GECMIS_PENCERE = 63

# Hangi ufuklarda sinanacak (islem gunu).
UFUKLAR = (21, 63, 126)

# Bir kategorinin olcume girmesi icin gereken en az fon sayisi.
# Az fonlu kategoride sira korelasyonu gurultuden ibaret olur.
ASGARI_FON = 15

# T noktalari arasindaki adim. Her gun olcmek ortusen pencereleri
# sisirir ve bagimsiz gozlem sayisini abartir.
ADIM = 21

# Dilim buyuklugu: ust/alt %20.
DILIM = 5

# Bir iliskiyi "kalici" diye ANMAK icin gereken en az sira
# korelasyonu. Bu bir istatistiksel sinama DEGIL, raporlama
# esigidir: metnin kendi sayisiyla celismemesini saglar.
KALICI_ESIK = 0.40


def _siralar(degerler: list) -> list:
    """Ortalama sirali siralama (beraberlik duzeltmeli).

    BERABERLIKLER ORTALAMA SIRA ALIR. Once sort sirasina gore ayri sira
    veriliyordu ve bu SAHTE korelasyon uretiyordu: butun degerleri ayni
    olan bir dizi (ornegin para piyasasi kategorisinde yuvarlanmis
    volatiliteler) Spearman = 1,00 donduruyordu. Yani "hicbir bilgi yok"
    durumu "mukemmel ongoru" gibi gorunuyordu.
    """
    n = len(degerler)
    sira = sorted(range(n), key=lambda i: degerler[i])
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and degerler[sira[j + 1]] == degerler[sira[i]]:
            j += 1
        ortalama = (i + j) / 2.0
        for k in range(i, j + 1):
            r[sira[k]] = ortalama
        i = j + 1
    return r


def _spearman(cift: list) -> float | None:
    """Sira korelasyonu. cift: [(gecmis_deger, ileri_deger), ...]"""
    n = len(cift)
    if n < 3:
        return None
    rg = _siralar([c[0] for c in cift])
    rf = _siralar([c[1] for c in cift])
    mg, mf = sum(rg) / n, sum(rf) / n
    kov = sum((rg[i] - mg) * (rf[i] - mf) for i in range(n))
    sg = math.sqrt(sum((v - mg) ** 2 for v in rg))
    sf = math.sqrt(sum((v - mf) ** 2 for v in rf))
    if sg * sf == 0:
        return None
    return kov / (sg * sf)


def _dilim_ortalamasi(sirali: list, k: float) -> float | None:
    """Ust dilimin ileri ortalamasi — BERABERLIGE ADIL.

    Once `sirali[:k]` ile kesiliyordu. Python'un siralamasi kararli
    oldugu icin ESIT gecmis degerine sahip fonlarda dilim uyeligi
    sozlugun giris sirasina bagli kaliyordu. Sinandi: ayni 20 fon, ayni
    fiyatlar, yalnizca sozluk sirasi tersine cevrilince ust/alt dilim
    +%12,5 / -%12,5 iken -%12,5 / +%12,5 oluyor; dilim farki +25 puandan
    -25 puana donuyordu. Yani rapor edilen sayi veriden degil sozluk
    sirasindan geliyordu.

    Cozum: sinirda kalan beraberlik grubu KESIRLI AGIRLIKLA girer.
    Grubun tamami esit muamele gorur, hicbir uyesi giris sirasi yuzunden
    iceride ya da disarida kalmaz.

    `sirali` gecmis degere gore siralanmis olmali (ust dilim icin
    azalan, alt dilim icin artan).
    """
    if not sirali or k <= 0:
        return None
    toplam, kullanilan = 0.0, 0.0
    i, n = 0, len(sirali)
    while i < n and kullanilan < k - 1e-12:
        j = i
        while j + 1 < n and sirali[j + 1][0] == sirali[i][0]:
            j += 1
        grup = sirali[i:j + 1]
        agirlik = min(1.0, (k - kullanilan) / len(grup))
        for _, ileri in grup:
            toplam += ileri * agirlik
            kullanilan += agirlik
        i = j + 1
    return toplam / kullanilan if kullanilan > 0 else None


def _getiri(fiyatlar: dict, tarihler: list, i0: int, i1: int) -> float | None:
    t0, t1 = tarihler[i0], tarihler[i1]
    p0, p1 = fiyatlar.get(t0), fiyatlar.get(t1)
    if p0 is None or p1 is None or p0 <= 0:
        return None
    return (p1 / p0 - 1) * 100


def _seri(fiyatlar: dict, tarihler: list, i0: int, i1: int) -> list:
    """(tarih, fiyat) dilimi — `metrikler` fonksiyonlarinin bekledigi bicim."""
    return [(t, fiyatlar[t]) for t in tarihler[max(0, i0):i1] if t in fiyatlar]


def _volatilite(fiyatlar: dict, tarihler: list, i0: int, i1: int):
    """Oynaklik — UYGULAMADAKI HESABIN AYNISI.

    Burada bir donem ayri bir kopya vardi ve canli yoldaki iki kuraldan
    ikisi de eksikti: sifir fiyat -%100'luk bir "gunluk getiri" olarak
    giriyordu, buyuk tarih bosluklari da tek gunluk degisim sayiliyordu.

    Olculdu: tek sifir fiyat iceren 64 gozlemde canli hesap %0, buradaki
    kopya %199,97 donuyordu. Iki yol AYNI bozuk girdiyi taban tabana zit
    yorumluyordu; boyle bir sinama uygulamayi degil kendini olcer.

    Artik dogrudan `metrikler.volatilite` cagriliyor. Pencere gecmis
    dilimin uzunluguna gore kisaltiliyor: geri sinamada 63 gozlemlik
    dilim var, uretimdeki 60 gunluk pencere tam oturuyor; daha kisa
    dilimlerde en az 20 getiri araniyor (altinda None).
    """
    seri = _seri(fiyatlar, tarihler, i0, i1)
    g = _metrikler.gunluk_getiriler(seri)
    if len(g) < 20:
        return None
    pencere = min(_metrikler.VOLATILITE_PENCERE, len(g))
    return _metrikler.volatilite(seri, pencere=pencere)


ISLEVLER = {"getiri": _getiri, "volatilite": _volatilite}

# ------------------------------------------------ uretimdeki puanin aynisi

# Getiri ekseni agirliklari ayarlar.json'dan gelir; modul saf kalsin
# diye disaridan verilebiliyor, verilmezse uretimdeki varsayilan.
VARSAYILAN_AGIRLIK = {
    "aylik_getiri": 0.35, "uc_aylik_getiri": 0.25, "haftalik_getiri": 0.20,
}
Z_KIRPMA = 3.0


def _uretim_metrikleri(fiyatlar: dict, tarihler: list, i0: int, i1: int):
    """Bir fonun o andaki metrikleri — `metrikler.hesapla` ile ayni yol."""
    seri = _seri(fiyatlar, tarihler, i0, i1)
    if len(seri) < 22:
        return None
    m = {
        "haftalik_getiri": _metrikler.getiri(seri, 5),
        "aylik_getiri": _metrikler.getiri(seri, 21),
        "uc_aylik_getiri": _metrikler.getiri(seri, 63),
        "volatilite": _volatilite(fiyatlar, tarihler, i0, i1),
        "maks_dusus": _metrikler.maks_dusus(seri, pencere=len(seri)),
    }
    return m


def _uretim_puanlari(metrik_haritasi: dict, eksen: str,
                     agirliklar: dict | None = None) -> dict:
    """Bir KATEGORININ fonlarini uretimdeki puanla puanlar.

    metrik_haritasi: {fon_kodu: metrikler sozlugu}
    eksen: "getiri" | "risk"

    `puanlama` modulunun kendi `_z`/`gecerli` fonksiyonlarini kullanir;
    kirpma, ters isaret ve eksik bilesende yeniden normalize etme
    davranisi uretimle birebir ayni olsun diye kopyalanmadi, cagrildi.

    Doner: {fon_kodu: puan}
    """
    if eksen == "getiri":
        bilesenler = _puanlama.GETIRI_BILESENLERI
        agirlik_haritasi = agirliklar or VARSAYILAN_AGIRLIK
    else:
        bilesenler = _puanlama.RISK_BILESENLERI
        agirlik_haritasi = _puanlama.RISK_AGIRLIKLARI
    normalize = sum(agirlik_haritasi.get(m, 0) for m in bilesenler)

    istatistik = {}
    for metrik in bilesenler:
        degerler = [m[metrik] for m in metrik_haritasi.values()
                    if _puanlama.gecerli(m.get(metrik))]
        if len(degerler) >= 2:
            istatistik[metrik] = _puanlama._ortalama_ve_sapma(degerler)

    puanlar = {}
    for kod, m in metrik_haritasi.items():
        toplam, kullanilan = 0.0, 0.0
        for metrik in bilesenler:
            if metrik not in istatistik:
                continue
            ort, sapma = istatistik[metrik]
            z = _puanlama._z(m.get(metrik), ort, sapma, Z_KIRPMA)
            if z is None:
                continue
            if metrik in _puanlama.TERS:
                z = -z
            agirlik = agirlik_haritasi.get(metrik, 0) / normalize
            toplam += agirlik * z
            kullanilan += agirlik
        if kullanilan > 0:
            puanlar[kod] = toplam / kullanilan
    return puanlar


def olc(seriler: dict, kategoriler: dict, olcut: str = "getiri") -> dict:
    """Bir olcutun ongoru gucunu olcer.

    seriler: {fon_kodu: {tarih: fiyat}}
    kategoriler: {fon_kodu: (fon_tipi, kategori_ad)}
    olcut: "getiri" | "volatilite"

    Doner: {ufuk_gun: {spearman, ust_dilim, alt_dilim, olcum_sayisi}}
    """
    islev = ISLEVLER.get(olcut)
    if islev is None:
        return {}

    tarihler = sorted({t for s in seriler.values() for t in s})
    sonuc = {}

    for ufuk in UFUKLAR:
        ro_list, ust_list, alt_list = [], [], []
        # TAHMIN BASLANGICI AYRI SAYILIR.
        #
        # `olcum_sayisi` = baslangic x kategori. Kategoriler kesitsel
        # tekrar saglar, o gercek bilgidir — ama hepsi AYNI piyasa
        # rejimini yasar. "Bu iliski zaman icinde kalici mi" sorusu
        # zamansal tekrar ister. Tek bir sayi vermek bagimsizligi
        # abartiyordu: 85 olcum, 5 baslangictan geliyordu.
        #
        # Ustelik ileri pencereler ADIM'dan uzun oldugunda baslangiclar
        # da ortusur; ortusmeyen en buyuk alt kume `ortusmeyen_baslangic`
        # olarak bildirilir (ADIM=21 iken 126 gunluk ufukta 1'e kadar
        # dusuyor).
        baslangic_sayisi = 0
        for ti in range(GECMIS_PENCERE, len(tarihler) - ufuk, ADIM):
            gruplar = defaultdict(list)
            for fon, fiyatlar in seriler.items():
                gecmis = islev(fiyatlar, tarihler, ti - GECMIS_PENCERE, ti)
                ileri = islev(fiyatlar, tarihler, ti, ti + ufuk)
                if gecmis is None or ileri is None:
                    continue
                gruplar[kategoriler.get(fon, ("?", "?"))].append(
                    (gecmis, ileri))

            kullanildi = False
            for cift in gruplar.values():
                if len(cift) < ASGARI_FON:
                    continue
                kullanildi = True
                ro = _spearman(cift)
                if ro is not None:
                    ro_list.append(ro)
                k = max(1, len(cift) // DILIM)
                ust = _dilim_ortalamasi(
                    sorted(cift, key=lambda c: -c[0]), k)
                alt = _dilim_ortalamasi(
                    sorted(cift, key=lambda c: c[0]), k)
                if ust is not None:
                    ust_list.append(ust)
                if alt is not None:
                    alt_list.append(alt)
            if kullanildi:
                baslangic_sayisi += 1

        if not ro_list:
            continue
        sonuc[ufuk] = {
            "spearman": round(sum(ro_list) / len(ro_list), 3),
            "ust_dilim": round(sum(ust_list) / len(ust_list), 2),
            "alt_dilim": round(sum(alt_list) / len(alt_list), 2),
            # kategori-tarih hucresi sayisi (kesitsel tekrar dahil)
            "olcum_sayisi": len(ro_list),
            # zamansal tekrar: kac ayri tahmin baslangici kullanildi
            "baslangic_sayisi": baslangic_sayisi,
            # ileri pencereleri ortusmeyen en buyuk baslangic alt kumesi
            "ortusmeyen_baslangic": max(
                1, -(-baslangic_sayisi // max(1, -(-ufuk // ADIM)))
            ) if baslangic_sayisi else 0,
        }
    return sonuc


def olc_uretim(seriler: dict, kategoriler: dict, eksen: str = "getiri",
               agirliklar: dict | None = None) -> dict:
    """EKRANDAKI PUANIN ongoru gucu.

    `olc()` ham bir buyugu (63 gunluk getiri / oynaklik) siralar. Bu
    fonksiyon ise uygulamanin GERCEKTEN YAYIMLADIGI puani siralar:

      eksen="getiri" -> `getiri_puani`: 21/63/5 gunluk getirilerin
                        kategori ici z-skorlarinin agirlikli bilesimi.
                        Ileri sonuc: gerceklesen ileri getiri (%).
      eksen="risk"   -> `risk_puani`: %60 oynaklik + %40 maksimum dusus
                        bilesimi (Sakinlik). Ileri sonuc: AYNI bilesimin
                        ileri penceredeki degeri — soru "sakin olan sakin
                        kaliyor mu".

    Ikisi ayni sey degil ve fark onemli: getiri ekseninde ileri sonucun
    getiri olmasi gerekir (kullanicinin kazandigi sey odur), risk
    ekseninde ise sorunun kendisi kaliciliktir.

    Doner: `olc()` ile ayni anahtarlar.
    """
    tarihler = sorted({t for s in seriler.values() for t in s})
    sonuc = {}
    # 63 gunluk getiri 64 gozlem ister.
    gecmis = GECMIS_PENCERE + 1

    for ufuk in UFUKLAR:
        ro_list, ust_list, alt_list = [], [], []
        baslangic_sayisi = 0
        for ti in range(gecmis, len(tarihler) - ufuk, ADIM):
            # 1) Her fonun o andaki uretim metrikleri.
            gecmis_metrik, ileri_metrik, ileri_getiri = {}, {}, {}
            for fon, fiyatlar in seriler.items():
                gm = _uretim_metrikleri(fiyatlar, tarihler, ti - gecmis, ti)
                if gm is None:
                    continue
                gecmis_metrik[fon] = gm
                if eksen == "risk":
                    im = _uretim_metrikleri(
                        fiyatlar, tarihler, ti, ti + ufuk)
                    if im is not None:
                        ileri_metrik[fon] = im
                else:
                    g = _getiri(fiyatlar, tarihler, ti, ti + ufuk)
                    if g is not None:
                        ileri_getiri[fon] = g

            # 2) Kategori ici puanlama — uretimdeki fonksiyonlarla.
            kat_gecmis = defaultdict(dict)
            for fon, m in gecmis_metrik.items():
                kat_gecmis[kategoriler.get(fon, ("?", "?"))][fon] = m
            kat_ileri = defaultdict(dict)
            for fon, m in ileri_metrik.items():
                kat_ileri[kategoriler.get(fon, ("?", "?"))][fon] = m

            kullanildi = False
            for anahtar, grup in kat_gecmis.items():
                if len(grup) < ASGARI_FON:
                    continue
                gecmis_puan = _uretim_puanlari(grup, eksen, agirliklar)
                if eksen == "risk":
                    ileri_grup = kat_ileri.get(anahtar) or {}
                    if len(ileri_grup) < ASGARI_FON:
                        continue
                    ileri_puan = _uretim_puanlari(
                        ileri_grup, eksen, agirliklar)
                else:
                    ileri_puan = ileri_getiri

                cift = [(gecmis_puan[f], ileri_puan[f])
                        for f in gecmis_puan if f in ileri_puan]
                if len(cift) < ASGARI_FON:
                    continue
                kullanildi = True

                ro = _spearman(cift)
                if ro is not None:
                    ro_list.append(ro)
                k = max(1, len(cift) // DILIM)
                ust = _dilim_ortalamasi(sorted(cift, key=lambda c: -c[0]), k)
                alt = _dilim_ortalamasi(sorted(cift, key=lambda c: c[0]), k)
                if ust is not None:
                    ust_list.append(ust)
                if alt is not None:
                    alt_list.append(alt)
            if kullanildi:
                baslangic_sayisi += 1

        if not ro_list:
            continue
        sonuc[ufuk] = {
            "spearman": round(sum(ro_list) / len(ro_list), 3),
            "ust_dilim": round(sum(ust_list) / len(ust_list), 2),
            "alt_dilim": round(sum(alt_list) / len(alt_list), 2),
            "olcum_sayisi": len(ro_list),
            "baslangic_sayisi": baslangic_sayisi,
            "ortusmeyen_baslangic": max(
                1, -(-baslangic_sayisi // max(1, -(-ufuk // ADIM)))
            ) if baslangic_sayisi else 0,
            # Ileri sonucun BIRIMI. Getiri ekseninde yuzde, risk
            # ekseninde puan — dilim sayilarini okurken sart.
            "birim": "yuzde" if eksen != "risk" else "puan",
        }
    return sonuc


def yorumla(getiri_gucu: dict, vol_gucu: dict,
            istikrar_gucu: dict | None = None,
            uretim_getiri: dict | None = None,
            uretim_risk: dict | None = None) -> dict:
    """Olcumleri kullaniciya soylenecek cumleye cevirir.

    `uretim_getiri` / `uretim_risk` verilirse BASLIK ONLARDAN yazilir:
    ekranda gosterilen puanin olcumu odur. Ham olcumler (getiri_gucu /
    vol_gucu) yine JSON'a giriyor ama artik karsilastirma icin.
    """
    if not getiri_gucu and not uretim_getiri:
        return {"durum": "olculemedi",
                "ozet": "Öngörü gücü ölçülemedi (yeterli geçmiş yok)."}

    # 3 aylik ufuk temsili alinir: ne cok kisa ne cok uzun.
    ham_g = (getiri_gucu or {}).get(63) or (
        list(getiri_gucu.values())[0] if getiri_gucu else None)
    # BASLIK YAYIMLANAN PUANIN OLCUMUDUR; yoksa hama duser.
    g = (uretim_getiri or {}).get(63) or ham_g
    v = (uretim_risk or {}).get(63) or (vol_gucu or {}).get(63)
    uretim_olculdu = bool((uretim_getiri or {}).get(63))

    fark = g["ust_dilim"] - g["alt_dilim"]
    # TEK BASLANGIC "CALISIYOR" DEMEK ICIN YETMEZ.
    #
    # Kosul yalnizca korelasyon ve dilim farkiydi; iki ortusmeyen
    # baslangici olmayan bir olcum de "calisiyor" diyebiliyordu. Bir
    # tek donemde gorulen iliski, farkli piyasa rejimlerinde surdugunu
    # gostermez — oynaklik metninde zaten uygulanan kural burada da
    # gecerli olmali.
    yeter = g.get("ortusmeyen_baslangic", 0) >= 2
    calisiyor = g["spearman"] >= 0.20 and fark > 1.0 and yeter

    hangi = ("uygulamada gösterilen getiri puanına"
             if uretim_olculdu else "geçmiş getiriye")
    ozet = (
        "ÖLÇÜLDÜ: %s göre sıralama geleceği tutmuyor. "
        "Üç ay sonrasına bakıldığında üst %%20'lik dilimin getirisi "
        "%%%.1f, alt %%20'lik dilimin %%%.1f — aradaki fark %+.1f puan. "
        "Sıra korelasyonu %.2f (0 = hiç bilgi yok)."
        % (hangi, g["ust_dilim"], g["alt_dilim"], fark, g["spearman"])
    ) if not calisiyor else (
        "ÖLÇÜLDÜ: %s göre sıralamanın bir miktar öngörü "
        "gücü var. Üst %%20 dilim %%%.1f, alt %%20 dilim %%%.1f getirdi "
        "(sıra korelasyonu %.2f)."
        % (hangi, g["ust_dilim"], g["alt_dilim"], g["spearman"])
    )

    # OLCULEN ILE YAYIMLANAN AYNI MI — acikca soylenir.
    if uretim_olculdu and ham_g:
        ozet += (
            " (Aynı dönemde ham üç aylık getiri sıralamasının korelasyonu "
            "%.2f; ekrandaki puan bileşik olduğu için ayrı ölçülüyor.)"
            % ham_g["spearman"])

    if v:
        # METIN KENDI SAYISINI KONTROL ETMELI.
        #
        # Bu cumle bir donem KOSULSUZ yaziliyordu: veri varsa "OYNAKLIK
        # kalici" deniyordu. Sinandi ve gerceklesti — korelasyon -0,90 ve
        # olcum sayisi 1 verildiginde metin yine kalicilik iddia ediyordu.
        # Yani ekrana bastigi sayiyla celisen bir cumle uretiyordu.
        oyn = v["spearman"]
        yeter = v.get("ortusmeyen_baslangic", 0) >= 2
        # NEYIN KALICI OLDUGU DOGRU ADLANDIRILMALI. Uretim olcumu varsa
        # sinanan sey ekrandaki SAKINLIK puani (%60 oynaklik + %40
        # maksimum dusus); yoksa yalnizca ham oynaklik. Ikisini ayni
        # cumleyle anlatmak, sinanmamis bir bilesim icin kalicilik
        # iddia etmek olurdu.
        ad = "SAKİNLİK puanı" if (uretim_risk or {}).get(63) else "OYNAKLIK"
        if oyn >= KALICI_ESIK and yeter:
            ozet += (
                " Buna karşılık %s kalıcı: sıra korelasyonu %.2f. "
                "Yani \"bu fon sakin\" demek geleceğe dair gerçek bir "
                "ifade, \"bu fon geçen ay iyi getirdi\" değil."
                % (ad, oyn))
        elif oyn >= KALICI_ESIK:
            ozet += (
                " %s için sıra korelasyonu %.2f gibi yüksek çıktı ama "
                "örtüşmeyen tahmin başlangıcı sayısı %d; bu ilişkinin "
                "farklı piyasa dönemlerinde de sürdüğü bu veriyle "
                "gösterilemez."
                % (ad, oyn, v.get("ortusmeyen_baslangic", 0)))
        elif oyn <= -KALICI_ESIK:
            ozet += (
                " %s için sıra korelasyonu %.2f, yani TERS yönlü: "
                "geçmişte sakin olan sonraki dönemde oynak çıkmış. Bu "
                "beklenmeyen bir sonuç; veri veya ölçüm kontrol "
                "edilmeli." % (ad, oyn))
        else:
            ozet += (
                " %s için sıra korelasyonu %.2f; bu veriyle kalıcı "
                "bir ilişki gösterilemedi." % (ad, oyn))

    # ISTIKRAR: "duzenli olarak akranlarini gecmek" AYRI bir sorudur ve
    # akilli filtre buna dayaniyor. Olculdu: 3 ayda 0,09 (ust dilim alt
    # dilimden KOTU), 6 ayda 0,17 ama yalnizca 20 olcum noktasiyla.
    # Ham getiriden biraz iyi, guvenilir bir sinyal degil.
    i = (istikrar_gucu or {}).get(126) or (istikrar_gucu or {}).get(63)
    if i:
        ozet += (
            " İSTİKRAR (düzenli olarak akranlarını geçmek) ayrı ölçüldü: "
            "sıra korelasyonu %.2f, üst %%20 dilim %%%.1f, alt %%20 dilim "
            "%%%.1f. Bu hesap %d kategori-tarih hücresinden geliyor ama "
            "yalnızca %d tahmin başlangıcı var (örtüşmeyen: %d); bu "
            "kadar kısa veriyle güvenilir bir sonuç çıkarılamaz."
            % (i["spearman"], i["ust_dilim"], i["alt_dilim"],
               i["olcum_sayisi"], i.get("baslangic_sayisi", 0),
               i.get("ortusmeyen_baslangic", 0))
        )

    return {
        "durum": "calisiyor" if calisiyor else "calismiyor",
        "ozet": ozet,
        # HAM olcumler: 63 gunluk getiri / oynaklik siralamasi. Artik
        # baslik bunlardan yazilmiyor, karsilastirma icin duruyorlar.
        "getiri": getiri_gucu or {},
        "volatilite": vol_gucu or {},
        "istikrar": istikrar_gucu or {},
        # UYGULAMADA GOSTERILEN puanlarin olcumu. Baslik bunlardan
        # yaziliyor (bkz. olc_uretim).
        "uretim_getiri": uretim_getiri or {},
        "uretim_risk": uretim_risk or {},
    }


def istikrar_olc(seriler: dict, kategoriler: dict) -> dict:
    """ISTIKRARIN ongoru gucu: duzenli olarak akranlarini gecen, gecmeye
    devam ediyor mu?

    Getiri SEVIYESI tutmuyor (Spearman ~0,05) ama "duzenli ustunluk" AYRI
    bir sorudur ve ayri sinanmali. Akilli filtre bu olcute dayaniyor.

    Olculdu: 3 ayda 0,11 (ust dilim alt dilimden KOTU), 6 ayda 0,19
    (ust dilim biraz iyi, ama yalnizca 20 olcum noktasi). Yani ham
    getiriden biraz iyi, ama guvenilir bir sinyal degil.
    """
    tarihler = sorted({t for s in seriler.values() for t in s})
    gecmis = 126        # istikrar icin daha uzun pencere gerekir
    sonuc = {}

    def aylik(f, i0, i1):
        """{donem_no: getiri} — DONEM NUMARASI KORUNUR.

        Once duz bir liste donuyordu ve eksik donemler listeden
        DUSUYORDU; ardindan `enumerate` kalanlari 0,1,2... diye yeniden
        numaraliyordu. Sonuc: bir fonun 2. donemi, akranlarinin 1. donem
        medyaniyla karsilastirilabiliyordu.

        Sinandi: fiyatlari ayni olan 20 fondan yalnizca birinin ilk
        gozlemi kaldirildi. Eksik gozlemli fonun istikrar orani 1,0,
        ayni performanstaki tam verili akraninin 0,0 cikti.

        Artik donem numarasi anahtar olarak tasiniyor; karsilastirma
        liste pozisyonuyla degil GERCEK DONEMLE yapiliyor.
        """
        dilim = tarihler[i0:i1]
        out = {}
        for no, j in enumerate(range(21, len(dilim), 21)):
            a, o = dilim[j], dilim[j - 21]
            if a in f and o in f and f[o] > 0:
                out[no] = f[a] / f[o] - 1
        return out

    for ufuk in (63, 126):
        ro_list, ust_list, alt_list = [], [], []
        # `olc()` ile AYNI muhasebe: olcum sayisi baslangic x kategori
        # oldugu icin tek basina bagimsizligi abartir. Istikrar bloku
        # bir donem bu alanlari HIC uretmiyordu ve yayimlanan JSON'da
        # None kaliyordu; ozet metni de 0 yaziyordu.
        baslangic_sayisi = 0
        for ti in range(gecmis, len(tarihler) - ufuk, ADIM):
            kat_getiri = defaultdict(lambda: defaultdict(list))
            gecmisler = {}
            for fon, f in seriler.items():
                g = aylik(f, ti - gecmis, ti)
                if len(g) < 4:
                    continue
                gecmisler[fon] = g
                for j, v in g.items():
                    kat_getiri[kategoriler.get(fon, ("?", "?"))][j].append(v)

            medyan = {}
            for k, d in kat_getiri.items():
                medyan[k] = {}
                for j, v in d.items():
                    s = sorted(v)
                    medyan[k][j] = s[len(s) // 2]

            gruplar = defaultdict(list)
            for fon, g in gecmisler.items():
                anahtar = kategoriler.get(fon, ("?", "?"))
                ust = sum(1 for j, v in g.items()
                          if medyan[anahtar].get(j) is not None
                          and v > medyan[anahtar][j])
                oran = ust / len(g)
                f = seriler[fon]
                t0, t1 = tarihler[ti], tarihler[ti + ufuk]
                if t0 not in f or t1 not in f or f[t0] <= 0:
                    continue
                gruplar[anahtar].append((oran, (f[t1] / f[t0] - 1) * 100))

            kullanildi = False
            for cift in gruplar.values():
                if len(cift) < ASGARI_FON:
                    continue
                kullanildi = True
                ro = _spearman(cift)
                if ro is not None:
                    ro_list.append(ro)
                k = max(1, len(cift) // DILIM)
                # Istikrar orani AZ SAYIDA olasi deger uretir (ornegin
                # 4 donemde 0, 0,25, 0,5, 0,75, 1) — yani beraberlik
                # kuraldir, istisna degil. Adil dilim burada kritik.
                ust = _dilim_ortalamasi(
                    sorted(cift, key=lambda c: -c[0]), k)
                alt = _dilim_ortalamasi(
                    sorted(cift, key=lambda c: c[0]), k)
                if ust is not None:
                    ust_list.append(ust)
                if alt is not None:
                    alt_list.append(alt)
            if kullanildi:
                baslangic_sayisi += 1

        if ro_list:
            sonuc[ufuk] = {
                "spearman": round(sum(ro_list) / len(ro_list), 3),
                "ust_dilim": round(sum(ust_list) / len(ust_list), 2),
                "alt_dilim": round(sum(alt_list) / len(alt_list), 2),
                "olcum_sayisi": len(ro_list),
                "baslangic_sayisi": baslangic_sayisi,
                "ortusmeyen_baslangic": max(
                    1, -(-baslangic_sayisi // max(1, -(-ufuk // ADIM)))
                ) if baslangic_sayisi else 0,
            }
    return sonuc
