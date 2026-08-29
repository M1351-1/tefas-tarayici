# -*- coding: utf-8 -*-
"""Fon kategorisi belirleme.

Iki kaynak var ve ikisi ESIT DEGIL:

  "api"  : TEFAS'in sfonTurKod filtresinden gelen kategori. Kesin bilgi.
           Sadece YATIRIM fonlarinda (fonTipi=YAT) calisiyor.

  "isim" : Fon adindan cikarim. Emeklilik ve borsa yatirim fonlarinda
           TEFAS kategori filtresini SESSIZCE YOK SAYIP butun fonlari
           donduruyor, yani API'den kategori ogrenmenin yolu yok. Bu
           fonlarin adlari cok duzenli oldugu icin ("... HISSE SENEDI
           EMEKLILIK YATIRIM FONU") addan cikarim guvenilir ama yine de
           bir cikarimdir; JSON'da kaynak alani ile isaretlenir ve
           uygulamada kullaniciya soylenir.

Katilim (faizsiz) olmak bir kategori DEGIL, bir nitelik: "ALTIN KATILIM"
fonu varlik sinifi olarak kiymetli madenlerdir ama katilim esaslidir.
Kategoriyi varlik sinifina gore veriyoruz, katilimi ayri bayrak olarak
tutuyoruz. Boylece hem risk karsilastirmasi dogru grupta yapiliyor hem de
faizsiz fon arayan kullanici hepsini bulabiliyor.
"""
from __future__ import annotations

# Sira ONEMLI: yukaridaki kural once uygular.
# "ALTIN KATILIM" -> Kiymetli Madenler (katilim bayragi ayrica kalkar)
# "HISSE SENEDI YOGUN BORSA YATIRIM" -> Hisse Senedi
KURALLAR = [
    ("PARA PİYASASI", "Para Piyasası"),
    ("FON SEPETİ", "Fon Sepeti"),
    ("ALTIN", "Kıymetli Madenler"),
    ("GÜMÜŞ", "Kıymetli Madenler"),
    ("KIYMETLİ MADEN", "Kıymetli Madenler"),
    ("BORÇLANMA ARAÇLARI", "Borçlanma Araçları"),
    ("HİSSE SENEDİ", "Hisse Senedi"),
    ("ENDEKS", "Hisse Senedi"),
    ("KARMA", "Karma"),
    ("DEĞİŞKEN", "Değişken"),
    # BES'e ozgu iki gercek kategori. "Standart" fon, mevzuatin belirledigi
    # varsayilan BES fonudur (agirlikli olarak kamu borclanma). "Yasam
    # dongusu" hedef tarihli fondur, dagilimi yasa gore kayar. Ikisi de
    # kendi icinde karsilastirilabilir gruplar olusturur; KATILIM'dan once
    # bakiyoruz cunku "OKS Katilim Standart" gibi adlarda dagilim profili
    # katilim niteliginden daha belirleyici (katilim ayrica bayrak olarak
    # zaten tutuluyor).
    ("STANDART", "Standart (BES)"),
    ("YAŞAM DÖNGÜSÜ", "Yaşam Döngüsü"),
    ("KATILIM", "Katılım"),
    ("BAŞLANGIÇ", "Para Piyasası"),
    ("KATKI", "Borçlanma Araçları"),
]

# Katilim (faizsiz) niteligi.
KATILIM_ANAHTARLARI = ("KATILIM", "KİRA SERTİFİKA", "FAİZSİZ")

BILINMIYOR = "Bilinmiyor"


def _normalize(ad):
    return (ad or "").upper().replace("İ", "İ")


def katilim_mi(fon_adi):
    """Fon katilim (faizsiz) esasli mi?"""
    a = _normalize(fon_adi)
    return any(k in a for k in KATILIM_ANAHTARLARI)


def isimden_kategori(fon_adi):
    """Fon adindan kategori cikarir. Eslesmezse None."""
    a = _normalize(fon_adi)
    for anahtar, kategori in KURALLAR:
        if anahtar in a:
            return kategori
    return None


def kategori_belirle(fon_kodu, fon_adi, api_haritasi):
    """(kategori_ad, kaynak) dondurur.

    api_haritasi: {fon_kodu: (kod, ad)} - sadece YAT fonlari icin dolu.
    """
    api = api_haritasi.get(fon_kodu)
    if api:
        # "Hisse Senedi Semsiye Fonu" -> "Hisse Senedi": semsiye kelimesi
        # kullaniciya bir sey soylemiyor, isimden cikarimla da ayni ada
        # ulasmak istiyoruz ki iki kaynak ayni etiketi uretsin.
        ad = api[1].replace(" Şemsiye Fonu", "").strip()
        return ad, "api"

    isim = isimden_kategori(fon_adi)
    if isim:
        return isim, "isim"
    return BILINMIYOR, "yok"
