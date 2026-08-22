"""Shared support helpers for device action workflows."""

import json
from pathlib import Path


def load_unlock_methods(path="unlocks.json"):
    """Load the user-facing unlock method definitions."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_unlock_method(methods, method_id):
    """Return the configured unlock method with ``method_id``, if present."""
    return next((method for method in methods if method.get("id") == method_id), None)


def unlock_modem(unlocker, manufacturer, soft_unlock=False):
    """Unlock a modem when the runtime preloader provided a client."""
    if unlocker is not None:
        unlocker.unlock(manufacturer, soft_unlock)


def maybe_show_contribution(enabled, prompt, x=500, y=500):
    """Show the contribution prompt only when enabled by settings."""
    if enabled is True:
        prompt(x, y)
