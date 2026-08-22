"""Smoke test that importing the application has no runtime bootstrap effects."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytest.importorskip("PyQt5")
pytest.importorskip("serial")

PROJECT_ROOT = Path(__file__).parents[1]


def test_main_imports_without_starting_runtime(tmp_path):
    # main.py loads strings.xml and persists settings relative to the cwd.
    # Use a temporary cwd so the smoke test cannot modify the checkout.
    shutil.copy2(PROJECT_ROOT / "strings.xml", tmp_path / "strings.xml")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert not (tmp_path / "settings.json").exists()


def test_qt_dialog_helper_defined_at_module_scope(tmp_path):
    # Regression: `qt_dialog_helper` must exist at module scope. The dialog
    # helpers and init_qt_dialog_helper() read it via `if qt_dialog_helper is
    # None`, which raises NameError at GUI-startup if the global was never
    # defined (the app then crashes in main() before any window shows).
    shutil.copy2(PROJECT_ROOT / "strings.xml", tmp_path / "strings.xml")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import main; assert hasattr(main, 'qt_dialog_helper')",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
