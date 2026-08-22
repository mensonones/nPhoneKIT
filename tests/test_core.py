"""Unit tests for nphonekit_core (pure logic + device-safety guards).

Run with:  python3 -m pytest
"""

import nphonekit_core as core
import pytest


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


def test_build_tab_specs_keeps_brand_order_and_callbacks():
    names = {
        "frp_unlock_android15_16", "frp_unlock_2024", "frp_unlock_2022",
        "frp_unlock_pre_2022", "verinfo", "reboot_sam", "reboot_download_sam",
        "wifitest", "imeicheck", "bloat_remove", "lg_screen_unlock",
        "moto_fastboot_frp", "mtkclient", "reboot", "set_fake_battery",
        "reset_fake_battery", "feature_request", "bug_report",
    }
    callbacks = {name: object() for name in names}

    tabs = core.build_tab_specs({}, callbacks)

    assert [title for title, _ in tabs] == ["Samsung", "LG", "Motorola", "MediaTek", "Android", "ADB", "Feedback"]
    assert tabs[0][1][0][2] is callbacks["frp_unlock_android15_16"]
    assert len(tabs[-1][1]) == 2


def test_load_settings_reads_json_object(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"dark_theme": false}', encoding="utf-8")

    assert core.load_settings(path) == {"dark_theme": False}


def test_load_settings_rejects_non_object(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="not a JSON object"):
        core.load_settings(path)


def test_save_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    expected = {"dark_theme": False, "future_flag": 1}

    core.save_settings(path, expected)

    assert core.load_settings(path) == expected


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


# ---------------------------------------------------------------------------
# select_serial_port  (transparency, never refuses)
# ---------------------------------------------------------------------------

def test_select_serial_port_none():
    assert core.select_serial_port([]) == (None, None)
    assert core.select_serial_port(None) == (None, None)


def test_select_serial_port_single_no_note():
    port, note = core.select_serial_port(["/dev/ttyACM0"])
    assert port == "/dev/ttyACM0"
    assert note is None


def test_select_serial_port_multiple_keeps_first_and_notes():
    ports = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"]
    port, note = core.select_serial_port(ports)
    # Historical behavior preserved: first candidate is chosen, never refused.
    assert port == "/dev/ttyACM0"
    assert note is not None
    # Note is informative: mentions the chosen port and lists the others.
    assert "/dev/ttyACM0" in note
    assert "/dev/ttyACM1" in note
    assert "/dev/ttyUSB0" in note


# ---------------------------------------------------------------------------
# multi_device_note  (device-aware: groups interfaces by USB VID/PID/serial)
# ---------------------------------------------------------------------------

class _FakePort:
    def __init__(self, device, vid=None, pid=None, serial_number=None):
        self.device = device
        self.vid = vid
        self.pid = pid
        self.serial_number = serial_number


def test_multi_device_note_none_when_no_ports():
    assert core.multi_device_note([]) is None
    assert core.multi_device_note(None) is None


def test_multi_device_note_single_device_multiple_interfaces_is_quiet():
    # One phone exposing three interfaces (same VID/PID/serial) -> no warning.
    ports = [
        _FakePort("/dev/ttyACM0", vid=0x04E8, pid=0x6860, serial_number="ABC"),
        _FakePort("/dev/ttyACM1", vid=0x04E8, pid=0x6860, serial_number="ABC"),
        _FakePort("/dev/ttyACM2", vid=0x04E8, pid=0x6860, serial_number="ABC"),
    ]
    assert core.multi_device_note(ports) is None


def test_multi_device_note_warns_on_two_distinct_devices():
    ports = [
        _FakePort("/dev/ttyACM0", vid=0x04E8, pid=0x6860, serial_number="AAA"),
        _FakePort("/dev/ttyACM1", vid=0x04E8, pid=0x6860, serial_number="AAA"),
        _FakePort("/dev/ttyACM2", vid=0x2717, pid=0xFF40, serial_number="BBB"),
    ]
    note = core.multi_device_note(ports)
    assert note is not None
    assert "Multiple devices detected" in note


def test_multi_device_note_ports_without_usb_identity_count_as_distinct():
    # No VID/PID/serial -> keyed by path, so two are two devices.
    ports = [_FakePort("/dev/ttyUSB0"), _FakePort("/dev/ttyUSB1")]
    assert core.multi_device_note(ports) is not None
    # ...but a single identity-less port is fine.
    assert core.multi_device_note([_FakePort("/dev/ttyUSB0")]) is None


def test_distinct_serial_devices_groups_by_identity():
    ports = [
        _FakePort("/dev/ttyACM0", vid=1, pid=2, serial_number="X"),
        _FakePort("/dev/ttyACM1", vid=1, pid=2, serial_number="X"),
        _FakePort("/dev/ttyACM2", vid=1, pid=2, serial_number="Y"),
    ]
    groups = core.distinct_serial_devices(ports)
    assert len(groups) == 2


def test_parse_devconinfo_renders_known_and_unknown_fields():
    output = core.parse_devconinfo(
        "+DEVCONINFO:MN(SM-S918B);SN(ABC123);CUSTOM();IGNORED"
    )

    assert output == "Model: SM-S918B\nSerial Number: ABC123\nCUSTOM: N/A"
