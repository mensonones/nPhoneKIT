"""Maintenance and diagnostic helpers for nPhoneKIT."""

import os
import platform
import importlib
import importlib.util
import subprocess
import sys
import traceback


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


ERR_OK = 0
ERR_PYSERIAL_NOT_INSTALLED = 1001
ERR_WRONG_SERIAL_PACKAGE = 1002
ERR_PIP_FAILED = 1003
ERR_IMPORT_SHADOWED = 1004


def self_fix_serial(
    *,
    find_spec=importlib.util.find_spec,
    input_func=input,
    check_call=subprocess.check_call,
    import_module=importlib.import_module,
    cwd=None,
    python_executable=None,
    platform_name=None,
    geteuid=None,
    output=print,
    traceback_formatter=traceback.format_exc,
):
    """Diagnose and, with explicit consent, repair the PySerial install.

    Dependencies are parameters so tests can exercise every branch without
    modifying the interpreter running the test suite.
    """
    python_executable = python_executable or sys.executable
    cwd = cwd or os.getcwd()
    platform_name = platform_name or os.name
    if geteuid is None and hasattr(os, "geteuid"):
        geteuid = os.geteuid

    output(f"[nPhoneKIT (Self-Fix)] Python: {python_executable}")

    shadow = next(
        (os.path.join(cwd, candidate) for candidate in ("serial.py", "serial")
         if os.path.exists(os.path.join(cwd, candidate))),
        None,
    )
    if shadow:
        output(f"[nPhoneKIT (Self-Fix)] Found shadowing path: {shadow}")
        output("[nPhoneKIT (Self-Fix)] Remove or rename this file/folder for nPhoneKIT to work.")
        error_code = ERR_IMPORT_SHADOWED
    else:
        spec = find_spec("serial")
        pyspec = find_spec("pyserial")
        output(f"[nPhoneKIT (Self-Fix)] serial spec: {spec}")
        output(f"[nPhoneKIT (Self-Fix)] pyserial spec: {pyspec}")

        if spec and not pyspec:
            output("[nPhoneKIT (Self-Fix)] The wrong 'serial' package appears to be installed instead of pyserial.")
            fix_cmds = [
                [python_executable, "-m", "pip", "uninstall", "-y", "serial"],
                [python_executable, "-m", "pip", "install", "--upgrade", "pyserial"],
            ]
            fail_code = ERR_WRONG_SERIAL_PACKAGE
        else:
            output("[nPhoneKIT (Self-Fix)] pyserial does not appear to be installed.")
            fix_cmds = [[python_executable, "-m", "pip", "install", "--upgrade", "pyserial"]]
            fail_code = ERR_PYSERIAL_NOT_INSTALLED

        output("[nPhoneKIT (Self-Fix)] These commands would fix it (they change THIS Python environment):")
        for command in fix_cmds:
            output("    " + " ".join(command))
        if platform_name != "nt" and geteuid is not None and geteuid() == 0:
            output("[nPhoneKIT (Self-Fix)] WARNING: running as root/sudo would modify SYSTEM Python packages.")

        consent = input_func("[nPhoneKIT (Self-Fix)] Run the commands above now? (y/n): ")
        if consent not in ("y", "Y"):
            output("[nPhoneKIT (Self-Fix)] Skipped. Run the commands above yourself when ready.")
            error_code = fail_code
        else:
            try:
                for command in fix_cmds:
                    check_call(command)
            except Exception as pip_error:
                output(f"[nPhoneKIT (Self-Fix)] pip failed: {pip_error}")
                error_code = ERR_PIP_FAILED
            else:
                try:
                    serial = import_module("serial")
                    output(
                        "[nPhoneKIT (Self-Fix)] serial fixed! "
                        f"version={getattr(serial, '__version__', 'unknown')}"
                    )
                    error_code = ERR_OK
                except Exception as retry_error:
                    output(f"[nPhoneKIT (Self-Fix)] Import still failing after fix: {retry_error}")
                    output(traceback_formatter())
                    error_code = fail_code

    if error_code == ERR_OK:
        output("[nPhoneKIT (Self-Fix)] Self-fix succeeded!")
    else:
        output(f"[nPhoneKIT (Self-Fix)] Failed to fix the error. Please open a GitHub issue with the error code: {error_code}")
    return error_code
