# -*- coding: utf-8 -*-
"""TEFAS yeni API istemcisi.

TEFAS Nisan 2026'da Next.js altyapisina gecti; eski /api/DB/* uclari 404
donuyor. Yeni uclar POST + JSON govde ister ve Origin/Referer basligi
olmadan calismaz.

Neden pytefas degil de kendi istemcimiz: pytefas kategori filtresini
(sfonTurKod) disari acmiyor. Ayri bir istemci daha yazsaydik iki istemci
birbirinden habersiz istek atip dakikada 6 sinirini asardi. Tek bir
HizSinirlayici uzerinden gecen tek istemci sart.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta

TEMEL = "https://www.tefas.gov.tr/api/funds"
BILGI_UCU = TEMEL + "/fonGnlBlgSiraliGetir"
TUR_UCU = TEMEL + "/fonTurGetir"
DAGILIM_UCU = TEMEL + "/dagilimSiraliGetirT"

# API tek istekte en fazla ~1 ay veriyor. 28 gun koruyucu esik.
AZAMI_GUN = 28

# Fon tipleri. GYF/GSYF disarida: gayrimenkul ve girisim sermayesi fonlari
# seyrek fiyatlanir ve perakende yatirimciya TEFAS uzerinden normal sekilde
# satilmaz; siralamaya sokmak yaniltici olur.
FON_TIPLERI = ("YAT", "EMK", "BYF")

FON_TIPI_ADI = {
    "YAT": "Yatirim Fonu",
    "EMK": "Emeklilik Fonu",
    "BYF": "Borsa Yatirim Fonu",
}

BASLIKLAR = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Origin": "https://www.tefas.gov.tr",
    "Referer": "https://www.tefas.gov.tr/tr/fon-verileri",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
}


class TefasHatasi(Exception):
    """Kullaniciya gosterilebilir TEFAS hatasi."""

    def __init__(self, mesaj, oneri="", teknik=""):
        super().__init__(mesaj)
        self.mesaj = mesaj
        self.oneri = oneri
        self.teknik = teknik

    def __str__(self):
        p = [self.mesaj]
        if self.oneri:
            p.append(self.oneri)
        if self.teknik:
            p.append("(" + self.teknik + ")")
        return " ".join(p)


class HizSinirlayici:
    """TEFAS dakikada 6 istek kabul eder.

    Jeton kovasi degil, kayan pencere: son 60 saniyedeki istek zamanlarini
    tutar, 6'ya ulasildiginda en eskisinin dusmesini bekler. Kovadan daha
    guvenli cunku patlama (burst) yapmiyor.
    """

    def __init__(self, azami=6, pencere=62.0):
        self.azami = azami
        self.pencere = pencere  # 60 degil 62: sunucu saatiyle sapma payi
        self._zamanlar = []

    def bekle(self):
        simdi = time.monotonic()
        self._zamanlar = [t for t in self._zamanlar if simdi - t < self.pencere]
        beklenen = 0.0
        if len(self._zamanlar) >= self.azami:
            beklenen = self.pencere - (simdi - self._zamanlar[0]) + 0.5
            if beklenen > 0:
                time.sleep(beklenen)
            simdi = time.monotonic()
            self._zamanlar = [t for t in self._zamanlar if simdi - t < self.pencere]
        self._zamanlar.append(time.monotonic())
        return beklenen


@dataclass
class Kayit:
    """Tek bir (fon, tarih) gozlemi."""
    tarih: str
    fon_kodu: str
    fon_tipi: str
    fon_adi: str
    fiyat: float
    pay_sayisi: float | None
    kisi_sayisi: int | None
    portfoy_buyukluk: float | None


class Istemci:
    def __init__(self, zaman_asimi=60, azami_deneme=5, sinirlayici=None,
                 sessiz=False):
        self.zaman_asimi = zaman_asimi
        self.azami_deneme = azami_deneme
        self.sinirlayici = sinirlayici or HizSinirlayici()
        self.sessiz = sessiz
        self.istek_sayisi = 0

    def _yaz(self, s):
        if not self.sessiz:
            print(s, flush=True)

    def _gonder(self, url, govde):
        """Hiz sinirina uyarak POST eder, JSON dondurur."""
        son_hata = ""
        for deneme in range(self.azami_deneme):
            beklendi = self.sinirlayici.bekle()
            if beklendi > 1:
                self._yaz("    (hiz siniri: %.0f sn beklendi)" % beklendi)
            istek = urllib.request.Request(
                url, data=json.dumps(govde).encode("utf-8"), headers=BASLIKLAR)
            try:
                self.istek_sayisi += 1
                with urllib.request.urlopen(istek, timeout=self.zaman_asimi) as y:
                    ham = y.read().decode("utf-8")
                if not ham.strip():
                    son_hata = "bos yanit"
                    time.sleep(15)
                    continue
                return json.loads(ham)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    son_hata = "HTTP 429 (hiz siniri)"
                    time.sleep(30)
                    continue
                if e.code == 404:
                    # Ucun kendisi yok: tekrar denemek anlamsiz.
                    raise TefasHatasi(
                        "TEFAS bu adresi tanimadi.",
                        "API yapisi degismis olabilir.",
                        "HTTP 404 " + url)
                son_hata = "HTTP %d" % e.code
                time.sleep(min(2 ** deneme, 30))
            except (urllib.error.URLError, TimeoutError) as e:
                son_hata = "%s: %s" % (type(e).__name__, e)
                time.sleep(min(2 ** deneme, 30))
            except json.JSONDecodeError as e:
                son_hata = "JSON cozulemedi: %s" % e
                time.sleep(15)
        raise TefasHatasi(
            "TEFAS'a ulasilamadi.",
            "Internet baglantini kontrol et; sorun surerse TEFAS gecici "
            "olarak kapali olabilir.",
            "%d deneme, son hata: %s" % (self.azami_deneme, son_hata))

    @staticmethod
    def _govde(**ek):
        """API'nin bekledigi tam govde. Eksik alan gonderirsen bos donuyor."""
        g = {
            "fonTipi": "YAT", "fonKodu": None, "aramaMetni": None,
            "fonTurKod": None, "fonGrubu": None, "sfonTurKod": None,
            "fonTurAciklama": None, "kurucuKod": None,
            "basTarih": None, "bitTarih": None,
            "basSira": 1, "bitSira": 100000, "dil": "TR",
            "sFonTurKod": "", "fonKod": "", "fonGrup": "", "fonUnvanTip": "",
        }
        g.update(ek)
        return g

    # ---------------- kategoriler ----------------

    def kategorileri_getir(self):
        """Semsiye fon turlerini (kod, ad) listesi olarak dondurur."""
        d = self._gonder(TUR_UCU, {"dil": "TR"})
        satirlar = d.get("resultList") or []
        return [(int(s["sfonTuru"]), s["sfonTurAciklama"]) for s in satirlar
                if s.get("sfonTuru") is not None]

    def kategorideki_fonlar(self, fon_tipi, kategori_kod, gun):
        """Bir kategorideki fon kodlarini dondurur.

        Kategori bilgisi fiyat yanitinda GELMIYOR; ogrenmenin tek yolu
        kategoriye gore filtreleyip donen kodlari etiketlemek.
        """
        g = self._govde(fonTipi=fon_tipi, sfonTurKod=kategori_kod,
                        basTarih=gun.strftime("%Y%m%d"),
                        bitTarih=gun.strftime("%Y%m%d"))
        d = self._gonder(BILGI_UCU, g)
        satirlar = d.get("resultList") or []
        return sorted({s["fonKodu"] for s in satirlar if s.get("fonKodu")})

    # ---------------- varlik dagilimi ----------------

    def dagilimlar(self, fon_tipi, gun):
        """Verilen gun icin TUM fonlarin portfoy dagilimini dondurur.

        {fon_kodu: {alan_kodu: yuzde}} seklinde.

        DIKKAT: bu ucta da `fonKodu` filtresi YOK SAYILIYOR. Tek fon
        istedigimizi sanip donen ilk satiri okursak bambaska bir fonun
        dagilimini gostermis oluruz - bir Amerika hisse fonuna "portfoyu
        repo ve mevduat" dedirtir. O yuzden hepsini cekip kodla eslestir.
        """
        g = self._govde(fonTipi=fon_tipi,
                        basTarih=gun.strftime("%Y%m%d"),
                        bitTarih=gun.strftime("%Y%m%d"))
        d = self._gonder(DAGILIM_UCU, g)
        hata = d.get("errorMessage")
        if hata and not any(m in hata.lower()
                            for m in ("out of bounds", "veri bulunamadi")):
            raise TefasHatasi("TEFAS hata dondurdu.", "", hata)

        cikti = {}
        for s in (d.get("resultList") or []):
            kod = s.get("fonKodu")
            if kod:
                cikti[kod] = s
        return cikti

    # ---------------- fiyatlar ----------------

    def fiyatlar(self, fon_tipi, baslangic, bitis):
        """Verilen araliktaki TUM fonlarin fiyatlarini dondurur.

        Aralik 28 gunden uzunsa otomatik parcalanir. Fon basina degil, tarih
        araligi basina istek atilir: 2038 fon tek cagrida geliyor.
        """
        if baslangic > bitis:
            raise ValueError("baslangic bitisten sonra olamaz")
        kayitlar = []
        p_bas = baslangic
        while p_bas <= bitis:
            p_bit = min(p_bas + timedelta(days=AZAMI_GUN - 1), bitis)
            g = self._govde(fonTipi=fon_tipi,
                            basTarih=p_bas.strftime("%Y%m%d"),
                            bitTarih=p_bit.strftime("%Y%m%d"))
            d = self._gonder(BILGI_UCU, g)

            hata = d.get("errorMessage")
            # Tatil/hafta sonu icin API "Index 0 out of bounds" gibi mesajlar
            # donebiliyor; bu hata degil, "veri yok" demek.
            if hata and not any(m in hata.lower()
                                for m in ("out of bounds", "veri bulunamadi")):
                raise TefasHatasi("TEFAS hata dondurdu.", "", hata)

            for s in (d.get("resultList") or []):
                if s.get("fiyat") is None or not s.get("fonKodu"):
                    continue
                kayitlar.append(Kayit(
                    tarih=s["tarih"], fon_kodu=s["fonKodu"], fon_tipi=fon_tipi,
                    fon_adi=(s.get("fonUnvan") or "").strip(),
                    fiyat=float(s["fiyat"]),
                    pay_sayisi=s.get("tedPaySayisi"),
                    kisi_sayisi=s.get("kisiSayisi"),
                    portfoy_buyukluk=s.get("portfoyBuyukluk"),
                ))
            self._yaz("    %s - %s: toplam %d kayit" % (p_bas, p_bit, len(kayitlar)))
            p_bas = p_bit + timedelta(days=1)
        return kayitlar
