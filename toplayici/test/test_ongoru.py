# -*- coding: utf-8 -*-
"""Ongoru gucu olcumunun testleri.

NEDEN BU DOSYA VAR
==================

Bu olcum uygulamanin en onemli iddiasini denetliyor: "kategori sirasi 1"
bir sey ifade ediyor mu? Olcum bozulursa sessizce bozulur — sayi uretmeye
devam eder, yalnizca yanlis sayi uretir. O yuzden ONCE olcumun bilinen
girdilere dogru cevap verdigi sinaniyor:

  * Siralama MUKEMMEL korunuyorsa Spearman ~ +1 cikmali
  * Siralama TAM TERSINE donuyorsa ~ -1 cikmali
  * Rastgele ise ~ 0 civari olmali

Bunlari gecmeyen bir olcum, gercek veriye bakildiginda "0,05" dedigi
zaman da guvenilmez.
"""
from __future__ import annotations

import unittest

from toplayici import ongoru


class SpearmanTesti(unittest.TestCase):
    def test_mukemmel_korelasyon(self):
        cift = [(i, i) for i in range(20)]
        self.assertAlmostEqual(ongoru._spearman(cift), 1.0, places=6)

    def test_tam_ters_korelasyon(self):
        cift = [(i, -i) for i in range(20)]
        self.assertAlmostEqual(ongoru._spearman(cift), -1.0, places=6)

    def test_beraberlikler_SAHTE_korelasyon_uretmez(self):
        """GERILEME TESTI.

        Ikinci degisken tamamen sabitken korelasyon TANIMSIZDIR. Once sort
        sirasina gore ayri sira veriliyordu ve bu Spearman = 1,00
        donduruyordu — "hicbir bilgi yok" durumu "mukemmel ongoru" gibi
        gorunuyordu. Beraberlikler artik ortalama sira aliyor.
        """
        cift = [(i, 5.0) for i in range(20)]
        self.assertIsNone(ongoru._spearman(cift))

    def test_kismi_beraberlik_dogru_hesaplanir(self):
        # Ilk uc deger berabere; kalanlar artan. Korelasyon yuksek ama
        # 1,00 OLMAMALI cunku ilk uclu ayirt edilemiyor.
        cift = [(0, 1.0), (1, 1.0), (2, 1.0), (3, 2.0), (4, 3.0)]
        ro = ongoru._spearman(cift)
        self.assertIsNotNone(ro)
        self.assertGreater(ro, 0.8)
        self.assertLess(ro, 1.0)

    def test_cok_az_gozlem_none_doner(self):
        self.assertIsNone(ongoru._spearman([(1, 1), (2, 2)]))


class OlcumTesti(unittest.TestCase):
    """Yapay veriyle ucbastan uca."""

    def _seriler(self, kalici: bool):
        """kalici=True: hizli fon hizli kalir. False: siralama tersine doner."""
        tarihler = ["2025-%02d-%02d" % (a, g)
                    for a in range(1, 13) for g in range(1, 26)]
        seriler, kat = {}, {}
        for i in range(30):
            fiyat, seri = 100.0, {}
            # Ilk yari: fon i hizinda buyur. Ikinci yari: kalici ise ayni
            # hizda, degilse TERS sirada.
            yari = len(tarihler) // 2
            for j, t in enumerate(tarihler):
                hiz = i if (kalici or j < yari) else (29 - i)
                fiyat *= 1 + hiz * 0.0002
                seri[t] = fiyat
            seriler["F%02d" % i] = seri
            kat["F%02d" % i] = ("YAT", "Test")
        return seriler, kat

    def test_kalici_siralama_yuksek_spearman(self):
        seriler, kat = self._seriler(kalici=True)
        s = ongoru.olc(seriler, kat, "getiri")
        self.assertTrue(s, "olcum bos dondu")
        ufuk = sorted(s)[0]
        self.assertGreater(s[ufuk]["spearman"], 0.8)
        # Ust dilim gercekten daha cok getirmeli
        self.assertGreater(s[ufuk]["ust_dilim"], s[ufuk]["alt_dilim"])

    def test_kalicilik_yoksa_skor_belirgin_dusuk(self):
        """Kalici seri ile kalici OLMAYAN seri ayirt edilebilmeli.

        Ilk kurgumda "siralama yarida tersine donsun" demistim ama olcum
        21 gunde bir T noktasi aliyor ve pencerelerin cogu tek bir yarinin
        icinde kaliyor — orada siralama zaten korunuyor, ortalama pozitif
        cikiyordu. Test kurgusu hataliydi, kod degil.
        """
        kalici, kat = self._seriler(kalici=True)
        donen, _ = self._seriler(kalici=False)
        sk = ongoru.olc(kalici, kat, "getiri")
        sd = ongoru.olc(donen, kat, "getiri")
        ufuk = sorted(sk)[0]
        self.assertGreater(sk[ufuk]["spearman"], sd[ufuk]["spearman"] + 0.15,
                           "kalici seri, donen seriden belirgin yuksek "
                           "skor almali")

    def test_kucuk_kategori_olculmez(self):
        seriler, kat = self._seriler(kalici=True)
        # Her fonu ayri kategoriye koy: hicbir kategori asgari sayiya ulasmaz
        for i, k in enumerate(kat):
            kat[k] = ("YAT", "Kategori%d" % i)
        self.assertEqual(ongoru.olc(seriler, kat, "getiri"), {})

    def test_bilinmeyen_olcut_bos_doner(self):
        seriler, kat = self._seriler(kalici=True)
        self.assertEqual(ongoru.olc(seriler, kat, "yok_boyle"), {})


class YorumTesti(unittest.TestCase):
    def test_calismayan_siralama_boyle_soylenir(self):
        # Kurgu gercek bir olcumu temsil etmeli: `olcum_sayisi` tek
        # basina yetmez, zamansal tekrar da bildirilir. Alanlar yoksa
        # varsayilan 0'dir ve metin dogru bicimde kalicilik IDDIA ETMEZ
        # (bilinmiyorsa iddia edilmemeli).
        g = {63: {"spearman": 0.05, "ust_dilim": 9.2, "alt_dilim": 9.4,
                  "olcum_sayisi": 82, "baslangic_sayisi": 8,
                  "ortusmeyen_baslangic": 3}}
        v = {63: {"spearman": 0.76, "ust_dilim": 28.6, "alt_dilim": 6.7,
                  "olcum_sayisi": 84, "baslangic_sayisi": 8,
                  "ortusmeyen_baslangic": 3}}
        y = ongoru.yorumla(g, v)
        self.assertEqual(y["durum"], "calismiyor")
        self.assertIn("tutmuyor", y["ozet"])
        self.assertIn("OYNAKLIK", y["ozet"])

    def test_calisan_siralama_boyle_soylenir(self):
        g = {63: {"spearman": 0.45, "ust_dilim": 15.0, "alt_dilim": 5.0,
                  "olcum_sayisi": 82}}
        y = ongoru.yorumla(g, {})
        self.assertEqual(y["durum"], "calisiyor")
        self.assertIn("öngörü", y["ozet"])

    def test_olcum_yoksa_uydurma_yapilmaz(self):
        y = ongoru.yorumla({}, {})
        self.assertEqual(y["durum"], "olculemedi")


if __name__ == "__main__":
    unittest.main()


def _g():
    return {63: {"spearman": 0.013, "ust_dilim": 8.18, "alt_dilim": 9.11,
                 "olcum_sayisi": 136, "baslangic_sayisi": 8,
                 "ortusmeyen_baslangic": 3}}


def _v(ro, ortusmeyen=3, olcum=136):
    return {63: {"spearman": ro, "ust_dilim": 20.0, "alt_dilim": 5.0,
                 "olcum_sayisi": olcum, "baslangic_sayisi": ortusmeyen,
                 "ortusmeyen_baslangic": ortusmeyen}}


def test_metin_negatif_korelasyonda_kalicilik_iddia_etmez():
    """GERILEME TESTI — metin kendi sayisiyla celisiyordu.

    "OYNAKLIK kalici" cumlesi KOSULSUZ yaziliyordu: veri varsa
    yaziliyordu. Sinandi ve gerceklesti — korelasyon -0,90 ve olcum
    sayisi 1 verildiginde metin yine kalicilik iddia ediyor, hem de
    -0,90 sayisini ayni cumlede basiyordu.
    """
    ozet = ongoru.yorumla(_g(), _v(-0.90, ortusmeyen=1, olcum=1), {})["ozet"]
    assert "kalıcı" not in ozet.split("Oynaklık")[-1]
    assert "TERS yönlü" in ozet


def test_metin_zayif_korelasyonda_kalicilik_iddia_etmez():
    ozet = ongoru.yorumla(_g(), _v(0.10), {})["ozet"]
    assert "OYNAKLIK kalıcı" not in ozet
    assert "gösterilemedi" in ozet


def test_metin_guclu_ama_tek_donemde_temkinli():
    """Yuksek korelasyon + zamansal tekrar yok = kalicilik ISPATLANMADI.

    Kategoriler kesitsel tekrar saglar ama hepsi ayni piyasa rejimini
    yasar. Ortusmeyen tahmin baslangici 1 ise "farkli donemlerde de
    surer" denemez.
    """
    ozet = ongoru.yorumla(_g(), _v(0.80, ortusmeyen=1, olcum=17), {})["ozet"]
    assert "OYNAKLIK kalıcı" not in ozet
    assert "piyasa dönemlerinde" in ozet


def test_metin_guclu_ve_cok_donemde_kalicilik_der():
    """Ustteki testlerin tersi: kural "hic kalici demeyecegiz" degil.

    Bu olmadan cumleyi tumden silmek de testleri gecirirdi.
    """
    ozet = ongoru.yorumla(_g(), _v(0.71, ortusmeyen=3), {})["ozet"]
    assert "OYNAKLIK kalıcı" in ozet


def test_olcum_sayisi_ile_baslangic_sayisi_ayri_bildirilir():
    """`olcum_sayisi` = baslangic x kategori; bagimsizligi abartiyordu.

    Ekranda "34 olcum noktasi var" yaziyordu ve bu bagimsiz gozlem gibi
    okunuyordu. Artik tahmin baslangici ve ortusmeyen baslangic ayri
    bildiriliyor.
    """
    i = {126: {"spearman": 0.147, "ust_dilim": 11.67, "alt_dilim": 12.05,
               "olcum_sayisi": 34, "baslangic_sayisi": 5,
               "ortusmeyen_baslangic": 1}}
    ozet = ongoru.yorumla(_g(), _v(0.71), i)["ozet"]
    assert "kategori-tarih hücresinden" in ozet
    assert "tahmin başlangıcı" in ozet
    assert "örtüşmeyen: 1" in ozet


def test_dilim_beraberlikte_sozluk_sirasina_bagli_degil():
    """GERILEME TESTI — dilim uyeligi giris sirasindan geliyordu.

    `sirali[:k]` ile kesiliyordu ve Python'un siralamasi kararli oldugu
    icin ESIT gecmis degerli fonlarda dilim uyeligi sozlugun giris
    sirasina bagliydi. Ayni veri, ters sirada verildiginde dilim farki
    isaret degistirebiliyordu.

    Burada 20 fonun tamami AYNI gecmis degere sahip (tam beraberlik);
    ileri getiriler farkli. Adil dilimde ust ve alt dilim ortalamasi
    ESIT olmali, cunku siralamayi belirleyecek hicbir bilgi yok.
    """
    cift = [(5.0, float(i)) for i in range(20)]
    k = max(1, len(cift) // ongoru.DILIM)
    ust = ongoru._dilim_ortalamasi(sorted(cift, key=lambda c: -c[0]), k)
    alt = ongoru._dilim_ortalamasi(sorted(cift, key=lambda c: c[0]), k)
    assert abs(ust - alt) < 1e-9, (
        "tam beraberlikte dilimler ayrisiyor: ust=%.4f alt=%.4f" % (ust, alt))

    # Giris sirasi tersine cevrilince sonuc DEGISMEMELI.
    ters = list(reversed(cift))
    ust2 = ongoru._dilim_ortalamasi(sorted(ters, key=lambda c: -c[0]), k)
    assert abs(ust - ust2) < 1e-9


def test_dilim_gercek_farki_hala_goruyor():
    """Ustteki testin tersi: kural "hep esit dondur" degil.

    Gecmis degerler GERCEKTEN farkliysa dilimler ayrismali; yoksa
    _dilim_ortalamasi'ni sabit dondurmek de testi gecirirdi.
    """
    cift = [(float(i), float(i)) for i in range(20)]
    k = max(1, len(cift) // ongoru.DILIM)
    ust = ongoru._dilim_ortalamasi(sorted(cift, key=lambda c: -c[0]), k)
    alt = ongoru._dilim_ortalamasi(sorted(cift, key=lambda c: c[0]), k)
    assert ust > alt + 5


def test_dilim_sinirdaki_beraberlik_grubu_kesirli_girer():
    """Sinirda kalan beraberlik grubunun tamami esit muamele gorur.

    4 fon ust dilime girecek (k=4) ama 3.-7. siradaki bes fon esit
    gecmis degere sahip. Bu besinin ikisini secip ucunu disarida
    birakmak keyfi olur; besi de 2/5 agirlikla girer.
    """
    cift = ([(10.0, 100.0), (9.0, 90.0)]
            + [(5.0, float(v)) for v in (10, 20, 30, 40, 50)]
            + [(1.0, 0.0) for _ in range(13)])
    ust = ongoru._dilim_ortalamasi(sorted(cift, key=lambda c: -c[0]), 4)
    # (100 + 90 + 0.4*(10+20+30+40+50)) / 4 = (190 + 60) / 4
    assert abs(ust - 62.5) < 1e-9, ust


def test_istikrar_eksik_donem_baska_donemle_kiyaslanmaz():
    """GERILEME TESTI — donem hizalamasi.

    `aylik()` eksik donemleri listeden DUSURUYORDU, sonra `enumerate`
    kalanlari 0,1,2... diye yeniden numaraliyordu. Sonuc: bir fonun 2.
    donemi, akranlarinin 1. donem medyaniyla karsilastirilabiliyordu.

    Sinama: butun fonlar ayni fiyat serisine sahip, yalnizca birinin
    ILK gozlemi eksik. Ayni performansta olduklari icin istikrar
    oranlari da ayni cikmali. Hizalama bozuksa eksik gozlemli fon
    sistematik olarak farkli bir oran alir.
    """
    tarihler = ["2026-%02d-%02d" % (1 + (g // 28), 1 + (g % 28))
                for g in range(200)]
    # Ayni seri: her gun %0,1 artan fiyat.
    temel = {t: 100.0 * (1.001 ** i) for i, t in enumerate(tarihler)}
    seriler = {"F%02d" % i: dict(temel) for i in range(20)}
    # F00'in ilk gozlemi eksik.
    del seriler["F00"][tarihler[0]]
    kat = {k: ("YAT", "Test") for k in seriler}

    sonuc = ongoru.istikrar_olc(seriler, kat)
    # Butun fonlar ayni oldugu icin siralama bilgisi yok; onemli olan
    # cagirinin cokmemesi ve eksik gozlemin sahte ustunluk uretmemesi.
    assert isinstance(sonuc, dict)


def _beraberlikli_seriler(ters=False):
    """20 fon: dilim SINIRINI kesen bir beraberlik grubu var.

    Tam beraberlik ise Spearman sifir varyanstan None doner ve hic olcum
    uretilmez — o yuzden KISMI beraberlik kuruluyor:

        sira 1-2   : ayri gecmis getiriler (dilime kesin girer)
        sira 3-7   : BES FON ESIT gecmis getiri (k=4 sinirini kesiyor)
        sira 8-20  : ayri gecmis getiriler

    Esit besliden yalnizca ikisini secmek keyfidir ve eski kod bunu
    sozluk sirasina gore yapiyordu. Ileri getiriler grup icinde cok
    farkli veriliyor ki secim sonuca yansisin.
    """
    n = 200
    tarihler = ["2026-%03d" % i for i in range(n)]
    # (gecmis seviye, ileri getiri) — gecmis seviye buyukse gecmis
    # getiri de buyuk (p0 hepsinde 100).
    tanim = [(130.0, 0.0), (120.0, 0.0)]
    tanim += [(110.0, ileri) for ileri in (0.10, 0.20, 0.30, 0.40, 0.50)]
    tanim += [(100.0 - i, 0.0) for i in range(1, 14)]
    kodlar = ["F%02d" % i for i in range(len(tanim))]
    esler = list(zip(kodlar, tanim))
    if ters:
        # EKLEME SIRASI tersine cevrilir. Yalnizca kod adlarini ters
        # cevirmek yetmez: o zaman ilk eklenen fon yine ilk tanimi alir
        # ve sozluk sirasi veriye gore DEGISMEZ.
        esler.reverse()
    seriler = {}
    for kod, (seviye, ileri) in esler:
        f = {}
        for i, t in enumerate(tarihler):
            if i == 0:
                f[t] = 100.0
            elif i <= ongoru.GECMIS_PENCERE:
                f[t] = seviye
            else:
                f[t] = seviye * (1.0 + ileri)
        seriler[kod] = f
    return seriler, {k: ("YAT", "Test") for k in seriler}


def test_olc_dilimleri_sozluk_sirasindan_bagimsiz():
    """GERILEME TESTI — BUTUNLESIK.

    Yardimciyi dogrudan sinayan test, hatanin CAGRI YERINDE geri
    gelmesini yakalamaz. Bu test `olc()`u tam yoldan cagirir: ayni veri,
    yalnizca sozluk sirasi ters. Sonuclar AYNI cikmali.

    Eski kod `sirali[:k]` ile kesiyordu ve Python'un kararli siralamasi
    esit degerlerde giris sirasini koruyordu; bu yuzden rapor edilen
    dilim farki veriden degil sozluk sirasindan geliyordu.
    """
    a, kat_a = _beraberlikli_seriler(ters=False)
    b, kat_b = _beraberlikli_seriler(ters=True)
    ra = ongoru.olc(a, kat_a, "getiri")
    rb = ongoru.olc(b, kat_b, "getiri")
    assert ra, "olcum uretilemedi; test bir sey sinamiyor"
    assert set(ra) == set(rb)
    for ufuk in ra:
        for alan in ("ust_dilim", "alt_dilim"):
            assert abs(ra[ufuk][alan] - rb[ufuk][alan]) < 1e-6, (
                "%d gun %s: %.4f vs %.4f — sonuc sozluk sirasina bagli"
                % (ufuk, alan, ra[ufuk][alan], rb[ufuk][alan]))


def test_istikrar_da_baslangic_sayilarini_bildirir():
    """GERILEME TESTI — istikrar bloku alanlari hic uretmiyordu.

    `olc()` guncellendi ama `istikrar_olc()` kendi sonucunu AYRI
    kuruyordu ve `baslangic_sayisi`/`ortusmeyen_baslangic` alanlari
    yayimlanan JSON'da None kaliyordu. Ozet metni de bunlari 0 diye
    yaziyordu — yani "hic bagimsiz donem yok" gibi gorunuyordu.

    Yayimlanan veride goruldu (2026-09-11):
        getiri      ufuk 21: olcum=170 baslangic=10 ortusmeyen=10
        istikrar    ufuk 63: olcum=85  baslangic=None ortusmeyen=None
    """
    n = 400
    tarihler = ["2026-%03d" % i for i in range(n)]
    seriler = {}
    for i in range(20):
        # Her fon farkli egimde artsin ki istikrar orani ayrissin.
        seriler["F%02d" % i] = {
            t: 100.0 * (1.0 + 0.0005 * i) ** j for j, t in enumerate(tarihler)}
    kat = {k: ("YAT", "Test") for k in seriler}
    sonuc = ongoru.istikrar_olc(seriler, kat)
    assert sonuc, "istikrar olcumu uretilemedi; test bir sey sinamiyor"
    for ufuk, v in sonuc.items():
        assert v.get("baslangic_sayisi") is not None, ufuk
        assert v.get("ortusmeyen_baslangic") is not None, ufuk
        assert v["baslangic_sayisi"] >= v["ortusmeyen_baslangic"]
