# -*- coding: utf-8 -*-
"""Kategori belirleme testleri. Gercek fon adlariyla calisir."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import kategoriler as k


# ------------------------------------------------------------ isimden cikarim

def test_emeklilik_hisse_senedi():
    assert k.isimden_kategori(
        "AGESA HAYAT VE EMEKLİLİK A.Ş. HİSSE SENEDİ EMEKLİLİK YATIRIM FONU"
    ) == "Hisse Senedi"


def test_emeklilik_borclanma():
    assert k.isimden_kategori(
        "AGESA HAYAT VE EMEKLİLİK A.Ş. BORÇLANMA ARAÇLARI EMEKLİLİK YATIRIM FONU"
    ) == "Borçlanma Araçları"


def test_emeklilik_para_piyasasi():
    assert k.isimden_kategori(
        "AGESA HAYAT VE EMEKLİLİK A.Ş. BİRİNCİ PARA PİYASASI EMEKLİLİK YATIRIM FONU"
    ) == "Para Piyasası"


def test_emeklilik_fon_sepeti():
    assert k.isimden_kategori(
        "AGESA HAYAT VE EMEKLİLİK A.Ş. BİRİNCİ FON SEPETİ EMEKLİLİK YATIRIM FONU"
    ) == "Fon Sepeti"


def test_altin_kiymetli_madene_gider():
    assert k.isimden_kategori(
        "AGESA HAYAT VE EMEKLİLİK A.Ş. ALTIN EMEKLİLİK YATIRIM FONU"
    ) == "Kıymetli Madenler"


def test_altin_katilim_kategorisi_kiymetli_maden():
    """Varlik sinifi kategoriyi belirler, katilim ayri bayraktir.

    'ALTIN KATILIM' fonunun riski altin riskidir; Katilim kategorisine
    koyup para piyasasi katilim fonlariyla yaristirmak yanlis olur.
    """
    ad = "AGESA HAYAT VE EMEKLİLİK A.Ş. ALTIN KATILIM EMEKLİLİK YATIRIM FONU"
    assert k.isimden_kategori(ad) == "Kıymetli Madenler"
    assert k.katilim_mi(ad) is True


def test_gumus_kiymetli_madene_gider():
    assert k.isimden_kategori(
        "QNB PORTFÖY GÜMÜŞ KATILIM BORSA YATIRIM FONU") == "Kıymetli Madenler"


def test_endeks_fonu_hisse_senedi_sayilir():
    assert k.isimden_kategori(
        "AK PORTFÖY BIST 30 ENDEKSİ HİSSE SENEDİ YOĞUN BORSA YATIRIM FONU"
    ) == "Hisse Senedi"


def test_tlref_endeksi_hisse_senedi_sayilir():
    # TLREF endeksi aslinda para piyasasi benzeri; ENDEKS anahtari
    # yakaliyor. Bu bilincli bir sadelestirme.
    assert k.isimden_kategori(
        "NUROL PORTFÖY BIST TLREF ENDEKSİ (TL) BORSA YATIRIM FONU"
    ) == "Hisse Senedi"


def test_baslangic_fonu_para_piyasasi():
    assert k.isimden_kategori(
        "AGESA HAYAT VE EMEKLİLİK A.Ş. BAŞLANGIÇ EMEKLİLİK YATIRIM FONU"
    ) == "Para Piyasası"


def test_eslesmezse_none():
    assert k.isimden_kategori("TAMAMEN ALAKASIZ BIR FON ADI") is None


def test_bos_ad_cokmez():
    assert k.isimden_kategori("") is None
    assert k.isimden_kategori(None) is None


# ------------------------------------------------------------------- katilim

def test_katilim_bayragi():
    assert k.katilim_mi("AK PORTFÖY ALTIN KATILIM BORSA YATIRIM FONU") is True


def test_katilim_olmayan():
    assert k.katilim_mi("AK PORTFÖY BIST 30 ENDEKSİ HİSSE SENEDİ FONU") is False


def test_kira_sertifikasi_katilim_sayilir():
    assert k.katilim_mi("X PORTFÖY KİRA SERTİFİKALARI FONU") is True


# --------------------------------------------------------- kaynak ayrimi

def test_api_kategorisi_oncelikli():
    harita = {"AAA": (104, "Hisse Senedi Şemsiye Fonu")}
    ad, kaynak = k.kategori_belirle("AAA", "HERHANGİ BİR PARA PİYASASI FONU",
                                    harita)
    # API bilgisi varken isme bakilmaz.
    assert ad == "Hisse Senedi"
    assert kaynak == "api"


def test_semsiye_kelimesi_temizlenir():
    harita = {"AAA": (107, "Para Piyasası Şemsiye Fonu")}
    ad, _ = k.kategori_belirle("AAA", "", harita)
    assert ad == "Para Piyasası"


def test_api_yoksa_isimden():
    ad, kaynak = k.kategori_belirle(
        "BBB", "X EMEKLİLİK HİSSE SENEDİ EMEKLİLİK YATIRIM FONU", {})
    assert ad == "Hisse Senedi"
    assert kaynak == "isim"


def test_hicbiri_yoksa_bilinmiyor():
    ad, kaynak = k.kategori_belirle("CCC", "ALAKASIZ", {})
    assert ad == k.BILINMIYOR
    assert kaynak == "yok"


def test_iki_kaynak_ayni_etiketi_uretir():
    """API 'Hisse Senedi Şemsiye Fonu' derken isim 'Hisse Senedi' uretiyor.

    Ikisi ayni etikete indirgenmezse ayni kategori uygulamada iki ayri
    satir olarak gorunur ve fonlar iki gruba bolunur.
    """
    api_ad, _ = k.kategori_belirle("A", "", {"A": (104, "Hisse Senedi Şemsiye Fonu")})
    isim_ad, _ = k.kategori_belirle("B", "X HİSSE SENEDİ FONU", {})
    assert api_ad == isim_ad


# ------------------------------------------------------ BES'e ozgu kategoriler

def test_standart_bes_fonu():
    assert k.isimden_kategori(
        "AGESA HAYAT VE EMEKLİLİK A.Ş. STANDART EMEKLİLİK YATIRIM FONU"
    ) == "Standart (BES)"


def test_oks_standart_fonu():
    assert k.isimden_kategori(
        "GARANTİ EMEKLİLİK VE HAYAT A.Ş. OKS STANDART EMEKLİLİK YATIRIM FONU"
    ) == "Standart (BES)"


def test_yasam_dongusu_fonu():
    assert k.isimden_kategori(
        "TÜRKİYE HAYAT VE EMEKLİLİK A.Ş. ÜÇÜNCÜ YAŞAM DÖNGÜSÜ EMEKLİLİK YATIRIM FONU"
    ) == "Yaşam Döngüsü"


def test_varlik_sinifi_standarttan_once_gelir():
    """'Altin Standart' diye bir fon cikarsa altin kategorisine gitmeli.

    Standart bir dagilim profili, altin bir varlik sinifi; risk
    karsilastirmasi varlik sinifina gore yapilmali.
    """
    assert k.isimden_kategori(
        "X EMEKLİLİK A.Ş. ALTIN STANDART EMEKLİLİK YATIRIM FONU"
    ) == "Kıymetli Madenler"
