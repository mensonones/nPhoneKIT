"""Samsung-specific device action workflows."""

import re
import threading


def samsung_2022_commands():
    """Return the exact AT sequence used by the Samsung 2022/23 flow."""
    initial = [
        "AT+SWATD=0", "AT+ACTIVATE=0,0,0", "AT+DEVCONINFO",
        "AT+KSTRINGB=0,3", "AT+DUMPCTRL=1,0", "AT+DEBUGLVC=0,5",
    ]
    repeated = [
        "AT+SWATD=0", "AT+ACTIVATE=0,0,0", "AT+SWATD=1",
        "AT+DEBUGLVC=0,5", "AT+KSTRINGB=0,3", "AT+DUMPCTRL=1,0",
        "AT+DEBUGLVC=0,5",
    ]
    return initial + repeated * 13


class SamsungFrpActions:
    """Execute Samsung FRP workflows using injected runtime dependencies."""

    def __init__(
        self,
        *,
        strings,
        load_methods,
        verinfo,
        at,
        adb,
        log_command_output,
        show_messagebox,
        success_checks,
        hardware_uuid,
        formrequest,
        confirm_method,
        read_output=None,
    ):
        self.strings = strings
        self.load_methods = load_methods
        self.verinfo = verinfo
        self.at = at
        self.adb = adb
        self.log_command_output = log_command_output
        self.show_messagebox = show_messagebox
        self.success_checks = success_checks
        self.hardware_uuid = hardware_uuid
        self.formrequest = formrequest
        self.confirm_method = confirm_method
        self.read_output = read_output

    def pre_aug2022(self):
        method = next(
            (
                item
                for item in self.load_methods("unlocks.json")
                if item.get("id") == "sam_pre_2022"
            ),
            None,
        )
        if not method or not self.confirm_method(
            method["title"],
            method["desc"],
            method["pros"],
            method["cons"],
            method["minutes"],
        ):
            return

        strings = self.strings
        print(strings["getVerInfo"], end="")
        info = self.verinfo(False)
        model = re.search(r"Model:\s*(\S+)", info)
        action = "FRP_Unlock_Pre_2022"

        if info == "Fail":
            print(strings["deviceCheckPluggedIn2"])
            self._report(model, action, "Fail")
            return

        at_commands = [
            "AT+DUMPCTRL=1,0",
            "AT+DEBUGLVC=0,5",
            "AT+SWATD=0",
            "AT+ACTIVATE=0,0,0",
            "AT+SWATD=1",
            "AT+DEBUGLVC=0,5",
        ]
        adb_commands = [
            "shell settings put global setup_wizard_has_run 1",
            "shell settings put secure user_setup_complete 1",
            "shell content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1",
            "shell content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:i:1",
            "shell content insert --uri content://settings/secure --bind name:s:INSTALL_NON_MARKET_APPS --bind value:i:1",
            "shell am start -c android.intent.category.HOME -a android.intent.action.MAIN",
        ]

        self.show_messagebox(500, 200, "nPhoneKIT", strings["misuseFrpGuidance"])
        print(strings["attemptingEnableAdb"], end="")
        self.show_messagebox(500, 200, "nPhoneKIT", strings["frpUnlockStepsPre2022"])
        for command in at_commands:
            self.at.send(command)

        output = self.log_command_output("AT", "AT")
        if "error" in output.lower():
            print(strings["failText"])
            print(strings["frpNotCompatible"])
            self._report(model, action, "Fail")
            self.formrequest()
            return

        print(strings["okText"])
        print(strings["runUnlock"], end="")
        self.show_messagebox(500, 200, "nPhoneKIT", strings["usbDebuggingPromptCheck"])
        for command in adb_commands:
            self.adb.send(command)
        print(strings["okText"])
        print(strings["unlockSuccess"])
        self._report(model, action, "Success")
        self.formrequest()

    def _report(self, model, action, status):
        threading.Thread(
            target=self.success_checks,
            args=(self.hardware_uuid(), model, action, status),
        ).start()

    def unlock_2024(self):
        method = next(
            (item for item in self.load_methods("unlocks.json") if item.get("id") == "sam_2024"),
            None,
        )
        if not method or not self.confirm_method(
            method["title"], method["desc"], method["pros"], method["cons"], method["minutes"]
        ):
            return

        strings = self.strings
        print(strings["getVerInfo"], end="")
        info = self.verinfo(False)
        model = re.search(r"Model:\s*(\S+)", info)
        action = "FRP_Unlock_2024"
        if info == "Fail":
            print(strings["deviceCheckPluggedIn2"])
            self._report(model, action, "Fail")
            return

        commands = [
            "AT+SWATD=0", "AT+ACTIVATE=0,0,0", "AT+DEVCONINFO",
            "AT+VERSNAME=3,2,3", "AT+FRPUNLCK=3,0,0", "AT+SWATD=0",
            "AT+ACTIVATE=0,0,0", "AT+SWATD=1", "AT+SWATD=1",
            "AT+PRECONFG=2,VZW", "AT+PRECONFG=1,0",
        ]
        adb_commands = [
            "shell settings put global setup_wizard_has_run 1",
            "shell settings put secure user_setup_complete 1",
            "shell content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1",
            "shell content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:i:1",
            "shell content insert --uri content://settings/secure --bind name:s:INSTALL_NON_MARKET_APPS --bind value:i:1",
            "shell am start -c android.intent.category.HOME -a android.intent.action.MAIN",
        ]
        self.show_messagebox(500, 200, "nPhoneKIT", strings["misuseFrpGuidance2024"])
        print(strings["attemptingEnableAdb"], end="")
        self.show_messagebox(500, 200, "nPhoneKIT", strings["frpUnlockSteps2024"])
        for command in commands:
            self.at.send(command)

        if "error" in self.read_output("AT").lower():
            print(strings["failText"])
            print(strings["frpNotCompatible"])
            self._report(model, action, "Fail")
            self.formrequest()
            return

        print(strings["okText"])
        print(strings["runUnlock"], end="")
        self.show_messagebox(500, 200, "nPhoneKIT", strings["usbDebuggingPromptCheck"])
        adb_failed = self.adb.wait_for_device() != "device"
        if not adb_failed:
            for command in adb_commands:
                self.adb.send(command)
                output = self.log_command_output("ADB", f"ADB {command}")
                if any(marker in output.lower() for marker in ("error:", "no devices", "unauthorized")):
                    adb_failed = True
                    break
        if adb_failed:
            print(strings["failText"])
            print(strings["frpNotCompatible"])
            self._report(model, action, "Fail")
            self.formrequest()
            return

        print(strings["okText"])
        print(strings["unlockSuccess"])
        if model == "" or model is None:
            model = re.search(r"Model:\s*(\S+)", self.verinfo(False, False))
        self._report(model, action, "Success")
        self.formrequest()

    def unlock_android15_16(self):
        method = next(
            (item for item in self.load_methods("unlocks.json") if item.get("id") == "sam_15_16"),
            None,
        )
        if not method or not self.confirm_method(
            method["title"], method["desc"], method["pros"], method["cons"], method["minutes"]
        ):
            return

        strings = self.strings
        print(strings["getVerInfo"], end="")
        info = self.verinfo(False)
        model = re.search(r"Model:\s*(\S+)", info)
        action = "FRP_Unlock_15_16"
        if info == "Fail":
            print(strings["deviceCheckPluggedIn2"])
            self._report(model, action, "Fail")
            return

        commands = [
            "AT", "AT+KSTRINGB=0,3", "AT+DUMPCTRL=1,0", "AT+DEBUGLVL=0,4",
            "AT+SWATD=0", "AT+ACTIVATE=0,0,0", "AT+SWATD=1",
        ]
        adb_commands = [
            "shell content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:s:1",
            "shell pm uninstall -k --user 0 com.google.android.gsf",
            "shell am start -n com.android.settings/com.android.settings.Settings",
        ]
        self.show_messagebox(500, 200, "nPhoneKIT", strings["misuseFrpGuidance2024"])
        print(strings["attemptingEnableAdb"], end="")
        self.show_messagebox(500, 200, "nPhoneKIT", strings["frpUnlockSteps2024"])
        for command in commands:
            self.at.send(command)
        self.log_command_output("AT", "AT")

        try:
            print(strings["okText"])
            print(strings["runUnlock"], end="")
            self.show_messagebox(500, 200, "nPhoneKIT", strings["usbDebuggingPromptCheck"])
            if self.adb.wait_for_device() != "device":
                raise RuntimeError("No authorized ADB device")
            for command in adb_commands:
                self.adb.send(command)
                output = self.log_command_output("ADB", f"ADB {command}")
                if any(marker in output.lower() for marker in ("error:", "no devices", "unauthorized")):
                    raise RuntimeError(f"ADB command failed: {command}")
            print(strings["okText"])
            print(strings["unlockSuccess"])
            if model == "" or model is None:
                model = re.search(r"Model:\s*(\S+)", self.verinfo(False, False))
            self._report(model, action, "Success")
            self.formrequest()
        except Exception:
            print(strings["failText"])
            print(strings["frpNotCompatible"])
            self._report(model, action, "Fail")
            self.formrequest()
