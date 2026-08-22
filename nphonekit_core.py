"""Pure, side-effect-free core logic for nPhoneKIT.

Everything in this module is deliberately free of I/O, global state, GUI and
`sys.exit` so it can be imported and unit-tested in isolation (`main.py` itself
is not importable in a test process because, at module load, it opens serial
ports, starts threads and may call `sys.exit`).

The functions here mirror logic that currently lives inline in `main.py`. They
are the canonical, tested implementations; `main.py` is expected to delegate to
them over time so that behaviour stays covered by the test-suite.

The device-selection guards exist to prevent destructive operations from firing
against the wrong or an ambiguous target — the failure mode that can actually
brick a phone.
"""

from __future__ import annotations

import re
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
