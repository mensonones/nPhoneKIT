"""Regression tests for main.py's import-safe entrypoint."""

import ast
from pathlib import Path


MAIN_PATH = Path(__file__).parents[1] / "main.py"
RUNTIME_CALLS = {
    "check_for_update",
    "check_serial_permissions",
    "Thread",
    "initialize_runtime",
}


def _called_names(node):
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            function = child.func
            if isinstance(function, ast.Name):
                names.add(function.id)
            elif isinstance(function, ast.Attribute):
                names.add(function.attr)
    return names


def test_runtime_setup_is_not_executed_at_import_time():
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    module_calls = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_calls.update(_called_names(node))

    assert not RUNTIME_CALLS & module_calls


def test_run_app_owns_runtime_setup_and_main_guard():
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    run_app = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_app")

    assert RUNTIME_CALLS <= _called_names(run_app)
    assert any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Call)
        and isinstance(node.body[0].value.func, ast.Name)
        and node.body[0].value.func.id == "run_app"
        for node in tree.body
    )
