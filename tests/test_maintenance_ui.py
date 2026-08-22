from nphonekit_maintenance_ui import get_output_text, show_serial_permission_fix


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.packed = False
        self.inserted = None

    def pack(self, **kwargs):
        self.packed = kwargs

    def insert(self, *args):
        self.inserted = args

    def config(self, **kwargs):
        self.configured = kwargs


class FakeRoot(FakeWidget):
    def title(self, value):
        self.window_title = value

    def geometry(self, value):
        self.window_geometry = value

    def destroy(self):
        self.destroyed = True

    def mainloop(self):
        self.looped = True


class FakeTk:
    Tk = FakeRoot
    Label = FakeWidget
    Text = FakeWidget
    Button = FakeWidget


def test_serial_permission_dialog_displays_command():
    show_serial_permission_fix("sudo usermod -aG dialout $USER", tk_module=FakeTk)


def test_get_output_text_handles_missing_window():
    assert get_output_text(None) == ""


def test_get_output_text_reads_window_output():
    class Output:
        def toPlainText(self):
            return "last error"

    class Window:
        output = Output()

    assert get_output_text(Window()) == "last error"
