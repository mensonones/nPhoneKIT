from nphonekit_other_actions import macos_libusb_present, run_mtkclient, run_moto_fastboot_frp


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
