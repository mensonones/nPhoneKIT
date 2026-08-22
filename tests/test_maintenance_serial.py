from nphonekit_maintenance import (
    ERR_IMPORT_SHADOWED,
    ERR_PIP_FAILED,
    ERR_PYSERIAL_NOT_INSTALLED,
    ERR_WRONG_SERIAL_PACKAGE,
    self_fix_serial,
)


def _run(**kwargs):
    output = []
    code = self_fix_serial(output=output.append, **kwargs)
    return code, output


def test_self_fix_refuses_to_change_environment_without_consent():
    calls = []
    code, output = _run(
        find_spec=lambda name: None,
        input_func=lambda prompt: "n",
        check_call=calls.append,
        python_executable="python-test",
    )

    assert code == ERR_PYSERIAL_NOT_INSTALLED
    assert calls == []
    assert any("Skipped" in line for line in output)


def test_self_fix_detects_wrong_serial_package():
    specs = {"serial": object(), "pyserial": None}
    code, output = _run(
        find_spec=specs.get,
        input_func=lambda prompt: "n",
        python_executable="python-test",
    )

    assert code == ERR_WRONG_SERIAL_PACKAGE
    assert any("wrong 'serial' package" in line for line in output)


def test_self_fix_reports_pip_failure():
    def fail(command):
        raise RuntimeError("pip unavailable")

    code, output = _run(
        find_spec=lambda name: None,
        input_func=lambda prompt: "y",
        check_call=fail,
    )

    assert code == ERR_PIP_FAILED
    assert any("pip unavailable" in line for line in output)


def test_self_fix_reports_shadowing_path(tmp_path):
    (tmp_path / "serial.py").touch()
    code, output = _run(cwd=str(tmp_path))

    assert code == ERR_IMPORT_SHADOWED
    assert any("shadowing path" in line for line in output)
