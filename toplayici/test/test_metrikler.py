# -*- coding: utf-8 -*-
"""Metrik testleri. Aga cikmaz, elle hesaplanmis degerlerle karsilastirir."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import metrikler as m


def seri(fiyatlar, ilk_gun=1, yil="2026", ay="03"):
    """Basit (tarih, fiyat) serisi uretir."""
    return [("%s-%s-%02d" % (yil, ay, ilk_gun + i), f)
            for i, f in enumerate(fiyatlar)]


# ------------------------------------------------------------------ getiri

def test_gunluk_getiri():
    # Kayan nokta aritmetiginde 110/100-1 tam 0.1 etmez; tolerans sart.
    sonuc = m.getiri(seri([100.0, 110.0]), 1)
    assert abs(sonuc - 10.0) < 1e-9


def test_haftalik_bes_gun_geriye_bakar():
    # 6 gozlem: sonuncu ile 5 onceki karsilastirilir
    s = seri([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    assert abs(m.getiri(s, 5) - 5.0) < 1e-9


def test_veri_yetmezse_none():
    s = seri([100.0, 101.0, 102.0])
    assert m.getiri(s, 5) is None


def test_sifir_fiyat_none_dondurur():
    s = seri([0.0, 100.0])
    assert m.getiri(s, 1) is None


def test_negatif_getiri():
    s = seri([200.0, 150.0])
    assert abs(m.getiri(s, 1) - (-25.0)) < 1e-9


# ------------------------------------------------------- yilbasindan getiri

def test_yilbasindan_onceki_yilin_son_gunune_bakar():
    s = [("2025-12-29", 90.0), ("2025-12-30", 100.0),
         ("2026-01-05", 120.0), ("2026-01-06", 130.0)]
    # 2025'in SON gozlemi 100; 130/100-1 = %30
    assert abs(m.yilbasindan_getiri(s) - 30.0) < 1e-9


def test_yilbasindan_onceki_yil_yoksa_none():
    s = [("2026-01-05", 120.0), ("2026-01-06", 130.0)]
    assert m.yilbasindan_getiri(s) is None


# -------------------------------------------------------------- volatilite

def test_volatilite_sabit_getiride_sifir():
    # Her gun tam %1 artan seri: gunluk getiri sapmasi sifir
    fiyatlar = [100.0 * (1.01 ** i) for i in range(65)]
    v = m.volatilite(seri(fiyatlar, ay="01"))
    assert v is not None and v < 1e-9


def test_volatilite_bilinen_deger():
    # Getiriler: %1, %2, %3 -> ornek sapma 0.01 -> yillik 0.01*kok(252)*100
    fiyatlar = [100.0, 101.0, 101.0 * 1.02, 101.0 * 1.02 * 1.03]
    beklenen = 0.01 * math.sqrt(252) * 100
    v = m.volatilite(seri(fiyatlar), pencere=3)
    assert abs(v - beklenen) < 1e-6


def test_volatilite_veri_yetmezse_none():
    assert m.volatilite(seri([100.0, 101.0])) is None


# --------------------------------------------------------------- maks dusus

def test_maks_dusus_tepe_dip():
    s = seri([100.0, 120.0, 90.0, 110.0])
    assert abs(m.maks_dusus(s) - (-25.0)) < 1e-9


def test_maks_dusus_hep_yukselen_seri_sifir():
    s = seri([100.0, 110.0, 120.0, 130.0])
    assert m.maks_dusus(s) == 0.0


def test_maks_dusus_dip_sonrasi_yeni_zirve():
    # 100 -> 80 (-%20) -> 200 -> 150 (-%25). En kotu -25 olmali.
    s = seri([100.0, 80.0, 200.0, 150.0])
    assert abs(m.maks_dusus(s) - (-25.0)) < 1e-9


# ------------------------------------------------------------------ hesapla

def test_hesapla_eksik_metrikleri_none_birakir():
    s = seri([100.0, 101.0, 102.0])
    h = m.hesapla(s)
    assert h["gunluk_getiri"] is not None
    assert h["yillik_getiri"] is None      # 252 gun yok
    assert h["volatilite"] is None         # 60 getiri yok
    assert h["gozlem_sayisi"] == 3
    assert h["son_fiyat"] == 102.0


def test_hesapla_bos_seri_cokmez():
    h = m.hesapla([])
    assert h["gozlem_sayisi"] == 0
    assert h["son_fiyat"] is None
    assert h["gunluk_getiri"] is None


def test_sifir_fiyat_dususu_gizlemez():
    """GERILEME TESTI — en kotu durumun sessizce silinmesi.

    `fiyat <= 0` olan gozlemler `continue` ile ATLANIYORDU. Niyet bozuk
    veriden korunmakti ama sonuc su oldu:

        maks_dusus([100, 0])      -> 0.0    (hic dusmemis!)
        maks_dusus([100, 50, 0])  -> -50.0  (sifira inis yok sayildi)

    Bu metrik risk puaninin %40'ini besliyor; cokmus fon "sakin"
    gorunuyordu. Sifir fiyat veri hatasi da tam kayip da olabilir ve
    ikisi veriden ayirt edilemez — ama "dusus yok" her iki halde de
    YANLIS cevap. Bu yuzden metrik gecersiz sayilir (None).
    """
    assert m.maks_dusus([("2026-01-01", 100.0), ("2026-01-02", 0.0)]) is None
    assert m.maks_dusus([("2026-01-01", 100.0), ("2026-01-02", 50.0),
                         ("2026-01-03", 0.0)]) is None
    assert m.maks_dusus([("2026-01-01", 100.0),
                         ("2026-01-02", -1.0)]) is None


def test_gecerli_seride_dusus_hesaplanmaya_devam_eder():
    """Ustteki testin tersi: kural "sifir gorursen vazgec" degil.

    Bu olmadan maks_dusus'u "hep None dondur" yapmak da testi gecirirdi.
    """
    d = m.maks_dusus([("2026-01-01", 100.0), ("2026-01-02", 75.0),
                      ("2026-01-03", 90.0)])
    assert abs(d - (-25.0)) < 1e-9


def test_uzun_bosluk_gunluk_getiri_sayilmaz():
    """GERILEME TESTI — ardisik gozlem, ardisik gun demek degil.

    Tarihe hic bakilmiyordu: iki ardisik KAYIT arasindaki degisim
    "gunluk getiri" sayilip kok(252) ile yillklandiriliyordu.
    Fiyatlanmayan bir fonun 216 gunluk degisimi tek bir gunluk getiri
    gibi isleniyordu.

    Olculdu (gercek veri): PDR %182,58 oynaklik bildiriyordu, bosluklar
    atlaninca %11,32; KPS 9582 -> 200. Butun fonlarda ortanca %6,86.
    """
    seri = [("2026-01-01", 100.0), ("2026-01-02", 101.0),
            ("2026-08-01", 150.0), ("2026-08-02", 151.0)]
    g = m.gunluk_getiriler(seri)
    assert len(g) == 2, "216 gunluk atlama gunluk getiri sayildi: %r" % (g,)
    assert abs(g[0] - 0.01) < 1e-9


def test_bayram_bosluklari_atlanmaz():
    """Esik "her boslugu at" DEGIL.

    Normal hafta sonu + tatil 4 gune cikar, bayram 9 gune tasiyabilir.
    Bunlari atmak gercek veriyi silmek olur; yalnizca 10 gunun otesi
    "fon fiyatlanmamis" sayilir.
    """
    seri = [("2026-01-01", 100.0), ("2026-01-09", 102.0)]   # 8 gun
    assert len(m.gunluk_getiriler(seri)) == 1
    seri = [("2026-01-01", 100.0), ("2026-01-20", 102.0)]   # 19 gun
    assert m.gunluk_getiriler(seri) == []


def test_bozuk_tarih_cokmez():
    seri = [(None, 100.0), ("2026-01-02", 101.0)]
    assert isinstance(m.gunluk_getiriler(seri), list)


def test_yillik_volatilite_ayri_pencereden_uretilir():
    """Risk-ayarli getiri PAYLA AYNI pencereyi kullanmali.

    Once yillik getiri 60 gozlemlik oynakliga bolunuyordu: bir yillik
    getiri uc aylik riske. Standart Sharpe pay ve bolende ayni ornegi
    kullanir.
    """
    fiyatlar = [100.0 * (1.0 + 0.001 * (i % 7)) for i in range(300)]
    s = [("2026-%02d-%02d" % (1 + i // 28, 1 + i % 28), f)
         for i, f in enumerate(fiyatlar)]
    m_ = m.hesapla(s)
    assert m_["volatilite"] is not None
    assert m_["yillik_volatilite"] is not None
    # Iki pencere ayri: degerler genelde farkli olur.
    assert m_["volatilite"] != m_["yillik_volatilite"]


def test_yillik_volatilite_gozlem_yetmezse_none():
    """252 gozlem yoksa oran hic uretilmemeli — uydurma yerine None."""
    fiyatlar = [100.0 + i for i in range(80)]
    s = [("2026-%02d-%02d" % (1 + i // 28, 1 + i % 28), f)
         for i, f in enumerate(fiyatlar)]
    m_ = m.hesapla(s)
    assert m_["volatilite"] is not None      # 60 gozlem yetiyor
    assert m_["yillik_volatilite"] is None   # 252 yetmiyor


def test_sifir_fiyat_yuzde_yuz_gunluk_getiri_uretmez():
    """GERILEME TESTI — sifir fiyat oynakligi patlatiyordu.

    `maks_dusus` sifir fiyati gecersiz sayiyordu ama `gunluk_getiriler`
    yalnizca `onceki > 0` kontrol ediyordu; `simdiki = 0` gecip -%100'luk
    bir GUNLUK getiri uretiyordu. Tek basina bu gozlem oynakligi ~%200
    yukseltir.

    Olculdu (KPS, yayimlanan veri): 2026-01-13'te 1,00 -> 2026-01-14'te
    0,00. Bosluk duzeltmesinden sonra bile oynaklik %284,59 kaliyordu;
    sebebi bu tek gozlemdi. Kural eklenince %200,83.
    """
    seri = [("2026-01-01", 100.0), ("2026-01-02", 101.0),
            ("2026-01-05", 0.0), ("2026-01-06", 1.0)]
    g = m.gunluk_getiriler(seri)
    assert all(x > -0.99 for x in g), "-%%100 getiri uretildi: %r" % (g,)
    assert len(g) == 1, g


def test_gecerli_dususler_korunur():
    """Kural "buyuk dususu at" DEGIL — yalnizca sifir/negatif fiyat.

    Gercek bir -%97 hareketi gizlemek, riski gizlemek olur.
    """
    seri = [("2026-01-01", 100.0), ("2026-01-02", 3.0)]
    g = m.gunluk_getiriler(seri)
    assert len(g) == 1 and abs(g[0] - (-0.97)) < 1e-9
