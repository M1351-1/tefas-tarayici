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

# Kac ISLEM GUNU geriye bakilacagi. Takvim gunu degil: fon fiyatlaninca
# bir gozlem olusur, tatiller zaten seride yoktur.
PENCERE = {
    "gunluk": 1,
    "haftalik": 5,
    "aylik": 21,
    "uc_aylik": 63,
    "yillik": 252,
}

VOLATILITE_PENCERE = 60      # gunluk getiri sayisi
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


def gunluk_getiriler(seri):
    """Ardisik gozlemler arasi oransal degisimler (yuzde degil, oran)."""
    cikti = []
    for i in range(1, len(seri)):
        onceki = seri[i - 1][1]
        simdiki = seri[i][1]
        if onceki and onceki > 0 and simdiki is not None:
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
    """
    if len(seri) < 2:
        return None
    son = seri[-pencere:] if len(seri) > pencere else seri
    zirve = None
    en_kotu = 0.0
    for _, fiyat in son:
        if fiyat is None or fiyat <= 0:
            continue
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
    m["maks_dusus"] = maks_dusus(seri)
    m["gozlem_sayisi"] = len(seri)
    m["ilk_tarih"] = seri[0][0] if seri else None
    m["son_tarih"] = seri[-1][0] if seri else None
    m["son_fiyat"] = seri[-1][1] if seri else None
    return m
