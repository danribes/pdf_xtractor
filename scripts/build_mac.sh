#!/bin/bash
# ============================================================
# PDF Extractor - macOS Build Script
# ============================================================
#
# Prerequisites:
#   - Python 3.10+ installed
#   - Xcode Command Line Tools: xcode-select --install
#   - create-dmg (optional): brew install create-dmg
#
# Usage:
#   ./build_mac.sh           - Build .app bundle only
#   ./build_mac.sh dmg       - Build .app + DMG installer
#   ./build_mac.sh universal - Build Universal binary (Intel + Apple Silicon)
#
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "============================================================"
echo "  PDF Extractor - macOS Build"
echo "============================================================"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Python 3 is not installed"
    echo "        Install with: brew install python3"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python found: $(python3 --version)"

# Check for Xcode Command Line Tools
if ! xcode-select -p &> /dev/null; then
    echo -e "${YELLOW}[WARNING]${NC} Xcode Command Line Tools not installed"
    echo "          Installing now..."
    xcode-select --install
    echo "          Please re-run this script after installation completes."
    exit 1
fi

# Create/activate virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo -e "${GREEN}[STEP]${NC} Creating virtual environment..."
    python3 -m venv venv
fi

echo -e "${GREEN}[STEP]${NC} Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo -e "${GREEN}[STEP]${NC} Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Ask about model bundling
echo ""
read -p "Bundle AI models for offline use? (y/N): " BUNDLE_MODELS
if [[ "$BUNDLE_MODELS" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${GREEN}[STEP]${NC} Downloading AI models (this may take several minutes)..."
    python scripts/download_models.py || {
        echo -e "${YELLOW}[WARNING]${NC} Model download failed. App will download on first run."
    }
fi

# Determine architecture
ARCH_FLAG=""
if [[ "$1" == "universal" ]]; then
    echo ""
    echo -e "${GREEN}[STEP]${NC} Building Universal binary (Intel + Apple Silicon)..."
    ARCH_FLAG="--target-arch universal2"
fi

# Build with PyInstaller
echo ""
echo -e "${GREEN}[STEP]${NC} Building application with PyInstaller..."
echo "        This may take 5-10 minutes..."
echo ""

pyinstaller build/pdfextractor.spec --clean --noconfirm $ARCH_FLAG

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[ERROR]${NC} PyInstaller build failed"
    exit 1
fi

echo ""
echo -e "${GREEN}[OK]${NC} Build complete!"
echo "    Output: dist/PDF Extractor.app"

# Create DMG if requested
if [[ "$1" == "dmg" ]] || [[ "$2" == "dmg" ]]; then
    echo ""
    echo -e "${GREEN}[STEP]${NC} Creating DMG installer..."

    if ! command -v create-dmg &> /dev/null; then
        echo -e "${YELLOW}[WARNING]${NC} create-dmg not found."
        echo "          Install with: brew install create-dmg"
        echo "          Creating simple DMG with hdiutil instead..."

        # Simple DMG creation with hdiutil
        DMG_NAME="PDF_Extractor_1.0.0.dmg"
        rm -f "dist/$DMG_NAME"

        hdiutil create -volname "PDF Extractor" \
            -srcfolder "dist/PDF Extractor.app" \
            -ov -format UDZO \
            "dist/$DMG_NAME"

        echo -e "${GREEN}[OK]${NC} DMG created: dist/$DMG_NAME"
    else
        # Fancy DMG with create-dmg
        DMG_NAME="PDF_Extractor_1.0.0.dmg"
        rm -f "dist/$DMG_NAME"

        create-dmg \
            --volname "PDF Extractor" \
            --volicon "assets/icon.icns" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "PDF Extractor.app" 150 190 \
            --hide-extension "PDF Extractor.app" \
            --app-drop-link 450 185 \
            --no-internet-enable \
            "dist/$DMG_NAME" \
            "dist/PDF Extractor.app" \
            2>/dev/null || {
                # Fallback if create-dmg fails (e.g., missing icon)
                echo -e "${YELLOW}[WARNING]${NC} create-dmg failed, using simple DMG..."
                hdiutil create -volname "PDF Extractor" \
                    -srcfolder "dist/PDF Extractor.app" \
                    -ov -format UDZO \
                    "dist/$DMG_NAME"
            }

        echo -e "${GREEN}[OK]${NC} DMG created: dist/$DMG_NAME"
    fi
fi

# Code signing reminder
echo ""
echo "============================================================"
echo "  Build Summary"
echo "============================================================"
echo ""
echo "  Application: dist/PDF Extractor.app"
if [ -f "dist/PDF_Extractor_1.0.0.dmg" ]; then
    echo "  DMG:         dist/PDF_Extractor_1.0.0.dmg"
fi
echo ""
echo "  To run: open \"dist/PDF Extractor.app\""
echo ""
echo -e "${YELLOW}[NOTE]${NC} For distribution outside the App Store:"
echo "       1. Sign the app: codesign --deep --force --sign \"Developer ID\" \"dist/PDF Extractor.app\""
echo "       2. Notarize: xcrun notarytool submit dist/PDF_Extractor_1.0.0.dmg --apple-id YOUR_ID --team-id YOUR_TEAM"
echo ""
echo "============================================================"
