#!/usr/bin/env bash
#
# Buddy Desktop Companion — Standalone macOS .app Builder
# Uses PyInstaller to bundle Buddy into a self-contained /Applications/Buddy.app
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

APP_NAME="Buddy"
BUNDLE_ID="com.saurabmishra.buddy"
VERSION="2.0.0"
ICON_PATH="assets/icons/buddy.icns"

echo "========================================================"
echo "  📦 Building Buddy.app for macOS (Standalone Bundle)"
echo "========================================================"

# 1. Check PyInstaller
if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "PyInstaller not found. Installing via pip..."
    python3 -m pip install --user pyinstaller
fi

# 2. Ensure .icns exists
if [ ! -f "${ICON_PATH}" ]; then
    echo "Generating ${ICON_PATH} from PNG..."
    mkdir -p /tmp/buddy.iconset
    sips -z 16 16 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_16x16.png >/dev/null
    sips -z 32 32 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_16x16@2x.png >/dev/null
    sips -z 32 32 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_32x32.png >/dev/null
    sips -z 64 64 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_32x32@2x.png >/dev/null
    sips -z 128 128 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_128x128.png >/dev/null
    sips -z 256 256 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_128x128@2x.png >/dev/null
    sips -z 256 256 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_256x256.png >/dev/null
    sips -z 512 512 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_256x256@2x.png >/dev/null
    sips -z 512 512 assets/icons/buddy.png --out /tmp/buddy.iconset/icon_512x512.png >/dev/null
    iconutil -c icns /tmp/buddy.iconset -o "${ICON_PATH}"
    rm -rf /tmp/buddy.iconset
fi

# 3. Clean previous build artifacts
echo "[1/3] Cleaning previous build output..."
rm -rf build dist "${APP_NAME}.spec"

# 4. Run PyInstaller
echo "[2/3] Compiling standalone macOS application bundle..."
pyinstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name "${APP_NAME}" \
    --icon "${ICON_PATH}" \
    --osx-bundle-identifier "${BUNDLE_ID}" \
    --add-data "assets:assets" \
    --add-data "skins:skins" \
    --collect-all "skins" \
    --collect-all "platforms" \
    --collect-all "pomodoro" \
    --collect-all "behavior" \
    --collect-all "core" \
    --collect-all "ui" \
    --hidden-import "AppKit" \
    --hidden-import "Foundation" \
    --hidden-import "Quartz" \
    --hidden-import "cairo" \
    --hidden-import "objc" \
    buddy

# 5. Tune Info.plist (LSUIElement for clean desktop accessory mode without dock clutter)
echo "[3/3] Setting high-DPI Retina and desktop accessory properties in Info.plist..."
PLIST_TARGET="dist/${APP_NAME}.app/Contents/Info.plist"

if [ -f "${PLIST_TARGET}" ]; then
    plutil -replace CFBundleShortVersionString -string "${VERSION}" "${PLIST_TARGET}"
    plutil -replace CFBundleVersion -string "${VERSION}" "${PLIST_TARGET}"
    plutil -replace NSHighResolutionCapable -bool true "${PLIST_TARGET}"
    # LSUIElement: Run as accessory (Status item + floating overlay, no persistent Dock icon)
    plutil -replace LSUIElement -string "1" "${PLIST_TARGET}"
fi

echo ""
echo "========================================================"
echo "  🎉 Standalone Buddy.app built successfully!"
echo "========================================================"
echo "Bundle location: $(pwd)/dist/${APP_NAME}.app"
echo ""
echo "To install into your user Applications directory:"
echo "    cp -R dist/${APP_NAME}.app /Applications/"
echo "or open it directly:"
echo "    open dist/${APP_NAME}.app"
