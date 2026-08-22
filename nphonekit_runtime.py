"""Runtime bootstrap for hardware-facing nPhoneKIT services."""

import asyncio
import threading
from dataclasses import dataclass


@dataclass
class RuntimeState:
    """Live hardware clients created during application startup."""

    serman: object
    serman1: object
    preloader: object
    samsung_modem_unlocker: object


def initialize_runtime(
    *,
    os_config,
    strings,
    debug_info,
    adb,
    at,
    rt,
    serial_manager,
    serial_manager_windows,
    modem_unlocker,
    preloader_factory,
    enable_preload,
    preload_error,
    preload_done,
    disable_preload,
    set_preload_error,
    set_brand,
    thread_factory=threading.Thread,
):
    """Configure device transports and start the modem preloader."""
    adb.configure(os_config, strings, rt)

    manager_class = (
        serial_manager_windows if os_config == "WINDOWS" else serial_manager
    )
    serman = manager_class(strings, debug_info)
    serman1 = serial_manager(strings, debug_info)
    at.configure(serman, enable_preload, preload_done, rt, strings)
    samsung_modem_unlocker = modem_unlocker(
        at, os_config, enable_preload, preload_error
    )
    preloader = preloader_factory(
        serman1,
        strings,
        debug_info,
        enable_preload,
        disable_preload,
        set_preload_error,
        preload_done,
        set_brand,
    )

    thread_factory(
        target=lambda: asyncio.run(preloader.run()),
        daemon=True,
    ).start()

    return RuntimeState(
        serman=serman,
        serman1=serman1,
        preloader=preloader,
        samsung_modem_unlocker=samsung_modem_unlocker,
    )
