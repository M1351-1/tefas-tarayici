# -*- coding: utf-8 -*-
"""Masaustu penceresini GERCEKTEN CIZEN testler.

NEDEN BU DOSYA VAR
==================

Bu projede ayni sinif hata iki kez yasandi: kod derleniyor, surec ayakta
kaliyor, pencere aciliyor — ama EKRANDA ISE YARAR BIR SEY YOK.

  * Konut uygulamasinda karar panelinde bir NameError vardi; 174 test
    geciyordu ve `import`-tabanli kontrol de geciyordu, cunku hicbiri
    paneli CIZMIYORDU. Uygulama bos ekranla aciliyordu.
  * Bu uygulamada ise sutun genislikleri toplami pencereye sigmadigi
    icin ASIL iki sutun (gecmis getiri, sakinlik) varsayilan gorunumde
    hic gorunmuyordu. Liste tam o sutuna gore sirali aciliyordu; yani
    ust satirlarin neden ustte oldugu ekranda YAZMIYORDU.

Bir widget'i ice aktarmak onu cizmek degildir. Bu testler pencereyi
ekransiz (offscreen) kurar, gercekci bir Durum ile doldurur ve
gorunurlugu sorgular.

NE OLCMUYOR: sayilarin dogrulugunu. Pencere acilabilir ve icerik yine
yanlis olabilir; bu dosya yalnizca "cizilmiyor / gorunmuyor" sinifini
kapatir.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from PySide6.QtWidgets import QApplication
except ImportError:                                   # pragma: no cover
    QApplication = None

if QApplication is not None:
    from masaustu import pencere as pencere_modulu
    from masaustu import veri as veri_modulu


def _durum():
    """Gercekci bir Durum: iki kategori, olculmus ongoru blogu."""
    fonlar = []
    for i in range(24):
        fonlar.append({
            "kod": "F%02d" % i,
            "ad": "TEST PORTFÖY %02d HİSSE SENEDİ FONU" % i,
            "kategori": "Hisse Senedi" if i % 2 else "Para Piyasası",
            "tip": "YAT", "tip_ad": "Yatırım Fonu", "katilim": False,
            "tarih": "2026-09-11", "fiyat": 10.0 + i, "gozlem": 280,
            "buyukluk": 1e9, "kisi_sayisi": 1000,
            "getiri": {"gunluk": 0.1, "haftalik": 0.5, "aylik": 3.0 + i,
                       "uc_aylik": 9.0, "yillik": 60.0,
                       "yilbasindan": 40.0},
            "volatilite": 5.0 + i,
            "maks_dusus": -5.0 - i,
            "net_yillik": 50.0,
            "stopaj": 0.175,
            "getiri_puani": 1.0 - i * 0.05,
            "getiri_sirasi": i + 1,
            "risk_puani": 1.5 - i * 0.1,
            "risk_sirasi": i + 1,
            "risk_eksik_bilesen": [] if i else ["maks_dusus"],
            "istikrar": [9, 12],
            "kategori_fon_sayisi": 12,
            "puanlanmama_nedeni": None,
        })
    return veri_modulu.Durum(
        veri_tarihi="2026-09-11",
        uretim_zamani="2026-09-11T20:19:11+03:00",
        sorumluluk_notu=(
            "Bu uygulama yatırım danışmanlığı değildir. Gösterilen "
            "sıralamalar geçmiş fiyat verilerinden hesaplanmış "
            "istatistiklerdir. Geçmiş getiri gelecek getiriyi göstermez."),
        fonlar=fonlar,
        kategoriler=[{"tip": "YAT", "tip_ad": "Yatırım Fonu",
                      "ad": "Hisse Senedi", "adet": 12}],
        sayilar={"puanlanan": 24},
        ongoru_gucu={
            "durum": "calismiyor",
            "ozet": "ÖLÇÜLDÜ: geçmiş getiriye göre sıralama geleceği "
                    "tutmuyor. Sıra korelasyonu 0.01.",
            "getiri": {}, "volatilite": {}, "istikrar": {},
        },
        agirliklar={},
    )


@unittest.skipIf(QApplication is None, "PySide6 kurulu degil")
class PencereCizimTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _pencere(self):
        p = pencere_modulu.AnaPencere()
        p.durum = _durum()
        p._ekrani_doldur() if hasattr(p, "_ekrani_doldur") else None
        p._ongoru_seridini_doldur()
        p._siralama_etiketini_yenile()
        p._tabloyu_doldur()
        return p

    def test_pencere_dolu_veriyle_cizilir(self):
        p = self._pencere()
        self.assertGreater(p.tablo.rowCount(), 0, "tablo bos kaldi")

    def test_asil_sutunlar_pencereye_sigar(self):
        """ASIL GERILEME TESTI.

        Sutun genislikleri toplami tablo alanina sigmazsa "gecmis
        getiri" ve "sakinlik" ekran disinda kalir. Liste tam o sutuna
        gore sirali oldugu icin siralama aciklanamaz hale geliyordu.
        """
        toplam = sum(genislik for _, _, genislik in pencere_modulu.SUTUNLAR)
        # Pencere 1400; boluceyle tabloya ~900 piksel veriliyor.
        self.assertLessEqual(
            toplam, 900,
            "sutun toplami %d piksel; tabloya ayrilan ~900 pikseli asiyor "
            "ve asil sutunlar ekran disinda kaliyor" % toplam)

    def test_ongoru_seridi_gorunur(self):
        """Olculen sonuc ekranda OLMALI.

        Uygulama siralamanin gelecegi tutmadigini olcup JSON'a
        yaziyordu ama hicbir yerde gostermiyordu.
        """
        p = self._pencere()
        self.assertTrue(p.ongoru_kutusu.isVisibleTo(p))
        self.assertIn("tutmuyor", p.ongoru_baslik.text())
        self.assertIn("ÖLÇÜLDÜ", p.ongoru_metin.text())

    def test_ongoru_yoksa_serit_gizlenir(self):
        """Olcum yoksa bos bir kutu gosterilmemeli."""
        p = pencere_modulu.AnaPencere()
        p.durum = _durum()
        p.durum.ongoru_gucu = None
        p._ongoru_seridini_doldur()
        self.assertFalse(p.ongoru_kutusu.isVisibleTo(p))

    def test_siralama_etiketi_olcutu_ve_uyariyi_yazar(self):
        """Siralama ortulu olmamali.

        Hangi olcute gore sirali oldugu yazmiyordu; kullanici ustteki
        satiri "en iyi fon" sanabiliyordu.
        """
        p = self._pencere()
        metin = p.siralama_etiketi.text()
        self.assertIn("Sakinlik", metin)
        self.assertIn("En iyi fon", metin)

    def test_getiri_siralamasinda_tavsiye_degil_uyarisi(self):
        p = self._pencere()
        p._sirala_sutun = "getiri_puani"
        p._siralama_etiketini_yenile()
        metin = p.siralama_etiketi.text()
        self.assertIn("TUTMUYOR", metin)
        self.assertIn("tavsiye değildir", metin)

    def test_sorumluluk_notu_kirpilmaz(self):
        """Uyari cumlesi ortasindan kesiliyordu.

        `[:160]` ile kirpiliyor ve ekranda "...gelecek getiriyi
        gosterme" diye yarim kaliyordu. Yarim kalan bir sorumluluk notu,
        olmamasindan daha kotudur.
        """
        p = self._pencere()
        tam = p.durum.sorumluluk_notu
        self.assertTrue(tam.endswith("göstermez."))
        self.assertEqual(p.durum_cubugu.toolTip(), tam)

    def test_bos_durumla_cokmez(self):
        p = pencere_modulu.AnaPencere()
        p.durum = veri_modulu.Durum()
        p._ongoru_seridini_doldur()
        p._siralama_etiketini_yenile()
        p._tabloyu_doldur()


if __name__ == "__main__":
    unittest.main()
