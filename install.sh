#!/usr/bin/env bash
#
# Buddy Desktop Pet — Automated Linux / Fedora Installer
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_SCALABLE_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
ICON_128_DIR="${HOME}/.local/share/icons/hicolor/128x128/apps"

echo "========================================================"
echo "  ⚡ Installing Buddy Desktop Pet on Linux / Fedora"
echo "========================================================"

# 1. Check Python and dependencies
echo "[1/5] Checking environment dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is required. On Fedora, install with: sudo dnf install python3"
    exit 1
fi

python3 -c "
import sys
missing = []
for mod in ['gi', 'cairo']:
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)
if missing:
    print('Missing system modules:', missing, file=sys.stderr)
    print('On Fedora, install them using: sudo dnf install python3-gobject gtk3 cairo-gobject libappindicator-gtk3', file=sys.stderr)
    sys.exit(1)
"

# 2. Make executable
echo "[2/5] Setting up launcher permissions..."
chmod +x "${SCRIPT_DIR}/buddy"

# 3. Create CLI symlink in ~/.local/bin
echo "[3/5] Installing CLI command into ${BIN_DIR}/buddy..."
mkdir -p "${BIN_DIR}"
ln -sf "${SCRIPT_DIR}/buddy" "${BIN_DIR}/buddy"

# 4. Install high-res desktop icons
echo "[4/5] Installing desktop icons..."
mkdir -p "${ICON_SCALABLE_DIR}"
mkdir -p "${ICON_128_DIR}"
cp -f "${SCRIPT_DIR}/assets/icons/buddy.svg" "${ICON_SCALABLE_DIR}/buddy.svg"
if [ -f "${SCRIPT_DIR}/assets/icons/buddy.png" ]; then
    cp -f "${SCRIPT_DIR}/assets/icons/buddy.png" "${ICON_128_DIR}/buddy.png"
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

# 5. Install Desktop Application entry
echo "[5/5] Installing application launcher in ${APP_DIR}..."
mkdir -p "${APP_DIR}"
cat > "${APP_DIR}/buddy.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Buddy
GenericName=Desktop Pet Companion
Comment=Modern animated desktop companion for Linux
Exec=${BIN_DIR}/buddy
Icon=buddy
Terminal=false
Categories=Utility;Amusement;Game;
Keywords=buddy;pet;thor;companion;desktop;
StartupNotify=false
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" >/dev/null 2>&1 || true
fi

echo ""
echo "========================================================"
echo "  🎉 Buddy has been successfully installed!"
echo "========================================================"
echo "You can launch Buddy anytime by running:"
echo "    buddy"
echo "or by searching 'Buddy' in your Fedora Application Menu."
echo ""
echo "Available commands:"
echo "    buddy --skin thor       (Launch with Thor & Mjolnir)"
echo "    buddy --skin dragon     (Launch with Dragon)"
echo "    buddy --skin cat        (Launch with Cat)"
echo "    buddy --skins           (Open visual Skin Gallery)"
echo "    buddy --settings        (Open Settings Dialog)"
echo "    buddy --pause           (Pause active pet)"
echo "    buddy --resume          (Resume active pet)"
echo "    buddy --debug           (Launch with Developer HUD)"
echo ""
