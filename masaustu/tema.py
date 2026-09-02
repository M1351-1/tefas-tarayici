# -*- coding: utf-8 -*-
"""Arayuz temasi: renkler, tipografi, kart bileseni.

Qt'nin varsayilan gorunumu Windows'ta 2010'lardan kalma duruyor. Burada
tek bir stil sayfasi ve birkac yardimci bilesenle guncel bir gorunum
kuruluyor - ek bagimlilik YOK, saf PySide6.

Tasarim kararlari:

  - KART yapisi. Bilgi yogunlugu yuksek bir uygulama; her bolum kendi
    cercevesinde olmazsa ekran duvar gibi gorunuyor.
  - Tek vurgu rengi. Coklu renk, "her sey onemli" demek olur; onemli
    olani ayirt edilemez hale getirir.
  - Durum renkleri SADECE karar tasiyan yerlerde: yesil/kirmizi/amber
    yalnizca "beklemek kazandiriyor / kaybettiriyor / belirsiz" gibi
    gercek bir yargida kullanilir, susleme icin degil.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# --- palet ---------------------------------------------------------------

ZEMIN = "#14161a"
KART = "#1c1f26"
KART_KENAR = "#2a2f3a"
METIN = "#e6e9ef"
METIN_SOLUK = "#9aa3b2"
VURGU = "#4db6ac"          # teal - finans, notr, kirmizi/yesil ile cakismaz
VURGU_KOYU = "#26867c"

IYI = "#4caf50"
KOTU = "#ef5350"
UYARI = "#ffa726"
NOTR = "#78909c"


def durum_rengi(hukum: str) -> str:
    """Bekleme kararina karsilik gelen renk."""
    return {
        "beklemek_kazandiriyor": IYI,
        "gec_kalinmis": KOTU,
        "beklemek_desteklenmiyor": UYARI,
    }.get(hukum, NOTR)


STIL = f"""
QMainWindow, QWidget {{
    background: {ZEMIN};
    color: {METIN};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}

QTabWidget::pane {{
    border: none;
    background: {ZEMIN};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {METIN_SOLUK};
    padding: 10px 20px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {METIN};
    border-bottom: 2px solid {VURGU};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{ color: {METIN}; }}

QPushButton {{
    background: {VURGU_KOYU};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {VURGU}; }}
QPushButton:disabled {{ background: #2a2f3a; color: {METIN_SOLUK}; }}
/* Secilebilir dugmeler (donem secici): secili olan belli olmali */
QPushButton:checkable {{
    background: transparent;
    color: {METIN_SOLUK};
    border: 1px solid {KART_KENAR};
}}
QPushButton:checked {{
    background: {VURGU_KOYU};
    color: #ffffff;
    border: 1px solid {VURGU};
}}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {KART};
    border: 1px solid {KART_KENAR};
    border-radius: 6px;
    padding: 6px 10px;
    color: {METIN};
    selection-background-color: {VURGU_KOYU};
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {VURGU};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {KART};
    border: 1px solid {KART_KENAR};
    selection-background-color: {VURGU_KOYU};
    color: {METIN};
}}

QScrollArea {{ border: none; background: {ZEMIN}; }}
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {KART_KENAR}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {METIN_SOLUK}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QGroupBox {{
    border: 1px solid {KART_KENAR};
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {METIN_SOLUK};
}}

QStatusBar {{ background: {KART}; color: {METIN_SOLUK}; }}
QCheckBox {{ spacing: 8px; }}
QToolTip {{
    background: {KART}; color: {METIN};
    border: 1px solid {KART_KENAR}; padding: 6px;
}}
"""


class Kart(QFrame):
    """Basligi olan, cerceveli bolum."""

    def __init__(self, baslik: str = "", alt_baslik: str = "") -> None:
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background: {KART}; border: 1px solid {KART_KENAR};"
            f" border-radius: 10px; }}"
        )
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(16, 14, 16, 14)
        self.duzen.setSpacing(8)

        if baslik:
            b = QLabel(baslik)
            b.setStyleSheet(
                f"color: {METIN}; font-size: 14px; font-weight: 600;"
                " border: none;"
            )
            self.duzen.addWidget(b)
        if alt_baslik:
            a = QLabel(alt_baslik)
            a.setWordWrap(True)
            a.setStyleSheet(
                f"color: {METIN_SOLUK}; font-size: 12px; border: none;")
            self.duzen.addWidget(a)

    def ekle(self, w: QWidget) -> None:
        self.duzen.addWidget(w)


def etiket(metin: str, boyut: int = 13, renk: str = METIN,
           kalin: bool = False, sar: bool = True) -> QLabel:
    """Stil sayfasindan bagimsiz, dogrudan bicimlenmis etiket."""
    e = QLabel(metin)
    e.setWordWrap(sar)
    agirlik = "600" if kalin else "400"
    e.setStyleSheet(
        f"color: {renk}; font-size: {boyut}px; font-weight: {agirlik};"
        " border: none; background: transparent;"
    )
    return e


def buyuk_sayi(deger: str, etiket_metni: str, renk: str = METIN,
               en_az_genislik: int = 150) -> QWidget:
    """Buyuk rakam + altinda kucuk aciklama.

    `en_az_genislik`: aciklama satiri dar bir sutunda uc satira bolunup
    kartin dengesini bozuyordu; taban genislik veriyoruz.
    """
    w = QWidget()
    w.setMinimumWidth(en_az_genislik)
    w.setStyleSheet("background: transparent; border: none;")
    d = QVBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(2)

    s = QLabel(deger)
    f = QFont()
    f.setPointSize(22)
    f.setWeight(QFont.Weight.DemiBold)
    s.setFont(f)
    s.setStyleSheet(f"color: {renk}; border: none; background: transparent;")
    s.setAlignment(Qt.AlignmentFlag.AlignLeft)

    a = QLabel(etiket_metni)
    a.setStyleSheet(
        f"color: {METIN_SOLUK}; font-size: 11px; border: none;"
        " background: transparent;")
    a.setWordWrap(True)

    d.addWidget(s)
    d.addWidget(a)
    return w


# --------------------------------------------------------------- bilesenler
#
# Asagidakiler mobil surumdeki (konut-mobil/lib/arayuz/tema.dart)
# bilesenlerin birebir karsiligi. Iki uygulama tek urun gibi dursun diye
# ayni palet, ayni yuvarlaklik, ayni bosluklar kullaniliyor.


def rejim_rengi(rejim: str) -> str:
    """Piyasa rejiminin rengi.

    Rejim bir YARGI degil bir DURUM: "ISINMA" alici icin kotu, satici icin
    iyidir. Bu yuzden renkler SICAKLIK bildiriyor (kirmizi = hizli hareket,
    mavi = durgun), iyi/kotu degil. Rejimin alici acisindan ne demek
    oldugunu renk degil, altindaki not satiri soyluyor.
    """
    return {
        "ISINMA": "#FF7043",
        "GEÇ ISINMA": "#EF5350",
        "SIKIŞMA": "#FFA726",
        "SOĞUK": "#42A5F5",
        "KREDİ AÇILIYOR": "#26C6DA",
    }.get(rejim, NOTR)


class GradyanKart(QFrame):
    """Sayfanin tepesinde duran, renkli gradyanli vurgu karti.

    Duz bir kart bilgi yogunlugu yuksek bir ekranda kayboluyordu; sayfanin
    ASIL cevabi (karar, rejim, kazanan varlik) gorsel olarak da one cikmali.
    """

    def __init__(self, renk: str) -> None:
        super().__init__()
        # Qt stil sayfasi gradyani: sol ust -> sag alt.
        self.setStyleSheet(
            f"QFrame {{"
            f" background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            f"   stop:0 {_karistir(renk, KART, 0.26)},"
            f"   stop:0.55 {_karistir(renk, KART, 0.07)},"
            f"   stop:1 {KART});"
            f" border: 1px solid {_karistir(renk, KART, 0.45)};"
            f" border-radius: 14px; }}"
        )
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(20, 17, 20, 19)
        self.duzen.setSpacing(9)

    def ekle(self, w) -> None:
        self.duzen.addWidget(w)


def _karistir(on: str, arka: str, oran: float) -> str:
    """Iki rengi karistirir. Qt stil sayfasi rgba() ile gradyan kabul
    etmedigi icin saydamlik yerine onceden karistirilmis renk uretiyoruz."""
    def ayir(h: str) -> tuple:
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    o, a = ayir(on), ayir(arka)
    return "#%02x%02x%02x" % tuple(
        int(a[i] + (o[i] - a[i]) * oran) for i in range(3))


def rozet(metin: str, renk: str = NOTR, dolu: bool = False) -> QLabel:
    """Renkli hap etiketi."""
    e = QLabel(metin)
    e.setStyleSheet(
        f"color: {'#ffffff' if dolu else renk};"
        f" background: {renk if dolu else _karistir(renk, KART, 0.16)};"
        f" border: 1px solid {_karistir(renk, KART, 0.45)};"
        f" border-radius: 9px; padding: 3px 9px;"
        f" font-size: 11px; font-weight: 700;"
    )
    e.setAlignment(Qt.AlignmentFlag.AlignCenter)
    e.setSizePolicy(e.sizePolicy().horizontalPolicy().Fixed,
                    e.sizePolicy().verticalPolicy().Fixed)
    return e


def bolum_basligi(metin: str, aciklama: str = "") -> QWidget:
    """Solunda vurgu cizgisi olan kucuk bolum basligi."""
    w = QWidget()
    w.setStyleSheet("background: transparent; border: none;")
    d = QVBoxLayout(w)
    d.setContentsMargins(2, 12, 2, 2)
    d.setSpacing(4)

    ust = QHBoxLayout()
    ust.setSpacing(9)
    cizgi = QFrame()
    cizgi.setFixedSize(3, 14)
    cizgi.setStyleSheet(f"background: {VURGU}; border-radius: 1px;")
    ust.addWidget(cizgi)
    b = QLabel(metin.upper())
    b.setStyleSheet(
        f"color: {METIN}; font-size: 11px; font-weight: 800;"
        " letter-spacing: 1px; border: none; background: transparent;")
    ust.addWidget(b)
    ust.addStretch(1)
    d.addLayout(ust)

    if aciklama:
        a = QLabel(aciklama)
        a.setWordWrap(True)
        a.setStyleSheet(
            f"color: {METIN_SOLUK}; font-size: 12px; border: none;"
            " background: transparent; padding-left: 12px;")
        d.addWidget(a)
    return w


def not_kutusu(metin: str, renk: str = NOTR) -> QWidget:
    """Renk tonlu bilgi/uyari kutusu."""
    w = QFrame()
    w.setStyleSheet(
        f"QFrame {{ background: {_karistir(renk, ZEMIN, 0.10)};"
        f" border: 1px solid {_karistir(renk, ZEMIN, 0.30)};"
        f" border-radius: 10px; }}"
    )
    d = QHBoxLayout(w)
    d.setContentsMargins(13, 11, 13, 11)
    d.setSpacing(10)
    e = QLabel(metin)
    e.setWordWrap(True)
    e.setStyleSheet(
        f"color: {METIN}; font-size: 12px; border: none;"
        " background: transparent;")
    d.addWidget(e, 1)
    return w


class DilimCetveli(QWidget):
    """Gostergenin tarihsel dagilimdaki yerini gosteren ince cubuk.

    Bir sayiyi tek basina gostermek ("reel faiz %8,2") anlamsiz: yuksek mi
    dusuk mu? Cetvel, degerin kendi gecmisindeki yerini bir bakista veriyor.
    """

    def __init__(self, yuzdelik: float, renk: str = VURGU) -> None:
        super().__init__()
        self.yuzdelik = max(0.0, min(1.0, yuzdelik))
        self.renk = renk
        self.setFixedHeight(16)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, olay) -> None:  # noqa: N802, D102
        from PySide6.QtGui import QColor, QLinearGradient, QPainter

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = self.width()
        y, yuk = 5, 6

        gr = QLinearGradient(0, 0, g, 0)
        gr.setColorAt(0.0, QColor(_karistir(self.renk, KART, 0.12)))
        gr.setColorAt(0.5, QColor(_karistir(self.renk, KART, 0.34)))
        gr.setColorAt(1.0, QColor(_karistir(self.renk, KART, 0.12)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gr)
        p.drawRoundedRect(0, y, g, yuk, 3, 3)

        p.setBrush(QColor(self.renk))
        x = int((g - 3) * self.yuzdelik)
        p.drawRoundedRect(x, 1, 3, 14, 1, 1)
        p.end()


class OranCubugu(QWidget):
    """Oran cubugu.

    `merkezli=True`  : ortadan iki yana buyur (-1..1). Kazanc/kayip gibi
                       ISARETI olan buyukluklerde sifir cizgisi gorunur
                       olmali.
    `merkezli=False` : soldan saga dolar (0..1). Pismanlik olasiligi ya da
                       "en buyugun kaci" gibi tek yonlu oranlar icin.
    """

    def __init__(self, oran: float, renk: str, yukseklik: int = 8,
                 merkezli: bool = True) -> None:
        super().__init__()
        self.merkezli = merkezli
        self.oran = (max(-1.0, min(1.0, oran)) if merkezli
                     else max(0.0, min(1.0, oran)))
        self.renk = renk
        self.setFixedHeight(yukseklik)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, olay) -> None:  # noqa: N802, D102
        from PySide6.QtGui import QColor, QPainter

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g, yuk = self.width(), self.height()
        yari = yuk // 2

        p.setPen(Qt.PenStyle.NoPen)

        if not self.merkezli:
            p.setBrush(QColor(KART_KENAR))
            p.drawRoundedRect(0, 0, g, yuk, yari, yari)
            uzunluk = max(2, int(g * self.oran))
            p.setBrush(QColor(self.renk))
            p.drawRoundedRect(0, 0, uzunluk, yuk, yari, yari)
            p.end()
            return

        orta = g // 2
        p.setBrush(QColor(KART_KENAR))
        p.drawRect(orta, 0, 1, yuk)

        uzunluk = max(2, int(orta * abs(self.oran)))
        p.setBrush(QColor(self.renk))
        x = orta if self.oran >= 0 else orta - uzunluk
        p.drawRoundedRect(x, 0, uzunluk, yuk, yari, yari)
        p.end()


# ------------------------------------------------------------ bicimlendirme


def sayi(deger: float, ondalik: int = 0) -> str:
    """1234567.8 -> '1.234.568' (Turkce ayirac)."""
    metin = ("%%.%df" % ondalik) % abs(deger)
    parcalar = metin.split(".")
    tam = parcalar[0]
    kume = []
    while len(tam) > 3:
        kume.insert(0, tam[-3:])
        tam = tam[:-3]
    kume.insert(0, tam)
    sonuc = ".".join(kume)
    if len(parcalar) > 1:
        sonuc += "," + parcalar[1]
    return ("-" if deger < 0 else "") + sonuc


def isaretli(deger: float, ondalik: int = 1) -> str:
    """Isaretli sayi: '+12,4' / '-3,1'."""
    return ("+" if deger >= 0 else "") + sayi(deger, ondalik)


_AY_ADLARI = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
              "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def ay_etiketi(ay: str) -> str:
    """'2026-07' -> 'Tem 2026'."""
    if not ay or len(ay) < 7 or ay[4] != "-":
        return ay
    try:
        m = int(ay[5:7])
    except ValueError:
        return ay
    if not 1 <= m <= 12:
        return ay
    return "%s %s" % (_AY_ADLARI[m - 1], ay[:4])
