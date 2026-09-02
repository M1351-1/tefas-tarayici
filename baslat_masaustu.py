# -*- coding: utf-8 -*-
"""TEFAS Fon Tarayici — masaustu surumu.

Konut zamanlayiciyla ayni yontem: PySide6 + PyInstaller. Flutter'in
Windows hedefi ~6 GB'lik Visual Studio kurulumu istiyor; buna gerek yok
cunku projenin zaten bir Python tarafi var.

AGA CIKMAZ: veri bu bilgisayardaki data/ klasorunden okunur.
"""
import sys

from masaustu.pencere import calistir

if __name__ == "__main__":
    sys.exit(calistir())
