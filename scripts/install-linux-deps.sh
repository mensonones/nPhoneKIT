#!/usr/bin/env bash
#
# Install the Linux system libraries nPhoneKIT's GUI needs.
#
# You only need this when PyQt5 is installed from pip (e.g. a virtualenv or
# `pip install -r requirements.txt`). The pip wheel does NOT pull in the Qt
# "xcb" platform system libraries, so without them the app fails to start with:
#
#     qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
#
# If you instead install PyQt5 from your distro (Debian/Ubuntu:
# `python3-pyqt5`, Arch: `pyqt5`), those packages already depend on these
# libraries and you do not need this script.
#
# Usage:  ./scripts/install-linux-deps.sh
#
set -euo pipefail

# Qt xcb platform runtime libraries + adb, on Debian/Ubuntu.
APT_PACKAGES=(
    python3-tk            # Tkinter (stdlib module, separate OS package)
    libxcb-xinerama0
    libxcb-icccm4
    libxcb-image0
    libxcb-keysyms1
    libxcb-render-util0
    libxcb-xkb1
    libxkbcommon-x11-0
    libxcb-cursor0
    libgl1                # Qt needs an OpenGL loader
    adb                   # Android Debug Bridge
)

if command -v apt-get >/dev/null 2>&1; then
    echo "Detected apt (Debian/Ubuntu). Installing GUI system libraries..."
    sudo apt-get update
    sudo apt-get install -y "${APT_PACKAGES[@]}"
    echo "Done."
    exit 0
fi

cat <<'EOF'
This script currently automates Debian/Ubuntu (apt) only.

For other distributions, install the Qt xcb platform libraries, Tkinter, an
OpenGL loader, and adb using your package manager. Equivalents:

  Arch:    sudo pacman -S --needed tk libxcb xcb-util-cursor xcb-util-keysyms \
                    xcb-util-wm xcb-util-image xcb-util-renderutil \
                    libxkbcommon-x11 libglvnd android-tools
  Fedora:  sudo dnf install python3-tkinter xcb-util-cursor xcb-util-keysyms \
                    xcb-util-wm xcb-util-image xcb-util-renderutil \
                    libxkbcommon-x11 mesa-libGL android-tools

Alternatively, install PyQt5 from your distro package (e.g. python3-pyqt5),
which already pulls in these libraries.
EOF
EOF
