# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller yapilandirmasi — TEFAS Fon Tarayici masaustu.

Konut zamanlayiciyla ayni yontem. Flutter'in Windows hedefi ~6 GB'lik
Visual Studio kurulumu istiyor; buna gerek yok cunku projenin zaten bir
Python tarafi var.

VERI PAKETE GOMULMEZ: data/ klasoru exe'nin yaninda durur ve toplayici
onu tazeler. Gomulseydi her veri guncellemesinde yeniden derlemek
gerekirdi.
"""

a = Analysis(
    ['baslat_masaustu.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Kullanilmayan agir Qt modulleri disarida: exe boyutu yariya iner.
    excludes=[
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.Qt3DCore',
        'PySide6.QtMultimedia', 'PySide6.QtNetwork', 'PySide6.QtPdf',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'tkinter', 'matplotlib', 'numpy', 'pandas',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TefasTarayici',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
