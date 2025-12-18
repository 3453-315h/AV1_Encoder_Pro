# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for AV1 Encoder Pro - CustomTkinter version

import os
import sys

# Get customtkinter path for data files
import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)

block_cipher = None

a = Analysis(
    ['av1_encoder_ctk.py'],
    pathex=[],
    binaries=[
        ('ffmpeg.exe', '.'),  # Bundle FFmpeg for self-contained app
    ],
    datas=[
        ('assets/av1_codec_logo.png', 'assets'),
        ('assets/CustomTkinter_icon_Windows.ico', 'assets'),
        (ctk_path, 'customtkinter/'),
    ],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AV1_Encoder_Pro',
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
    icon='assets/CustomTkinter_icon_Windows.ico',
    version='version_info.txt',
)
