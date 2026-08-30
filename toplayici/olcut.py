# -*- coding: utf-8 -*-
"""Istikrar, risk-ayarli getiri ve para piyasasi olcutu.

Uc olcu de "bu fon gercekten iyi mi, yoksa sansli mi" sorusuna farkli
aciklardan cevap arar:

  ISTIKRAR      Son 12 ayin kacinda kendi kategorisinin MEDYANINI gecti?
                Tek seferlik siçrama yapan fon 3/12 cikar, istikrarli fon
                10/12. Getiri siralamasi bu ikisini ayirt edemez.

  OLCUT         Para piyasasi fonlarinin medyan yillik getirisi. Turkiye'de
                bu, pratikte risksiz getiridir.

                DIKKAT - VERGI ONCESI. TEFAS fiyatlari stopaj kesilmeden
                once. Olculen ~%60'in yatirimcinin cebine giren karsiligi
                ~%40'tir; aradaki fark satista kesilen stopaj. Uc ayri
                kurucunun fonunda dogrulandi (aylik %3,3-4,6, bilesik
                ~%60) ve konut projesinde kullaniciyla teyit edilen net
                carpani 0,69 ile birebir ortusuyor: 59,9 x 0,69 = 41,3.

                UYGULAMADAKI BUTUN GETIRILER VERGI ONCESIDIR. Fonlar
                birbiriyle tutarli sekilde karsilastirilir ama ekrandaki
                yuzde, elinize gecen para DEGILDIR.

                Neden stopaji modellemiyoruz: oran fon turune gore
                degisiyor (hisse yogun fonlarla borclanma/para piyasasi
                fonlari ayni oranda vergilenmiyor). Tahmini oranlar
                girmek siralamayi gercekten degistirir; dogrulanmamis
                vergi orani yazmaktansa her seyi vergi oncesi tutup
                bunu acikca soylemek dogru.

  RISK-AYARLI   (yillik getiri - olcut) / oynaklik. Yani Sharpe orani.
                Olcutu CIKARMAK sart: cikarmazsak para piyasasi fonlari
                (%60 / %1,6 = 37) her hisse fonunu ezer ve olcu anlamini
                yitirir. Cikarinca dogru soruyu sorar: risksiz alternatifin
                USTUNE, aldigi risk basina ne koydu?
"""
from __future__ import annotations

# Sharpe hesabinda paydanin cok kucuk olmasi orani patlatir. %0,5'in
# altindaki oynaklik pratikte "hic oynamiyor" demektir ve boyle bir fon
# icin risk-ayarli getiri anlamli degildir.
ASGARI_OYNAKLIK = 0.5

# Istikrar icin bakilan ay sayisi.
ISTIKRAR_AY = 12

# Bir ayin sayilabilmesi icin kategoride en az bu kadar fon olmali;
# 3 fonun medyani "kategori ortasi" saymaz.
ASGARI_KATEGORI = 5

# ---------------------------------------------------------------- stopaj
#
# Kullanicinin bildirdigi iki gercek:
#   - Hisse senedi yogun fonlarda stopaj YOK.
#   - Para piyasasi fonlarinda stopaj %17,5.
#
# Bu bir GOSTERIM AYRINTISI DEGIL, siralamayi gercekten degistiren bir
# duzeltmedir: %96 getiren bir hisse fonu %96 net kalirken %60 getiren
# bir PPF %49,5'e duser. Brutle karsilastirmak hisse fonlarini haksiz
# yere geride gosterir.
#
# FON ISLETME GIDERI BURADA DUSULMEZ - zaten dusulmustur. TEFAS'in
# birim pay degeri NAV/pay sayisidir; NAV, fon giderleri gunluk
# tahakkuk ettirildikten SONRAKI degerdir. Bir kez daha dusmek cift
# sayma olur. Stopaj ise fiyata girmez, satista kesilir.
STOPAJ_MUAF = 0.0
STOPAJ_STANDART = 0.175

# Muafiyet fon adina degil PORTFOYE bakar.
#
# "Hisse Senedi" kategorisindeki her fon muaf degildir: AFA'nin
# portfoyunun %98'i YABANCI hisse (yhs), yerli hisse (hs) degil.
# Muafiyet yerli hisse yogunluguna baglidir. Kategori etiketine
# bakarak karar vermek bu fonu yanlislikla vergisiz sayardi.
# Esik: portfoyunun %51'inden fazlasi BIST'te islem goren hisse
# senedinden olusan fonlar "hisse senedi yogun" sayilir ve stopajdan
# muaftir. Kullanici teyit etti (+%50).
#
# Gercek veride 792 fon muaf, 1667 fon stopajli cikiyor. Kategori
# adina bakan bir kural AFA/AFS/AFT/AFV gibi YABANCI hisse fonlarini
# (yerli hisse orani %0) yanlislikla muaf sayardi.
YERLI_HISSE_ALANI = "hs"
YOGUNLUK_ESIGI = 51.0


def stopaj_orani(dagilim_kalemleri):
    """Fonun portfoyune bakarak stopaj oranini belirler.

    dagilim_kalemleri: [(alan_kodu, yuzde), ...] ya da None.

    Doner: (oran, gerekce_metni, yerli_hisse_yuzdesi)

    Dagilim verisi yoksa STANDART oran uygulanir - muafiyeti
    kanitlayamadigimiz fonu vergisiz saymak, getirisini oldugundan
    yuksek gosterirdi.
    """
    if not dagilim_kalemleri:
        return (STOPAJ_STANDART,
                "Portföy dağılımı bilinmiyor; stopajlı varsayıldı.", None)

    yerli = 0.0
    for alan, yuzde in dagilim_kalemleri:
        if alan == YERLI_HISSE_ALANI:
            yerli = float(yuzde)
            break

    if yerli >= YOGUNLUK_ESIGI:
        return (STOPAJ_MUAF,
                "Portföyünün %%%.0f'si yerli hisse senedi; hisse yoğun "
                "fon sayıldığı için stopaj yok." % yerli, yerli)
    return (STOPAJ_STANDART,
            "Yerli hisse oranı %%%.0f, %%%.0f eşiğinin altında; stopaj "
            "uygulanır." % (yerli, YOGUNLUK_ESIGI), yerli)


def net_getiri(vergi_oncesi, stopaj):
    """Stopaj sonrasi getiri.

    Stopaj kazanc uzerinden SATISTA kesilir; gunluk/haftalik fiyat
    hareketine uygulanmaz. Bu yuzden sadece YILLIK getiriye ve olcut
    karsilastirmasina uygulaniyor.
    """
    if vergi_oncesi is None or stopaj is None:
        return None
    return vergi_oncesi * (1.0 - stopaj)


def bilesikten_basite(bilesik_yillik):
    """Bilesik yillik getiriyi Turkiye'de kullanilan BASIT yillik
    gosterime cevirir.

    Bu bir hesap hilesi degil, gercek bir dil farki: bankalar ve fon
    platformlari getiriyi basit yillik olarak yazar (aylik x 12), fiyat
    verisinden olculen ise bilesiktir. Ayni fon icin %56 (bilesik) ve
    %45 (basit) ayni anda dogru olabilir. Kullaniciya hangisini
    gosterdigimizi soylemezsek "abartiyorsun" demekte haklidir.
    """
    if bilesik_yillik is None:
        return None
    aylik = (1.0 + bilesik_yillik / 100.0) ** (1.0 / 12.0) - 1.0
    return aylik * 12.0 * 100.0


def _ay_ekle(ay, adet=1):
    """'2026-08' + 1 -> '2026-09'"""
    yil, a = int(ay[:4]), int(ay[5:7])
    toplam = (yil * 12 + a - 1) + adet
    return "%04d-%02d" % (toplam // 12, toplam % 12 + 1)


def ay_sonu_fiyatlari(seri):
    """{'2026-08': 1.29, ...} - her takvim ayinin son gozlemi.

    seri (tarih, fiyat) ciftleri, eskiden yeniye sirali.
    """
    aylar = {}
    for tarih, fiyat in seri:
        if fiyat is not None and fiyat > 0:
            aylar[tarih[:7]] = fiyat  # sirali oldugu icin son yazan kalir
    return aylar


def aylik_getiriler(seri, azami_ay=ISTIKRAR_AY):
    """Son `azami_ay` ayin aylik yuzde getirileri: {'2026-08': 4.3, ...}

    ARDISIK OLMAYAN aylar atlanir. Fon bir ay fiyatlanmamissa, iki aylik
    degisimi "aylik getiri" diye kaydetmek o ayi olduğundan iyi gosterir.
    """
    aylar = ay_sonu_fiyatlari(seri)
    anahtarlar = sorted(aylar)
    getiriler = {}
    for i in range(1, len(anahtarlar)):
        onceki, simdiki = anahtarlar[i - 1], anahtarlar[i]
        if _ay_ekle(onceki) != simdiki:
            continue
        p0 = aylar[onceki]
        if p0 and p0 > 0:
            getiriler[simdiki] = (aylar[simdiki] / p0 - 1.0) * 100.0
    son = sorted(getiriler)[-azami_ay:]
    return {a: getiriler[a] for a in son}


def medyan(degerler):
    n = len(degerler)
    if n == 0:
        return None
    s = sorted(degerler)
    orta = n // 2
    return s[orta] if n % 2 else (s[orta - 1] + s[orta]) / 2.0


def kategori_medyanlari(fonlar):
    """Her (tip, kategori, ay) icin medyan aylik getiri.

    fonlar: her biri 'fon_tipi', 'kategori_ad' ve 'aylik_getiriler'
            iceren sozlukler.
    Doner: {(tip, kategori): {ay: medyan}}
    """
    kova = {}
    for f in fonlar:
        anahtar = (f.get("fon_tipi"), f.get("kategori_ad"))
        for ay, g in (f.get("aylik_getiriler") or {}).items():
            kova.setdefault(anahtar, {}).setdefault(ay, []).append(g)

    cikti = {}
    for anahtar, aylar in kova.items():
        cikti[anahtar] = {
            ay: medyan(degerler)
            for ay, degerler in aylar.items()
            if len(degerler) >= ASGARI_KATEGORI
        }
    return cikti


def istikrar(fon, medyanlar):
    """(ustunde_kalan_ay, degerlendirilen_ay) ya da None.

    Sadece kategori medyaninin hesaplanabildigi aylar sayilir.
    """
    anahtar = (fon.get("fon_tipi"), fon.get("kategori_ad"))
    kategori = medyanlar.get(anahtar) or {}
    kendi = fon.get("aylik_getiriler") or {}

    ustunde = 0
    toplam = 0
    for ay, g in kendi.items():
        m = kategori.get(ay)
        if m is None:
            continue
        toplam += 1
        if g > m:
            ustunde += 1
    return (ustunde, toplam) if toplam else None


def para_piyasasi_olcutu(fonlar):
    """Para piyasasi fonlarinin medyan yillik getirisi (%), VERGI ONCESI.

    Turkiye'de pratik risksiz getiri budur. Sadece YATIRIM fonlarina
    bakiyoruz: emeklilik fonlarinin masraf yapisi farkli, olcut olmaz.

    Donen sayi vergi oncesidir (bkz. modul basligi). Elinize gecen
    yaklasik degeri icin NET_CARPANI kullanin.
    """
    degerler = [
        f["yillik_getiri"] for f in fonlar
        if f.get("kategori_ad") == "Para Piyasası"
        and f.get("fon_tipi") == "YAT"
        and f.get("yillik_getiri") is not None
    ]
    if len(degerler) < ASGARI_KATEGORI:
        return None, 0
    return medyan(degerler), len(degerler)


def risk_ayarli(yillik_getiri, oynaklik, olcut):
    """(yillik - olcut) / oynaklik. Sharpe orani.

    None doner: veri eksikse ya da oynaklik anlamli olmayacak kadar
    kucukse (bkz. ASGARI_OYNAKLIK).
    """
    if yillik_getiri is None or oynaklik is None or olcut is None:
        return None
    if oynaklik < ASGARI_OYNAKLIK:
        return None
    return (yillik_getiri - olcut) / oynaklik
