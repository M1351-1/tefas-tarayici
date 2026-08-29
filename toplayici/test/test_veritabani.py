# -*- coding: utf-8 -*-
"""Veritabani testleri. Gecici dosyada calisir, aga cikmaz."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import veritabani as vt
from istemci import Kayit


def k(tarih, kod="AAA", fiyat=100.0, tip="YAT", ad="TEST FONU",
      kisi=1000, buyukluk=50_000_000.0):
    return Kayit(tarih=tarih, fon_kodu=kod, fon_tipi=tip, fon_adi=ad,
                 fiyat=fiyat, pay_sayisi=1000.0, kisi_sayisi=kisi,
                 portfoy_buyukluk=buyukluk)


@pytest.fixture
def depo(tmp_path):
    d = vt.Depo(tmp_path / "test.db")
    yield d
    d.kapat()


def test_bos_veritabani(depo):
    assert depo.kayit_sayisi() == 0
    assert depo.fon_sayisi() == 0
    assert depo.en_son_tarih() is None


def test_yazma_ve_okuma(depo):
    depo.fiyat_yaz([k("2026-08-27"), k("2026-08-28", fiyat=110.0)])
    assert depo.kayit_sayisi() == 2
    assert depo.fon_sayisi() == 1
    assert depo.en_son_tarih() == "2026-08-28"


def test_ayni_gun_iki_kez_yazilirsa_tekrar_olmaz(depo):
    depo.fiyat_yaz([k("2026-08-28", fiyat=100.0)])
    depo.fiyat_yaz([k("2026-08-28", fiyat=105.0)])
    assert depo.kayit_sayisi() == 1
    # Yeni deger eskisinin ustune yazilmali
    assert depo.fiyat_serisi("AAA")[-1][1] == 105.0


def test_fiyat_serisi_tarihe_gore_sirali(depo):
    depo.fiyat_yaz([k("2026-08-28", fiyat=3.0), k("2026-08-26", fiyat=1.0),
                    k("2026-08-27", fiyat=2.0)])
    seri = depo.fiyat_serisi("AAA")
    assert [f for _, f in seri] == [1.0, 2.0, 3.0]


def test_fon_listesi_son_gozlemi_verir(depo):
    depo.fiyat_yaz([k("2026-08-26", fiyat=1.0, kisi=100),
                    k("2026-08-28", fiyat=3.0, kisi=300)])
    liste = depo.fon_listesi()
    assert len(liste) == 1
    assert liste[0]["fiyat"] == 3.0
    assert liste[0]["kisi_sayisi"] == 300
    assert liste[0]["tarih"] == "2026-08-28"


def test_tum_seriler_fon_basina_gruplar(depo):
    depo.fiyat_yaz([k("2026-08-27", kod="AAA"), k("2026-08-28", kod="AAA"),
                    k("2026-08-28", kod="BBB")])
    seriler = depo.tum_seriler()
    assert set(seriler) == {"AAA", "BBB"}
    assert len(seriler["AAA"]) == 2 and len(seriler["BBB"]) == 1


def test_kategori_yaz_ve_oku(depo):
    depo.kategori_yaz({"AAA": (104, "Hisse Senedi Semsiye Fonu")}, "2026-08-29")
    harita = depo.kategori_haritasi()
    assert harita["AAA"] == (104, "Hisse Senedi Semsiye Fonu")


def test_kategori_guncellenir(depo):
    depo.kategori_yaz({"AAA": (104, "Hisse")}, "2026-08-29")
    depo.kategori_yaz({"AAA": (107, "Para Piyasasi")}, "2026-08-30")
    assert depo.kategori_haritasi()["AAA"] == (107, "Para Piyasasi")


def test_en_son_tarih_fon_tipine_gore(depo):
    depo.fiyat_yaz([k("2026-08-28", kod="AAA", tip="YAT"),
                    k("2026-08-20", kod="EEE", tip="EMK")])
    assert depo.en_son_tarih("YAT") == "2026-08-28"
    assert depo.en_son_tarih("EMK") == "2026-08-20"


def test_bos_liste_yazmak_cokmez(depo):
    assert depo.fiyat_yaz([]) == 0
    assert depo.kategori_yaz({}, "2026-08-29") == 0
