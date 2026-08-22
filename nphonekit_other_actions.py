"""Non-Samsung device action helpers."""

import ctypes.util
import os
import re
import time


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


def run_moto_fastboot_frp(
    *,
    methods,
    confirm_method,
    show_messagebox,
    strings,
    eraser_class,
    select_target,
    describe_reason,
    output=print,
):
    """Erase Motorola FRP partitions only after an unambiguous target check."""
    method = next((item for item in methods if item.get("id") == "moto_fastboot_frp_unlock"), None)
    if not method or not confirm_method(
        method["title"], method["desc"], method["pros"], method["cons"], method["minutes"]
    ):
        return False

    show_messagebox(200, 200, "nPhoneKIT", strings["motoFastbootGuide"])
    try:
        eraser = eraser_class()
    except FileNotFoundError as error:
        output(f"Aborting: {error}")
        show_messagebox(200, 200, "nPhoneKIT", str(error))
        return False

    serial, reason = select_target([(serial, "device") for serial in eraser.list_devices()])
    if reason:
        message = describe_reason(reason)
        output(f"Aborting fastboot FRP erase: {message}")
        show_messagebox(200, 200, "nPhoneKIT", message)
        return False

    eraser.erase_config(serial)
    eraser.erase_persist(serial)
    eraser.erase_frp(serial)
    eraser.wipe_data_cache(serial)
    return True


def run_lg_screen_unlock(
    *, methods, confirm_method, strings, verinfo, at, flush_output,
    show_messagebox, success_checks, hardware_uuid, read_output,
    sleep=time.sleep, output=print,
):
    """Run the supported LG screen-unlock flow."""
    method = next((item for item in methods if item.get("id") == "lg_unlock"), None)
    if not method or not confirm_method(
        method["title"], method["desc"], method["pros"], method["cons"], method["minutes"]
    ):
        return False
    info = verinfo(False)
    model = re.search(r"Model:\s*(\S+)", info)
    show_messagebox(500, 200, "nPhoneKIT", strings["lgScreenUnlockSupportedDevs"])
    output(strings["lgRunningScreenUnlock"], end="")
    show_messagebox(600, 100, "nPhoneKIT", strings["lgScreenUnlockSteps"])
    sleep(1)
    if not at.usbswitch("-l", "LG Screen Unlock"):
        return False
    flush_output()
    at.send("AT%KEYLOCK=0")
    device_output = read_output()
    if "error" in device_output or "Error" in device_output:
        output(strings["failText"] + "\n")
        output(strings["lgScreenUnlockError"])
        success_checks(hardware_uuid(), model, "LG_Screen_Unlock", "Fail")
        return False
    flush_output()
    output(strings["okText"] + "\n")
    output(strings["lgScreenUnlockSuccess"])
    success_checks(hardware_uuid(), model, "LG_Screen_Unlock", "Success")
    return True
