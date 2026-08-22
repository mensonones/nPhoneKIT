"""Unit tests for nphonekit_core (pure logic + device-safety guards).

Run with:  python3 -m pytest
"""

import nphonekit_core as core


# ---------------------------------------------------------------------------
# merge_settings
# ---------------------------------------------------------------------------

DEFAULTS = {
    "dark_theme": True,
    "update_check": False,
    "basic_success_checks": True,
    "contributionsuggestions": True,
}


def test_merge_fills_missing_keys():
    # Old settings file missing a key added later must not lose it.
    loaded = {"dark_theme": False}
    merged = core.merge_settings(DEFAULTS, loaded)
    assert merged["dark_theme"] is False           # user value preserved
    assert merged["contributionsuggestions"] is True  # default filled in
    assert set(merged) == set(DEFAULTS)


def test_merge_preserves_user_overrides():
    loaded = {"update_check": True, "basic_success_checks": False}
    merged = core.merge_settings(DEFAULTS, loaded)
    assert merged["update_check"] is True
    assert merged["basic_success_checks"] is False


def test_merge_ignores_extra_unknown_keys_are_kept():
    # Unknown keys from a newer/edited file are kept (forward-compatible).
    merged = core.merge_settings(DEFAULTS, {"future_flag": 1})
    assert merged["future_flag"] == 1


def test_merge_corrupt_loaded_falls_back_to_defaults():
    for bad in (None, [], "not a dict", 42):
        merged = core.merge_settings(DEFAULTS, bad)
        assert merged == DEFAULTS
        assert merged is not DEFAULTS  # returns a copy, never the original


def test_merge_does_not_mutate_defaults():
    core.merge_settings(DEFAULTS, {"dark_theme": False})
    assert DEFAULTS["dark_theme"] is True


# ---------------------------------------------------------------------------
# parse_model
# ---------------------------------------------------------------------------

def test_parse_model_basic():
    assert core.parse_model("Model: SM-G991B\nOther: x") == "SM-G991B"


def test_parse_model_extra_whitespace():
    assert core.parse_model("Model:     SM-A536E") == "SM-A536E"


def test_parse_model_absent_returns_none():
    assert core.parse_model("no model here") is None


def test_parse_model_empty_and_none():
    assert core.parse_model("") is None
    assert core.parse_model(None) is None


# ---------------------------------------------------------------------------
# parse_imei
# ---------------------------------------------------------------------------

def test_parse_imei_basic():
    assert core.parse_imei("IMEI: 490154203237518") == "490154203237518"


def test_parse_imei_rejects_non_digits():
    # Letters after IMEI: must not be captured as an IMEI.
    assert core.parse_imei("IMEI: not-available") is None


def test_parse_imei_absent_and_none():
    assert core.parse_imei("nothing") is None
    assert core.parse_imei(None) is None


# ---------------------------------------------------------------------------
# parse_adb_devices
# ---------------------------------------------------------------------------

def test_parse_adb_devices_single():
    out = "List of devices attached\nR58N12ABCDE\tdevice\n"
    assert core.parse_adb_devices(out) == [("R58N12ABCDE", "device")]


def test_parse_adb_devices_multiple_states():
    out = (
        "List of devices attached\n"
        "AAAA\tdevice\n"
        "BBBB\tunauthorized\n"
        "CCCC\toffline\n"
    )
    assert core.parse_adb_devices(out) == [
        ("AAAA", "device"),
        ("BBBB", "unauthorized"),
        ("CCCC", "offline"),
    ]


def test_parse_adb_devices_empty_and_none():
    assert core.parse_adb_devices("List of devices attached\n") == []
    assert core.parse_adb_devices("") == []
    assert core.parse_adb_devices(None) == []


def test_parse_adb_devices_skips_blank_and_malformed():
    out = "List of devices attached\n\ngarbage-no-tab\nAAAA\tdevice\n"
    assert core.parse_adb_devices(out) == [("AAAA", "device")]


# ---------------------------------------------------------------------------
# Device-selection guards  (device-safety critical)
# ---------------------------------------------------------------------------

def test_select_single_ready_device_ok():
    serial, reason = core.select_target_device([("AAAA", "device")])
    assert serial == "AAAA"
    assert reason is None


def test_select_no_device():
    serial, reason = core.select_target_device([])
    assert serial is None
    assert reason == core.NO_DEVICE


def test_select_multiple_ready_is_refused():
    # Two ready devices: a destructive op must NOT guess which one.
    serial, reason = core.select_target_device([("AAAA", "device"), ("BBBB", "device")])
    assert serial is None
    assert reason == core.MULTIPLE_DEVICES


def test_select_unauthorized_reported():
    serial, reason = core.select_target_device([("AAAA", "unauthorized")])
    assert serial is None
    assert reason == core.UNAUTHORIZED


def test_select_offline_reported():
    serial, reason = core.select_target_device([("AAAA", "offline")])
    assert serial is None
    assert reason == core.OFFLINE


def test_select_unauthorized_takes_priority_over_offline():
    # When both a fixable (unauthorized) and a stuck (offline) device exist and
    # none is ready, surface the actionable one first.
    pairs = [("AAAA", "offline"), ("BBBB", "unauthorized")]
    serial, reason = core.select_target_device(pairs)
    assert serial is None
    assert reason == core.UNAUTHORIZED


def test_select_unknown_state_is_not_ready():
    serial, reason = core.select_target_device([("AAAA", "bootloader")])
    assert serial is None
    assert reason == core.NOT_READY


def test_usable_devices_filters_to_ready_only():
    pairs = [("AAAA", "device"), ("BBBB", "offline"), ("CCCC", "device")]
    assert core.usable_devices(pairs) == ["AAAA", "CCCC"]


# ---------------------------------------------------------------------------
# has_required_group  (Linux serial-permission decision)
# ---------------------------------------------------------------------------

SERIAL_GROUPS = ["dialout", "uucp", "lock", "tty"]


def test_has_required_group_member():
    assert core.has_required_group(["wheel", "dialout"], SERIAL_GROUPS) is True


def test_has_required_group_not_member():
    assert core.has_required_group(["wheel", "sudo"], SERIAL_GROUPS) is False


def test_has_required_group_empty_user_groups():
    assert core.has_required_group([], SERIAL_GROUPS) is False


def test_has_required_group_handles_none():
    assert core.has_required_group(None, SERIAL_GROUPS) is False
    assert core.has_required_group(["dialout"], None) is False


# ---------------------------------------------------------------------------
# parse_fastboot_devices
# ---------------------------------------------------------------------------

def test_parse_fastboot_devices_single():
    assert core.parse_fastboot_devices("ZY22ABCDEF\tfastboot\n") == ["ZY22ABCDEF"]


def test_parse_fastboot_devices_multiple():
    out = "AAAA\tfastboot\nBBBB\tfastboot\n"
    assert core.parse_fastboot_devices(out) == ["AAAA", "BBBB"]


def test_parse_fastboot_devices_empty_and_none():
    assert core.parse_fastboot_devices("") == []
    assert core.parse_fastboot_devices(None) == []
    assert core.parse_fastboot_devices("\n\n") == []


def test_parse_fastboot_devices_bare_serial_line():
    assert core.parse_fastboot_devices("AAAA\n") == ["AAAA"]


# ---------------------------------------------------------------------------
# fastboot selection via select_target_device (0 / 1 / many)
# ---------------------------------------------------------------------------

def _fb_pairs(serials):
    return [(s, "device") for s in serials]


def test_fastboot_single_ok():
    serial, reason = core.select_target_device(_fb_pairs(["AAAA"]))
    assert serial == "AAAA"
    assert reason is None


def test_fastboot_none_refused():
    serial, reason = core.select_target_device(_fb_pairs([]))
    assert serial is None
    assert reason == core.NO_DEVICE


def test_fastboot_multiple_refused():
    serial, reason = core.select_target_device(_fb_pairs(["AAAA", "BBBB"]))
    assert serial is None
    assert reason == core.MULTIPLE_DEVICES


# ---------------------------------------------------------------------------
# describe_selection_reason
# ---------------------------------------------------------------------------

def test_describe_reason_known_codes_are_nonempty():
    for reason in (core.NO_DEVICE, core.UNAUTHORIZED, core.OFFLINE,
                   core.NOT_READY, core.MULTIPLE_DEVICES):
        msg = core.describe_selection_reason(reason)
        assert isinstance(msg, str) and msg


def test_describe_reason_unknown_has_fallback():
    assert core.describe_selection_reason("something_else") == "Device not available."


def test_describe_reason_none_has_fallback():
    assert core.describe_selection_reason(None) == "Device not available."
