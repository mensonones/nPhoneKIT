"""Maintenance and diagnostic helpers for nPhoneKIT."""

import os
import platform


def get_os_info():
    """Collect platform and runtime information for diagnostics.

    The function intentionally returns a plain dictionary so callers can
    decide whether and how to display or transmit the information.
    """
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "architecture": platform.architecture()[0],
        "python_version": platform.python_version(),
    }
    system = info["system"]

    if system == "Linux":
        os_release = {}
        try:
            os_release = platform.freedesktop_os_release()
        except AttributeError:
            for path in ("/etc/os-release", "/usr/lib/os-release"):
                if os.path.exists(path):
                    with open(path) as release_file:
                        for line in release_file:
                            line = line.strip()
                            if not line or line.startswith("#") or "=" not in line:
                                continue
                            key, value = line.split("=", 1)
                            os_release[key] = value.strip('"').strip("'")
                    break

        for key, source in (
            ("distro_name", "NAME"),
            ("distro_pretty_name", "PRETTY_NAME"),
            ("distro_id", "ID"),
            ("distro_id_like", "ID_LIKE"),
            ("distro_version", "VERSION"),
            ("distro_version_id", "VERSION_ID"),
            ("distro_codename", "VERSION_CODENAME"),
        ):
            info[key] = os_release.get(source)

        try:
            info["libc"] = platform.libc_ver()
        except Exception:
            info["libc"] = None

        try:
            with open("/proc/version") as version_file:
                info["kernel_build_string"] = version_file.read().strip()
        except Exception:
            info["kernel_build_string"] = None

    elif system == "Windows":
        win_ver = platform.win32_ver()
        info.update(
            {
                "windows_release": win_ver[0],
                "windows_version": win_ver[1],
                "windows_service_pack": win_ver[2],
                "windows_type": win_ver[3],
            }
        )
        try:
            info["windows_edition"] = platform.win32_edition()
        except Exception:
            info["windows_edition"] = None
        try:
            info["windows_is_iot"] = platform.win32_is_iot()
        except Exception:
            info["windows_is_iot"] = None

    elif system == "Darwin":
        info["mac_version"] = platform.mac_ver()

    return info
