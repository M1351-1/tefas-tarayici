# -*- coding: utf-8 -*-
"""SQLite deposu.

Fiyat gecmisini ve fon->kategori haritasini tutar. Ayni gunu iki kez
cekersen ustune yazar (INSERT OR REPLACE), tekrar kayit olusmaz.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SEMA = """
CREATE TABLE IF NOT EXISTS fiyat (
    tarih            TEXT NOT NULL,
    fon_kodu         TEXT NOT NULL,
    fon_tipi         TEXT NOT NULL,
    fon_adi          TEXT,
    fiyat            REAL NOT NULL,
    pay_sayisi       REAL,
    kisi_sayisi      INTEGER,
    portfoy_buyukluk REAL,
    PRIMARY KEY (fon_kodu, tarih)
);
CREATE INDEX IF NOT EXISTS ix_fiyat_tarih ON fiyat(tarih);

CREATE TABLE IF NOT EXISTS kategori (
    fon_kodu     TEXT PRIMARY KEY,
    kategori_kod INTEGER NOT NULL,
    kategori_ad  TEXT NOT NULL,
    guncelleme   TEXT NOT NULL
);

-- Portfoy varlik dagilimi. Sadece EN SON gun tutulur (bkz. dagilim.py):
-- gecmise donuk dagilim ne gosteriliyor ne de puanlamaya giriyor.
CREATE TABLE IF NOT EXISTS dagilim (
    fon_kodu   TEXT NOT NULL,
    alan       TEXT NOT NULL,
    yuzde      REAL NOT NULL,
    tarih      TEXT NOT NULL,
    PRIMARY KEY (fon_kodu, alan)
);

-- Cekim gecmisi: neyin ne zaman alindigini bilmek, "bugun cektim mi"
-- sorusunu API'ye sormadan cevaplamayi saglar.
CREATE TABLE IF NOT EXISTS cekim (
    zaman     TEXT NOT NULL,
    fon_tipi  TEXT NOT NULL,
    baslangic TEXT NOT NULL,
    bitis     TEXT NOT NULL,
    kayit     INTEGER NOT NULL
);
"""


class Depo:
    def __init__(self, yol):
        self.yol = Path(yol)
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        self.baglanti = sqlite3.connect(str(self.yol))
        self.baglanti.row_factory = sqlite3.Row
        # WAL: uzun surecek dolum sirasinda okuma yapilabilsin.
        self.baglanti.execute("PRAGMA journal_mode=WAL")
        self.baglanti.executescript(SEMA)
        self.baglanti.commit()

    def kapat(self):
        self.baglanti.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kapat()

    # ---------------- yazma ----------------

    def fiyat_yaz(self, kayitlar):
        """Kayit listesini yazar, yazilan satir sayisini dondurur."""
        if not kayitlar:
            return 0
        veri = [(k.tarih, k.fon_kodu, k.fon_tipi, k.fon_adi, k.fiyat,
                 k.pay_sayisi, k.kisi_sayisi, k.portfoy_buyukluk)
                for k in kayitlar]
        self.baglanti.executemany(
            "INSERT OR REPLACE INTO fiyat "
            "(tarih, fon_kodu, fon_tipi, fon_adi, fiyat, pay_sayisi, "
            " kisi_sayisi, portfoy_buyukluk) VALUES (?,?,?,?,?,?,?,?)", veri)
        self.baglanti.commit()
        return len(veri)

    def kategori_temizle(self):
        """Kategori tablosunu bosaltir.

        Yeniden eslemeden once sart: eski bir hatali esleme, yeni eslemede
        yer almayan fonlar icin tabloda kalir ve sessizce yanlis kategori
        gostermeye devam eder.
        """
        self.baglanti.execute("DELETE FROM kategori")
        self.baglanti.commit()

    def kategori_yaz(self, esleme, zaman):
        """esleme: {fon_kodu: (kategori_kod, kategori_ad)}"""
        if not esleme:
            return 0
        veri = [(k, v[0], v[1], zaman) for k, v in esleme.items()]
        self.baglanti.executemany(
            "INSERT OR REPLACE INTO kategori "
            "(fon_kodu, kategori_kod, kategori_ad, guncelleme) "
            "VALUES (?,?,?,?)", veri)
        self.baglanti.commit()
        return len(veri)

    def dagilim_yaz(self, kalemler, tarih):
        """kalemler: {fon_kodu: [(alan_kodu, etiket, yuzde), ...]}

        Once tabloyu bosaltir: bir fonun portfoyunden cikan varlik sinifi,
        eski satir kalirsa sonsuza kadar gorunmeye devam ederdi.
        """
        self.baglanti.execute("DELETE FROM dagilim")
        veri = [(kod, alan, yuzde, tarih)
                for kod, liste in kalemler.items()
                for alan, _etiket, yuzde in liste]
        if veri:
            self.baglanti.executemany(
                "INSERT OR REPLACE INTO dagilim (fon_kodu, alan, yuzde, tarih) "
                "VALUES (?,?,?,?)", veri)
        self.baglanti.commit()
        return len(veri)

    def dagilim_haritasi(self):
        """{fon_kodu: [(alan_kodu, yuzde), ...]} - buyukten kucuge."""
        harita = {}
        for r in self.baglanti.execute(
                "SELECT fon_kodu, alan, yuzde FROM dagilim "
                "ORDER BY fon_kodu, yuzde DESC"):
            harita.setdefault(r["fon_kodu"], []).append((r["alan"], r["yuzde"]))
        return harita

    def cekim_kaydet(self, zaman, fon_tipi, baslangic, bitis, kayit):
        self.baglanti.execute(
            "INSERT INTO cekim (zaman, fon_tipi, baslangic, bitis, kayit) "
            "VALUES (?,?,?,?,?)",
            (zaman, fon_tipi, str(baslangic), str(bitis), kayit))
        self.baglanti.commit()

    # ---------------- okuma ----------------

    def en_son_tarih(self, fon_tipi=None):
        if fon_tipi:
            s = self.baglanti.execute(
                "SELECT MAX(tarih) t FROM fiyat WHERE fon_tipi=?",
                (fon_tipi,)).fetchone()
        else:
            s = self.baglanti.execute("SELECT MAX(tarih) t FROM fiyat").fetchone()
        return s["t"]

    def fon_sayisi(self):
        return self.baglanti.execute(
            "SELECT COUNT(DISTINCT fon_kodu) n FROM fiyat").fetchone()["n"]

    def kayit_sayisi(self):
        return self.baglanti.execute(
            "SELECT COUNT(*) n FROM fiyat").fetchone()["n"]

    def kategori_haritasi(self):
        """{fon_kodu: (kod, ad)}"""
        return {r["fon_kodu"]: (r["kategori_kod"], r["kategori_ad"])
                for r in self.baglanti.execute(
                    "SELECT fon_kodu, kategori_kod, kategori_ad FROM kategori")}

    def fon_listesi(self):
        """Her fonun son gozlemi: kod, tip, ad, kisi sayisi, buyukluk."""
        return [dict(r) for r in self.baglanti.execute("""
            SELECT f.fon_kodu, f.fon_tipi, f.fon_adi, f.tarih,
                   f.fiyat, f.kisi_sayisi, f.portfoy_buyukluk
            FROM fiyat f
            JOIN (SELECT fon_kodu, MAX(tarih) mt FROM fiyat GROUP BY fon_kodu) s
              ON f.fon_kodu = s.fon_kodu AND f.tarih = s.mt
            ORDER BY f.fon_kodu
        """)]

    def fiyat_serisi(self, fon_kodu):
        """[(tarih, fiyat), ...] eskiden yeniye."""
        return [(r["tarih"], r["fiyat"]) for r in self.baglanti.execute(
            "SELECT tarih, fiyat FROM fiyat WHERE fon_kodu=? ORDER BY tarih",
            (fon_kodu,))]

    def tum_seriler(self):
        """{fon_kodu: [(tarih, fiyat), ...]} - tek sorguda, hizli."""
        seriler = {}
        for r in self.baglanti.execute(
                "SELECT fon_kodu, tarih, fiyat FROM fiyat "
                "ORDER BY fon_kodu, tarih"):
            seriler.setdefault(r["fon_kodu"], []).append((r["tarih"], r["fiyat"]))
        return seriler
