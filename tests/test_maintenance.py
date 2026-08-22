from nphonekit_maintenance import get_os_info


def test_get_os_info_contains_common_runtime_fields():
    info = get_os_info()

    assert info["system"]
    assert info["python_version"]
    assert "machine" in info


def test_get_os_info_linux_includes_diagnostics(monkeypatch):
    monkeypatch.setattr("nphonekit_maintenance.platform.system", lambda: "Linux")
    monkeypatch.setattr(
        "nphonekit_maintenance.platform.freedesktop_os_release",
        lambda: {"NAME": "Test Linux", "ID": "test"},
    )
    monkeypatch.setattr("nphonekit_maintenance.platform.libc_ver", lambda: ("glibc", "2"))

    info = get_os_info()

    assert info["distro_name"] == "Test Linux"
    assert info["distro_id"] == "test"
    assert info["libc"] == ("glibc", "2")
    assert "kernel_build_string" in info


def test_get_os_info_windows_handles_optional_metadata(monkeypatch):
    monkeypatch.setattr("nphonekit_maintenance.platform.system", lambda: "Windows")
    monkeypatch.setattr("nphonekit_maintenance.platform.win32_ver", lambda: ("11", "10", "", ""))
    monkeypatch.setattr("nphonekit_maintenance.platform.win32_edition", lambda: "Professional")
    monkeypatch.setattr("nphonekit_maintenance.platform.win32_is_iot", lambda: False)

    info = get_os_info()

    assert info["windows_release"] == "11"
    assert info["windows_edition"] == "Professional"
    assert info["windows_is_iot"] is False
