"""Device command clients used by the nPhoneKIT application."""

import os
import shlex
import shutil
import subprocess
import time

import nphonekit_core


class ADB:
    """Small, time-bounded ADB client with an application-configured context."""

    _os_config = "LINUX"
    _strings = {}
    _rt_callback = staticmethod(lambda: None)

    @classmethod
    def configure(cls, os_config, strings, rt_callback):
        cls._os_config = os_config
        cls._strings = strings
        cls._rt_callback = staticmethod(rt_callback)

    @staticmethod
    def path():
        adb_path = shutil.which("adb")
        if adb_path is None:
            for candidate in ("/opt/homebrew/bin/adb", "/usr/local/bin/adb", "/usr/bin/adb"):
                if os.path.exists(candidate):
                    adb_path = candidate
                    break
        return adb_path

    @classmethod
    def _run(cls, adb_path, command, timeout=15):
        if cls._os_config == "LINUX":
            argv = ["sudo", adb_path] + shlex.split(command)
        else:
            argv = [adb_path] + shlex.split(command)
        return subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )

    @classmethod
    def devices(cls):
        adb_path = cls.path()
        if adb_path is None:
            return []
        try:
            result = cls._run(adb_path, "devices", timeout=10)
        except Exception:
            return []
        return nphonekit_core.parse_adb_devices(result.stdout)

    @classmethod
    def wait_for_device(cls, timeout=40):
        adb_path = cls.path()
        if adb_path is None:
            return "none"
        try:
            cls._run(adb_path, "start-server", timeout=15)
        except Exception:
            pass
        strings = cls._strings
        print(strings.get("adbWaiting", "Waiting for ADB device..."))
        deadline = time.time() + timeout
        last = "none"
        while time.time() < deadline:
            states = [state for _, state in cls.devices()]
            if "device" in states:
                print(strings.get("adbReady", "ADB device ready."))
                return "device"
            if "unauthorized" in states:
                if last != "unauthorized":
                    print(strings.get("adbUnauthorized", "ADB device is unauthorized."))
                last = "unauthorized"
            time.sleep(1)
        print(strings.get("adbTimedOut", "Timed out waiting for ADB device.") if last == "unauthorized" else strings.get("adbNoDevice", "No ADB device found."))
        return last

    @classmethod
    def send(cls, command):
        cls._rt_callback()
        adb_path = cls.path()
        if adb_path is None:
            print("ADB not found. Please install platform-tools and ensure adb is on PATH.")
            with open("tmp_output_adb.txt", "w", encoding="utf-8") as output_file:
                output_file.write("ADB not found")
            time.sleep(0.5)
            return
        try:
            result = cls._run(adb_path, command, timeout=30)
            output = result.stdout or ""
        except subprocess.TimeoutExpired:
            output = "error: adb command timed out"
        with open("tmp_output_adb.txt", "w", encoding="utf-8") as output_file:
            output_file.write(output)
        time.sleep(0.5)

    @staticmethod
    def usbswitch(arg, action):
        return True
