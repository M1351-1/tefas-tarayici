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
