# -*- mode: python ; coding: utf-8 -*-
# build/pokemon-tcg-tracker.spec — PyInstaller 6.x --onedir spec
# Paramètres compatibles PyInstaller 6.0+ (cipher + win_no_prefer_redirects supprimés en 6.x/5.x)
import os, sys

# EasyOCR models — inclus si présents dans ~/.EasyOCR/model/
easyocr_models = []
_models_dir = os.path.expanduser("~/.EasyOCR/model")
if os.path.isdir(_models_dir):
    easyocr_models = [(_models_dir, ".EasyOCR/model")]

a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../ui', 'ui'),
        ('../assets', 'assets'),
        *easyocr_models,
    ],
    hiddenimports=[
        'webview.platforms.winforms',
        'pystray._win32',
        'win32gui', 'win32con', 'win32api', 'win32process',
        'PIL._tkinter_finder',
        'mss.windows',
        'easyocr',
        'torch',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pokemon-tcg-tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='../assets/icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pokemon-tcg-tracker',
)
