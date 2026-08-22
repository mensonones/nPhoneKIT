from nphonekit_runtime import RuntimeState, initialize_runtime


class FakeThread:
    instances = []

    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon
        self.started = False
        self.instances.append(self)

    def start(self):
        self.started = True


class FakeAdb:
    def __init__(self):
        self.configured = None

    def configure(self, *args):
        self.configured = args


class FakeAt:
    def __init__(self):
        self.configured = None

    def configure(self, *args):
        self.configured = args


class FakeSerial:
    instances = []

    def __init__(self, strings, debug_info):
        self.args = (strings, debug_info)
        self.instances.append(self)


class FakeModem:
    def __init__(self, *args):
        self.args = args


class FakePreloader:
    def __init__(self, *args):
        self.args = args

    async def run(self):
        return None


def test_initialize_runtime_configures_clients_and_starts_preloader():
    FakeThread.instances = []
    adb = FakeAdb()
    at = FakeAt()
    state = initialize_runtime(
        os_config="LINUX",
        strings={"x": "y"},
        debug_info=True,
        adb=adb,
        at=at,
        rt="rt",
        serial_manager=FakeSerial,
        serial_manager_windows=FakeSerial,
        modem_unlocker=FakeModem,
        preloader_factory=FakePreloader,
        enable_preload=lambda: True,
        preload_error=lambda: None,
        preload_done="done",
        disable_preload=lambda: None,
        set_preload_error=lambda value: None,
        set_brand=lambda name: None,
        thread_factory=FakeThread,
    )

    assert isinstance(state, RuntimeState)
    assert adb.configured == ("LINUX", {"x": "y"}, "rt")
    assert at.configured[0] is state.serman
    assert isinstance(state.samsung_modem_unlocker, FakeModem)
    assert isinstance(state.preloader, FakePreloader)
    assert FakeThread.instances[0].daemon is True
    assert FakeThread.instances[0].started is True


def test_initialize_runtime_uses_windows_serial_manager():
    class WindowsSerial(FakeSerial):
        pass

    created = []

    def serial_manager(*args):
        created.append("unix")
        return FakeSerial(*args)

    def windows_manager(*args):
        created.append("windows")
        return WindowsSerial(*args)

    initialize_runtime(
        os_config="WINDOWS",
        strings={},
        debug_info=False,
        adb=FakeAdb(),
        at=FakeAt(),
        rt=None,
        serial_manager=serial_manager,
        serial_manager_windows=windows_manager,
        modem_unlocker=FakeModem,
        preloader_factory=FakePreloader,
        enable_preload=lambda: False,
        preload_error=lambda: None,
        preload_done=None,
        disable_preload=lambda: None,
        set_preload_error=lambda value: None,
        set_brand=lambda name: None,
        thread_factory=FakeThread,
    )

    assert created == ["windows", "unix"]
