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

# On Linux the app needs the current user to be in a serial-access group to talk
# to the device. If they aren't, add them to 'dialout' and re-launch under that
# group with `sg`, so access works immediately -- no logout/reboot required.
in_serial_group() {
    local groups g
    groups=$(id -nG)
    for g in dialout uucp lock tty; do
        case " $groups " in *" $g "*) return 0 ;; esac
    done
    return 1
}

if [ "$(uname)" = "Linux" ] && ! in_serial_group; then
    if getent group dialout >/dev/null 2>&1; then
        echo "==> Adding $(id -un) to the 'dialout' group for serial access..."
        sudo usermod -aG dialout "$(id -un)"
        echo "==> Launching nPhoneKIT (dialout active for this run; no reboot needed)..."
        exec sg dialout -c "cd \"$PWD\" && exec python3 main.py"
    fi
fi

echo "==> Launching nPhoneKIT..."
exec python3 main.py
