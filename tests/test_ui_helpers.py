from nphonekit_ui_helpers import find_logo


def test_find_logo_returns_first_existing_candidate():
    existing = {"./logo.png"}

    assert find_logo(exists=existing.__contains__) == "./logo.png"


def test_find_logo_returns_none_when_no_candidate_exists():
    assert find_logo(exists=lambda path: False) is None
