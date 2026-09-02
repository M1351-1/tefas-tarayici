# -*- coding: utf-8 -*-
"""Masaustu veri katmani testleri — ozellikle TURKCE ARAMA.

NEDEN BU DOSYA VAR
==================

Turkce arama sessizce bozulan turden bir hatadir: kullanici bir sey arar,
bos sonuc gelir, "demek ki yok" diye dusunur. Hicbir hata mesaji cikmaz.

Python'un lower() metodu Turkce buyuk I icin yanlis calisir:

    "PIYASASI".lower() -> "pi̇yasasi"   (i + BIRLESTIRICI UST NOKTA)

Kullanicinin yazdigi duz "piyasasi" bununla eslesmez. TEFAS fon
adlarinin neredeyse hepsinde I, S, G gectigi icin bu, aramanin buyuk
kismini oldurmustu.
"""
from __future__ import annotations

import unittest

from masaustu import veri


class KatlamaTesti(unittest.TestCase):
    def test_turkce_buyuk_I_duz_i_ile_eslesir(self):
        self.assertEqual(veri.katla("PİYASASI"), veri.katla("piyasasi"))
        self.assertEqual(veri.katla("PİYASASI"), "piyasasi")

    def test_noktasiz_i_ayni_yere_katlanir(self):
        self.assertEqual(veri.katla("ALTIN"), veri.katla("altın"))
        self.assertEqual(veri.katla("ALTIN"), "altin")

    def test_diger_turkce_harfler(self):
        self.assertEqual(veri.katla("ŞGÜÖÇ"), "sguoc")
        self.assertEqual(veri.katla("şgüöç"), "sguoc")

    def test_birlestirici_nokta_temizlenir(self):
        # lower()'in biraktigi iz kalmamali.
        self.assertEqual(veri.katla("PİYASASI".lower()), "piyasasi")

    def test_bos_girdi_cokmez(self):
        self.assertEqual(veri.katla(""), "")
        self.assertEqual(veri.katla(None), "")


class SuzmeTesti(unittest.TestCase):
    def _durum(self):
        return veri.Durum(fonlar=[
            {"kod": "TI1", "ad": "İŞ PORTFÖY PARA PİYASASI (TL) FONU",
             "kategori": "Para Piyasası", "tip": "YAT", "getiri_puani": 1.0},
            {"kod": "FGA", "ad": "QNB PORTFÖY ALTIN KATILIM BYF",
             "kategori": "Kıymetli Madenler", "tip": "BYF",
             "getiri_puani": 0.5},
            {"kod": "ZZZ", "ad": "PUANSIZ FON", "kategori": "Serbest",
             "tip": "YAT", "getiri_puani": None},
        ])

    def test_ASIL_SINAV_turkce_ad_duz_sorguyla_bulunur(self):
        """Eski kod bunlarin hepsinde BOS donuyordu."""
        d = self._durum()
        for sorgu in ("para piyasasi", "PARA PİYASASI", "piyasası",
                      "is portfoy", "İŞ PORTFÖY"):
            with self.subTest(sorgu=sorgu):
                self.assertEqual(
                    [f["kod"] for f in veri.suz(d, arama=sorgu)], ["TI1"])

    def test_kod_ile_aranabilir(self):
        d = self._durum()
        self.assertEqual([f["kod"] for f in veri.suz(d, arama="fga")], ["FGA"])

    def test_alakasiz_sorgu_bos_doner(self):
        d = self._durum()
        self.assertEqual(veri.suz(d, arama="tahvil"), [])

    def test_puansiz_fon_varsayilan_olarak_elenir(self):
        d = self._durum()
        kodlar = [f["kod"] for f in veri.suz(d)]
        self.assertNotIn("ZZZ", kodlar)
        self.assertIn("ZZZ", [f["kod"] for f in veri.suz(d, yalniz_puanli=False)])

    def test_kategori_ve_tip_suzgeci(self):
        d = self._durum()
        self.assertEqual(
            [f["kod"] for f in veri.suz(d, kategori="Para Piyasası")], ["TI1"])
        self.assertEqual([f["kod"] for f in veri.suz(d, tip="BYF")], ["FGA"])


class YuklemeTesti(unittest.TestCase):
    def test_dosya_yoksa_COKMEZ_yonlendirir(self):
        """Kullanici toplayiciyi hic calistirmamis olabilir; uygulama
        acilip ne yapmasi gerektigini soylemeli, kapanmamali."""
        from pathlib import Path
        d = veri.yukle(Path("olmayan_dosya_12345.json"))
        self.assertFalse(d.yuklendi)
        self.assertIn("toplayici", d.hata)

    def test_olmayan_fonun_gecmisi_bos_liste(self):
        from pathlib import Path
        self.assertEqual(
            veri.fiyat_gecmisi("YOK", db_yolu=Path("olmayan.db")), [])


if __name__ == "__main__":
    unittest.main()


class PaketlenmisYolTesti(unittest.TestCase):
    """PyInstaller ile paketlenmis halde data/ nerede aranmali?

    Paketlenmis exe kaynaklari gecici bir klasore acar ve `data/` orada
    YOKTUR. `__file__` kullanmak gecici klasoru gosterir; uygulama acilir
    ama BOS acilir. Cokmedigi icin "exe calisiyor mu" testi bunu
    yakalamaz — bu yuzden yol cozumlemesi ayrica sinaniyor.
    """

    def _frozen_kok(self, exe_yolu):
        import sys
        from pathlib import Path

        eski_frozen = getattr(sys, "frozen", None)
        eski_exe = sys.executable
        try:
            sys.frozen = True
            sys.executable = str(Path(exe_yolu))
            return veri._kok()
        finally:
            if eski_frozen is None:
                del sys.frozen
            else:
                sys.frozen = eski_frozen
            sys.executable = eski_exe

    def test_paketlenmisse_data_klasoru_yukari_dogru_aranir(self):
        """Exe dist/ altinda, data/ proje kokunde.

        Sadece exe'nin klasorune bakmak yetmiyordu: dist/data/ yok,
        ../data/ var. Uygulama yine ACILIR ama BOS acilir — cokmedigi
        icin "exe calisiyor mu" testi bunu yakalamaz.
        """
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as gecici:
            kok = Path(gecici)
            (kok / "data").mkdir()
            (kok / "data" / "fonlar.json").write_text("{}", encoding="utf-8")
            (kok / "dist").mkdir()
            bulunan = self._frozen_kok(kok / "dist" / "TefasTarayici.exe")
            self.assertEqual(bulunan, kok.resolve())

    def test_data_exe_yanindaysa_orasi_kullanilir(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as gecici:
            kok = Path(gecici)
            (kok / "data").mkdir()
            (kok / "data" / "fonlar.json").write_text("{}", encoding="utf-8")
            bulunan = self._frozen_kok(kok / "TefasTarayici.exe")
            self.assertEqual(bulunan, kok.resolve())

    def test_hicbir_yerde_yoksa_exe_yani_donulur(self):
        """Hata mesajinin dogru yolu gosterebilmesi icin."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as gecici:
            kok = Path(gecici) / "bos"
            kok.mkdir()
            self.assertEqual(
                self._frozen_kok(kok / "TefasTarayici.exe"), kok.resolve())

    def test_kaynaktan_calisirken_proje_koku_kullanilir(self):
        import sys
        from pathlib import Path

        self.assertFalse(getattr(sys, "frozen", False))
        # masaustu/ klasorunun bir ustu = proje koku
        self.assertEqual(veri._kok(),
                         Path(veri.__file__).resolve().parent.parent)
