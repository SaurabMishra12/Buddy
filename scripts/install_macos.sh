#!/usr/bin/env bash
#
# Buddy Desktop Companion — Automated macOS Installer
# Supports macOS 12 Monterey, 13 Ventura, 14 Sonoma, 15 Sequoia (Intel & Apple Silicon)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${HOME}/.local/bin"
SYSTEM_BIN_DIR="/usr/local/bin"
APP_SUPPORT_DIR="${HOME}/Library/Application Support/Buddy"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"

echo "========================================================"
echo "  ⚡ Installing Buddy Desktop Companion on macOS"
echo "========================================================"

# 1. Platform Check
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This installer is designed specifically for macOS (Darwin)."
    echo "For Linux, please run: ./install.sh"
    exit 1
fi

ARCH="$(uname -m)"
OS_VER="$(sw_vers -productVersion 2>/dev/null || echo 'Unknown')"
echo "Detected macOS ${OS_VER} (${ARCH})"

# 2. Python & Homebrew Verification
echo "[1/4] Checking Python 3 and native dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required. Install it via Homebrew: brew install python3"
    exit 1
fi

PYTHON_BIN="$(command -v python3)"
echo "Using Python: ${PYTHON_BIN}"

# Check for required modules: pycairo, AppKit, Quartz
MISSING_PKGS=()
"${PYTHON_BIN}" -c "import cairo" 2>/dev/null || MISSING_PKGS+=("pycairo")
"${PYTHON_BIN}" -c "import AppKit" 2>/dev/null || MISSING_PKGS+=("pyobjc-framework-Cocoa")
"${PYTHON_BIN}" -c "import Quartz" 2>/dev/null || MISSING_PKGS+=("pyobjc-framework-Quartz")

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo "Installing missing Python packages: ${MISSING_PKGS[*]}..."
    "${PYTHON_BIN}" -m pip install --user "${MISSING_PKGS[@]}"
fi

# 3. Setup permissions and directories
echo "[2/4] Setting up Buddy runtime directories and permissions..."
chmod +x "${SCRIPT_DIR}/buddy"
mkdir -p "${APP_SUPPORT_DIR}"
mkdir -p "${LAUNCH_AGENTS_DIR}"

# 4. CLI Symlink
echo "[3/4] Installing CLI command..."
mkdir -p "${BIN_DIR}"
ln -sf "${SCRIPT_DIR}/buddy" "${BIN_DIR}/buddy"

# Attempt /usr/local/bin if writable or with user permission
if [ -w "${SYSTEM_BIN_DIR}" ]; then
    ln -sf "${SCRIPT_DIR}/buddy" "${SYSTEM_BIN_DIR}/buddy"
    TARGET_BIN="${SYSTEM_BIN_DIR}/buddy"
else
    TARGET_BIN="${BIN_DIR}/buddy"
fi
echo "Buddy CLI linked to: ${TARGET_BIN}"

# Ensure ~/.local/bin is in PATH hint
if [[ ":$PATH:" != *":${BIN_DIR}:"* && "${TARGET_BIN}" == "${BIN_DIR}/buddy" ]]; then
    echo "Note: Make sure ${BIN_DIR} is in your PATH. You can add it with:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# 5. Verification
echo "[4/4] Verifying Buddy installation..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/buddy" --version

echo ""
echo "========================================================"
echo "  🎉 Buddy has been successfully installed on macOS!"
echo "========================================================"
echo "You can launch Buddy anytime by running:"
echo "    buddy"
echo ""
echo "Quick Commands:"
echo "    buddy --skin thor       (Launch with Thor & Mjolnir)"
echo "    buddy --skin dragon     (Launch with Dragon)"
echo "    buddy --skin ironman    (Launch with Iron Man)"
echo "    buddy --skin spiderman  (Launch with Spider-Man)"
echo "    buddy --skins           (Open Character Skin Gallery)"
echo "    buddy --settings        (Open Settings Dialog)"
echo "    buddy --pomodoro start  (Start Pomodoro focus timer)"
echo "    buddy --stats           (View productivity stats)"
echo "    buddy --quit            (Exit active Buddy)"
echo ""
echo "Tip: Right-click the companion or the top Menu Bar icon"
echo "for instant controls, skins, settings, and Pomodoro timers."
