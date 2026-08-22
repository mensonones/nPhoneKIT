"""Unit tests for device clients without requiring connected hardware."""

from types import SimpleNamespace

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
