"""Application settings loading and persistence."""

import json
from pathlib import Path

import nphonekit_core


DEFAULT_SETTINGS = {
    "dark_theme": True,
    "hacker_font": False,
    "slower_animations": False,
    "update_check": False,
    "enable_preload": True,
    "debug_info": False,
    "basic_success_checks": True,
    "contributionsuggestions": True,
}


class SettingsStore:
    """Own the settings file boundary and default merging policy."""

    def __init__(self, path, defaults=None, output=print):
        self.path = Path(path)
        self.defaults = dict(defaults or DEFAULT_SETTINGS)
        self.output = output

    def load_saved(self):
        """Load the raw user settings, preserving existing error semantics."""
        return nphonekit_core.load_settings(self.path)

    def load_effective(self):
        """Load user settings merged over the current application defaults."""
        if not self.path.exists():
            return dict(self.defaults)
        try:
            loaded = self.load_saved()
        except (json.JSONDecodeError, ValueError, OSError) as error:
            self.output(
                f"[nPhoneKIT] Could not read settings ({error}); falling back to defaults."
            )
            loaded = {}
        return nphonekit_core.merge_settings(self.defaults, loaded)

    def save(self, settings):
        nphonekit_core.save_settings(self.path, settings)

    def persist(self, settings):
        """Persist settings during application startup without crashing the app."""
        try:
            self.save(settings)
        except OSError as error:
            self.output(f"[nPhoneKIT] Could not write settings: {error}")
