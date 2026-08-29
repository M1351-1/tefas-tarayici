# -*- coding: utf-8 -*-
"""Puanlama testleri. Aga cikmaz."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import puanlama as p

AYAR = {
    "agirliklar": {
        "aylik_getiri": 0.35, "uc_aylik_getiri": 0.25,
        "haftalik_getiri": 0.20, "volatilite": 0.20,
    },
    "asgari_gecmis_gun": 90,
    "asgari_fon_buyuklugu": 10_000_000,
    "asgari_kategori_fon_sayisi": 10,
    "z_kirpma": 3.0,
}


def fon(kod, aylik=10.0, uc=30.0, haftalik=2.0, vol=20.0,
        kategori="Hisse Senedi", tip="YAT", gozlem=250,
        buyukluk=100_000_000):
    return {
        "fon_kodu": kod, "fon_tipi": tip, "kategori_ad": kategori,
        "aylik_getiri": aylik, "uc_aylik_getiri": uc,
        "haftalik_getiri": haftalik, "volatilite": vol,
        "gozlem_sayisi": gozlem, "portfoy_buyukluk": buyukluk,
    }


def grup(n, kategori="Hisse Senedi", tip="YAT", **ek):
    """n adet birbirinden farkli fon uretir."""
    return [fon("F%02d" % i, aylik=10.0 + i, uc=30.0 + i,
                haftalik=2.0 + i * 0.1, vol=20.0 + i,
                kategori=kategori, tip=tip, **ek) for i in range(n)]


# --------------------------------------------------------------------- eleme

def test_kisa_gecmisli_fon_elenir():
    uygun, elenen = p.ele([fon("A", gozlem=50)], AYAR)
    assert uygun == []
    assert "yeterli gecmis yok" in elenen[0]["eleme_nedeni"]


def test_kucuk_fon_elenir():
    uygun, elenen = p.ele([fon("A", buyukluk=1_000_000)], AYAR)
    assert uygun == []
    assert "cok kucuk" in elenen[0]["eleme_nedeni"]


def test_eksik_metrikli_fon_elenir():
    uygun, elenen = p.ele([fon("A", vol=None)], AYAR)
    assert uygun == []
    assert "metrik hesaplanamadi" in elenen[0]["eleme_nedeni"]
    assert "volatilite" in elenen[0]["eleme_nedeni"]


def test_uygun_fon_gecer():
    uygun, elenen = p.ele([fon("A")], AYAR)
    assert len(uygun) == 1 and elenen == []


def test_eleme_girdiyi_bozmaz():
    f = fon("A", gozlem=50)
    p.ele([f], AYAR)
    assert "eleme_nedeni" not in f


# ------------------------------------------------------------------ puanlama

def test_kucuk_kategori_puanlanmaz():
    puanlanan, puanlanmayan = p.puanla(grup(5), AYAR)
    assert puanlanan == []
    assert len(puanlanmayan) == 5
    assert all(f["puan"] is None for f in puanlanmayan)
    assert "sadece 5 fon" in puanlanmayan[0]["puanlanmama_nedeni"]


def test_yeterli_kategori_puanlanir():
    puanlanan, puanlanmayan = p.puanla(grup(10), AYAR)
    assert len(puanlanan) == 10 and puanlanmayan == []
    assert all(f["puan"] is not None for f in puanlanan)


def test_kirilim_toplami_puana_esit():
    puanlanan, _ = p.puanla(grup(12), AYAR)
    for f in puanlanan:
        toplam = sum(k["katki"] for k in f["puan_kirilimi"].values())
        assert abs(toplam - f["puan"]) < 1e-3


def test_dusuk_volatilite_puan_kazandirir():
    # Iki fon her seyde ayni, sadece volatilite farkli.
    fonlar = grup(10)
    for f in fonlar:
        f["aylik_getiri"] = 10.0
        f["uc_aylik_getiri"] = 30.0
        f["haftalik_getiri"] = 2.0
    fonlar[0]["volatilite"] = 5.0    # en sakin
    fonlar[-1]["volatilite"] = 90.0  # en oynak
    puanlanan, _ = p.puanla(fonlar, AYAR)
    puan = {f["fon_kodu"]: f["puan"] for f in puanlanan}
    assert puan["F00"] > puan["F09"]


def test_yuksek_aylik_getiri_puan_kazandirir():
    fonlar = grup(10)
    for f in fonlar:
        f["volatilite"] = 20.0
        f["uc_aylik_getiri"] = 30.0
        f["haftalik_getiri"] = 2.0
    puanlanan, _ = p.puanla(fonlar, AYAR)
    puan = {f["fon_kodu"]: f["puan"] for f in puanlanan}
    assert puan["F09"] > puan["F00"]   # F09'un aylik getirisi en yuksek


def test_kategoriler_ayri_puanlanir():
    # Hisse fonlari %50 getiriyor, para piyasasi %3. Ayni cetvele
    # vurulursa para piyasasinin tamami dibe duser; ayri puanlanmali.
    hisse = [fon("H%d" % i, aylik=50.0 + i, kategori="Hisse") for i in range(10)]
    para = [fon("P%d" % i, aylik=3.0 + i * 0.1, kategori="Para Piyasasi")
            for i in range(10)]
    puanlanan, _ = p.puanla(hisse + para, AYAR)
    p_puan = [f["puan"] for f in puanlanan if f["kategori_ad"] == "Para Piyasasi"]
    # Kendi icinde en iyisi pozitif puan almali
    assert max(p_puan) > 0


def test_fon_tipleri_ayri_puanlanir():
    yat = grup(10, tip="YAT")
    emk = grup(10, tip="EMK")
    puanlanan, _ = p.puanla(yat + emk, AYAR)
    tipler = {f["fon_tipi"] for f in puanlanan}
    assert tipler == {"YAT", "EMK"}
    # Her tipte 1. sira olmali
    birinciler = [f for f in puanlanan if f["kategori_sirasi"] == 1]
    assert len(birinciler) == 2


def test_sira_numarasi_puana_gore():
    puanlanan, _ = p.puanla(grup(10), AYAR)
    sirali = sorted(puanlanan, key=lambda f: f["kategori_sirasi"])
    puanlar = [f["puan"] for f in sirali]
    assert puanlar == sorted(puanlar, reverse=True)


def test_z_kirpma_ucuk_fonu_sinirlar():
    # Bir fon delice getiri yapiyor: kirpma olmasa sapmayi sisirir.
    # 30 fon: kirpmanin devreye girebilmesi icin yeterli (asagiya bak).
    fonlar = grup(30)
    fonlar[0]["aylik_getiri"] = 100000.0
    puanlanan, _ = p.puanla(fonlar, AYAR)
    ucuk = next(f for f in puanlanan if f["fon_kodu"] == "F00")
    assert ucuk["puan_kirilimi"]["aylik_getiri"]["z"] == 3.0


def test_z_skorun_matematiksel_ust_siniri():
    """n fonluk bir grupta |z| en fazla (n-1)/kok(n) olabilir.

    Bu yuzden 10 fonluk bir kategoride z asla 2.85'i gecemez ve
    z_kirpma=3.0 hic devreye girmez. Kirpma kucuk kategoriler icin
    olu bir ayar, buyuk kategoriler icin gercek bir emniyet supabi.
    Ayari degistiren biri bunu bilsin diye test olarak sabitliyoruz.
    """
    import math
    fonlar = grup(10)
    fonlar[0]["aylik_getiri"] = 10 ** 9   # ne kadar buyutursen buyut
    puanlanan, _ = p.puanla(fonlar, AYAR)
    ucuk = next(f for f in puanlanan if f["fon_kodu"] == "F00")
    ust_sinir = 9 / math.sqrt(10)         # = 2.846
    assert abs(ucuk["puan_kirilimi"]["aylik_getiri"]["z"] - ust_sinir) < 1e-3


def test_ayni_degerlerde_z_sifir():
    fonlar = [fon("F%d" % i) for i in range(10)]  # hepsi birebir ayni
    puanlanan, _ = p.puanla(fonlar, AYAR)
    assert all(abs(f["puan"]) < 1e-9 for f in puanlanan)


# ------------------------------------------------------------ agirlik kontrol

def test_agirlik_toplami_bir_degilse_uyarir():
    bozuk = dict(AYAR)
    bozuk["agirliklar"] = dict(AYAR["agirliklar"])
    bozuk["agirliklar"]["aylik_getiri"] = 0.50
    sorunlar = p.agirlik_kontrolu(bozuk)
    assert any("toplami" in s for s in sorunlar)


def test_dogru_agirlik_sorun_uretmez():
    assert p.agirlik_kontrolu(AYAR) == []


def test_eksik_agirlik_yakalanir():
    bozuk = dict(AYAR)
    bozuk["agirliklar"] = {"aylik_getiri": 1.0}
    sorunlar = p.agirlik_kontrolu(bozuk)
    assert any("eksik agirlik" in s for s in sorunlar)
