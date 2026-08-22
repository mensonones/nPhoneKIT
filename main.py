#
#             ███████████  █████                                   █████   ████ █████ ███████████
#            ░░███░░░░░███░░███                                   ░░███   ███░ ░░███ ░█░░░███░░░█
#  ████████   ░███    ░███ ░███████    ██████  ████████    ██████  ░███  ███    ░███ ░   ░███  ░
# ░░███░░███  ░██████████  ░███░░███  ███░░███░░███░░███  ███░░███ ░███████     ░███     ░███
#  ░███ ░███  ░███░░░░░░   ░███ ░███ ░███ ░███ ░███ ░███ ░███████  ░███░░███    ░███     ░███
#  ░███ ░███  ░███         ░███ ░███ ░███ ░███ ░███ ░███ ░███░░░   ░███ ░░███   ░███     ░███
#  ████ █████ █████        ████ █████░░██████  ████ █████░░██████  █████ ░░████ █████    █████
# ░░░░ ░░░░░ ░░░░░        ░░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░░   ░░░░ ░░░░░    ░░░░░
#

# IMPORTS AND WHY EACH ONE IS NEEDED

import os # Executing most commands
import tkinter as tk # Main GUI (deprecated, slowly being removed)
from tkinter import messagebox # Opening message/warning boxes
from pathlib import Path # Importing settings
import sys # Getting basic system info
import platform # Checking the current OS
import threading # Using multiple threads
import webbrowser # Opening browser to any page
import xml.etree.ElementTree as ET # Importing strings.xml
from PyQt5 import QtCore, QtGui, QtWidgets # GUI
from PyQt5.QtGui import QFont
from nphonekit_ui import (
    InstantTooltips,
    MainWindow as UiMainWindow,
    MainWindowServices,
    QtDialogHelper,
)
import nphonekit_core # Pure, unit-tested core logic (parsing, settings merge, device guards)
from nphonekit_services import (
    FeedbackClient,
    TelemetryClient,
    UpdateClient,
    public_hardware_uuid,
)
from nphonekit_maintenance import get_os_info, self_fix_serial
from nphonekit_runtime import initialize_runtime
from nphonekit_settings import DEFAULT_SETTINGS, SettingsStore
from nphonekit_maintenance_ui import get_output_text, show_serial_permission_fix
from nphonekit_action_support import (
    load_unlock_methods,
    maybe_show_contribution,
    unlock_modem,
)
from nphonekit_samsung_actions import SamsungFrpActions
from nphonekit_other_actions import (
    run_lg_screen_unlock,
    run_mtkclient,
    run_moto_fastboot_frp,
    reset_fake_battery_percent,
    set_fake_battery_percent,
    submit_feedback,
)
from nphonekit_ui_helpers import find_logo, material_qss, prompt_input
from nphonekit_legacy_ui import stw

## nPhoneKIT permissions (these are the things that nPhoneKIT is capable of doing):

# Communicate with USB devices using ADB, MTP, and AT commands.
# Communicate with external servers to verify whether an action worked or not.
# Open a new tab in the default browser
# Checking and getting basic information about the current system

# ===========================================================================================================
# CONFIGURATION VARIABLES
# ===========================================================================================================

VERSION = "1.6.8"
DEBUGMODE = False

# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE (included in the nPhoneKIT source) for more details.

# ===========================================================================================================

# Requirements:
#
# Ubuntu >=20.0.4-LTS
# Windows support exists but is not well-supported yet.
# At least 1 USB A or USB C port
# Python
# Everything in requirements.txt
#

# ============================================================================= #
# You shouldn't edit anything below this line unless you know what you're doing #
# ============================================================================= #

SETTINGS_PATH = Path("settings.json") # Load settings externally
settings_store = SettingsStore(SETTINGS_PATH, DEFAULT_SETTINGS)
settings = settings_store.load_effective()

dark_theme = settings['dark_theme']
hacker_font = settings['hacker_font']
slower_animations = settings['slower_animations']
update_check = settings['update_check']
enable_preload = settings['enable_preload']
debug_info = settings['debug_info']
basic_success_checks = settings['basic_success_checks']
contributionsuggestions = settings['contributionsuggestions']

def load_strings(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    return {
        elem.attrib['name']: elem.text.replace('\\n', '\n') if elem.text else ''
        for elem in root.findall('string')
    }

# Load strings
strings = load_strings("strings.xml") # Load almost every string from strings.xml (ez translations)

# Load settings
def load_settings():
    return settings_store.load_saved()

# Save settings
def save_settings(new_settings):
    settings_store.save(new_settings)


def persist_settings():
    settings_store.persist(settings)

if platform.system() == "Windows":
    os_config = "WINDOWS"
elif platform.system() == "Darwin":
    os_config = "MACOS"
else:
    os_config = "LINUX"  # Linux and other POSIX systems

if os_config == "WINDOWS":
    enable_preload = False # Preload doesn't work on Windows; disable it

preload_done = threading.Event() # Event variable to check whether the Samsung modem preload has completed

# Imports that have error handling because they are sometimes not installed or are the cause of another error
try:
    import serial  # Communicating with device; late for self-fix bootstrap  # noqa: E402,F401
except ModuleNotFoundError:
    print("[nPhoneKIT] PySerial Error, wasn't able to import serial module.")
    x = input("Run Self-Fix Diagnostics? (RECOMMENDED, THIS USUALLY FIXES THE ISSUE) (y/n):")
    if x == "y" or x == "Y":
        self_fix_serial()

from nphonekit_devices import (  # noqa: E402
    ADB,
    AT,
    FastbootPartitionEraser,
    log_command_output,
    readOutput,
    rt,
    SamsungBloatwareRemover,
    SamsungDownloadModeClient,
    SamsungDeviceInfoClient,
    SamsungRebootClient,
    SamsungWifiTestClient,
    MtkClientRunner,
    BatteryLevelClient,
    SerialManager,
    SerialManagerWindows,
    SamsungPreloader,
    SamsungModemUnlocker,
    check_serial_permissions,
    is_root,
)  # noqa: E402

MAIN_SCRIPT = os.path.abspath(__file__)

# --- PRIVACY_UPDATER_START ---

def privacyupdate():
    # The original "Privacy Mode" wrote a temporary .py file, executed it, and
    # rewrote main.py in place to strip out networking. That self-modifying /
    # dynamic-exec machinery has been removed. Automatic telemetry is already
    # disabled at the source (see TELEMETRY_ENABLED / success_checks), so no
    # self-rewrite is needed to keep this copy from phoning home.
    try:
        messagebox.showinfo(
            "nPhoneKIT",
            "Privacy Mode is not needed in this build: automatic telemetry is "
            "already disabled and nPhoneKIT does not contact external servers "
            "on its own."
        )
    except Exception:
        print("[nPhoneKIT] Automatic telemetry is disabled in this build.")

# --- PRIVACY_UPDATER_END ---


# Helper: worker used when we need to run the dialog in a new process.
# This must be a top-level function for multiprocessing to work reliably.
def check_for_update():
    try:
        latest_version_raw, latest_version = UpdateClient().latest()

        # If the tag is different then the current version, assume it's newer, and prompt update.

        # Based on the unicode "v", depending on whether it's normal or U+2174, prompt for normal update and FORCE for critical update

        # *************************************************************************
        # It's not reccomended to change this in order to bypass a critical update.
        # *************************************************************************

        if latest_version != VERSION:
            # Note: the upstream project could force-quit the app here for a
            # "critical" update (the U+2174 trick). That remote lockout has
            # been removed so an update notice can never block local use.
            if "ⅴ" in latest_version_raw:
                messagebox.showinfo(
                    strings['updateReqd'],
                    strings['updateReqdString'].format(version=VERSION, latest_version=latest_version)
                )
            else:
                messagebox.showinfo(
                    strings['updateAvail'],
                    strings['updateAvailString'].format(version=VERSION, latest_version=latest_version)
                )
    except Exception:
        print(strings['updateCheckFailed'])

def get_public_hardware_uuid():
    return public_hardware_uuid()

FIREBASE_URL = "https://nphonekit-default-rtdb.firebaseio.com/" # URL for success checks

# --- Automatic telemetry hard-disabled ---
# nPhoneKIT normally phones home to Firebase on startup and after actions,
# sending a hashed-MAC UUID, model, action, status, captured errors and OS info.
# This is not required for any device (ADB/serial/FRP/MTK) functionality, so it
# is disabled here. Set to True to re-enable the automatic success checks.
TELEMETRY_ENABLED = False

def success_checks(uuid, model, action, status, first=True):
    TelemetryClient(
        FIREBASE_URL, TELEMETRY_ENABLED, basic_success_checks, VERSION,
        pull_errors=lambda: get_output_text(UiMainWindow.instance),
        get_os_info=get_os_info,
        marker_path=Path(__file__).parent / ".notfirst",
    ).submit(uuid, model, action, status, first)

def report_action(action, status, model=None):
    """Fire the anonymized success-check telemetry for one action, off-thread.

    Wraps the repeated `threading.Thread(target=success_checks, ...)` boilerplate
    used across the device-action wrappers.
    """
    threading.Thread(
        target=success_checks,
        args=(get_public_hardware_uuid(), model, action, status),
    ).start()

# =============================================
#  Different instructions for the user
# =============================================

def MTPmenu():
    show_messagebox_at(500, 200, "nPhoneKIT", strings['mtpMenu'])
    # Show user instructions to enable MTP mode

def adbMenu():
    ADB.send("devices")
    show_messagebox_at(500, 200, "nPhoneKIT", strings['adbMenu'])
    # Show user instructions to enable ADB mode

def show_messagebox_at(x, y, title, content): # Show a customizable message box
    app = QtWidgets.QApplication.instance()
    if app is not None:
        if qt_dialog_helper is None:
            init_qt_dialog_helper()
        if app.thread() != QtCore.QThread.currentThread():
            done = threading.Event()
            result = {}
            qt_dialog_helper.request_message.emit(x, y, title, content, result, done)
            done.wait()
            return
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(content)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.exec_()
        return

    # Create a new top-level window
    box = tk.Tk()
    box.title(title)
    box.geometry(f"+{x}+{y}")
    box.resizable(False, False)

    # Frame and Label
    tk.Label(box, text=content, font=("Segoe UI", 12), padx=20, pady=20).pack()

    # OK button that closes the window
    tk.Button(box, text="OK", width=10, command=box.destroy).pack(pady=(0, 15))

    # Keep it modal — BLOCK everything until this window closes
    box.attributes("-topmost", True)
    box.grab_set()
    box.wait_window()  # <--- THIS is what blocks until closed

def contribution_prompt(x, y):  # Nicely formatted contribution/support message box
    uuid_str = str(get_public_hardware_uuid())

    # If the Qt app is running, show a Qt dialog on the main thread. Creating a raw Tk window here
    # (this is usually called from a worker thread after an unlock) hard-crashes the process on macOS.
    app = QtWidgets.QApplication.instance()
    if app is not None:
        if qt_dialog_helper is None:
            init_qt_dialog_helper()
        if app.thread() != QtCore.QThread.currentThread():
            done = threading.Event()
            qt_dialog_helper.request_contribution.emit(uuid_str, done)
            done.wait()
        else:
            qt_dialog_helper._show_contribution(uuid_str, threading.Event())
        return

    box = tk.Tk()
    box.title("Support nPhoneKIT")
    box.geometry(f"+{x}+{y}")
    box.resizable(False, False)

    message = (
        "PLEASE DO NOT IGNORE THIS MESSAGE:\n\n"
        "Want to help support nPhoneKIT, and get a special Contributor\n"
        "thank you message on the README? Simply fill out the quick\n"
        "and simple form linked below.\n\n"
        "Remember, you can (and should!) submit the form, whether the\n"
        "unlock worked flawlessly or failed horribly! This helps fix\n"
        "bugs and errors for the future.\n\n"
        f"Your unique submission code (prevents spam):\n{uuid_str}\n\n"
        "Want to turn off this message? Turn off 'Contribution Messages'\n"
        "in settings."
    )

    tk.Label(
        box, text=message, font=("Segoe UI", 11),
        padx=25, pady=20, justify="left"
    ).pack()

    # Notification label (hidden until button is clicked)
    notice_label = tk.Label(box, text="", font=("Segoe UI", 9, "italic"), fg="green")
    notice_label.pack(pady=(0, 5))

    def open_form():
        box.clipboard_clear()
        box.clipboard_append(uuid_str)
        box.update()  # keep clipboard content after window closes
        notice_label.config(text="✅ UUID copied to clipboard! Opening form in your browser...")
        webbrowser.open("https://forms.gle/SM8Mjyoz43Jcwxzn8")

    support_button = tk.Button(
        box, text="Support nPhoneKIT — Open Form", width=30, height=2,
        bg="#1a73e8", fg="white", font=("Segoe UI", 11, "bold"),
        activebackground="#1558b0", activeforeground="white",
        command=open_form
    )
    support_button.pack(pady=(0, 15))

    # Small delayed decline link
    decline_label = tk.Label(
        box, text="", font=("Segoe UI", 8), fg="gray50", cursor="hand2"
    )
    decline_label.pack(pady=(0, 15))

    def countdown(remaining):
        if remaining > 0:
            decline_label.config(text=f"(decline available in {remaining}s)")
            box.after(1000, countdown, remaining - 1)
        else:
            decline_label.config(text="No, I don't want to support open-source developers.")
            decline_label.bind("<Button-1>", lambda e: box.destroy())

    countdown(5)

    box.attributes("-topmost", True)
    box.grab_set()
    box.wait_window()

def modemUnlock(manufacturer, softUnlock=False):
    unlock_modem(samsung_modem_unlocker, manufacturer, softUnlock)

# Function that can parse DEVCONINFO in order to make it more readable
parse_devconinfo = nphonekit_core.parse_devconinfo

def formrequest():
    maybe_show_contribution(contributionsuggestions, contribution_prompt)
# =============================================
#  Unlocking methods for different devices
# =============================================

def frp_unlock_pre_aug2022():
    samsung_frp_actions.pre_aug2022()


def frp_unlock_aug2022_to_dec2022():
    samsung_frp_actions.unlock_2022_to_dec2022()


def frp_unlock_2024():
    samsung_frp_actions.unlock_2024()


def frp_unlock_android15_16():
    samsung_frp_actions.unlock_android15_16()

def general_frp_unlock(): # Not completed yet
    raise NotImplementedError("This function is not yet implemented.")
    info = verinfo(False)
    if "Model: SM" in info:
        frp_unlock_pre_aug2022()
    else:
        # to do, add FULLY universal FRP unlock
        print(strings['deviceNotSupportedUniversal'])

def LG_screen_unlock():
    run_lg_screen_unlock(
        methods=load_unlock_methods("unlocks.json"),
        confirm_method=stw,
        strings=strings,
        verinfo=verinfo,
        at=AT,
        flush_output=rt,
        show_messagebox=show_messagebox_at,
        success_checks=lambda *args: threading.Thread(target=success_checks, args=args).start(),
        hardware_uuid=get_public_hardware_uuid,
        read_output=lambda: Path("tmp_output.txt").read_text(),
    )

def MotoFastbootFRP1():
    run_moto_fastboot_frp(
        methods=load_unlock_methods("unlocks.json"),
        confirm_method=stw,
        show_messagebox=show_messagebox_at,
        strings=strings,
        eraser_class=FastbootPartitionEraser,
        select_target=nphonekit_core.select_target_device,
        describe_reason=nphonekit_core.describe_selection_reason,
    )

# ==============================================
#  Simple functions that do stuff to the device
# ==============================================

def verinfo(gui=True, showtext=True): # Get version info on the device. Pretty simple. (not simple, this has taken me hours.)
    info_client = SamsungDeviceInfoClient(AT, readOutput, rt, samsung_modem_unlocker)
    if gui:
        print(strings['getVerInfo'], end="")
        output = info_client.fetch(enable_preload, gui=True)
        if not output:
            print(strings['failText'])
            print(strings['verInfoCheckConn'])
            model = nphonekit_core.parse_model(output)
            report_action("VersionInfo", "Fail", model)
        else:
            print(strings['okText'])
            model = nphonekit_core.parse_model(output)
            report_action("VersionInfo", "Success", model)
        output = parse_devconinfo(output)
        print(output)
    else:
        #print(strings['getVerInfo'], end="")
        if 1 == 1: # We should verify AT is working before running the below code (deprecated)
            output = info_client.fetch(enable_preload)
            if not output and showtext:
                print(strings['failText'])
            elif output and showtext:
                print(strings['okText'])
            output = parse_devconinfo(output) # Make the output actually readable (parse the output)
            model = nphonekit_core.parse_model(output) # Extract only the model no. from the output
            if output == "" or output is None:
                report_action("VersionInfo", "Fail", model)
                return "Fail"
            else:
                report_action("VersionInfo", "Success", model)
                return output # Return the version info

def wifitest(): # Opens a hidden WLANTEST menu on Samsung devices
    info = verinfo(False)
    model = nphonekit_core.parse_model(info)

    print(strings['openingWifitest'], end="")
    MTPmenu()
    if SamsungWifiTestClient(
        AT, samsung_modem_unlocker, rt, readOutput
    ).open():
        print(strings['okText'])
        report_action("WIFITEST", "Success", model)
    else:
        print(strings['failText'])
        report_action("WIFITEST", "Fail", model)

def reboot(): # Crash an android phone to reboot
    print(strings['crashingToReboot'], end="")
    MTPmenu()
    info = verinfo(False)
    model = nphonekit_core.parse_model(info)
    result = SamsungRebootClient(AT, rt, readOutput).crash_reboot()
    if result is False:
        print(strings['failText'])
        print(strings['crashRebootFailed'])
        report_action("REBOOT", "Fail", model)
    elif result is True:
        print(strings['okText'])
        report_action("REBOOT", "Success", model)

def reboot_sam(): # Crash a Samsung phone to reboot
    print(strings['crashingToReboot'], end="")
    MTPmenu()
    modemUnlock("SAMSUNG", True)
    info = verinfo(False)
    model = nphonekit_core.parse_model(info)
    result = SamsungRebootClient(AT, rt, readOutput).crash_reboot()
    if result is False:
        print(strings['failText'])
        print(strings['crashRebootFailed'])
        report_action("REBOOT_SAM", "Fail", model)
    elif result is True:
        print(strings['okText'])
        report_action("REBOOT_SAM", "Success", model)

def bloatRemove():
    print(strings['uninstallingPackages'], end="")
    adbMenu()

    # Pre-flight: only debloat when exactly one ready device is connected, so
    # `pm uninstall` can't run against the wrong phone. Target it explicitly.
    serial, reason = nphonekit_core.select_target_device(ADB.devices())
    if reason:
        msg = nphonekit_core.describe_selection_reason(reason)
        print(strings['failText'])
        print(msg)
        return

    remover = SamsungBloatwareRemover(ADB, readOutput)
    if remover.remove(serial):
        print(strings['okText'])
        print(strings['debloatSucceeded'])
        report_action("DEBLOAT_SAM", "Success")
    else:
        print(strings['failText'])
        print(strings['devNotConnectedOrOtherErr'])
        report_action("DEBLOAT_SAM", "Fail")

def reboot_download_sam(): # Reboot Samsung device to download mode
    print(strings['rebootingDownloadMode'], end="")
    MTPmenu()
    SamsungDownloadModeClient(AT, samsung_modem_unlocker).enter(basic_success_checks)
    if basic_success_checks:
        info = verinfo(False)
        model = nphonekit_core.parse_model(info)
        report_action("REBOOT_DOWNLOAD_SAM", "Fail", model)
    print(" OK")

def imeicheck():
    info = verinfo(False)
    imei = nphonekit_core.parse_imei(info)
    if imei:
        messagebox.showinfo("nPhoneKIT", strings['imeiCheckGuide'])
        if os_config in ("WINDOWS", "MACOS"): # macOS opens the browser the same way Windows does; without this the IMEI page never opens on Mac
            webbrowser.open_new_tab(f"https://www.imei.info/services/blacklist-simple/samsung/check-free/?imei={str(imei)}")
        elif os_config == "LINUX":
            url = f"https://www.imei.info/services/blacklist-simple/samsung/check-free/?imei={str(imei)}"
            original_user = os.environ.get("SUDO_USER", "yourusername")  # linux is complicated :/
            cmd = f'su - {original_user} -c "DISPLAY=$DISPLAY DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS xdg-open \\"{url}\\""'
            os.system(cmd)
        print(strings['imeiChecked'])
    else:
        print(strings['imeiNotFound'])

def mtkclient():
    run_mtkclient(
        MtkClientRunner,
        os_config,
        sys.executable,
        lambda message: (
            print(message),
            show_messagebox_at(500, 200, "nPhoneKIT", message),
        ),
        strings['mtkLibusbMissing'],
    )

def tkinput(title="Enter Value", text="Please enter a value:", placeholder="", ok_text="OK", cancel_text="Cancel"):
    return prompt_input(
        title, text, placeholder, ok_text, cancel_text,
        qt_app=QtWidgets.QApplication.instance(), qt_widgets=QtWidgets,
        qt_core=QtCore, dialog_helper=qt_dialog_helper,
        init_dialog_helper=init_qt_dialog_helper, tk_module=tk,
    )

def featureRequest():
    submit_feedback(
        "feature", tkinput, FeedbackClient(FIREBASE_URL),
        get_public_hardware_uuid, VERSION,
    )

def bugReport():
    submit_feedback(
        "bug", tkinput, FeedbackClient(FIREBASE_URL),
        get_public_hardware_uuid, VERSION,
    )

def setFakeBatteryPercent():
    percent = tkinput(
        title="nPhoneKIT",
        text="Fake Battery Percent:",
        placeholder="e.g: 101",
        ok_text="Submit",
        cancel_text="Cancel"
    )
    set_fake_battery_percent(
        value=percent,
        adb_menu=adbMenu,
        client=BatteryLevelClient(ADB, readOutput),
    )

def resetBatteryPercent():
    reset_fake_battery_percent(
        adb_menu=adbMenu,
        client=BatteryLevelClient(ADB, readOutput),
    )

# ===================================
#  PyQt5 GUI Stuff
# ===================================

# ------------ theme & assets helpers ------------
def build_ui_actions():
    return {
        "frp_unlock_android15_16": frp_unlock_android15_16,
        "frp_unlock_2024": frp_unlock_2024,
        "frp_unlock_2022": frp_unlock_aug2022_to_dec2022,
        "frp_unlock_pre_2022": frp_unlock_pre_aug2022,
        "verinfo": verinfo,
        "reboot_sam": reboot_sam,
        "reboot_download_sam": reboot_download_sam,
        "wifitest": wifitest,
        "imeicheck": imeicheck,
        "bloat_remove": bloatRemove,
        "lg_screen_unlock": LG_screen_unlock,
        "moto_fastboot_frp": MotoFastbootFRP1,
        "mtkclient": mtkclient,
        "reboot": reboot,
        "set_fake_battery": setFakeBatteryPercent,
        "reset_fake_battery": resetBatteryPercent,
        "feature_request": featureRequest,
        "bug_report": bugReport,
    }

current_brand = strings.get('brandCurrent', 'Samsung')


def select_brand(name):
    global current_brand
    current_brand = name
    if UiMainWindow.instance:
        UiMainWindow.instance.set_brand(name)

def set_brand(name):
    select_brand(name)

# ------------- entry point -------------
def init_qt_dialog_helper():
    global qt_dialog_helper
    if qt_dialog_helper is None:
        qt_dialog_helper = QtDialogHelper()


def main():
    app = QtWidgets.QApplication(sys.argv)
    init_qt_dialog_helper()
    # apply tooltip palette for visibility
    pal = app.palette()
    pal.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(42,42,42))
    pal.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(240,240,240))
    app.setPalette(pal)
    app.setFont(QFont("Sans Serif"))

    fast_tips = InstantTooltips(delay_ms=1, hide_ms=299000)
    app.installEventFilter(fast_tips)

    services = MainWindowServices(
        strings=strings,
        version=VERSION,
        actions=build_ui_actions(),
        load_settings=load_settings,
        save_settings=save_settings,
        find_logo=find_logo,
        material_qss=material_qss,
    )
    win = UiMainWindow(services)
    win.show()
    sys.exit(app.exec_())

# ===================================
#  Preparing to start the app
# ===================================

serman1 = None
preloader = None
samsung_modem_unlocker = None
samsung_frp_actions = None


def disable_preload():
    global enable_preload
    enable_preload = False


def set_preload_error(value):
    global preload_error
    preload_error = value

def run_app():
    """Perform runtime setup and start the GUI.

    Importing this module defines the application API only. Settings
    persistence, permission checks, serial connections, update checks, and
    background threads belong to the executable entrypoint and therefore
    happen only when the app is launched.
    """
    global serman, serman1, preloader, samsung_modem_unlocker, samsung_frp_actions

    persist_settings()

    if os_config == "LINUX":
        if not check_serial_permissions(os_config, show_serial_permission_fix):
            return
    elif os_config == "WINDOWS" and not is_root(os_config) and not DEBUGMODE:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("nPhoneKIT", strings['sudoReqdError'])
        sys.exit(1)

    if update_check:
        check_for_update()

    runtime = initialize_runtime(
        os_config=os_config,
        strings=strings,
        debug_info=debug_info,
        adb=ADB,
        at=AT,
        rt=rt,
        serial_manager=SerialManager,
        serial_manager_windows=SerialManagerWindows,
        modem_unlocker=SamsungModemUnlocker,
        preloader_factory=SamsungPreloader,
        enable_preload=lambda: enable_preload,
        preload_error=lambda: preload_error,
        preload_done=preload_done,
        disable_preload=disable_preload,
        set_preload_error=set_preload_error,
        set_brand=set_brand,
    )
    serman = runtime.serman
    serman1 = runtime.serman1
    preloader = runtime.preloader
    samsung_modem_unlocker = runtime.samsung_modem_unlocker
    samsung_frp_actions = SamsungFrpActions(
        strings=strings,
        load_methods=load_unlock_methods,
        verinfo=verinfo,
        at=AT,
        adb=ADB,
        log_command_output=log_command_output,
        show_messagebox=show_messagebox_at,
        success_checks=success_checks,
        hardware_uuid=get_public_hardware_uuid,
        formrequest=formrequest,
        confirm_method=stw,
        read_output=readOutput,
    )

    ttthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), "NOT_First", "NOT_First", "Success", False))
    ttthread.start() # Sends basic, anonymized success_checks info with only the model number.
    rt() # Flush the buffer from previous runs of nPhoneKIT just in case
    main() # Start the main GUI (with a cool animation)


if __name__ == "__main__":
    run_app()
