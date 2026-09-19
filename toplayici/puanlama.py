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

# Risk ekseninde z-skoru TERS isaretle girecek metrikler.
#
# ISARET TUZAGI — bu kume genisletilirken dikkat. "Riskte az olan
# sakindir" kurali her metrige ayni sekilde uygulanamaz, cunku metrikler
# FARKLI ISARETLE saklaniyor:
#
#   volatilite  POZITIF saklanir (3,0 gibi). Az olan sakindir  -> TERS.
#   maks_dusus  NEGATIF saklanir (-5,0 / -80,0). Sifira yakin olan
#               sakindir, yani BUYUK olan sakindir  -> TERS DEGIL.
#
# `maks_dusus` bir donem bu kumedeydi ve sonuc tam tersine donuyordu:
# -%80 dusmus fon, -%5 dusmusten DAHA SAKIN puanlaniyordu. Olculdu
# (2026-09-11 yayimlanan veri, 2302 fon): maks dususu -%50'den kotu olan
# 112 fonun ortalama sakinlik puani +0,065; -%5'ten iyi olan 1169 fonun
# +0,044. "En sakin 10" listesinde -%80, -%83, -%89 dusmus fonlar vardi.
#
# Onemi: bu, uygulamanin OLCULEREK GUVENILIR BULUNAN tek ekseni
# (siralamanin ileri Spearman'i 0,71) ve agirliginin %40'i ters yone
# bakiyordu. Gerileme testi: test_puanlama.py::test_maks_dusus_isareti.
TERS = {"volatilite"}


def gecerli(x):
    """Sayi puanlamaya girebilir mi.

    `is not None` YETMEZ. NaN ve sonsuz da "deger var" gibi gecer ve
    bulastiklari her yeri bozar:

      * `ele()` fonu elemez,
      * kategori ortalamasi ve sapmasi NaN olur,
      * `_z` icinde `sapma <= 0` karsilastirmasi NaN ile False dondugu
        icin bolme yapilir ve `min(kirpma, nan)` Python'da `kirpma`
        dondurur — yani KATEGORIDEKI HERKES +kirpma alir.

    Olculdu (10 fonluk kategori, birinin aylik getirisi NaN): kalan
    dokuz fonun aylik z-skoru sirasiyla -1,49..+1,49 olmasi gerekirken
    HEPSI +3,0 cikti. Bilesen tumuyle bilgisizlesti; fonun kendi
    degerinin bozuk olmasi yetmiyor, TEK bir bozuk sayi butun
    kategoriyi ayni puana esitliyor.

    Bu yuzden gecerlilik tek noktada degil, zincirin her halkasinda
    (eleme -> kategori istatistigi -> z -> JSON yazimi) sorulur.
    """
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


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

    GECERSIZ SAYI EN IYI PUANI ALMAMALI.
    ====================================

    Sonluluk kontrolu yoktu ve NaN/sonsuz deger EN YUKSEK z'yi aliyordu:
    `(nan - ort) / sapma` -> nan, sonra `min(kirpma, nan)` Python'da
    `kirpma` donduruyor (karsilastirma False oldugu icin). Yani
    `_z(nan, 0, 1, 3)` = **+3**. Bozuk veriyle gelen bir fon, kategorisinin
    en iyisi gibi puanlaniyordu.

    KATEGORI ISTATISTIGI DE DENETLENIR. Once yalnizca `x` bakiliyordu;
    ama `ort`/`sapma` NaN ise `sapma <= 0` False donuyor ve bolme
    yapiliyordu. Bu durumda fonun kendi degeri saglam olsa bile z
    anlamsizdir — bileseni hic saymamak dogrusu.
    """
    if not gecerli(x) or not gecerli(ort) or not gecerli(sapma):
        return None
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
        elif any(not gecerli(f.get(m)) for m in GEREKLI):
            # `is None` degil `gecerli` — NaN/sonsuz da hesaplanamamis
            # sayilir, yoksa fon elenmeden gecip kategori istatistigini
            # bozuyor (bkz. gecerli()).
            eksik = [m for m in GEREKLI if not gecerli(f.get(m))]
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
            # GECERSIZ SAYI KATEGORI ISTATISTIGINE GIRMEMELI. Tek bir
            # NaN ortalamayi ve sapmayi NaN yapar; sonrasinda kategorinin
            # butun fonlari ayni z'yi alir.
            degerler = [f[metrik] for f in grup if gecerli(f.get(metrik))]
            if len(degerler) >= 2:
                istatistik[metrik] = _ortalama_ve_sapma(degerler)

        # Getiri ekseni agirliklari kendi icinde normalize edilir:
        # ayarlar.json'daki agirliklarin toplami 0,80 idi (kalan 0,20
        # volatiliteye gidiyordu ve o artik ayri eksende).
        getiri_toplam = sum(agirliklar.get(m, 0) for m in GETIRI_BILESENLERI)

        for f in grup:
            g = dict(f)

            def eksen(bilesenler, agirlik_haritasi, normalize):
                """Bir eksenin puanini ve kirilimini uretir.

                EKSIK BILESEN PUANI KUCULTMEMELI.
                =================================

                Once `toplam` dogrudan donuyordu. Bileseni eksik olan fon
                bu yuzden sistematik olarak SIFIRA yakin puan aliyordu:
                maksimum dususu hesaplanamayan bir fonun risk puani
                yalnizca oynakliktan geliyor, yani buyuklugu %60'a
                sikisiyordu. Eksik veri, "ortalama risk" gibi gorunuyordu.

                Artik kullanilan agirliga bolunuyor. Butun bilesenler
                varken `kullanilan` 1,0 oldugu icin tam kayitlarda sonuc
                DEGISMEZ; yalnizca eksik kayitlar duzelir.

                Ayrica `_z` gecersiz sayida None donuyor; o bilesen hic
                sayilmaz (once NaN en yuksek puani aliyordu).
                """
                toplam, ham_kirilim, kullanilan = 0.0, {}, 0.0
                for metrik in bilesenler:
                    deger = f.get(metrik)
                    if not gecerli(deger) or metrik not in istatistik:
                        continue
                    ort, sapma = istatistik[metrik]
                    z = _z(deger, ort, sapma, kirpma)
                    if z is None:
                        continue
                    if metrik in TERS:
                        z = -z
                    ham = agirlik_haritasi.get(metrik, 0)
                    agirlik = (ham / normalize) if normalize else 0.0
                    toplam += agirlik * z
                    kullanilan += agirlik
                    ham_kirilim[metrik] = (deger, ort, z, agirlik)
                if kullanilan <= 0:
                    return None, {}

                # KATKILAR DA YENIDEN NORMALIZE EDILMELI.
                #
                # Puan `toplam / kullanilan` olarak doner ama kirilimdeki
                # `agirlik`/`katki` ham agirliktan yaziliyordu. Bileseni
                # eksik bir fonda ikisi tutmuyordu: maksimum dususu
                # olmayan bir fonun risk puani 1,4863 iken katkilarinin
                # toplami 0,8918 idi (0,6 agirlikla). Ekranda "neden ust
                # sirada" dokumu puani aciklamiyordu.
                #
                # Artik bolen katkilara da uygulaniyor; butun bilesenler
                # varken `kullanilan` 1,0 oldugu icin tam kayitlarda
                # hicbir sey degismez.
                kirilim = {
                    metrik: {
                        "deger": round(deger, 4),
                        "kategori_ortalamasi": round(ort, 4),
                        "z": round(z, 4),
                        "agirlik": round(agirlik / kullanilan, 4),
                        "katki": round(agirlik * z / kullanilan, 4),
                    }
                    for metrik, (deger, ort, z, agirlik)
                    in ham_kirilim.items()
                }
                return round(toplam / kullanilan, 4), kirilim

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
            # HANGI BILESEN EKSIK KALDI.
            #
            # Yeniden normalize etmek olcegi duzeltir ama belirsizligi yok
            # etmez: tek bilesenden uretilen puan daha az bilgiyle
            # kurulmustur. Arayuz bunu isaretleyebilsin diye disari
            # yaziliyor; eksik bilesenli puan tam puanla ayni sutunda
            # kayitsizca kiyaslanmamali.
            g["risk_eksik_bilesen"] = [
                m for m in RISK_BILESENLERI if m not in (risk_kirilimi or {})]

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
