import json

from nphonekit_settings import SettingsStore


def test_load_effective_uses_defaults_when_file_is_missing(tmp_path):
    store = SettingsStore(tmp_path / "settings.json", {"dark_theme": True})

    assert store.load_effective() == {"dark_theme": True}


def test_load_effective_merges_saved_values(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"dark_theme": False}))
    store = SettingsStore(path, {"dark_theme": True, "debug_info": False})

    assert store.load_effective() == {"dark_theme": False, "debug_info": False}


def test_load_effective_falls_back_and_reports_corrupt_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not-json")
    messages = []
    store = SettingsStore(path, {"dark_theme": True}, output=messages.append)

    assert store.load_effective() == {"dark_theme": True}
    assert "Could not read settings" in messages[0]


def test_persist_reports_write_failure(tmp_path, monkeypatch):
    messages = []
    store = SettingsStore(tmp_path / "settings.json", output=messages.append)
    monkeypatch.setattr(store, "save", lambda settings: (_ for _ in ()).throw(OSError("read-only")))

    store.persist({"dark_theme": True})

    assert "Could not write settings" in messages[0]
