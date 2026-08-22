"""Reusable presentation helpers for the Qt interface."""

import os


def find_logo(exists=os.path.exists):
    """Return the first available application logo path."""
    for path in ("assets/logo.png", "logo.png", "./assets/logo.png", "./logo.png"):
        if exists(path):
            return path
    return None
