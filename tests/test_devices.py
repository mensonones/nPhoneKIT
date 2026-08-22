"""Unit tests for device clients without requiring connected hardware."""

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
