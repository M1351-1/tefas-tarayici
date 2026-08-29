# -*- coding: utf-8 -*-
"""GitHub Actions is akisi testleri.

Neden var: is akisi YAML'i bozuldugunda GitHub HICBIR sey calistirmiyor ve
gunluge tek satir bile yazmiyor. Tek belirti alakasiz bir hata mesaji
oluyor ("workflow_dispatch tetikleyicisi yok") ve veri sessizce
guncellenmemeye basliyor. Bu testler o sessiz kirilmayi yakalar.
"""
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent.parent
IS_AKISI = KOK / ".github" / "workflows" / "gunluk.yml"

yaml = pytest.importorskip("yaml", reason="pyyaml kurulu degil")


@pytest.fixture(scope="module")
def akis():
    with open(IS_AKISI, encoding="utf-8") as d:
        return yaml.safe_load(d)


def test_dosya_var():
    assert IS_AKISI.exists(), "is akisi dosyasi bulunamadi"


def test_yaml_ayristirilabiliyor(akis):
    """En kritik test.

    Tirnaksiz bir YAML degerinin icinde "iki nokta + bosluk" gecerse
    (ornegin `run: echo "Adres: http://..."`) ayristirma coker.
    """
    assert isinstance(akis, dict)


def _tetikleyiciler(akis):
    # YAML 1.1'de 'on' bir BOOLEAN'dir; pyyaml onu True'ya cevirir.
    # GitHub kendi ayristiricisiyla dogru okuyor, biz ikisine de bakiyoruz.
    return akis.get("on", akis.get(True))


def test_zamanlama_var(akis):
    t = _tetikleyiciler(akis)
    assert "schedule" in t


def test_elle_tetiklenebiliyor(akis):
    t = _tetikleyiciler(akis)
    assert "workflow_dispatch" in t


def test_cron_hafta_ici_aksam(akis):
    """TR 20:00 = 17:00 UTC, hafta ici.

    TEFAS fiyatlari aksam guncelleniyor; daha erken calistirirsan bir
    onceki gunun verisini alirsin.
    """
    cron = _tetikleyiciler(akis)["schedule"][0]["cron"]
    dakika, saat, _, _, gun = cron.split()
    assert saat == "17", "TR 20:00 icin UTC 17 olmali, %s bulundu" % saat
    assert dakika == "0"
    assert gun == "1-5", "hafta ici olmali"


def test_yazma_izni_var(akis):
    """Veri dalina push edebilmek icin contents: write sart."""
    izinler = akis["jobs"]["topla"]["permissions"]
    assert izinler.get("contents") == "write"


def test_es_zamanli_calisma_engelli(akis):
    """Iki calisma ayni anda TEFAS'a giderse dakikada 6 siniri asilir."""
    assert "concurrency" in akis


def test_testler_toplamadan_once_kosuyor(akis):
    """Bozuk kodla veri yayimlamayalim."""
    adlar = [a.get("name", "") for a in akis["jobs"]["topla"]["steps"]]
    assert any("Test" in a for a in adlar)
    test_sirasi = next(i for i, a in enumerate(adlar) if "Test" in a)
    topla_sirasi = next(i for i, a in enumerate(adlar) if "topla" in a.lower())
    assert test_sirasi < topla_sirasi


def test_cikti_dogrulama_adimi_var(akis):
    """Bos ya da eksik bir JSON yayimlamak, hic yayimlamamaktan kotudur:
    kullanicilar eski veriyi gormeye devam etsin."""
    adlar = [a.get("name", "") for a in akis["jobs"]["topla"]["steps"]]
    assert any("dogrula" in a.lower() for a in adlar)


def test_zaman_asimi_makul(akis):
    """Tam dolum ~30 dakika; onbellek kacarsa yetecek sure olmali."""
    dk = akis["jobs"]["topla"]["timeout-minutes"]
    assert dk >= 45


def test_veritabani_onbellege_aliniyor(akis):
    """Onbellek olmazsa her calisma 30 dakikalik tam dolum yapar."""
    adimlar = akis["jobs"]["topla"]["steps"]
    onbellek = [a for a in adimlar if "cache" in str(a.get("uses", ""))]
    assert onbellek, "veritabani onbellege alinmiyor"
    assert "fon_gecmis.db" in onbellek[0]["with"]["path"]
