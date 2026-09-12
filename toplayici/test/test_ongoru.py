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
