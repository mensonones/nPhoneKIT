from nphonekit_other_actions import (
    macos_libusb_present,
    reset_fake_battery_percent,
    run_lg_screen_unlock,
    run_mtkclient,
    run_moto_fastboot_frp,
    set_fake_battery_percent,
    submit_feedback,
)


def test_macos_libusb_present_uses_known_library():
    assert macos_libusb_present(find_library=lambda name: "libusb", exists=lambda path: False)


def test_macos_libusb_present_checks_fallback_paths():
    assert macos_libusb_present(find_library=lambda name: None, exists=lambda path: path.startswith("/opt/homebrew"))


def test_run_mtkclient_reports_missing_dependency():
    messages = []

    class Runner:
        def __init__(self, *args):
            pass

        def available(self):
            return False

    assert not run_mtkclient(Runner, "LINUX", "python", messages.append, "missing")
    assert messages == ["missing"]


def test_run_moto_fastboot_frp_refuses_ambiguous_target():
    messages = []

    class Eraser:
        def list_devices(self):
            return ["one", "two"]

    run_moto_fastboot_frp(
        methods=[{"id": "moto_fastboot_frp_unlock", "title": "t", "desc": "d", "pros": "p", "cons": "c", "minutes": 1}],
        confirm_method=lambda *args: True,
        show_messagebox=lambda *args: None,
        strings={"motoFastbootGuide": "guide"},
        eraser_class=Eraser,
        select_target=lambda devices: (None, "multiple_devices"),
        describe_reason=lambda reason: "ambiguous",
        output=messages.append,
    )

    assert messages == ["Aborting fastboot FRP erase: ambiguous"]


def test_run_lg_screen_unlock_reports_device_error():
    reports = []

    class At:
        def usbswitch(self, *args):
            return True

        def send(self, command):
            assert command == "AT%KEYLOCK=0"

    ok = run_lg_screen_unlock(
        methods=[{"id": "lg_unlock", "title": "t", "desc": "d", "pros": "p", "cons": "c", "minutes": 1}],
        confirm_method=lambda *args: True,
        strings={"lgScreenUnlockSupportedDevs": "supported", "lgRunningScreenUnlock": "running", "lgScreenUnlockSteps": "steps", "failText": "FAIL", "lgScreenUnlockError": "error"},
        verinfo=lambda gui: "Model: LG1",
        at=At(),
        flush_output=lambda: None,
        show_messagebox=lambda *args: None,
        success_checks=lambda *args: reports.append(args),
        hardware_uuid=lambda: "uuid",
        read_output=lambda: "Error",
        sleep=lambda seconds: None,
        output=lambda text, **kwargs: None,
    )

    assert not ok
    assert reports[0][2:] == ("LG_Screen_Unlock", "Fail")


def test_submit_feedback_routes_feature_request():
    calls = []

    class Client:
        def feature_request(self, *args):
            calls.append(args)
            return True

    assert submit_feedback("feature", lambda **kwargs: "idea", Client(), lambda: "uuid", "1.0", output=lambda *args: None)
    assert calls == [("idea", "uuid", "1.0")]


def test_set_fake_battery_reports_unauthorized_device():
    messages = []

    class Client:
        def set_level(self, value):
            return "unauthorized"

        @staticmethod
        def unauthorized(value):
            return value == "unauthorized"

    assert not set_fake_battery_percent(value="101", adb_menu=lambda: None, client=Client(), output=messages.append)
    assert "FAIL" in messages[-1]


def test_reset_fake_battery_succeeds():
    messages = []

    class Client:
        def reset(self):
            return "ok"

        @staticmethod
        def unauthorized(value):
            return False

    assert reset_fake_battery_percent(adb_menu=lambda: None, client=Client(), output=messages.append)
    assert "OK" in messages[-1]
