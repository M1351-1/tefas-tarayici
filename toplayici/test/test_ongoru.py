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
        g = {63: {"spearman": 0.05, "ust_dilim": 9.2, "alt_dilim": 9.4,
                  "olcum_sayisi": 82}}
        v = {63: {"spearman": 0.76, "ust_dilim": 28.6, "alt_dilim": 6.7,
                  "olcum_sayisi": 84}}
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
