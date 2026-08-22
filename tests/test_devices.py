"""Unit tests for device clients without requiring connected hardware."""

import asyncio
from types import SimpleNamespace
import threading

import pytest

pytest.importorskip("serial")

import nphonekit_devices as devices


def test_adb_run_builds_linux_sudo_command(monkeypatch):
    captured = {}
    devices.ADB.configure("LINUX", {}, lambda: None)

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(devices.subprocess, "run", fake_run)

    devices.ADB._run("/usr/bin/adb", "shell getprop ro.product.model", timeout=7)

    assert captured["argv"] == ["sudo", "/usr/bin/adb", "shell", "getprop", "ro.product.model"]
    assert captured["kwargs"]["timeout"] == 7


def test_command_output_helpers_round_trip_and_clear(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tmp_output.txt").write_text("AT response", encoding="utf-8")
    (tmp_path / "tmp_output_adb.txt").write_text("ADB response", encoding="utf-8")

    assert devices.readOutput("AT") == "AT response"
    assert devices.readOutput("ADB") == "ADB response"
    assert devices.readOutput("unknown") == ""

    devices.rt()

    assert not (tmp_path / "tmp_output.txt").exists()
    assert not (tmp_path / "tmp_output_adb.txt").exists()


def test_log_command_output_returns_buffer_content(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tmp_output.txt").write_text("AT response", encoding="utf-8")

    assert devices.log_command_output("AT", "AT") == "AT response"
    assert "AT response" in capsys.readouterr().out


def test_adb_devices_uses_core_parser(monkeypatch):
    devices.ADB.configure("LINUX", {}, lambda: None)
    monkeypatch.setattr(devices.ADB, "path", staticmethod(lambda: "/usr/bin/adb"))
    monkeypatch.setattr(
        devices.ADB,
        "_run",
        classmethod(lambda cls, path, command, timeout=15: SimpleNamespace(
            stdout="List of devices attached\nABC\tdevice\nXYZ\tunauthorized\n"
        )),
    )

    assert devices.ADB.devices() == [("ABC", "device"), ("XYZ", "unauthorized")]


def test_adb_devices_hides_command_errors(monkeypatch):
    devices.ADB.configure("LINUX", {}, lambda: None)
    monkeypatch.setattr(devices.ADB, "path", staticmethod(lambda: "/usr/bin/adb"))

    def fail(*args, **kwargs):
        raise TimeoutError("adb wedged")

    monkeypatch.setattr(devices.ADB, "_run", classmethod(lambda cls, *args, **kwargs: fail()))

    assert devices.ADB.devices() == []


def test_serial_manager_detects_linux_port(monkeypatch):
    manager = devices.SerialManager.__new__(devices.SerialManager)
    monkeypatch.setattr(devices.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        devices.glob,
        "glob",
        lambda pattern: ["/dev/ttyACM0"] if pattern == "/dev/ttyACM*" else [],
    )

    assert manager.detect_port() == "/dev/ttyACM0"


def test_serial_manager_send_reads_fake_serial():
    class FakeSerial:
        is_open = True

        def __init__(self):
            self.written = []
            self.responses = [b"OK\r\n", b""]

        def flushInput(self):
            pass

        def flushOutput(self):
            pass

        def write(self, value):
            self.written.append(value)

        def readline(self):
            return self.responses.pop(0)

    manager = devices.SerialManager.__new__(devices.SerialManager)
    manager.ser = FakeSerial()
    manager.strings = {}

    assert manager.send("AT+TEST") == "OK"
    assert manager.ser.written == [b"AT+TEST\r\n"]


def test_at_sends_through_configured_manager(monkeypatch, tmp_path):
    class FakeManager:
        def __init__(self):
            self.commands = []

        def send(self, command):
            self.commands.append(command)
            return "OK"

    manager = FakeManager()
    devices.AT.configure(manager, lambda: False, threading.Event(), lambda: None, {})
    monkeypatch.chdir(tmp_path)

    assert devices.AT.send("AT+TEST") is True
    assert manager.commands == ["AT+TEST"]
    assert (tmp_path / "tmp_output.txt").read_text(encoding="utf-8") == "OK"


def test_serial_permission_check_accepts_required_group():
    assert devices.check_serial_permissions("LINUX", user="alice", user_groups=["dialout"])


def test_serial_permission_check_reports_distro_command():
    commands = []

    result = devices.check_serial_permissions(
        "LINUX",
        on_fix_required=commands.append,
        user="alice",
        user_groups=[],
        distro_name="arch",
    )

    assert result is False
    assert commands == ["sudo usermod -aG uucp,lock alice"]


def test_serial_permission_check_skips_macos_group_prompt():
    assert devices.check_serial_permissions("MACOS", user="alice", user_groups=[])


def test_samsung_preloader_runs_commands_when_usb_is_present():
    class FakeSerial:
        def __init__(self):
            self.commands = []

        def send(self, command):
            self.commands.append(command)

    serial_manager = FakeSerial()
    done = threading.Event()
    state = {"enabled": True, "error": None, "brand": None}
    preloader = devices.SamsungPreloader(
        serial_manager,
        {},
        False,
        lambda: state["enabled"],
        lambda value: state.update(enabled=value),
        lambda value: state.update(error=value),
        done,
        lambda value: state.update(brand=value),
        probe_usb=lambda system: "Samsung USB device",
    )

    asyncio.run(preloader.run())

    assert serial_manager.commands == ["AT+SWATD=0", "AT+ACTIVATE=0,0,0"]
    assert state == {"enabled": True, "error": False, "brand": "Samsung"}
    assert done.is_set()


def test_samsung_preloader_disables_when_usb_is_absent():
    done = threading.Event()
    state = {"enabled": True, "error": None}
    preloader = devices.SamsungPreloader(
        SimpleNamespace(send=lambda command: None),
        {},
        False,
        lambda: state["enabled"],
        lambda value: state.update(enabled=value),
        lambda value: state.update(error=value),
        done,
        lambda value: None,
        probe_usb=lambda system: "generic usb device",
    )

    asyncio.run(preloader.run())

    assert state == {"enabled": False, "error": True}
    assert done.is_set()


def test_samsung_modem_unlocker_uses_soft_unlock_sequence():
    class FakeAT:
        def __init__(self):
            self.commands = []

        def send(self, command, *args):
            self.commands.append((command, args))

    at = FakeAT()
    unlocker = devices.SamsungModemUnlocker(at, "MACOS", lambda: False, lambda: False)

    unlocker.unlock("SAMSUNG", soft_unlock=True)

    assert at.commands == [("AT+SWATD=0", ())]


def test_samsung_modem_unlocker_retries_failed_linux_preload_once():
    class FakeAT:
        def __init__(self):
            self.commands = []

        def send(self, command, *args):
            self.commands.append((command, args))

    at = FakeAT()
    unlocker = devices.SamsungModemUnlocker(at, "LINUX", lambda: False, lambda: True)

    unlocker.unlock("SAMSUNG")
    unlocker.unlock("SAMSUNG")

    assert at.commands == [
        ("AT+SWATD=0", (True,)),
        ("AT+ACTIVATE=0,0,0", (True,)),
        ("AT+SWATD=0", ()),
        ("AT+ACTIVATE=0,0,0", ()),
    ]


def test_fastboot_eraser_targets_each_destructive_command(monkeypatch):
    monkeypatch.setattr(devices.shutil, "which", lambda path: "/usr/bin/fastboot")
    eraser = devices.FastbootPartitionEraser()
    commands = []
    monkeypatch.setattr(eraser, "_run", lambda args: commands.append(args) or "")

    eraser.erase_config("ABC")
    eraser.erase_persist("ABC")
    eraser.erase_frp("ABC")
    eraser.wipe_data_cache("ABC")

    assert commands == [
        ["-s", "ABC", "erase", "config"],
        ["-s", "ABC", "erase", "persist"],
        ["-s", "ABC", "erase", "frp"],
        ["-s", "ABC", "-w"],
    ]


def test_fastboot_eraser_lists_devices_with_core_parser(monkeypatch):
    monkeypatch.setattr(devices.shutil, "which", lambda path: "/usr/bin/fastboot")
    eraser = devices.FastbootPartitionEraser()
    monkeypatch.setattr(
        devices.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="ABC\tfastboot\n"),
    )

    assert eraser.list_devices() == ["ABC"]
