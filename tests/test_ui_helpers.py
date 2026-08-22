from nphonekit_ui_helpers import find_logo, prompt_input


def test_find_logo_returns_first_existing_candidate():
    existing = {"./logo.png"}

    assert find_logo(exists=existing.__contains__) == "./logo.png"


def test_find_logo_returns_none_when_no_candidate_exists():
    assert find_logo(exists=lambda path: False) is None


def test_prompt_input_uses_qt_result():
    class App:
        def thread(self):
            return "same"

    class Thread:
        @staticmethod
        def currentThread():
            return "same"

    class Core:
        QThread = Thread

    class Input:
        @staticmethod
        def getText(*args, **kwargs):
            return "answer", True

    class Widgets:
        QInputDialog = Input

    assert prompt_input(qt_app=App(), qt_widgets=Widgets, qt_core=Core) == "answer"
