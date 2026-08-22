"""Core logic for nPhoneKIT.

Most functions are deliberately free of I/O, global state, GUI and `sys.exit`
so they can be imported and unit-tested in isolation. The narrow settings JSON
helpers are the explicit file-I/O boundary used by `main.py`.

The functions here mirror logic that currently lives inline in `main.py`. They
are the canonical, tested implementations; `main.py` is expected to delegate to
them over time so that behaviour stays covered by the test-suite.

The device-selection guards exist to prevent destructive operations from firing
against the wrong or an ambiguous target — the failure mode that can actually
brick a phone.
"""

from __future__ import annotations

import re
import json
from typing import Optional

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def merge_settings(defaults: dict, loaded: object) -> dict:
    """Merge a loaded settings object over the defaults.

    A settings file written by an older version can be missing keys added
    later; reading those keys directly used to raise ``KeyError`` and stop the
    app from opening. Merging over the defaults guarantees every expected key
    exists while preserving any value the user has customised.

    ``loaded`` that is not a dict (corrupt file, wrong JSON shape) is ignored
    and the defaults are returned unchanged.
    """
    result = dict(defaults)
    if isinstance(loaded, dict):
        result.update(loaded)
    return result


def load_settings(path) -> object:
    """Load and validate a settings JSON object from ``path``.

    File and JSON errors are intentionally propagated so the application layer
    can choose the appropriate user-facing fallback message.
    """
    with open(path, "r") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("settings file is not a JSON object")
    return loaded


def save_settings(path, settings: dict) -> None:
    """Write a settings object as indented JSON to ``path``."""
    with open(path, "w") as handle:
        json.dump(settings, handle, indent=2)


def build_tab_specs(strings: dict, actions: dict) -> list[tuple[str, list[tuple[str, str, object]]]]:
    """Build the brand-tab action map without importing GUI or device code."""
    text = strings.get
    samsung = [
        ("FRP Unlock Android 15/16 🔓", "", actions["frp_unlock_android15_16"]),
        (text("frpUnlock2024", "FRP Unlock 2024 🔓"), text("frpUnlock2024info", ""), actions["frp_unlock_2024"]),
        (text("frpUnlock2022", "FRP Unlock 2022 ⛓️"), text("frpUnlock2022info", ""), actions["frp_unlock_2022"]),
        (text("frpUnlockPre2022", "FRP Unlock pre-2022 🔓"), text("frpUnlockPre2022info", ""), actions["frp_unlock_pre_2022"]),
        (text("getVerInfo", "Get Version Info 🧾"), text("getVerInfoTooltip", ""), actions["verinfo"]),
        (text("crashReboot", "Crash/Reboot ⚡"), text("crashRebootInfo", ""), actions["reboot_sam"]),
        (text("samRebootDownloadMode", "Reboot to Download ⬇️"), text("samRebootDownloadModeInfo", ""), actions["reboot_download_sam"]),
        (text("samWifitest", "WIFITEST 🔧"), text("samWifitestInfo", ""), actions["wifitest"]),
        (text("samImeiCheck", "IMEI Check 🔍"), text("samImeiCheckInfo", ""), actions["imeicheck"]),
        (text("samRemoveBloat", "Remove Bloat 🧹"), text("samRemoveBloatInfo", ""), actions["bloat_remove"]),
    ]
    lg = [(text("lgScreenUnlockLabel", "LG Screen Unlock 🔓"), text("lgScreenUnlockTooltip", ""), actions["lg_screen_unlock"])]
    moto = [(text("motoFastbootUnlockFRP1", "Fastboot-Based FRP Unlock"), text("fbbFRPu1tooltip", ""), actions["moto_fastboot_frp"])]
    mtk = [(text("mtkClientLabel", "MTK Client GUI 🚀"), text("mtkClientTooltip", ""), actions["mtkclient"])]
    android = [(text("crashReboot", "Crash/Reboot ⚡"), text("crashRebootInfo", ""), actions["reboot"])]
    adb = [
        (text("fbp", "Set Fake Battery %"), text("fbpInfo", ""), actions["set_fake_battery"]),
        (text("rbp", "Reset Fake Battery %"), text("rbpInfo", ""), actions["reset_fake_battery"]),
    ]
    feedback = [
        (text("featureRequest", "Feature Request"), text("featureRequestInfo", ""), actions["feature_request"]),
        (text("bugReport", "Bug Report"), text("bugReportInfo", ""), actions["bug_report"]),
    ]
    return [
        (text("brandSamsung", "Samsung"), samsung),
        (text("brandLg", "LG"), lg),
        (text("brandMoto", "Motorola"), moto),
        (text("brandMediatek", "MediaTek"), mtk),
        (text("brandAndroid", "Android"), android),
        (text("ADB", "ADB"), adb),
        (text("feedback", "Feedback"), feedback),
    ]


# ---------------------------------------------------------------------------
# Device-info parsing (pure string -> value)
# ---------------------------------------------------------------------------

_MODEL_RE = re.compile(r"Model:\s*(\S+)")
_IMEI_RE = re.compile(r"IMEI:\s*([0-9]+)")


def parse_model(text: Optional[str]) -> Optional[str]:
    """Extract the device model from AT/verinfo output, or ``None``.

    Mirrors the ``re.search(r'Model:\\s*(\\S+)', ...)`` used throughout main.py.
    """
    if not text:
        return None
    m = _MODEL_RE.search(text)
    return m.group(1) if m else None


def parse_imei(text: Optional[str]) -> Optional[str]:
    """Extract a numeric IMEI from device output, or ``None``.

    Only digits are accepted, matching main.py's ``IMEI:\\s*([0-9]+)``.
    """
    if not text:
        return None
    m = _IMEI_RE.search(text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# `adb devices` parsing
# ---------------------------------------------------------------------------


def parse_adb_devices(stdout: Optional[str]) -> list[tuple[str, str]]:
    """Parse ``adb devices`` stdout into ``(serial, state)`` pairs.

    ``state`` is e.g. ``device``, ``unauthorized``, ``offline``. The first line
    (``List of devices attached``) and any blank / malformed line is skipped.
    Mirrors the parser in ``ADB.devices``.
    """
    pairs: list[tuple[str, str]] = []
    if not stdout:
        return pairs
    for line in stdout.splitlines()[1:]:  # skip the header line
        line = line.strip()
        if not line or "\t" not in line:
            continue
        serial, state = line.split("\t", 1)
        pairs.append((serial.strip(), state.strip()))
    return pairs


# ---------------------------------------------------------------------------
# Device-selection guards  (prevent acting on the wrong / not-ready target)
# ---------------------------------------------------------------------------

# Machine-readable reasons a target could not be selected. Callers map these to
# user-facing messages; keeping them as codes keeps this module UI-free.
NO_DEVICE = "no_device"
UNAUTHORIZED = "unauthorized"
OFFLINE = "offline"
NOT_READY = "not_ready"
MULTIPLE_DEVICES = "multiple_devices"


def has_required_group(user_groups, required_groups) -> bool:
    """True if the user belongs to at least one of the serial-access groups.

    Pure decision half of the Linux serial-permission pre-flight in main.py
    (which must still gather ``user_groups`` from the OS). Kept here so the
    membership logic is unit-tested and can't silently regress.
    """
    user = set(user_groups or [])
    return any(g in user for g in (required_groups or []))


def parse_fastboot_devices(stdout: Optional[str]) -> list[str]:
    """Parse ``fastboot devices`` stdout into a list of serials.

    Lines look like ``SERIAL\tfastboot``. Blank / malformed lines are skipped.
    Unlike ``adb devices`` there is no header line and no per-device state
    beyond "fastboot".
    """
    serials: list[str] = []
    if not stdout:
        return serials
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        # Accept "SERIAL fastboot" (normal) or a bare "SERIAL" line.
        if len(parts) >= 2 and parts[1] == "fastboot":
            serials.append(parts[0])
        elif len(parts) == 1:
            serials.append(parts[0])
    return serials


def parse_devconinfo(raw_input: str) -> str:
    """Render Samsung ``AT+DEVCONINFO`` output as readable key/value lines."""
    friendly_names = {
        "MN": "Model", "BASE": "Baseband", "VER": "Software Version",
        "HIDVER": "Hidden Version", "MNC": "Mobile Network Code",
        "MCC": "Mobile Country Code", "PRD": "Product Code", "AID": "App ID",
        "CC": "Country Code", "OMCCODE": "OMC Code", "SN": "Serial Number",
        "IMEI": "IMEI", "UN": "Unique Number", "PN": "Phone Number",
        "CON": "Connection Types", "LOCK": "SIM Lock", "LIMIT": "Limit Status",
        "SDP": "SDP Mode", "HVID": "Partition Info",
    }
    parsed_output = []
    for line in (raw_input or "").strip().splitlines():
        if "+DEVCONINFO:" not in line:
            continue
        content = line.split(":", 1)[1].strip()
        for item in content.split(";"):
            if not item:
                continue
            match = re.match(r'(\w+)\((.*?)\)', item)
            if match:
                key, value = match.groups()
                parsed_output.append(
                    f"{friendly_names.get(key, key)}: {value if value else 'N/A'}"
                )
    return "\n".join(parsed_output)


# User-facing explanations for each selection failure reason. Kept here (UI-free
# strings) so the mapping is testable; callers render them however they like.
_REASON_MESSAGES = {
    NO_DEVICE: "No device detected. Connect the device and try again.",
    UNAUTHORIZED: (
        "Device is unauthorized. Accept the USB debugging prompt on the "
        "device screen, then try again."
    ),
    OFFLINE: "Device is offline. Reconnect it (or re-plug the cable) and try again.",
    NOT_READY: "Device is not ready yet. Wait for it to finish connecting and try again.",
    MULTIPLE_DEVICES: (
        "More than one device is connected. Connect only the target device and "
        "try again — this operation refuses to guess which one you mean."
    ),
}


def describe_selection_reason(reason: Optional[str]) -> str:
    """Map a selection reason code to a user-facing message."""
    return _REASON_MESSAGES.get(reason, "Device not available.")


def select_serial_port(ports) -> tuple[Optional[str], Optional[str]]:
    """Pick the serial port to use and, when ambiguous, return an info note.

    Returns ``(port, note)``. This deliberately does NOT refuse when several
    ports are present: a single phone commonly exposes multiple serial
    interfaces (e.g. ttyACM0/ttyACM1), so port count is not device count and
    refusing would break the normal single-device case. The historical
    "first candidate" choice is preserved; ``note`` is a heads-up (or None).
    """
    ports = list(ports or [])
    if not ports:
        return None, None
    chosen = ports[0]
    if len(ports) == 1:
        return chosen, None
    note = (
        f"Multiple serial ports detected ({', '.join(ports)}); using {chosen}. "
        "A single phone can expose several interfaces, so this is normal — but "
        "if a second device is connected, disconnect it to be sure."
    )
    return chosen, note


def _serial_device_identity(port):
    """Identity that groups serial interfaces belonging to the same phone.

    A single device commonly exposes several serial interfaces (ttyACM0/1/...),
    all sharing one USB VID/PID/serial-number. Ports without any USB identity
    (virtual/legacy serial) are treated as distinct, keyed by their path.
    ``port`` is a pyserial ``ListPortInfo``-like object.
    """
    vid = getattr(port, "vid", None)
    pid = getattr(port, "pid", None)
    serial_number = getattr(port, "serial_number", None)
    if vid is None and pid is None and serial_number is None:
        return ("path", getattr(port, "device", None))
    return ("usb", vid, pid, serial_number)


def distinct_serial_devices(ports) -> dict:
    """Group ``list_ports.comports()``-like entries by physical device.

    Returns a mapping of identity -> list of ports for that device.
    """
    groups: dict = {}
    for port in ports or []:
        groups.setdefault(_serial_device_identity(port), []).append(port)
    return groups


def multi_device_note(ports) -> Optional[str]:
    """Warn only when more than one distinct physical device is connected.

    Unlike a raw port count, this groups a phone's multiple serial interfaces
    into one device (via USB VID/PID/serial), so the note fires for genuinely
    separate devices -- the case that risks acting on the wrong phone -- and not
    for a normal single phone that exposes several interfaces. Returns None when
    zero or one device is present.
    """
    groups = distinct_serial_devices(ports)
    if len(groups) <= 1:
        return None
    labels = []
    for port_list in groups.values():
        labels.append(", ".join(sorted(
            getattr(p, "device", "?") or "?" for p in port_list
        )))
    return (
        f"Multiple devices detected ({'; '.join(sorted(labels))}). "
        "Connect only the target device so operations can't act on the wrong one."
    )


def usable_devices(pairs: list[tuple[str, str]]) -> list[str]:
    """Return serials of devices in the ready ``device`` state."""
    return [serial for serial, state in pairs if state == "device"]


def select_target_device(pairs: list[tuple[str, str]]) -> tuple[Optional[str], Optional[str]]:
    """Choose the single device a destructive op may run against.

    Returns ``(serial, None)`` only when exactly one device is present and
    ready. Otherwise returns ``(None, reason)`` where ``reason`` is one of the
    module-level codes. This is the pre-flight gate: a flash/unlock/reboot
    should refuse to proceed unless the target is unambiguous and ready, so an
    accidental multi-device or half-connected state can't hit the wrong phone.
    """
    ready = usable_devices(pairs)
    if len(ready) == 1:
        return ready[0], None
    if len(ready) > 1:
        return None, MULTIPLE_DEVICES
    # No ready device: explain why, most actionable first.
    if not pairs:
        return None, NO_DEVICE
    states = {state for _, state in pairs}
    if "unauthorized" in states:
        return None, UNAUTHORIZED
    if "offline" in states:
        return None, OFFLINE
    return None, NOT_READY
