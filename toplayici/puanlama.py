# -*- coding: utf-8 -*-
"""Kategori ici z-skor puanlamasi.

Kara kutu bir "al bunu" tavsiyesi degil: her fonun puani, hangi bilesenden
ne kadar geldigi ile birlikte disari yazilir; ekranda "neden ust sirada"
gosterilebilir.

Iki tasarim karari:

1. Puanlama KATEGORI ICINDE yapilir. Para piyasasi fonu ile hisse fonunu
   ayni listede yaristirmak anlamsiz: biri %40 volatiliteyle %80 getirir,
   digeri %1 volatiliteyle %45. Ayni cetvelle olculemezler.

2. Ayrica FON TIPI ICINDE yapilir (yatirim / emeklilik / borsa yatirim).
   Emeklilik fonlarinin masraf ve vergi yapisi farklidir; ayni kategorinin
   emeklilik ve yatirim versiyonu ayni sutunda yarismamalidir.
"""
from __future__ import annotations

import math

# Puanlanabilmesi icin gereken metrikler. Biri eksikse fon puanlanmaz -
# eksik metrigi sifir saymak, kotu performansi orta performans gibi
# gosterirdi.
GEREKLI = ("aylik_getiri", "uc_aylik_getiri", "haftalik_getiri", "volatilite")

# Volatilite tek "az iyidir" metrigi: z-skoru ters isaretle girer.
TERS = {"volatilite"}


def _ortalama_ve_sapma(degerler):
    n = len(degerler)
    if n < 2:
        return (degerler[0] if n else 0.0), 0.0
    ort = sum(degerler) / n
    var = sum((x - ort) ** 2 for x in degerler) / (n - 1)
    return ort, math.sqrt(var)


def _z(x, ort, sapma, kirpma):
    """Standart skor. Sapma sifirsa (hepsi ayni) herkes 0 alir.

    Kirpma neden gerekli: tek bir ucuk fon (ornegin serbest fonda %900
    aylik getiri) standart sapmayi sisirir ve digerlerinin z-skorunu
    sifira ezer. Kirpmadan siralama tek fonun rehinesi olur.
    """
    if sapma <= 0:
        return 0.0
    z = (x - ort) / sapma
    return max(-kirpma, min(kirpma, z))


def ele(fonlar, ayarlar):
    """Puanlanamayacak fonlari ayirir.

    Doner: (uygun, elenen) - elenen listesinde her fona 'eleme_nedeni' eklenir.
    """
    asgari_gecmis = ayarlar["asgari_gecmis_gun"]
    asgari_buyukluk = ayarlar["asgari_fon_buyuklugu"]
    uygun, elenen = [], []
    for f in fonlar:
        neden = None
        if f.get("gozlem_sayisi", 0) < asgari_gecmis:
            neden = "yeterli gecmis yok (%d gun, en az %d gerekli)" % (
                f.get("gozlem_sayisi", 0), asgari_gecmis)
        elif any(f.get(m) is None for m in GEREKLI):
            eksik = [m for m in GEREKLI if f.get(m) is None]
            neden = "metrik hesaplanamadi: " + ", ".join(eksik)
        elif f.get("portfoy_buyukluk") is None:
            neden = "fon buyuklugu bilinmiyor"
        elif f["portfoy_buyukluk"] < asgari_buyukluk:
            neden = "fon cok kucuk (%.0f TL, en az %.0f TL)" % (
                f["portfoy_buyukluk"], asgari_buyukluk)
        if neden:
            g = dict(f)
            g["eleme_nedeni"] = neden
            elenen.append(g)
        else:
            uygun.append(dict(f))
    return uygun, elenen


def puanla(fonlar, ayarlar):
    """Fonlari kategori icinde puanlar.

    Girdi fonlarinda su alanlar beklenir: fon_tipi, kategori_ad,
    ve GEREKLI metrikler.

    Doner: (puanlanan, puanlanmayan)
    """
    agirliklar = ayarlar["agirliklar"]
    kirpma = ayarlar["z_kirpma"]
    asgari_adet = ayarlar["asgari_kategori_fon_sayisi"]

    gruplar = {}
    for f in fonlar:
        anahtar = (f.get("fon_tipi", "?"), f.get("kategori_ad", "Bilinmiyor"))
        gruplar.setdefault(anahtar, []).append(f)

    puanlanan, puanlanmayan = [], []

    for (tip, kategori), grup in gruplar.items():
        if len(grup) < asgari_adet:
            # Z-skor "ortalamadan kac standart sapma" demektir. 4 fonluk bir
            # kategoride ortalama da sapma da anlamsizdir; puan uretmek
            # bilimsel gorunumlu curuk sayi uretmek olur.
            for f in grup:
                g = dict(f)
                g["puan"] = None
                g["puanlanmama_nedeni"] = (
                    "kategoride sadece %d fon var, saglikli karsilastirma "
                    "icin en az %d gerekiyor" % (len(grup), asgari_adet))
                puanlanmayan.append(g)
            continue

        istatistik = {}
        for metrik in GEREKLI:
            degerler = [f[metrik] for f in grup]
            istatistik[metrik] = _ortalama_ve_sapma(degerler)

        for f in grup:
            g = dict(f)
            kirilim = {}
            toplam = 0.0
            for metrik in GEREKLI:
                ort, sapma = istatistik[metrik]
                z = _z(f[metrik], ort, sapma, kirpma)
                if metrik in TERS:
                    z = -z
                agirlik = agirliklar[metrik]
                katki = agirlik * z
                toplam += katki
                kirilim[metrik] = {
                    "deger": round(f[metrik], 4),
                    "kategori_ortalamasi": round(ort, 4),
                    "z": round(z, 4),
                    "agirlik": agirlik,
                    "katki": round(katki, 4),
                }
            g["puan"] = round(toplam, 4)
            g["puan_kirilimi"] = kirilim
            g["kategori_fon_sayisi"] = len(grup)
            puanlanan.append(g)

    # Kategori icinde sirala ve sira numarasi ver.
    for (tip, kategori) in gruplar:
        alt = [f for f in puanlanan
               if f.get("fon_tipi") == tip and f.get("kategori_ad") == kategori]
        alt.sort(key=lambda x: x["puan"], reverse=True)
        for i, f in enumerate(alt, 1):
            f["kategori_sirasi"] = i

    puanlanan.sort(key=lambda x: (x.get("fon_tipi", ""),
                                  x.get("kategori_ad", ""),
                                  x.get("kategori_sirasi", 0)))
    return puanlanan, puanlanmayan


def agirlik_kontrolu(ayarlar):
    """Agirliklarin toplami 1 degilse uyar.

    Toplam 1 olmak zorunda degil ama olmadiginda puanlar kategoriler arasi
    karsilastirilamaz hale gelir; sessizce gecmek yerine soyleyelim.
    """
    toplam = sum(ayarlar["agirliklar"].values())
    eksik = set(GEREKLI) - set(ayarlar["agirliklar"])
    fazla = set(ayarlar["agirliklar"]) - set(GEREKLI)
    sorunlar = []
    if abs(toplam - 1.0) > 1e-9:
        sorunlar.append("agirliklar toplami %.4f, 1.0 olmali" % toplam)
    if eksik:
        sorunlar.append("eksik agirlik: " + ", ".join(sorted(eksik)))
    if fazla:
        sorunlar.append("taninmayan agirlik: " + ", ".join(sorted(fazla)))
    return sorunlar
