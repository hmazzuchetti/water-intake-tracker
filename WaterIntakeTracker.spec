# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os

# Check if icon exists
icon_path = 'icon.ico' if os.path.exists('icon.ico') else 'NONE'

datas = [('sounds', 'sounds'), ('data', 'data')]

# Add resource folders if they exist
if os.path.exists('models'):
    datas.append(('models', 'models'))
if os.path.exists('mascots'):
    datas.append(('mascots', 'mascots'))
if os.path.exists('personalities'):
    datas.append(('personalities', 'personalities'))

datas += collect_data_files('mediapipe')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['mediapipe', 'cv2', 'PyQt5', 'winsound'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WaterIntakeTracker',
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
    icon=icon_path,
)
