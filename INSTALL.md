# 📦 Buddy Installation Guide

This guide covers installing Buddy on **macOS (Apple Silicon & Intel)**, **Fedora Linux**, and other major Linux distributions.

---

## 🍏 macOS (Apple Silicon & Intel)

Buddy features native AppKit & PyObjC desktop integration on macOS without requiring X11, XQuartz, or GTK.

### 1. Prerequisites (Homebrew)

```bash
brew install python3
```

### 2. Automated Installer

```bash
cd /path/to/buddy
./scripts/install_macos.sh
```

The script verifies required packages (`pycairo`, `pyobjc-framework-Cocoa`, `pyobjc-framework-Quartz`), configures `~/Library/Application Support/Buddy`, and links the `buddy` command into `~/.local/bin/buddy`.

### 3. Standalone Application Bundle (`Buddy.app`)

To build and install a standalone `.app` into `/Applications`:

```bash
./scripts/build_macos_app.sh
cp -R dist/Buddy.app /Applications/
open /Applications/Buddy.app
```

For complete details, architecture, and gestures, see [MACOS.md](MACOS.md).

---

## 🎩 Fedora Linux (Primary Target)

Fedora provides all required libraries in its standard repositories.

### 1. Install System Dependencies

```bash
sudo dnf install -y python3 python3-gobject gtk3 cairo-gobject libappindicator-gtk3 pipewire-utils
```

### 2. Run the Buddy Installer

```bash
cd /path/to/buddy
./install.sh
```

The installer will:
1. Validate required Python and GTK libraries.
2. Create a symlink in `~/.local/bin/buddy`.
3. Install the application icon in `~/.local/share/icons/hicolor/`.
4. Install `buddy.desktop` in `~/.local/share/applications/` and update desktop database.

### 3. Verify Installation

```bash
which buddy
buddy --version
```

---

## 🐧 Ubuntu / Debian / Pop!_OS / Linux Mint

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 python3-cairo pulseaudio-utils
```

### 2. Run Installer

```bash
cd /path/to/buddy
./install.sh
```

---

## 🏹 Arch Linux / Manjaro

### 1. Install Dependencies

```bash
sudo pacman -S --needed python python-gobject gtk3 cairo libappindicator-gtk3 pipewire-pulse
```

### 2. Run Installer

```bash
cd /path/to/buddy
./install.sh
```

---

## 🦎 openSUSE (Tumbleweed / Leap)

```bash
sudo zypper install python3 python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-3_0 libappindicator3-1
./install.sh
```

---

## ⚙️ Enabling Autostart on Login

You can enable Buddy to start automatically on login in two ways:

1. **Via Settings Dialog**:
   Run `buddy --settings`, switch to the **Startup** tab, and check **"Start Buddy automatically on login"**.

2. **Via CLI / Terminal**:
   ```bash
   cp ~/.local/share/applications/buddy.desktop ~/.config/autostart/
   ```
