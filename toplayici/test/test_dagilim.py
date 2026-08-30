# -*- coding: utf-8 -*-
"""Portfoy dagilimi testleri. Aga cikmaz."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dagilim as d

# TEFAS'tan gercekten donen bir satir (AFA - Amerika hisse senedi fonu).
AFA = {
    "fonKodu": "AFA", "fonUnvan": "AK PORTFÖY AMERİKA...", "tarih": "2026-08-28",
    "rn": 1, "yhs": 96.99, "yyf": 1.74, "tr": 1.26, "tpp": 0.01,
    "hs": 0.0, "dt": 0.0, "vmtl": None,
}


def test_sadece_sifir_olmayan_kalemler():
    k = d.ayikla(AFA)
    kodlar = [x[0] for x in k]
    assert "yhs" in kodlar
    assert "hs" not in kodlar      # sifir
    assert "vmtl" not in kodlar    # None


def test_meta_alanlar_varlik_sayilmaz():
    kodlar = [x[0] for x in d.ayikla(AFA)]
    for m in ("fonKodu", "fonUnvan", "tarih", "rn"):
        assert m not in kodlar


def test_buyukten_kucuge_sirali():
    yuzdeler = [x[2] for x in d.ayikla(AFA)]
    assert yuzdeler == sorted(yuzdeler, reverse=True)


def test_etiketler_turkce():
    k = dict((x[0], x[1]) for x in d.ayikla(AFA))
    assert k["yhs"] == "Yabancı Hisse Senedi"
    assert k["tr"] == "Ters-Repo"


def test_cok_kucuk_kalem_elenir():
    satir = {"fonKodu": "X", "hs": 99.99, "tr": 0.001}
    kodlar = [x[0] for x in d.ayikla(satir)]
    assert kodlar == ["hs"]


def test_bilinmeyen_kod_atilmaz():
    """TEFAS yeni bir varlik sinifi eklerse sessizce kaybolmamali.

    Kod etiket olarak gorunur; boylece fark edip sozluge ekleyebiliriz.
    """
    satir = {"fonKodu": "X", "hs": 50.0, "zzz": 50.0}
    k = dict((x[0], x[1]) for x in d.ayikla(satir))
    assert "zzz" in k
    assert k["zzz"] == "zzz"


def test_bos_satir_cokmez():
    assert d.ayikla({"fonKodu": "X"}) == []


# ------------------------------------------------------------------ ozetle

def test_az_kalem_oldugu_gibi_kalir():
    k = d.ayikla(AFA)
    assert d.ozetle(k) == k


def test_cok_kalem_ozetlenir():
    kalemler = [("k%d" % i, "Etiket %d" % i, 10.0 - i * 0.5) for i in range(15)]
    o = d.ozetle(kalemler, azami=7)
    assert len(o) == 8                    # 7 + "Diğer"
    assert o[-1][0] == "_diger"
    assert "8 kalem" in o[-1][1]


def test_ozet_toplami_korunur():
    """Ozetleme yuzde kaybetmemeli: kalanlarin toplami "Diğer"e gitmeli."""
    kalemler = [("k%d" % i, "E%d" % i, 5.0) for i in range(20)]
    o = d.ozetle(kalemler, azami=7)
    assert abs(sum(x[2] for x in o) - sum(x[2] for x in kalemler)) < 1e-9


def test_ozet_sirasi_bozulmaz():
    kalemler = [("k%d" % i, "E%d" % i, 20.0 - i) for i in range(12)]
    o = d.ozetle(kalemler, azami=5)
    assert [x[2] for x in o[:5]] == [20.0, 19.0, 18.0, 17.0, 16.0]


def test_sozluk_tefas_alanlarini_kapsiyor():
    """Canli veride gorulen 41 alan kodunun hepsi sozlukte olmali.

    Liste 29 Agustos 2026'da 2030 fonun tamamindan cikarildi.
    """
    canlida_gorulenler = [
        "yyf", "hs", "vint", "tr", "vmtl", "tpp", "osdb", "fb", "kba", "vmd",
        "yhs", "ost", "dt", "osks", "ybyf", "khtl", "d", "byf", "gsykb",
        "vdm", "ybosb", "btas", "bpp", "kkstl", "km", "kibd", "oksyd", "khd",
        "gykb", "r", "kmbyf", "hb", "ybkb", "kksd", "kmkks", "kksyd", "btaa",
        "kmkba", "khau", "vmau", "gas",
    ]
    eksik = [k for k in canlida_gorulenler if k not in d.ETIKETLER]
    assert not eksik, "sozlukte eksik alan kodlari: %s" % eksik
