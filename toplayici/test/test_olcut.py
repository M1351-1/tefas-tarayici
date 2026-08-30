# -*- coding: utf-8 -*-
"""Istikrar / olcut / risk-ayarli getiri testleri. Aga cikmaz."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import olcut as o


def seri(*ciftler):
    """(tarih, fiyat) listesi."""
    return list(ciftler)


# ------------------------------------------------------------- ay aritmetigi

def test_ay_ekle():
    assert o._ay_ekle("2026-08") == "2026-09"


def test_ay_ekle_yil_doner():
    assert o._ay_ekle("2026-12") == "2027-01"


def test_ay_ekle_ocaktan():
    assert o._ay_ekle("2026-01") == "2026-02"


# --------------------------------------------------------- ay sonu fiyatlari

def test_ay_sonu_son_gozlemi_alir():
    s = seri(("2026-07-01", 100.0), ("2026-07-31", 110.0),
             ("2026-08-15", 120.0))
    a = o.ay_sonu_fiyatlari(s)
    assert a == {"2026-07": 110.0, "2026-08": 120.0}


def test_sifir_fiyat_atlanir():
    a = o.ay_sonu_fiyatlari(seri(("2026-07-01", 0.0), ("2026-07-31", 110.0)))
    assert a == {"2026-07": 110.0}


# ----------------------------------------------------------- aylik getiriler

def test_aylik_getiri_hesaplanir():
    s = seri(("2026-06-30", 100.0), ("2026-07-31", 110.0),
             ("2026-08-31", 121.0))
    g = o.aylik_getiriler(s)
    assert abs(g["2026-07"] - 10.0) < 1e-9
    assert abs(g["2026-08"] - 10.0) < 1e-9
    # Ilk ay icin onceki ay yok
    assert "2026-06" not in g


def test_ardisik_olmayan_ay_atlanir():
    """Fon bir ay fiyatlanmamissa iki aylik degisimi aylik saymamaliyiz.

    Aksi halde o ay olmadigindan cok daha iyi gorunur.
    """
    s = seri(("2026-06-30", 100.0), ("2026-08-31", 121.0))
    g = o.aylik_getiriler(s)
    assert g == {}


def test_sadece_son_n_ay():
    s = [("2025-%02d-28" % ay, 100.0 + ay) for ay in range(1, 13)]
    s += [("2026-%02d-28" % ay, 120.0 + ay) for ay in range(1, 9)]
    g = o.aylik_getiriler(s, azami_ay=6)
    assert len(g) == 6
    assert max(g) == "2026-08"


# ------------------------------------------------------------------- medyan

def test_medyan_tek_sayida():
    assert o.medyan([3.0, 1.0, 2.0]) == 2.0


def test_medyan_cift_sayida():
    assert o.medyan([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_medyan_bos():
    assert o.medyan([]) is None


# ------------------------------------------------------------- kategori medyani

def fon(kod, getiriler, kategori="Hisse Senedi", tip="YAT"):
    return {"fon_kodu": kod, "fon_tipi": tip, "kategori_ad": kategori,
            "aylik_getiriler": getiriler}


def test_kategori_medyani_hesaplanir():
    fonlar = [fon("F%d" % i, {"2026-08": float(i)}) for i in range(5)]
    m = o.kategori_medyanlari(fonlar)
    assert m[("YAT", "Hisse Senedi")]["2026-08"] == 2.0


def test_az_fonlu_ay_medyansiz_kalir():
    """3 fonun medyani 'kategori ortasi' saymaz."""
    fonlar = [fon("F%d" % i, {"2026-08": float(i)}) for i in range(3)]
    m = o.kategori_medyanlari(fonlar)
    assert m[("YAT", "Hisse Senedi")] == {}


def test_kategoriler_ayri_hesaplanir():
    fonlar = ([fon("H%d" % i, {"2026-08": 50.0}, "Hisse Senedi")
               for i in range(5)] +
              [fon("P%d" % i, {"2026-08": 4.0}, "Para Piyasası")
               for i in range(5)])
    m = o.kategori_medyanlari(fonlar)
    assert m[("YAT", "Hisse Senedi")]["2026-08"] == 50.0
    assert m[("YAT", "Para Piyasası")]["2026-08"] == 4.0


# ------------------------------------------------------------------ istikrar

def test_istikrar_sayar():
    digerleri = [fon("D%d" % i, {"2026-07": 5.0, "2026-08": 5.0})
                 for i in range(5)]
    hedef = fon("HEDEF", {"2026-07": 9.0, "2026-08": 1.0})
    m = o.kategori_medyanlari(digerleri + [hedef])
    assert o.istikrar(hedef, m) == (1, 2)


def test_istikrarli_fon_yuksek_cikar():
    digerleri = [fon("D%d" % i, {"2026-0%d" % ay: 5.0 for ay in range(1, 9)})
                 for i in range(5)]
    istikrarli = fon("IYI", {"2026-0%d" % ay: 6.0 for ay in range(1, 9)})
    m = o.kategori_medyanlari(digerleri + [istikrarli])
    assert o.istikrar(istikrarli, m) == (8, 8)


def test_tek_sicrama_yapan_fon_dusuk_cikar():
    """Getiri siralamasinin ayirt edemedigi durum.

    Bu fon tek ayda %100 yapip digerlerinde geride kaliyor. Yillik
    getirisi harika gorunur ama istikrari 1/8'dir.
    """
    digerleri = [fon("D%d" % i, {"2026-0%d" % ay: 5.0 for ay in range(1, 9)})
                 for i in range(5)]
    sansli = fon("SANS", dict({"2026-0%d" % ay: 1.0 for ay in range(1, 9)},
                              **{"2026-03": 100.0}))
    m = o.kategori_medyanlari(digerleri + [sansli])
    assert o.istikrar(sansli, m) == (1, 8)


def test_medyansiz_aylar_sayilmaz():
    hedef = fon("HEDEF", {"2026-08": 9.0})
    # Kategoride tek fon var -> medyan hesaplanmaz -> degerlendirilecek ay yok
    m = o.kategori_medyanlari([hedef])
    assert o.istikrar(hedef, m) is None


# -------------------------------------------------------------------- olcut

def ppf(kod, yillik):
    return {"fon_kodu": kod, "fon_tipi": "YAT",
            "kategori_ad": "Para Piyasası", "yillik_getiri": yillik}


def test_olcut_para_piyasasi_medyani():
    fonlar = [ppf("P%d" % i, 58.0 + i) for i in range(5)]
    deger, adet = o.para_piyasasi_olcutu(fonlar)
    assert deger == 60.0 and adet == 5


def test_olcut_emeklilik_fonlarini_saymaz():
    """Emeklilik fonlarinin masraf yapisi farkli; olcut olmazlar."""
    fonlar = [ppf("P%d" % i, 60.0) for i in range(5)]
    fonlar += [{"fon_kodu": "E1", "fon_tipi": "EMK",
                "kategori_ad": "Para Piyasası", "yillik_getiri": 10.0}]
    deger, adet = o.para_piyasasi_olcutu(fonlar)
    assert deger == 60.0 and adet == 5


def test_olcut_az_fon_varsa_none():
    deger, adet = o.para_piyasasi_olcutu([ppf("P1", 60.0)])
    assert deger is None and adet == 0


# ------------------------------------------------------------- risk-ayarli

def test_risk_ayarli_hesaplanir():
    # (96 - 60) / 20 = 1.8
    assert abs(o.risk_ayarli(96.0, 20.0, 60.0) - 1.8) < 1e-9


def test_olcutu_gecemeyen_fon_negatif():
    """%52 getiren, %40 oynayan fon risksiz %60'in altinda kalmis."""
    assert o.risk_ayarli(52.0, 40.0, 60.0) < 0


def test_para_piyasasinin_kendisi_sifira_yakin():
    """Olcutu cikarmasaydik para piyasasi her fonu ezerdi.

    60/1.6 = 37,5 gibi bir sayi cikardi ve olcu anlamsiz olurdu.
    """
    assert abs(o.risk_ayarli(60.0, 1.6, 60.0)) < 1e-9


def test_cok_dusuk_oynaklikta_none():
    assert o.risk_ayarli(60.0, 0.2, 55.0) is None


def test_eksik_veride_none():
    assert o.risk_ayarli(None, 20.0, 60.0) is None
    assert o.risk_ayarli(90.0, None, 60.0) is None
    assert o.risk_ayarli(90.0, 20.0, None) is None


# ------------------------------------------------------------ stopaj / net

def test_hisse_yogun_fon_stopajdan_muaf():
    """Kullanici: '+%50 hisse senedi iceriyorsa stopaj %0'."""
    oran, gerekce, yerli = o.stopaj_orani([("hs", 91.0), ("tr", 9.0)])
    assert oran == 0.0
    assert yerli == 91.0
    assert "stopaj yok" in gerekce


def test_yabanci_hisse_fonu_muaf_degil():
    """AFA gercek verisi: portfoyun %98'i YABANCI hisse, yerli hisse %0.

    Kategori adina bakan bir kural bu fonu 'Hisse Senedi' diye muaf
    sayar ve getirisini %17,5 fazla gosterirdi. Muafiyet YERLI hisse
    yogunluguna bagli.
    """
    oran, gerekce, yerli = o.stopaj_orani(
        [("yhs", 98.2), ("yyf", 1.77), ("tr", 0.02)])
    assert oran == o.STOPAJ_STANDART
    assert yerli == 0.0


def test_esik_altinda_stopaj_var():
    oran, _, _ = o.stopaj_orani([("hs", 50.0), ("dt", 50.0)])
    assert oran == o.STOPAJ_STANDART


def test_esikte_muaf():
    oran, _, _ = o.stopaj_orani([("hs", 51.0), ("dt", 49.0)])
    assert oran == 0.0


def test_dagilim_yoksa_stopajli_varsayilir():
    """Muafiyeti kanitlayamadigimiz fonu vergisiz saymak getirisini
    oldugundan yuksek gosterirdi."""
    oran, gerekce, yerli = o.stopaj_orani(None)
    assert oran == o.STOPAJ_STANDART
    assert yerli is None
    assert "bilinmiyor" in gerekce.lower()


def test_ppf_neti_kullanicinin_rakamina_yakin():
    """IOO (Is Portfoy Ikinci PPF) olculen bilesik brut %46,7.

    Stopaj %17,5 sonrasi net %38,6. Kullanici 'Is Bankasi PPF %39
    veriyor' dedi - o rakam BASIT yillik brut (%39,0). Ikisi de dogru,
    farkli gosterimler. Bu test ikisinin de beklenen bantta kalmasini
    sabitler.
    """
    brut_bilesik = 46.7
    assert 38.0 <= o.net_getiri(brut_bilesik, o.STOPAJ_STANDART) <= 39.0
    assert 38.5 <= o.bilesikten_basite(brut_bilesik) <= 39.5


def test_hisse_fonunda_net_brute_esit():
    assert o.net_getiri(96.0, o.STOPAJ_MUAF) == 96.0


def test_net_getiri_none_gecirir():
    assert o.net_getiri(None, 0.175) is None
    assert o.net_getiri(50.0, None) is None


def test_bilesikten_basite_kucultur():
    """Bilesik her zaman basitten buyuktur (pozitif getiride)."""
    assert o.bilesikten_basite(60.0) < 60.0


def test_bilesikten_basite_none():
    assert o.bilesikten_basite(None) is None


def test_stopaj_hisse_fonunu_one_gecirir():
    """Bu duzeltmenin siralamayi GERCEKTEN degistirdigini gosterir.

    Brut karsilastirmada PPF (%60) hisse fonuna (%58) yakin durur;
    net karsilastirmada arada 8 puan acilir.
    """
    ppf_net = o.net_getiri(60.0, o.STOPAJ_STANDART)      # 49,5
    hisse_net = o.net_getiri(58.0, o.STOPAJ_MUAF)        # 58,0
    assert 60.0 > 58.0          # brut: PPF onde
    assert hisse_net > ppf_net  # net: hisse fonu onde
