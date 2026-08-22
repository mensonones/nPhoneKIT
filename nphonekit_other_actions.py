"""Non-Samsung device action helpers."""

import ctypes.util
import os


def macos_libusb_present(find_library=ctypes.util.find_library, exists=os.path.exists):
    """Check libusb in system and common macOS package-manager paths."""
    if find_library("usb-1.0") or find_library("usb"):
        return True
    candidates = (
        "/opt/homebrew/lib/libusb-1.0.dylib",
        "/usr/local/lib/libusb-1.0.dylib",
        "/opt/local/lib/libusb-1.0.dylib",
    )
    return any(exists(path) for path in candidates)


def run_mtkclient(runner_class, os_config, python_executable, show_missing, missing_message):
    """Run the MTK client when its native libusb dependency is available."""
    runner = runner_class(os_config, python_executable, macos_libusb_present)
    if not runner.available():
        show_missing(missing_message)
        return False
    runner.run()
    return True
