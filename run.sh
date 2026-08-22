#!/usr/bin/env bash
#
# Turnkey launcher for Linux: install everything nPhoneKIT needs, then run it.
#
# Usage:
#   ./run.sh                 # install missing deps (if any), then launch
#   ./run.sh --no-install    # skip the install step and just launch
#
# On Debian/Ubuntu this installs the Python packages from the distro
# (python3-pyqt5 etc.), which also pull in the Qt "xcb" system libraries, so no
# virtualenv or pip step is required. For other distros, install the equivalent
# packages first (see README / scripts/install-linux-deps.sh), then run with
# `./run.sh --no-install`.
#
set -euo pipefail

cd "$(dirname "$0")"

INSTALL=1
for arg in "$@"; do
    case "$arg" in
        --no-install) INSTALL=0 ;;
    esac
done

if [ "$INSTALL" -eq 1 ]; then
    if command -v apt-get >/dev/null 2>&1; then
        echo "==> Installing nPhoneKIT dependencies (Debian/Ubuntu)..."
        sudo apt-get update
        sudo apt-get install -y \
            python3 python3-tk python3-serial python3-requests python3-pyqt5 adb \
            libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
            libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0 libxcb-cursor0 libgl1
    else
        echo "==> Non-apt system detected; skipping automatic install."
        echo "    Install dependencies with your package manager first"
        echo "    (see README.md / scripts/install-linux-deps.sh), then run:"
        echo "        ./run.sh --no-install"
    fi
fi

echo "==> Launching nPhoneKIT..."
# Note: on Linux the app checks serial-port permissions on startup. If you are
# not in a serial group (e.g. dialout), it will show the exact command to fix it.
exec python3 main.py
