# PDF Extractor

Cross-platform desktop application for extracting content from PDF documents using IBM Docling's AI-powered document understanding.

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)
[![Build Desktop App](https://github.com/danribes/pdf_xtractor/actions/workflows/build.yml/badge.svg)](https://github.com/danribes/pdf_xtractor/actions/workflows/build.yml)

## Features

- **Drag & Drop Interface**: Simply drag PDF files into the application
- **Multiple Export Formats**:
  - JSON (structured document data)
  - Markdown (clean text output)
  - CSV/Excel (extracted tables)
  - HTML (web-viewable format)
- **AI-Powered Extraction**: Uses IBM Docling for intelligent layout detection and table extraction
- **Cross-Platform**: Native apps for Windows and macOS
- **GPU Acceleration**: Automatic CUDA/MPS support for faster processing

## Download

Download the latest release for your platform from the [Releases page](https://github.com/danribes/pdf_xtractor/releases/latest).

| Platform | File | Description |
|----------|------|-------------|
| Windows (Installer) | `PDF_Extractor_Setup_x.x.x.exe` | Standard Windows installer |
| Windows (Portable) | `PDF_Extractor_Portable.zip` | No installation required |
| macOS (Intel) | `PDF_Extractor_macOS.dmg` | For Intel-based Macs |
| macOS (Apple Silicon) | `PDF_Extractor_macOS_ARM.dmg` | For M1/M2/M3/M4 Macs |

> **Note**: On first run, the app downloads AI models (~300MB). This only happens once.

---

## Installation

### Windows - Installer (Recommended)

1. Download `PDF_Extractor_Setup_x.x.x.exe` from the [latest release](https://github.com/danribes/pdf_xtractor/releases/latest)
2. Run the installer (if Windows SmartScreen appears, click **"More info"** → **"Run anyway"**)
3. Follow the setup wizard
4. Launch **PDF Extractor** from the Start Menu or desktop shortcut

### Windows - Portable Version

The portable version requires no installation and can run from any folder or USB drive.

1. Download `PDF_Extractor_Portable.zip` from the [latest release](https://github.com/danribes/pdf_xtractor/releases/latest)
2. Extract the zip file to any folder (e.g., `C:\Apps\PDF Extractor\`)
3. Double-click `PDF Extractor.exe` to run the application
4. **First run only**: If Windows SmartScreen shows "Windows protected your PC":
   - Click **"More info"**
   - Click **"Run anyway"**

> **Important**: Keep the `_internal` folder in the same location as `PDF Extractor.exe` - the application needs it to run.

### macOS

1. Download the appropriate DMG for your Mac:
   - **Intel Macs**: `PDF_Extractor_macOS.dmg`
   - **Apple Silicon (M1/M2/M3/M4)**: `PDF_Extractor_macOS_ARM.dmg`
2. Open the DMG file
3. Drag **PDF Extractor** to your Applications folder
4. Launch from Applications or Spotlight

> **Note**: If you see "App is damaged" or "unidentified developer" warning, see [Troubleshooting](#troubleshooting) below.

---

## Building from Source

### Prerequisites

- Python 3.10 or higher
- Git

### Quick Start (Development)

```bash
# Clone the repository
git clone https://github.com/danribes/pdf_xtractor.git
cd pdf_xtractor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

### Building Distributables

#### Windows

```batch
# Build executable only
scripts\build_windows.bat

# Build executable + installer
scripts\build_windows.bat installer
```

**Output:**
- `dist\PDF Extractor.exe` - Standalone executable
- `dist\PDF_Extractor_Setup_1.0.0.exe` - Installer (requires [Inno Setup](https://jrsoftware.org/isinfo.php))

#### macOS

```bash
# Build .app bundle
./scripts/build_mac.sh

# Build .app + DMG installer
./scripts/build_mac.sh dmg

# Build Universal binary (Intel + Apple Silicon)
./scripts/build_mac.sh universal dmg
```

**Output:**
- `dist/PDF Extractor.app` - Application bundle
- `dist/PDF_Extractor_1.0.0.dmg` - DMG installer

### Bundling AI Models (Offline Distribution)

For distribution without requiring internet on first run:

```bash
# Download models to local directory
python scripts/download_models.py

# Then build normally - models will be included
./scripts/build_mac.sh dmg  # or build_windows.bat
```

This increases the app size by ~300MB but allows fully offline usage.

## Project Structure

```
pdf_xtractor/
├── src/
│   ├── main.py              # Application entry point
│   ├── gui.py               # PySide6 desktop interface
│   ├── converter.py         # Docling processing logic
│   └── config.py            # Configuration management
├── build/
│   ├── pdfextractor.spec    # PyInstaller configuration
│   ├── installer_windows.iss # Inno Setup script
│   └── version_info.txt     # Windows version metadata
├── scripts/
│   ├── build_windows.bat    # Windows build script
│   ├── build_mac.sh         # macOS build script
│   ├── download_models.py   # Pre-download AI models
│   └── create_icons.py      # Generate app icons
├── assets/
│   ├── icon.ico             # Windows icon
│   ├── icon.icns            # macOS icon
│   └── icon.png             # Reference icon
├── .github/
│   └── workflows/
│       └── build.yml        # CI/CD for automated builds
├── requirements.txt
└── README.md
```

## Export Format Details

| Format | Method | Use Case |
|--------|--------|----------|
| JSON | `export_to_dict()` | Full document hierarchy for developers |
| Markdown | `export_to_markdown()` | Clean text for LLMs or documentation |
| CSV/Excel | `table.export_to_dataframe()` | Structured data for analysis |
| HTML | `export_to_html()` | Visualizing the document in a browser |

## Code Signing & Notarization

### Windows

For distribution, sign your executable with a code signing certificate:

```batch
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com "dist\PDF Extractor.exe"
```

### macOS

For distribution outside the App Store:

```bash
# Sign the app
codesign --deep --force --sign "Developer ID Application: Your Name (TEAM_ID)" "dist/PDF Extractor.app"

# Create signed DMG
codesign --sign "Developer ID Application: Your Name (TEAM_ID)" "dist/PDF_Extractor_1.0.0.dmg"

# Notarize
xcrun notarytool submit dist/PDF_Extractor_1.0.0.dmg \
    --apple-id "your@email.com" \
    --team-id "TEAM_ID" \
    --password "app-specific-password" \
    --wait

# Staple the notarization
xcrun stapler staple "dist/PDF_Extractor_1.0.0.dmg"
```

## CI/CD with GitHub Actions

The project includes automated builds via GitHub Actions. To create a release:

1. Tag a version: `git tag v1.0.0`
2. Push the tag: `git push origin v1.0.0`
3. GitHub Actions will build for all platforms
4. Download artifacts from the draft release

You can also manually trigger a build from the [Actions tab](https://github.com/danribes/pdf_xtractor/actions/workflows/build.yml).

## Troubleshooting

### "App is damaged" on macOS

This happens with unsigned apps. Remove the quarantine attribute:

```bash
xattr -cr "/Applications/PDF Extractor.app"
```

### Models fail to download

If behind a firewall, pre-download models and set environment variables:

```bash
export HF_HOME=/path/to/models
python scripts/download_models.py
```

### GPU not detected

Ensure you have the correct PyTorch version for your GPU:

```bash
# For NVIDIA CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# For Apple Silicon (MPS)
pip install torch torchvision  # MPS support is automatic
```

## Requirements

- Python 3.10+
- docling >= 2.5.0
- PySide6 >= 6.6.0
- pandas >= 2.0.0
- PyInstaller >= 6.0.0 (for building)

## License

MIT License

## Acknowledgments

- [IBM Docling](https://github.com/DS4SD/docling) - Document understanding AI
- [PySide6](https://doc.qt.io/qtforpython-6/) - Qt for Python
- [PyInstaller](https://pyinstaller.org/) - Python application bundling
