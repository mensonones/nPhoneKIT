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
