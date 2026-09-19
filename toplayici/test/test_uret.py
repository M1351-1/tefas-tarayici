# -*- coding: utf-8 -*-
"""JSON uretimi testleri.

NE OLCUYOR: telefona giden dosyanin OKUNABILIR ve TAM oldugunu.
Sayilarin dogrulugu degil — o `test_puanlama` / `test_metrikler`
isi. Buradaki iki sinif hata daha once yasandi:

  * uretilen bir alan JSON'a hic yazilmadi (risk kirilimi, eksik
    bilesen uyarisi): uygulamada puan vardi, gerekcesi yoktu;
  * gecersiz sayi standart olmayan `NaN` belirteci olarak yazildi:
    Dart'in `jsonDecode`'u bunu okuyamaz, yani tek bozuk fon butun
    listeyi acilmaz hale getirir.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uret as u


def _fon(kod="AAA", **ek):
    temel = {
        "fon_kodu": kod, "fon_adi": "TEST FON", "fon_tipi": "YAT",
        "fon_tipi_ad": "Yatırım Fonu", "kategori_ad": "Hisse Senedi",
        "son_tarih": "2026-09-11", "son_fiyat": 12.5,
        "portfoy_buyukluk": 1e9, "gozlem_sayisi": 280,
        "aylik_getiri": 3.0, "uc_aylik_getiri": 9.0,
        "haftalik_getiri": 0.5, "yillik_getiri": 60.0,
        "volatilite": 12.0, "maks_dusus": -8.0,
        "getiri_puani": 1.2, "risk_puani": 0.4,
        "risk_kirilimi": {
            "volatilite": {"deger": 12.0, "kategori_ortalamasi": 20.0,
                           "z": 0.8, "agirlik": 0.6, "katki": 0.48},
            "maks_dusus": {"deger": -8.0, "kategori_ortalamasi": -15.0,
                           "z": -0.2, "agirlik": 0.4, "katki": -0.08},
        },
        "risk_eksik_bilesen": [],
        "stopaj": 0.0, "stopaj_gerekce": "...", "stopaj_kosullu": True,
    }
    temel.update(ek)
    return temel


def test_risk_kirilimi_disari_yazilir():
    """Uretiliyordu ama JSON'a HIC girmiyordu.

    Sonuc: uygulamada risk puani vardi, "neden" yoktu.
    """
    k = u.fon_kaydi(_fon())
    assert k["risk_kirilim"]["volatilite"]["katki"] == 0.48
    assert k["risk_eksik"] == []


def test_eksik_risk_bileseni_isaretlenir():
    """Yalniz oynakliktan uretilmis bir puan, tam veriyle uretilmis
    puanla ayni sutunda ayirt edilmeden kiyaslanmamali."""
    k = u.fon_kaydi(_fon(risk_eksik_bilesen=["maks_dusus"]))
    assert k["risk_eksik"] == ["maks_dusus"]


def test_stopaj_kosullu_isareti_tasinir():
    """Muafiyet tek gunluk dagilim fotografindan cikariliyor; sureklilik
    ve 1 yillik elde tutma dogrulanamiyor. Arayuz bunu bilmeli."""
    assert u.fon_kaydi(_fon())["stopaj_kosullu"] is True
    assert u.fon_kaydi(_fon(stopaj_kosullu=False))["stopaj_kosullu"] is False


def test_gecersiz_sayi_null_olur():
    """`_yuvarla` once yalnizca None'a bakiyordu; NaN gecip gidiyordu."""
    k = u.fon_kaydi(_fon(volatilite=float("nan"),
                         maks_dusus=float("inf"),
                         aylik_getiri=float("-inf")))
    assert k["volatilite"] is None
    assert k["maks_dusus"] is None
    assert k["getiri"]["aylik"] is None


def test_json_nan_belirteci_yazmaz(tmp_path):
    """ASIL GERILEME TESTI.

    `json.dump` varsayilan `allow_nan=True` ile bir NaN'i **`NaN`**
    diye yazar. Standart JSON degildir; Dart'in `jsonDecode`'u
    FormatException atar ve telefondaki uygulama fon listesini HIC
    acamaz. Tek bozuk fon butun ekrani goturur.
    """
    yol = tmp_path / "fonlar.json"
    ayar = {"agirliklar": {"aylik_getiri": 1.0}, "asgari_gecmis_gun": 90,
            "asgari_fon_buyuklugu": 1e7, "asgari_kategori_fon_sayisi": 10,
            "z_kirpma": 3.0}
    bozuk = _fon("BBB")
    bozuk["risk_puani"] = float("nan")       # _yuvarla'dan gecmeyen alan
    u.ozet_yaz(yol, [bozuk], [], [], ayar, "2026-09-11")

    ham = yol.read_text(encoding="utf-8")
    assert "NaN" not in ham
    assert "Infinity" not in ham
    # Ve gercekten ayristirilabilir olmali (katı ayristirici ile).
    icerik = json.loads(ham, parse_constant=_patlat)
    assert icerik["fonlar"][0]["risk_puani"] is None


def _patlat(ad):
    raise AssertionError("standart disi JSON belirteci: %s" % ad)


def test_gecerli_sayilar_bozulmaz():
    """Temizlik ise yarayan veriyi elememeli."""
    k = u.fon_kaydi(_fon())
    assert k["volatilite"] == 12.0
    assert k["getiri"]["aylik"] == 3.0
    assert math.isclose(k["risk_puani"], 0.4)
