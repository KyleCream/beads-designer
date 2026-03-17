# beads_designer.spec

import sys
import os

block_cipher = None
ROOT = os.path.abspath('.')

a = Analysis(
    ['main.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join('palettes', '*.json'), 'palettes'),
    ],
    hiddenimports=[
        'scipy.spatial',
        'scipy.spatial._kdtree',
        'numpy',
        'PIL',
        'reportlab',
        'reportlab.lib',
        'reportlab.pdfgen',
        'reportlab.pdfbase',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除 PyQt5，只用 PyQt6
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
        # 排除不需要的模块减小体积
        'matplotlib',
        'tkinter',
        'unittest',
        'email',
        'xml',
        'pydoc',
        'doctest',
        'test',
        'distutils',
        'setuptools',
        'PySide2',
        'PySide6',
    ],
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
    name='BeadsDesigner',
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
    name='BeadsDesigner',
)