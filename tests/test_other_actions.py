from nphonekit_other_actions import macos_libusb_present, run_mtkclient


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
