# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['src/postshow/main.py'],
    pathex=[],
    binaries=[],
    datas=[('data/template_config.ini', 'data'), ('vendor/lame', 'vendor')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='PostShow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PostShow',
)
app = BUNDLE(
    coll,
    name='PostShow.app',
    icon='assets/PostShow Icon.icns',
    bundle_identifier="dog.s0ph0s.postshow.v3",
    version="3.0.3",
)
