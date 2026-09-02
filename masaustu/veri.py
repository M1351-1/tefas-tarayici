# -*- coding: utf-8 -*-
"""Masaustu surumunun veri katmani.

MOBILDEN FARKI: AGA CIKMAZ.
===========================

Telefon uygulamasi hazir JSON'u GitHub'dan indiriyor cunku toplayici
baska bir makinede calisiyor. Masaustunde ise toplayicinin kendisi ayni
bilgisayarda: `data/fonlar.json` ve `data/fon_gecmis.db` yaninizda duruyor.

Bu yuzden burada indirme yok. Iki sonucu var:

  1. Aninda acilir, internet gerekmez.
  2. Veri her zaman SIZIN son topladiginiz kadar tazedir - uzaktaki
     depoya push edilmis olmasi gerekmez.

Fiyat gecmisi dogrudan SQLite'tan okunur; mobildeki gibi fon basina ayri
JSON dosyasi uretmeye gerek yok.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

def _kok() -> Path:
    """data/ klasorunun bulundugu kok dizin.

    PAKETLENMIS HALDE __file__ KULLANILAMAZ.
    ========================================

    PyInstaller tek dosyalik exe'yi calistirirken kaynaklari gecici bir
    klasore acar (%TEMP%\\_MEIxxxxx). Orada `masaustu/veri.py` vardir ama
    `data/` YOKTUR — cunku veriyi bilerek pakete gommuyoruz: gomseydik
    her veri guncellemesinde yeniden derlemek gerekirdi.

    Yani `Path(__file__).parent.parent` paketlenmis halde gecici klasoru
    gosterir ve uygulama "veri bulunamadi" der. Uygulama ACILIR, cokmez —
    bu yuzden "exe calisiyor mu" testi bunu YAKALAMAZ. Sessiz bir bos
    ekran olurdu.

    Dogrusu: paketlenmisse exe'nin BULUNDUGU yere bak.
    """
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent

    # Paketlenmis halde exe genelde dist/ altinda durur ama data/ proje
    # kokundedir. Kullaniciyi "exe'yi su klasore tasi" diye ugrastirmak
    # yerine birkac makul yeri sirayla ariyoruz.
    exe = Path(sys.executable).resolve().parent
    for aday in (exe, exe.parent, exe.parent.parent):
        if (aday / "data" / "fonlar.json").exists():
            return aday
    # Hicbiri yoksa exe'nin yanini dondur: hata mesaji o yolu gosterip
    # kullaniciya nereye bakmasi gerektigini soyler.
    return exe


KOK = _kok()
VARSAYILAN_JSON = KOK / "data" / "fonlar.json"
VARSAYILAN_DB = KOK / "data" / "fon_gecmis.db"


@dataclass
class Durum:
    """Arayuzun gosterecegi her sey."""

    veri_tarihi: str = ""
    uretim_zamani: str = ""
    sorumluluk_notu: str = ""
    fonlar: list = field(default_factory=list)
    kategoriler: list = field(default_factory=list)
    sayilar: dict = field(default_factory=dict)
    olcut: dict | None = None
    ongoru_gucu: dict | None = None
    agirliklar: dict = field(default_factory=dict)
    hata: str = ""

    @property
    def yuklendi(self) -> bool:
        return bool(self.fonlar)


def yukle(json_yolu: Path | None = None) -> Durum:
    """fonlar.json'u okur. Dosya yoksa BOS DURUM doner, cokmez.

    Cokmemesi onemli: kullanici toplayiciyi hic calistirmamis olabilir ve
    o durumda uygulamanin acilip "once toplayiciyi calistir" demesi
    gerekir, kapanmasi degil.
    """
    yol = Path(json_yolu or VARSAYILAN_JSON)
    if not yol.exists():
        return Durum(hata=(
            "Veri dosyası bulunamadı:\n%s\n\n"
            "Önce toplayıcıyı çalıştırın:\n"
            "    python toplayici/topla.py gunluk" % yol))
    try:
        with open(yol, encoding="utf-8") as d:
            ham = json.load(d)
    except (OSError, json.JSONDecodeError) as hata:
        return Durum(hata="Veri dosyası okunamadı (%s): %s"
                          % (type(hata).__name__, yol))

    return Durum(
        veri_tarihi=ham.get("veri_tarihi", ""),
        uretim_zamani=ham.get("uretim_zamani", ""),
        sorumluluk_notu=ham.get("sorumluluk_notu", ""),
        fonlar=ham.get("fonlar") or [],
        kategoriler=ham.get("kategoriler") or [],
        sayilar=ham.get("sayilar") or {},
        olcut=ham.get("olcut"),
        ongoru_gucu=ham.get("ongoru_gucu"),
        agirliklar=(ham.get("ayarlar") or {}).get("agirliklar") or {},
    )


def fiyat_gecmisi(fon_kodu: str, gun: int = 400,
                  db_yolu: Path | None = None) -> list:
    """[(tarih, fiyat), ...] — dogrudan SQLite'tan.

    Mobilde bu veri fon basina ayri JSON dosyasindan geliyor (telefon
    108 MB'lik veritabanini indiremez). Masaustunde veritabani zaten
    burada; ara dosyaya gerek yok.
    """
    yol = Path(db_yolu or VARSAYILAN_DB)
    if not yol.exists():
        return []
    try:
        with sqlite3.connect("file:%s?mode=ro" % yol.as_posix(),
                             uri=True) as b:
            satirlar = b.execute(
                "SELECT tarih, fiyat FROM fiyat "
                "WHERE fon_kodu = ? AND fiyat > 0 "
                "ORDER BY tarih DESC LIMIT ?",
                (fon_kodu, gun),
            ).fetchall()
    except sqlite3.Error:
        return []
    return list(reversed(satirlar))


def kategori_listesi(durum: Durum) -> list:
    """(tip_ad, kategori_ad, adet) uclileri, sirali."""
    cikti = []
    for k in durum.kategoriler:
        cikti.append((k.get("tip_ad", k.get("tip", "?")),
                      k.get("ad", "?"), k.get("adet", 0)))
    return sorted(cikti)


# TURKCE ARAMA KATLAMASI.
#
# Python'un lower() metodu Turkce buyuk I icin YANLIS calisir:
# "PIYASASI".lower() -> "pi̇yasasi" (i + BIRLESTIRICI UST NOKTA).
# Kullanicinin yazdigi duz "piyasasi" bununla ESLESMEZ ve arama sessizce
# bos doner. Turkce fon adlarinin neredeyse hepsinde I, S, G var, yani
# bu tek basina aramayi kullanilmaz hale getiriyordu.
#
# Cozum: iki tarafi da ASCII'ye katla. Yan faydasi, kullanicinin
# "gunluk" yazip "GUNLUK" bulabilmesi - Turkce klavyesi olmayan ya da
# aceleyle yazan biri icin dogru davranis.
_KATLAMA = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "i": "i",
    "Ş": "s", "ş": "s",
    "Ğ": "g", "ğ": "g",
    "Ü": "u", "ü": "u",
    "Ö": "o", "ö": "o",
    "Ç": "c", "ç": "c",
    "̇": "",          # birlestirici ust nokta: lower()'in biraktigi iz
})


def katla(metin: str) -> str:
    """Arama karsilastirmasi icin metni Turkce-duyarli bicimde katlar."""
    return (metin or "").translate(_KATLAMA).lower()


def suz(durum: Durum, arama: str = "", kategori: str = "",
        tip: str = "", yalniz_puanli: bool = True) -> list:
    """Fon listesini suzer.

    Arama hem KODA hem ADA bakar: kullanici "TI1" de yazabilir
    "para piyasasi" da.
    """
    arama = katla((arama or "").strip())
    sonuc = []
    for f in durum.fonlar:
        if yalniz_puanli and f.get("getiri_puani") is None:
            continue
        if kategori and f.get("kategori") != kategori:
            continue
        if tip and f.get("tip") != tip:
            continue
        if arama:
            if (arama not in katla(f.get("kod") or "")
                    and arama not in katla(f.get("ad") or "")):
                continue
        sonuc.append(f)
    return sonuc
