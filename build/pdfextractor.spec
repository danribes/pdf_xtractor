# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PDF Extractor.

Build commands:
  Windows: pyinstaller build/pdfextractor.spec --clean
  macOS:   pyinstaller build/pdfextractor.spec --clean

Prerequisites:
  pip install pyinstaller

For smaller builds (without pre-bundled models):
  Models will download on first run (~300MB)

For offline distribution (with bundled models):
  1. python scripts/download_models.py
  2. pyinstaller build/pdfextractor.spec --clean
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Paths
SPEC_DIR = Path(SPECPATH)
ROOT_DIR = SPEC_DIR.parent
SRC_DIR = ROOT_DIR / 'src'
ASSETS_DIR = ROOT_DIR / 'assets'
MODELS_DIR = ROOT_DIR / 'models'

# Platform detection
is_windows = sys.platform == 'win32'
is_mac = sys.platform == 'darwin'

# Application info
APP_NAME = 'PDF Extractor'
APP_VERSION = '1.0.0'
BUNDLE_ID = 'com.pdfextractor.app'

# Collect all required data files
datas = []

# Docling models and data
datas += collect_data_files('docling')
datas += collect_data_files('docling_core')
datas += collect_data_files('docling_ibm_models')
datas += collect_data_files('docling_parse')

# Transformers and torch data
datas += collect_data_files('transformers', include_py_files=True)

# RapidOCR models
datas += collect_data_files('rapidocr')

# Include pre-downloaded models if they exist
if MODELS_DIR.exists():
    datas.append((str(MODELS_DIR), 'models'))

# Hidden imports - modules that PyInstaller can't detect automatically
hiddenimports = [
    # Docling and dependencies
    'docling',
    'docling.document_converter',
    'docling.datamodel',
    'docling.pipeline',
    'docling_core',
    'docling_ibm_models',
    'docling_parse',

    # AI/ML frameworks
    'torch',
    'torch.nn',
    'torch.utils',
    'torchvision',
    'torchvision.transforms',
    'transformers',
    'transformers.models',
    'safetensors',
    'accelerate',

    # OCR
    'rapidocr',
    'cv2',
    'PIL',
    'PIL.Image',

    # Data processing
    'pandas',
    'numpy',
    'openpyxl',
    'lxml',
    'lxml.etree',

    # PySide6
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',

    # Other
    'json',
    'pathlib',
    'dataclasses',
    'typing',
    'huggingface_hub',
    'filelock',
    'fsspec',
    'requests',
    'tqdm',
    'yaml',
    'omegaconf',
]

# Collect all submodules for complex packages
hiddenimports += collect_submodules('docling')
hiddenimports += collect_submodules('transformers')
hiddenimports += collect_submodules('torch')

# Exclude unnecessary modules to reduce size
excludes = [
    'tkinter',
    'matplotlib',
    'IPython',
    'jupyter',
    'notebook',
    'pytest',
    'sphinx',
    'docutils',
]

# Analysis
a = Analysis(
    [str(SRC_DIR / 'main.py')],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT_DIR / 'build' / 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
a.datas = list(set(a.datas))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if is_mac:
    # ============ macOS Build ============
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,  # UPX can cause issues on macOS
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,  # Use 'universal2' for Intel+Apple Silicon
        codesign_identity=None,  # Add your signing identity for distribution
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )

    # Icon path
    icon_path = ASSETS_DIR / 'icon.icns'

    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=str(icon_path) if icon_path.exists() else None,
        bundle_identifier=BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            'CFBundleDisplayName': APP_NAME,
            'CFBundleName': APP_NAME,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'CFBundleIdentifier': BUNDLE_ID,
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,  # Support dark mode
            'LSMinimumSystemVersion': '10.15.0',
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'PDF Document',
                    'CFBundleTypeExtensions': ['pdf'],
                    'CFBundleTypeRole': 'Viewer',
                    'LSHandlerRank': 'Alternate',
                }
            ],
        },
    )

else:
    # ============ Windows Build ============
    icon_path = ASSETS_DIR / 'icon.ico'

    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(icon_path) if icon_path.exists() else None,
        version=str(ROOT_DIR / 'build' / 'version_info.txt') if (ROOT_DIR / 'build' / 'version_info.txt').exists() else None,
    )
