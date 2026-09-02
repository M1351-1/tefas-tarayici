# -*- coding: utf-8 -*-
"""Fiyat grafigi — CustomPainter yerine QPainter ile dogrudan cizilir.

Hazir grafik paketi BILEREK kullanilmiyor: Turkce sayi bicimi ve dokunmali
okuma icin ayar cekmek, kendi cizmekten uzun suruyor. Ayrica ek bagimlilik
paketleme boyutunu buyutuyor.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from . import tema

KENAR_SOL = 62
KENAR_SAG = 12
KENAR_UST = 12
KENAR_ALT = 26


class FiyatGrafigi(QWidget):
    """Tek serili fiyat grafigi; fare imleciyle okuma destekler."""

    def __init__(self, seri: list) -> None:
        super().__init__()
        # seri: [(tarih, fiyat), ...] eskiden yeniye
        self.seri = [(t, f) for t, f in seri if f is not None and f > 0]
        self.setMouseTracking(True)
        self.setStyleSheet("background: transparent; border: none;")
        self._imlec = None

    def mouseMoveEvent(self, olay) -> None:  # noqa: N802, D102
        self._imlec = olay.position().x()
        self.update()

    def leaveEvent(self, olay) -> None:  # noqa: N802, D102
        self._imlec = None
        self.update()

    def paintEvent(self, olay) -> None:  # noqa: N802, D102
        if len(self.seri) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        alan = QRectF(KENAR_SOL, KENAR_UST,
                      self.width() - KENAR_SOL - KENAR_SAG,
                      self.height() - KENAR_UST - KENAR_ALT)
        if alan.width() <= 0 or alan.height() <= 0:
            p.end()
            return

        fiyatlar = [f for _, f in self.seri]
        en_az, en_cok = min(fiyatlar), max(fiyatlar)
        if en_cok - en_az < 1e-12:
            en_az, en_cok = en_az * 0.99, en_cok * 1.01
        pay = (en_cok - en_az) * 0.08
        en_az, en_cok = en_az - pay, en_cok + pay

        n = len(self.seri)

        def px(i):
            return alan.left() + alan.width() * i / (n - 1)

        def py(v):
            return alan.bottom() - alan.height() * (v - en_az) / (en_cok - en_az)

        # Izgara ve y etiketleri
        olcu = QFontMetrics(self.font())
        p.setPen(QPen(QColor(tema.KART_KENAR), 1))
        for k in range(5):
            v = en_az + (en_cok - en_az) * k / 4
            y = py(v)
            p.drawLine(QPointF(alan.left(), y), QPointF(alan.right(), y))
            p.setPen(QColor(tema.METIN_SOLUK))
            metin = tema.sayi(v, 2)
            p.drawText(QRectF(0, y - 9, KENAR_SOL - 6, 18),
                       Qt.AlignmentFlag.AlignRight
                       | Qt.AlignmentFlag.AlignVCenter, metin)
            p.setPen(QPen(QColor(tema.KART_KENAR), 1))

        # Cizgi
        yol = QPainterPath()
        for i, (_, f) in enumerate(self.seri):
            nokta = QPointF(px(i), py(f))
            if i == 0:
                yol.moveTo(nokta)
            else:
                yol.lineTo(nokta)
        # Yukselmis mi dusmus mu? Renk buna gore — susleme degil, bilgi.
        yukselen = self.seri[-1][1] >= self.seri[0][1]
        renk = QColor(tema.IYI if yukselen else tema.KOTU)
        p.setPen(QPen(renk, 2))
        p.drawPath(yol)

        # X etiketleri: bas ve son
        p.setPen(QColor(tema.METIN_SOLUK))
        p.drawText(QRectF(alan.left(), alan.bottom() + 4, 120, 18),
                   Qt.AlignmentFlag.AlignLeft, self.seri[0][0])
        p.drawText(QRectF(alan.right() - 120, alan.bottom() + 4, 120, 18),
                   Qt.AlignmentFlag.AlignRight, self.seri[-1][0])

        # Imlec okumasi
        if self._imlec is not None and alan.left() <= self._imlec <= alan.right():
            oran = (self._imlec - alan.left()) / alan.width()
            i = max(0, min(n - 1, round(oran * (n - 1))))
            tarih, fiyat = self.seri[i]
            x = px(i)
            p.setPen(QPen(QColor(tema.METIN_SOLUK), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x, alan.top()), QPointF(x, alan.bottom()))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(renk)
            p.drawEllipse(QPointF(x, py(fiyat)), 3.5, 3.5)

            metin = "%s   %s" % (tarih, tema.sayi(fiyat, 4))
            genislik = olcu.horizontalAdvance(metin) + 14
            kutu = QRectF(x - genislik / 2, alan.top(), genislik, 22)
            if kutu.left() < alan.left():
                kutu.moveLeft(alan.left())
            if kutu.right() > alan.right():
                kutu.moveRight(alan.right())
            p.setBrush(QColor(tema.KART))
            p.setPen(QPen(QColor(tema.KART_KENAR), 1))
            p.drawRoundedRect(kutu, 5, 5)
            p.setPen(QColor(tema.METIN))
            p.drawText(kutu, Qt.AlignmentFlag.AlignCenter, metin)

        p.end()
