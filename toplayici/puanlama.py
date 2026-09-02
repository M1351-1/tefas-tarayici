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

# IKI AYRI EKSEN — TEK PUAN DEGIL.
#
# NEDEN AYRILDI (olculdu, varsayilmadi):
#
#   bilesen            ileri Spearman
#   aylik getiri            0,07
#   uc aylik getiri         0,05
#   haftalik getiri         0,07
#   volatilite              0,76   <-- KALICI
#   maksimum dusus          0,57   <-- KALICI
#
# Ust %20 dilimin uc aylik ileri getirisi %8,8, alt %20 dilimin %9,6.
# Yani gecmis getiriye gore siralama gelecegi TUTMUYOR. Oysa oynaklik ve
# dusus guclu bicimde kaliciydi.
#
# Ikisini tek bir "puan"da toplamak, tutmayan bir bileseni tutan bir
# bilesenle harmanlayip ikisini de bulaniklastiriyordu. Ayrica tek puan
# "bu fon iyi" gibi okunuyordu; oysa elde iki AYRI bilgi var:
#
#   GETIRI EKSENI : gecmiste ne oldu. TASVIR. Ongoru iddiasi YOK.
#   RISK EKSENI   : bu fon akranlarina gore ne kadar sakin. KALICI,
#                   yani gelecege dair gercek bir ifade.
#
# Risk ekseni "daha iyi" demek DEGILDIR: hisse fonunda dusuk oynaklik,
# fonun isini yapmamasi da olabilir. Bir PROFIL bildirir, bir yargi degil.

GETIRI_BILESENLERI = ("aylik_getiri", "uc_aylik_getiri", "haftalik_getiri")
RISK_BILESENLERI = ("volatilite", "maks_dusus")

# Getiri ekseni agirliklari ayarlar.json'dan gelir ve kendi icinde
# yeniden normalize edilir (eski toplam 0,80 idi).
# Risk ekseni agirliklari OLCULEN kaliciliga gore: volatilite (0,76)
# dususten (0,57) daha guvenilir bir sinyal.
RISK_AGIRLIKLARI = {"volatilite": 0.6, "maks_dusus": 0.4}

# Puanlanabilmesi icin gereken metrikler. Biri eksikse fon puanlanmaz -
# eksik metrigi sifir saymak, kotu performansi orta performans gibi
# gosterirdi.
GEREKLI = GETIRI_BILESENLERI + ("volatilite",)

# Risk ekseninde AZ olan "daha sakin"dir: z-skoru ters isaretle girer.
TERS = {"volatilite", "maks_dusus"}


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

        # Her eksen KENDI istatistigiyle olculur.
        istatistik = {}
        for metrik in set(GETIRI_BILESENLERI) | set(RISK_BILESENLERI):
            degerler = [f[metrik] for f in grup if f.get(metrik) is not None]
            if len(degerler) >= 2:
                istatistik[metrik] = _ortalama_ve_sapma(degerler)

        # Getiri ekseni agirliklari kendi icinde normalize edilir:
        # ayarlar.json'daki agirliklarin toplami 0,80 idi (kalan 0,20
        # volatiliteye gidiyordu ve o artik ayri eksende).
        getiri_toplam = sum(agirliklar.get(m, 0) for m in GETIRI_BILESENLERI)

        for f in grup:
            g = dict(f)

            def eksen(bilesenler, agirlik_haritasi, normalize):
                """Bir eksenin puanini ve kirilimini uretir."""
                toplam, kirilim, kullanilan = 0.0, {}, 0.0
                for metrik in bilesenler:
                    deger = f.get(metrik)
                    if deger is None or metrik not in istatistik:
                        continue
                    ort, sapma = istatistik[metrik]
                    z = _z(deger, ort, sapma, kirpma)
                    if metrik in TERS:
                        z = -z
                    ham = agirlik_haritasi.get(metrik, 0)
                    agirlik = (ham / normalize) if normalize else 0.0
                    katki = agirlik * z
                    toplam += katki
                    kullanilan += agirlik
                    kirilim[metrik] = {
                        "deger": round(deger, 4),
                        "kategori_ortalamasi": round(ort, 4),
                        "z": round(z, 4),
                        "agirlik": round(agirlik, 4),
                        "katki": round(katki, 4),
                    }
                if kullanilan <= 0:
                    return None, {}
                return round(toplam, 4), kirilim

            getiri_puani, getiri_kirilimi = eksen(
                GETIRI_BILESENLERI, agirliklar, getiri_toplam)
            risk_puani, risk_kirilimi = eksen(
                RISK_BILESENLERI, RISK_AGIRLIKLARI,
                sum(RISK_AGIRLIKLARI.values()))

            # GETIRI EKSENI: gecmisin tasviri, ongoru iddiasi yok.
            g["getiri_puani"] = getiri_puani
            g["getiri_kirilimi"] = getiri_kirilimi
            # RISK EKSENI: akranlarina gore ne kadar sakin. Yuksek = sakin.
            # Bu bir YARGI degil PROFIL: hisse fonunda dusuk oynaklik,
            # fonun isini yapmamasi da olabilir.
            g["risk_puani"] = risk_puani
            g["risk_kirilimi"] = risk_kirilimi

            # `puan` GERIYE UYUMLULUK icin getiri eksenine esitlenir.
            # Yeni kod getiri_puani kullanmali; bu alan "kalite puani"
            # DEGILDIR ve oyle okunmamalidir.
            g["puan"] = getiri_puani
            g["puan_kirilimi"] = getiri_kirilimi
            g["kategori_fon_sayisi"] = len(grup)
            puanlanan.append(g)

    # HER EKSEN ICIN AYRI SIRA. Tek bir "kategori sirasi" iki farkli
    # bilgiyi tek sayiya ezmek olurdu; kullanici hangi eksende baktigini
    # bilerek secmeli.
    for (tip, kategori) in gruplar:
        alt = [f for f in puanlanan
               if f.get("fon_tipi") == tip and f.get("kategori_ad") == kategori]

        getirili = [f for f in alt if f.get("getiri_puani") is not None]
        getirili.sort(key=lambda x: x["getiri_puani"], reverse=True)
        for i, f in enumerate(getirili, 1):
            f["getiri_sirasi"] = i
            # Geriye uyumluluk: eski alan getiri sirasini gosterir.
            f["kategori_sirasi"] = i

        riskli = [f for f in alt if f.get("risk_puani") is not None]
        riskli.sort(key=lambda x: x["risk_puani"], reverse=True)
        for i, f in enumerate(riskli, 1):
            f["risk_sirasi"] = i

    puanlanan.sort(key=lambda x: (x.get("fon_tipi", ""),
                                  x.get("kategori_ad", ""),
                                  x.get("getiri_sirasi", 0)))
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
