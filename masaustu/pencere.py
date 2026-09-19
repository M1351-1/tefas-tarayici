# -*- coding: utf-8 -*-
"""TEFAS Fon Tarayici — masaustu arayuzu.

NEDEN PySide6, FLUTTER DESKTOP DEGIL
====================================

Flutter'in Windows hedefi "Desktop development with C++" is yukunu
gerektiriyor: ~6 GB'lik Visual Studio kurulumu. Oysa bu projenin zaten
bir Python tarafi var (toplayici/) ve konut zamanlayici da PySide6 +
PyInstaller ile paketleniyor. Ayni yontemi kullanmak hem ek kurulum
gerektirmiyor hem iki uygulama ayni gorunume sahip oluyor.

TASARIM: konut-zamanlayici ile AYNI tema dosyasi kullaniliyor.

IKI EKSEN
=========

Tablo tek bir "puan" yerine iki ayri sutun gosterir:

  GETIRI   — gecmisin tasviri. Olculdu: ileri Spearman ~0, ust %20
             dilimle alt %20 dilimin uc aylik getirisi ayni. Bu sutun
             gelecege dair bir iddia TASIMAZ.
  SAKINLIK — akranlarina gore oynaklik (%60) + maksimum dusus (%40).
             Olculdu: bu BILESIMIN siralamasi uc ayri orneklemde de
             surdu (ileri Spearman 0,67-0,73). Getiri ekseni ayni
             orneklemlerde 0,02-0,15 arasinda savruluyor — yani Sakinlik
             hem guclu hem TEKRARLANABILIR. Yine de olcum ~14 aylik tek
             bir piyasa rejiminden ve 3 ortusmeyen pencereden geliyor;
             "her zaman kalicidir" DEGIL.

Bu bir yatirim tavsiyesi araci degildir.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import grafik, tema, veri

# SUTUN DUZENI — ASIL SUTUNLAR EKRANDA KALMALI.
#
# Once "Ad" 230, "Kategori" 150 piksel idi; toplam ~1010 piksel. Saga
# eklenen detay paneliyle birlikte tablo yatay kaydirmaya dusuyor ve
# uygulamanin ASIL iki sutunu (Getiri, Sakinlik) varsayilan gorunumde
# HIC gorunmuyordu. Liste getiri puanina gore sirali aciliyor ama o
# sutun ekranda olmadigi icin ust satirlarin NEDEN ustte oldugu
# belirsiz kaliyordu.
#
# "Ad" kisaltildi (tam ad detay panelinde ve satir ipucunda duruyor),
# "Kategori" daraltildi; kazanilan yer puan sutunlarina verildi.
#
# ETIKETLER NE OLDUKLARINI SOYLUYOR. "Getiri" tek basina bir KALITE
# puani gibi okunuyordu. Olculdu: gecmis getiriye gore siralamanin ileri
# Spearman'i 0,01 ve ust %20 dilim alt %20 dilimin ALTINDA kaliyor —
# yani bu sutun gelecege dair bilgi tasimiyor, gecmisi TASVIR ediyor.
# Eksik risk bileseninin okunur adi (tablo ipucunda).
EKSIK_ADLARI = {"volatilite": "oynaklik", "maks_dusus": "en buyuk dusus"}

SUTUNLAR = [
    ("kod", "Fon", 62),
    ("ad", "Ad", 150),
    ("kategori", "Kategori", 112),
    ("gunluk", "Günlük", 70),
    ("aylik", "Aylık", 70),
    ("uc_aylik", "3 Aylık", 74),
    ("yillik", "Yıllık", 74),
    ("volatilite", "Oynaklık", 76),
    ("getiri_puani", "Geçmiş getiri", 104),
    ("risk_puani", "Sakinlik", 84),
]


class AnaPencere(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TEFAS Fon Tarayıcı")
        self.resize(1400, 880)
        self.setStyleSheet(tema.STIL)

        self.durum = veri.Durum()
        # VARSAYILAN SIRALAMA: olculen tek KALICI eksen.
        #
        # Once `getiri_puani` idi. Uygulama o siralamanin gelecegi
        # tutmadigini KENDI olcuyor (ileri Spearman 0,01; ust %20 dilim
        # alt %20 dilimin ALTINDA) ve ekrana yaziyor — ama liste tam o
        # sutuna gore sirali aciliyordu. Tablo arayuzunde en ust satir
        # "en iyisi" diye okunur; yanindaki aciklama metni bunu telafi
        # etmiyor.
        #
        # Sakinlik ise kategori icinde olculdugunde kalici (0,71). Ama
        # bu da "en iyi fon" DEMEK DEGIL: hisse fonunda dusuk oynaklik,
        # fonun isini yapmamasi da olabilir. O yuzden asil duzeltme
        # varsayilani degistirmek degil, siralamanin NE OLDUGUNU
        # gorunur kilmak (bkz. _siralama_etiketi).
        self._sirala_sutun = "risk_puani"
        self._azalan = True

        merkez = QWidget()
        self.setCentralWidget(merkez)
        d = QVBoxLayout(merkez)
        d.setContentsMargins(16, 14, 16, 10)
        d.setSpacing(10)

        d.addWidget(self._ust_cubuk())
        # OLCUM EKRANDA OLMALI.
        #
        # Uygulama siralamanin gelecegi tutup tutmadigini HER TOPLAMADA
        # olcuyor ve sonucu JSON'a yaziyordu — ama ekranda hicbir yerde
        # gostermiyordu. Kullanici listeyi "en iyiden kotuye" diye
        # okuyup gidiyordu. Bulgunun degeri, gorunur olmasina bagli.
        d.addWidget(self._ongoru_seridi())
        d.addWidget(self._suzgec_cubugu())

        bolucu = QSplitter(Qt.Orientation.Horizontal)
        bolucu.addWidget(self._tablo_kur())
        bolucu.addWidget(self._detay_kur())
        bolucu.setStretchFactor(0, 3)
        bolucu.setStretchFactor(1, 2)
        # Detay paneli 420 pikselin altina inmesin: iki eksen yan yana
        # sigmayinca metinler kesiliyordu.
        bolucu.setSizes([900, 480])
        bolucu.setCollapsible(1, False)
        d.addWidget(bolucu, 1)

        self.durum_cubugu = self.statusBar()
        self.durum_cubugu.showMessage("Yükleniyor…")

        # Pencere GORUNDUKTEN sonra yukle: 2500 fonluk tabloyu doldurmak
        # bir saniye surebiliyor ve o sure boyunca pencere hic
        # gorunmezse kullanici "acilmiyor" der.
        QTimer.singleShot(50, self._yukle)

    # ------------------------------------------------------------ kurulum

    def _ust_cubuk(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        d = QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        self.baslik = tema.etiket("TEFAS Fon Tarayıcı", boyut=17, kalin=True,
                                  sar=False)
        d.addWidget(self.baslik)
        d.addStretch(1)
        self.tazelik = tema.etiket("", boyut=12, renk=tema.METIN_SOLUK,
                                   sar=False)
        d.addWidget(self.tazelik)
        return w

    def _ongoru_seridi(self) -> QWidget:
        """Olculen ongoru gucunu tek satirda, renkle bildirir.

        Metin `veri.Durum.ongoru_gucu` icinden gelir; burada yeniden
        yorum URETILMEZ. Toplayici ne olctuyse o yazilir.
        """
        self.ongoru_kutusu = QWidget()
        self.ongoru_kutusu.setObjectName("ongoruSerit")
        d = QVBoxLayout(self.ongoru_kutusu)
        d.setContentsMargins(12, 9, 12, 9)
        d.setSpacing(3)
        self.ongoru_baslik = tema.etiket("", boyut=12, kalin=True, sar=False)
        self.ongoru_metin = tema.etiket("", boyut=11,
                                        renk=tema.METIN_SOLUK)
        d.addWidget(self.ongoru_baslik)
        d.addWidget(self.ongoru_metin)
        self.ongoru_kutusu.setVisible(False)
        return self.ongoru_kutusu

    def _ongoru_seridini_doldur(self) -> None:
        og = self.durum.ongoru_gucu or {}
        ozet = (og.get("ozet") or "").strip()
        if not ozet:
            self.ongoru_kutusu.setVisible(False)
            return
        calisiyor = og.get("durum") == "calisiyor"
        renk = tema.UYARI if not calisiyor else tema.IYI
        self.ongoru_baslik.setText(
            "SIRALAMA SINANDI — geçmiş getiriye göre sıralama geleceği "
            "tutmuyor" if not calisiyor
            else "SIRALAMA SINANDI — bir miktar öngörü gücü ölçüldü")
        self.ongoru_baslik.setStyleSheet("color: %s;" % renk)
        self.ongoru_metin.setText(ozet)
        self.ongoru_kutusu.setStyleSheet(
            "#ongoruSerit { background: %s; border: 1px solid %s; "
            "border-radius: 8px; }" % (tema.KART, renk))
        self.ongoru_kutusu.setVisible(True)


    # OLCUTUN NE ANLAMA GELDIGI, SIRALAMANIN YANINDA.
    #
    # Her olcut icin ayri bir cumle: kullanici "Gecmis getiri"ye gore
    # siralarsa bunun bir tavsiye olmadigini AYNI ANDA gormeli.
    SIRALAMA_NOTU = {
        "risk_puani": "Sakinlik — ölçümde sürekliliği gösterilen tek eksen. "
                      "“En iyi fon” demek değil: hisse fonunda düşük "
                      "oynaklık, fonun işini yapmaması da olabilir.",
        "getiri_puani": "Geçmiş getiri — ölçüldü, geleceği TUTMUYOR. "
                        "Bu sıralama bir tavsiye değildir.",
        "volatilite": "Oynaklık — ham ölçüm, akranlarına göre "
                      "düzeltilmemiştir.",
    }

    def _siralama_etiketini_yenile(self) -> None:
        alan = self._sirala_sutun
        baslik = next((b for a, b, _ in SUTUNLAR if a == alan), alan)
        yon = "azalan" if self._azalan else "artan"
        notu = self.SIRALAMA_NOTU.get(alan, "")
        self.siralama_etiketi.setText(
            "Sıralama: %s (%s)%s" % (baslik, yon, "  ·  " + notu if notu else ""))
        self.siralama_etiketi.setToolTip(notu)

    def _suzgec_cubugu(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        d = QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(10)

        self.arama = QLineEdit()
        self.arama.setPlaceholderText("Fon kodu veya adı ara…")
        self.arama.setMinimumWidth(260)
        self.arama.textChanged.connect(self._tabloyu_doldur)
        d.addWidget(self.arama)

        self.tip_secici = QComboBox()
        self.tip_secici.addItem("Tüm fon tipleri", "")
        self.tip_secici.currentIndexChanged.connect(self._tabloyu_doldur)
        d.addWidget(self.tip_secici)

        self.kategori_secici = QComboBox()
        self.kategori_secici.addItem("Tüm kategoriler", "")
        self.kategori_secici.setMinimumWidth(220)
        self.kategori_secici.currentIndexChanged.connect(self._tabloyu_doldur)
        d.addWidget(self.kategori_secici)

        d.addStretch(1)
        self.sayac = tema.etiket("", boyut=12, renk=tema.METIN_SOLUK,
                                 sar=False)
        d.addWidget(self.sayac)
        # SIRALAMA ARTIK ORTULU DEGIL.
        #
        # Hangi olcute gore sirali oldugu yazili degildi; kullanici
        # ustteki satiri "en iyi fon" sanabiliyordu. Simdi olcut ve
        # "tavsiye degil" uyarisi ayni satirda duruyor.
        self.siralama_etiketi = tema.etiket("", boyut=11,
                                            renk=tema.METIN_SOLUK, sar=False)
        d.addWidget(self.siralama_etiketi)
        return w

    def _tablo_kur(self) -> QWidget:
        self.tablo = QTableWidget(0, len(SUTUNLAR))
        self.tablo.setHorizontalHeaderLabels([b for _, b, _ in SUTUNLAR])
        self.tablo.verticalHeader().hide()
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tablo.setAlternatingRowColors(False)
        self.tablo.setShowGrid(False)
        basliklar = self.tablo.horizontalHeader()
        for i, (_, _, genislik) in enumerate(SUTUNLAR):
            self.tablo.setColumnWidth(i, genislik)
        # AD SUTUNU STRETCH DEGIL SABIT.
        #
        # Stretch iken pencere daraldiginda ad sutunu once eziliyordu ve
        # "PUSU...", "HEDE..." gibi okunmaz hale geliyordu. Fon adi bu
        # tablodaki en bilgilendirici sutun; sabit tutulup gerekirse
        # tablo yatay kaydiriliyor.
        basliklar.setSectionResizeMode(1, QHeaderView.Interactive)
        basliklar.setStretchLastSection(False)
        basliklar.setMinimumSectionSize(56)
        basliklar.setSectionsClickable(True)
        basliklar.sectionClicked.connect(self._basliga_tiklandi)
        self.tablo.itemSelectionChanged.connect(self._secim_degisti)
        return self.tablo

    def _detay_kur(self) -> QWidget:
        kaydir = QScrollArea()
        kaydir.setWidgetResizable(True)
        ic = QWidget()
        self.detay_duzen = QVBoxLayout(ic)
        self.detay_duzen.setContentsMargins(14, 12, 14, 12)
        self.detay_duzen.setSpacing(10)
        self.detay_duzen.addWidget(
            tema.etiket("Soldan bir fon seçin.", renk=tema.METIN_SOLUK))
        self.detay_duzen.addStretch(1)
        kaydir.setWidget(ic)
        return kaydir

    # -------------------------------------------------------------- yukleme

    def _yukle(self) -> None:
        """Diskten okur, sonra ekrani doldurur.

        YUKLEME ILE CIZIM AYRI. Once ikisi tek metottaydi ve bu, arayuzu
        SINANAMAZ kiliyordu: test bir Durum verip cizimi dogrulamak
        isteyince metot diski okuyup verdigi durumu eziyordu. Bu
        projede "derlendi ama ekranda bir sey yok" hatasi iki kez
        yasandi; tek koruma cizimi gercekten cagiran bir test.
        """
        self.durum = veri.yukle()
        if self.durum.hata:
            self.durum_cubugu.showMessage("Veri yüklenemedi")
            self._detayi_temizle()
            self.detay_duzen.insertWidget(
                0, tema.not_kutusu(self.durum.hata, tema.UYARI))
            return
        self._ekrani_doldur()

    def _ekrani_doldur(self) -> None:
        """`self.durum`u ekrana yazar. Diske DOKUNMAZ."""
        tipler = sorted({(f.get("tip"), f.get("tip_ad"))
                         for f in self.durum.fonlar if f.get("tip")})
        for kod, ad in tipler:
            self.tip_secici.addItem(ad or kod, kod)
        for _, ad, _ in veri.kategori_listesi(self.durum):
            if self.kategori_secici.findText(ad) < 0:
                self.kategori_secici.addItem(ad, ad)

        s = self.durum.sayilar
        self.tazelik.setText(
            "Veri tarihi: %s   ·   %s fon puanlandı   ·   üretim %s"
            % (self.durum.veri_tarihi, s.get("puanlanan", "?"),
               (self.durum.uretim_zamani or "")[:16].replace("T", " ")))
        self._ongoru_seridini_doldur()
        self._siralama_etiketini_yenile()
        self._tabloyu_doldur()
        # UYARI CUMLESI ORTASINDAN KESILIYORDU.
        #
        # `[:160]` ile kirpiliyordu ve ekranda "...gelecek getiriyi
        # gosterme" diye yarim kaliyordu. Yarim kalan bir sorumluluk
        # notu, olmamasindan daha kotu: cumlenin nasil bittigini
        # kullanici tahmin ediyor. Tamami veriliyor; durum cubugu
        # sigdirmazsa ipucunda tam metin duruyor.
        not_metni = self.durum.sorumluluk_notu or ""
        self.durum_cubugu.showMessage(not_metni)
        self.durum_cubugu.setToolTip(not_metni)

    # --------------------------------------------------------------- tablo

    def _deger(self, f: dict, alan: str):
        if alan in ("gunluk", "aylik", "uc_aylik", "yillik"):
            return (f.get("getiri") or {}).get(alan)
        return f.get(alan)

    def _basliga_tiklandi(self, sutun: int) -> None:
        alan = SUTUNLAR[sutun][0]
        if alan == self._sirala_sutun:
            self._azalan = not self._azalan
        else:
            self._sirala_sutun = alan
            self._azalan = alan not in ("kod", "ad", "kategori")
        self._siralama_etiketini_yenile()
        self._tabloyu_doldur()

    def _tabloyu_doldur(self) -> None:
        if not self.durum.yuklendi:
            return
        liste = veri.suz(
            self.durum,
            arama=self.arama.text(),
            kategori=self.kategori_secici.currentData() or "",
            tip=self.tip_secici.currentData() or "",
        )

        alan = self._sirala_sutun

        def anahtar(f):
            v = self._deger(f, alan)
            if v is None:
                # Eksik deger HER ZAMAN sona: sirali listede basa gelmesi
                # "en iyi" gibi okunurdu.
                return (1, 0)
            return (0, -v if self._azalan and not isinstance(v, str) else v)

        liste.sort(key=anahtar)
        if self._azalan and alan in ("kod", "ad", "kategori"):
            liste.reverse()

        self.tablo.setRowCount(len(liste))
        self._satir_fonlari = liste
        for satir, f in enumerate(liste):
            for sutun, (a, _, _) in enumerate(SUTUNLAR):
                v = self._deger(f, a)
                oge = QTableWidgetItem(self._bicimle(a, v))
                if a in ("gunluk", "aylik", "uc_aylik", "yillik",
                         "volatilite", "getiri_puani", "risk_puani"):
                    oge.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                         | Qt.AlignmentFlag.AlignVCenter)
                renk = self._renk(a, v)
                if renk:
                    oge.setForeground(QColor(renk))
                # EKSIK BILESENLI PUAN ISARETLENIR.
                #
                # Risk puani, bileseni eksik oldugunda kalan agirliga
                # yeniden normalize ediliyor. Bu OLCEGI duzeltir ama
                # BELIRSIZLIGI yok etmez: tek bilesenden uretilmis bir
                # puan, iki bilesenden uretilmisle ayni sutunda kayitsizca
                # kiyaslanmamali. Uretici bunu JSON'a yaziyor; ekranda
                # gorunmuyordu.
                #
                # Gercek veride 17 fon boyle (2335'te) ve tam olarak
                # sifir fiyat / uzun bosluk iceren fonlar — yani en
                # supheli olanlar.
                if a == "risk_puani" and f.get("risk_eksik"):
                    oge.setText(oge.text() + " *")
                    oge.setToolTip(
                        "Bu puan eksik veriyle hesaplandi: %s "
                        "hesaplanamadi. Kalan bilesenden uretildi; tam "
                        "veriyle hesaplanmis puanlarla ayni guvende "
                        "degildir."
                        % ", ".join(EKSIK_ADLARI.get(m, m)
                                    for m in f["risk_eksik"]))
                self.tablo.setItem(satir, sutun, oge)

        self.sayac.setText("%d fon" % len(liste))

    @staticmethod
    def _bicimle(alan: str, v) -> str:
        if v is None:
            return "—"
        if alan in ("kod", "ad", "kategori"):
            return str(v)
        if alan in ("getiri_puani", "risk_puani"):
            return tema.sayi(v, 2)
        return "%%%s" % tema.sayi(v, 2)

    @staticmethod
    def _renk(alan: str, v) -> str:
        if v is None:
            return ""
        if alan in ("gunluk", "aylik", "uc_aylik", "yillik"):
            return tema.IYI if v > 0 else (tema.KOTU if v < 0 else "")
        if alan == "risk_puani":
            # Yuksek = daha sakin. Ama bu bir YARGI degil PROFIL: hisse
            # fonunda dusuk oynaklik, fonun isini yapmamasi da olabilir.
            # Bu yuzden yesil/kirmizi degil, VURGU tonu kullaniliyor.
            return tema.VURGU if v > 0 else tema.METIN_SOLUK
        if alan == "getiri_puani":
            return tema.METIN
        return ""

    # --------------------------------------------------------------- detay

    def _detayi_temizle(self) -> None:
        while self.detay_duzen.count():
            oge = self.detay_duzen.takeAt(0)
            if oge.widget():
                oge.widget().deleteLater()

    def _secim_degisti(self) -> None:
        satirlar = self.tablo.selectionModel().selectedRows()
        if not satirlar or not getattr(self, "_satir_fonlari", None):
            return
        i = satirlar[0].row()
        if i >= len(self._satir_fonlari):
            return
        self._detayi_goster(self._satir_fonlari[i])

    def _detayi_goster(self, f: dict) -> None:
        self._detayi_temizle()

        baslik = tema.Kart()
        baslik.ekle(tema.etiket(f.get("kod", ""), boyut=22, kalin=True,
                                renk=tema.VURGU, sar=False))
        baslik.ekle(tema.etiket(f.get("ad", ""), boyut=13))
        rozetler = QHBoxLayout()
        rozetler.setSpacing(6)
        rozetler.addWidget(tema.rozet(f.get("tip_ad", ""), tema.NOTR))
        rozetler.addWidget(tema.rozet(f.get("kategori", ""), tema.NOTR))
        if f.get("katilim"):
            rozetler.addWidget(tema.rozet("katılım", tema.VURGU))
        rozetler.addStretch(1)
        baslik.duzen.addLayout(rozetler)
        self.detay_duzen.addWidget(baslik)

        # IKI EKSEN YAN YANA — hangisinin ne anlama geldigi yazili.
        eksen = tema.Kart(
            "İki ayrı eksen",
            "Getiri geçmişin tasviridir; ölçülen öngörü gücü sıfıra yakın "
            "ve örneklemden örnekleme savruluyor (0,02-0,15). Sakinlik "
            "sıralaması ölçülen dönem boyunca sürdü ve tekrarlandı "
            "(0,67-0,73) — kat kat dayanıklı, ama tek dönemlik veriyle "
            "kalıcılık kanıtlanmış sayılmaz. Güncel sayılar üstteki "
            "ölçüm şeridinde.")
        satir = QHBoxLayout()
        satir.setSpacing(24)
        gp, rp = f.get("getiri_puani"), f.get("risk_puani")
        satir.addWidget(tema.buyuk_sayi(
            tema.sayi(gp, 2) if gp is not None else "—",
            "getiri puanı\nkategoride %s. / %s" % (
                f.get("getiri_sirasi", "?"), f.get("kategori_fon_sayisi", "?")),
            tema.METIN, en_az_genislik=150))
        satir.addWidget(tema.buyuk_sayi(
            tema.sayi(rp, 2) if rp is not None else "—",
            "sakinlik puanı\nkategoride %s." % f.get("risk_sirasi", "?"),
            tema.VURGU, en_az_genislik=150))
        satir.addStretch(1)
        eksen.duzen.addLayout(satir)
        self.detay_duzen.addWidget(eksen)

        # Fiyat grafigi
        gecmis = veri.fiyat_gecmisi(f.get("kod", ""))
        if len(gecmis) >= 2:
            g_kart = tema.Kart("Fiyat geçmişi",
                               "%d işlem günü" % len(gecmis))
            c = grafik.FiyatGrafigi(gecmis)
            c.setMinimumHeight(220)
            g_kart.ekle(c)
            self.detay_duzen.addWidget(g_kart)

        # Sayilar
        olculer = tema.Kart("Ölçümler")
        g = f.get("getiri") or {}
        for etiket, deger, birim in (
            ("Günlük getiri", g.get("gunluk"), "%"),
            ("Aylık getiri", g.get("aylik"), "%"),
            ("3 aylık getiri", g.get("uc_aylik"), "%"),
            ("Yıllık getiri", g.get("yillik"), "%"),
            ("Oynaklık (yıllık)", f.get("volatilite"), "%"),
            ("Maksimum düşüş", f.get("maks_dusus"), "%"),
            ("Fon büyüklüğü", f.get("buyukluk"), "TL"),
            ("Yatırımcı sayısı", f.get("kisi_sayisi"), ""),
        ):
            if deger is None:
                continue
            ondalik = 2 if birim == "%" else 0
            metin = tema.sayi(deger, ondalik)
            if birim == "%":
                metin = "%" + metin
            elif birim:
                metin += " " + birim
            renk = tema.METIN
            if birim == "%" and etiket.endswith("getiri"):
                renk = tema.IYI if deger > 0 else tema.KOTU
            olculer.duzen.addWidget(_deger_satiri(etiket, metin, renk))
        self.detay_duzen.addWidget(olculer)

        # Stopaj — kullanicinin cebine giren rakami degistiren tek sey
        if f.get("stopaj_gerekce"):
            oran = f.get("stopaj")
            olculer2 = tema.Kart(
                "Stopaj: %%%s" % tema.sayi((oran or 0) * 100, 1),
                f.get("stopaj_gerekce", ""))
            self.detay_duzen.addWidget(olculer2)

        self.detay_duzen.addStretch(1)


def _deger_satiri(etiket: str, deger: str, renk: str) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent; border: none;")
    d = QHBoxLayout(w)
    d.setContentsMargins(0, 2, 0, 2)
    d.addWidget(tema.etiket(etiket, boyut=12.5, renk=tema.METIN_SOLUK,
                            sar=False))
    d.addStretch(1)
    d.addWidget(tema.etiket(deger, boyut=13, kalin=True, renk=renk,
                            sar=False))
    return w


def calistir() -> int:
    uygulama = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    return uygulama.exec()
