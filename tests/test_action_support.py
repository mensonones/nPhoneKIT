import json

from nphonekit_action_support import (
    find_unlock_method,
    load_unlock_methods,
    maybe_show_contribution,
    unlock_modem,
)


def test_load_unlock_methods_reads_json(tmp_path):
    path = tmp_path / "unlocks.json"
    path.write_text(json.dumps([{"id": "sam_2024"}]))

    assert load_unlock_methods(path) == [{"id": "sam_2024"}]


def test_find_unlock_method_returns_match_or_none():
    methods = [{"id": "old"}, {"id": "new", "title": "New"}]

    assert find_unlock_method(methods, "new")["title"] == "New"
    assert find_unlock_method(methods, "missing") is None


def test_unlock_modem_is_noop_without_runtime_unlocker():
    unlock_modem(None, "SAMSUNG")


def test_unlock_modem_forwards_arguments():
    calls = []

    class Unlocker:
        def unlock(self, *args):
            calls.append(args)

    unlock_modem(Unlocker(), "SAMSUNG", True)

    assert calls == [("SAMSUNG", True)]


def test_maybe_show_contribution_respects_setting():
    calls = []
    prompt = lambda x, y: calls.append((x, y))

    maybe_show_contribution(False, prompt)
    maybe_show_contribution(True, prompt)

    assert calls == [(500, 500)]
