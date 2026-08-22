"""Device command clients used by the nPhoneKIT application."""

import glob
import getpass
import os
import platform
import shlex
import shutil
import subprocess
import time

import nphonekit_core
import serial
from serial.tools import list_ports


SERIAL_GROUPS = ("dialout", "uucp", "lock", "tty")


def is_root(os_config):
    """Return whether the current process has the required OS privileges."""
    if os_config == "WINDOWS":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    if os_config in ("LINUX", "MACOS"):
        return os.geteuid() == 0
    return False


def serial_permission_command(distro_name, user):
    """Return the group-membership command appropriate for a Linux distro."""
    if distro_name in ("ubuntu", "debian", "linuxmint", "zorin", "fedora", "rhel", "centos"):
        return f"sudo usermod -aG dialout {user}"
    if distro_name in ("arch", "endeavouros", "cachyos", "manjaro", "garuda"):
        return f"sudo usermod -aG uucp,lock {user}"
    return f"sudo usermod -aG dialout,uucp,lock {user}"


def check_serial_permissions(os_config, on_fix_required=None, user=None, user_groups=None, distro_name=None):
    """Check serial access and optionally report the corrective command."""
    if os_config not in ("LINUX", "MACOS"):
        return True
    user = user or getpass.getuser()
    if user_groups is None:
        try:
            import grp
            user_groups = [group.gr_name for group in grp.getgrall() if user in group.gr_mem]
        except Exception:
            user_groups = []
        try:
            user_groups.append(grp.getgrgid(os.getgid()).gr_name)
        except Exception:
            pass
    if nphonekit_core.has_required_group(user_groups, SERIAL_GROUPS):
        return True
    if os_config == "MACOS":
        return True
    if distro_name is None:
        try:
            import distro
            distro_name = distro.id()
        except Exception:
            distro_name = ""
    command = serial_permission_command(distro_name, user)
    if on_fix_required is not None:
        on_fix_required(command)
    return False


class ADB:
    """Small, time-bounded ADB client with an application-configured context."""

    _os_config = "LINUX"
    _strings = {}
    _rt_callback = staticmethod(lambda: None)

    @classmethod
    def configure(cls, os_config, strings, rt_callback):
        cls._os_config = os_config
        cls._strings = strings
        cls._rt_callback = staticmethod(rt_callback)

    @staticmethod
    def path():
        adb_path = shutil.which("adb")
        if adb_path is None:
            for candidate in ("/opt/homebrew/bin/adb", "/usr/local/bin/adb", "/usr/bin/adb"):
                if os.path.exists(candidate):
                    adb_path = candidate
                    break
        return adb_path

    @classmethod
    def _run(cls, adb_path, command, timeout=15):
        if cls._os_config == "LINUX":
            argv = ["sudo", adb_path] + shlex.split(command)
        else:
            argv = [adb_path] + shlex.split(command)
        return subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )

    @classmethod
    def devices(cls):
        adb_path = cls.path()
        if adb_path is None:
            return []
        try:
            result = cls._run(adb_path, "devices", timeout=10)
        except Exception:
            return []
        return nphonekit_core.parse_adb_devices(result.stdout)

    @classmethod
    def wait_for_device(cls, timeout=40):
        adb_path = cls.path()
        if adb_path is None:
            return "none"
        try:
            cls._run(adb_path, "start-server", timeout=15)
        except Exception:
            pass
        strings = cls._strings
        print(strings.get("adbWaiting", "Waiting for ADB device..."))
        deadline = time.time() + timeout
        last = "none"
        while time.time() < deadline:
            states = [state for _, state in cls.devices()]
            if "device" in states:
                print(strings.get("adbReady", "ADB device ready."))
                return "device"
            if "unauthorized" in states:
                if last != "unauthorized":
                    print(strings.get("adbUnauthorized", "ADB device is unauthorized."))
                last = "unauthorized"
            time.sleep(1)
        print(strings.get("adbTimedOut", "Timed out waiting for ADB device.") if last == "unauthorized" else strings.get("adbNoDevice", "No ADB device found."))
        return last

    @classmethod
    def send(cls, command):
        cls._rt_callback()
        adb_path = cls.path()
        if adb_path is None:
            print("ADB not found. Please install platform-tools and ensure adb is on PATH.")
            with open("tmp_output_adb.txt", "w", encoding="utf-8") as output_file:
                output_file.write("ADB not found")
            time.sleep(0.5)
            return
        try:
            result = cls._run(adb_path, command, timeout=30)
            output = result.stdout or ""
        except subprocess.TimeoutExpired:
            output = "error: adb command timed out"
        with open("tmp_output_adb.txt", "w", encoding="utf-8") as output_file:
            output_file.write(output)
        time.sleep(0.5)

    @staticmethod
    def usbswitch(arg, action):
        return True


class SerialManager:
    """Cross-platform serial manager for AT command communication."""

    def __init__(self, strings=None, debug_info=False, baud=115200):
        self.strings = strings or {}
        self.debug_info = debug_info
        self.baud = baud
        self.port = self.detect_port()
        self.ser = None
        if not self.port:
            if self.debug_info:
                print(self.strings.get("noDeviceSermanError", "No serial device found."))
        else:
            try:
                self.ser = serial.Serial(self.port, self.baud, timeout=2)
                time.sleep(0.5)
                if self.debug_info:
                    print(f"{self.strings.get('sermanConnectedPort', 'Connected: ')}{self.port}")
            except serial.SerialException as error:
                message = self.strings.get("sermanOpeningPortError", "Could not open serial port ")
                raise RuntimeError(f"{message}{self.port}: {error}") from error

    def reset(self):
        self.__init__(self.strings, self.debug_info, self.baud)

    def detect_port(self):
        system = platform.system()
        if system == "Windows":
            for index in range(1, 256):
                try:
                    connection = serial.Serial(f"COM{index}")
                    connection.close()
                    return f"COM{index}"
                except Exception:
                    pass
        elif system == "Darwin":
            ports = glob.glob("/dev/tty.usb*")
            chosen, note = nphonekit_core.select_serial_port(ports)
            if note:
                print(note)
            return chosen
        else:
            ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
            chosen, note = nphonekit_core.select_serial_port(ports)
            if note:
                print(note)
            return chosen
        return None

    def send(self, command):
        if not self.ser or not self.ser.is_open:
            print(self.strings.get("noDeviceGenericError", "No serial device connected."))
            return None
        self.ser.flushInput()
        self.ser.flushOutput()
        self.ser.write((command.strip() + "\r\n").encode())
        time.sleep(0.1)
        output = []
        while True:
            line = self.ser.readline()
            if not line:
                break
            output.append(line.decode(errors="ignore").strip())
        return "\n".join(output)

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()


class SerialManagerWindows:
    """Windows-specific serial manager with COM-port prioritization."""

    def __init__(self, strings=None, debug_info=False, port=None, baud=115200):
        self.strings = strings or {}
        self.debug = debug_info
        self.baud = baud
        self.ser = None
        if platform.system() != "Windows":
            raise RuntimeError(self.strings.get("sermanWindowsOsError", "Windows-only serial manager."))
        self.port = port or self.detect_port()
        if not self.port:
            if self.debug:
                print(self.strings.get("sermanNoComPort", "No COM port found."))
            return
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=2)
            time.sleep(0.5)
            if self.debug:
                print(f"{self.strings.get('sermanConnectedPort', 'Connected: ')}{self.port} @ {self.baud} baud")
        except (serial.SerialException, PermissionError) as error:
            if self.debug:
                message = self.strings.get("sermanOpeningPortError", "Could not open serial port ")
                print(f"{message}{self.port}: {error}")

    def reset(self):
        self.__init__(self.strings, self.debug, self.port, self.baud)

    def detect_port(self):
        ports = list_ports.comports()
        if self.debug:
            available = [port.device for port in ports]
            print(f"{self.strings.get('sermanWinAvailablePorts', 'Available ports: ')}{available}")
        sorted_ports = sorted(
            ports,
            key=lambda port: any(
                marker in port.description.upper() for marker in ("SAMSUNG", "MOBILE", "MODEM", "USB")
            ),
            reverse=True,
        )
        for port in sorted_ports:
            if port.device.upper().startswith("COM"):
                try:
                    test_connection = serial.Serial(port.device)
                    test_connection.close()
                    if self.debug:
                        print(f"{self.strings.get('sermanWinDev', 'Using port: ')}{port.device}")
                    return port.device
                except (serial.SerialException, PermissionError):
                    continue
        return None

    def send(self, command, wait=0.1):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError(self.strings.get("serPortNotOpen", "Serial port is not open."))
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write((command.strip() + "\r\n").encode())
        time.sleep(wait)
        lines = []
        while True:
            line = self.ser.readline()
            if not line:
                break
            lines.append(line.decode(errors="ignore").strip())
        return "\n".join(lines)

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            if self.debug:
                print(self.strings.get("sermanWinConClosed", "Serial connection closed."))


class AT:
    """AT command adapter around a configured serial manager."""

    _serial_manager = None
    _enable_preload = staticmethod(lambda: False)
    _preload_done = None
    _rt_callback = staticmethod(lambda: None)
    _strings = {}

    @classmethod
    def configure(cls, serial_manager, enable_preload, preload_done, rt_callback, strings):
        cls._serial_manager = serial_manager
        cls._enable_preload = staticmethod(enable_preload)
        cls._preload_done = preload_done
        cls._rt_callback = staticmethod(rt_callback)
        cls._strings = strings

    @classmethod
    def send(cls, command, not_first=False):
        cls._rt_callback()
        if cls._enable_preload():
            cls._preload_done.wait()
        if not_first:
            cls._serial_manager.reset()
        with open("tmp_output.txt", "w", encoding="utf-8") as output_file:
            try:
                result = cls._serial_manager.send(command)
                if result is None:
                    result = cls._serial_manager.send(command)
                    if result is None:
                        result = ""
                output_file.write(result)
            except Exception:
                cls._serial_manager.reset()
                time.sleep(1)
                try:
                    result = cls._serial_manager.send(command)
                    if result is None:
                        result = cls._serial_manager.send(command)
                        if result is None:
                            result = ""
                    output_file.write(result)
                except Exception:
                    print(cls._strings.get("deviceConCheckNotPlugged", "Device is not connected."))
        return True

    @staticmethod
    def usbswitch(arg, action):
        return True


class SamsungPreloader:
    """Detect a Samsung USB device and run the modem preload sequence."""

    def __init__(self, serial_manager, strings, debug_info, enabled, set_enabled, set_error, done, select_brand, probe_usb=None):
        self.serial_manager = serial_manager
        self.strings = strings
        self.debug_info = debug_info
        self.enabled = enabled
        self.set_enabled = set_enabled
        self.set_error = set_error
        self.done = done
        self.select_brand = select_brand
        self.probe_usb = probe_usb or self._probe_usb

    @staticmethod
    def _probe_usb(system):
        if system == "Linux":
            return subprocess.check_output(["lsusb"]).decode().lower()
        if system == "Darwin":
            return subprocess.check_output(["system_profiler", "SPUSBDataType"]).decode().lower()
        if system == "Windows":
            return subprocess.check_output(["powershell", "Get-PnpDevice"]).decode().lower()
        return ""

    async def run(self):
        if not self.enabled():
            self.done.set()
            return
        try:
            output = self.probe_usb(platform.system())
            if "samsung" in output.lower():
                if self.debug_info:
                    print(self.strings.get("samPreloadUsbDetected", "Samsung USB device detected."))
                self.select_brand("Samsung")
                self.serial_manager.send("AT+SWATD=0")
                self.serial_manager.send("AT+ACTIVATE=0,0,0")
                if self.debug_info:
                    print(self.strings.get("samPreloadComplete", "Samsung modem preload complete."))
                self.set_error(False)
            else:
                if self.debug_info:
                    print(self.strings.get("samNoUsbFound", "No Samsung USB device found."))
                self.set_enabled(False)
                self.set_error(True)
        except Exception as error:
            if self.debug_info:
                print(self.strings.get("samPreloadError", "Samsung preload failed."), error)
            self.set_enabled(False)
            self.set_error(True)
        finally:
            self.done.set()


class SamsungModemUnlocker:
    """Apply the Samsung modem-unlock sequence for an individual action."""

    def __init__(self, at_client, os_config, enable_preload, preload_error):
        self.at_client = at_client
        self.os_config = os_config
        self.enable_preload = enable_preload
        self.preload_error = preload_error
        self.first_unlock = False

    def unlock(self, manufacturer, soft_unlock=False):
        if manufacturer != "SAMSUNG":
            return
        if self.os_config == "LINUX":
            if self.enable_preload():
                return
            if self.preload_error() and not self.first_unlock:
                self.at_client.send("AT+SWATD=0", True)
                self.at_client.send("AT+ACTIVATE=0,0,0", True)
                self.first_unlock = True
                return
        elif self.os_config not in ("WINDOWS", "MACOS"):
            return
        self.at_client.send("AT+SWATD=0")
        if not soft_unlock:
            self.at_client.send("AT+ACTIVATE=0,0,0")


class FastbootPartitionEraser:
    """Run explicitly targeted Fastboot erase operations."""

    def __init__(self, fastboot_path="fastboot"):
        if not shutil.which(fastboot_path):
            raise FileNotFoundError(f"Fastboot binary '{fastboot_path}' not found in PATH.")
        self.fastboot = fastboot_path

    def _run(self, args):
        command = [self.fastboot] + args
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Command {' '.join(command)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    @staticmethod
    def _target_args(device_id):
        return ["-s", device_id] if device_id else []

    def erase_config(self, device_id=None):
        return self._run(self._target_args(device_id) + ["erase", "config"])

    def erase_persist(self, device_id=None):
        return self._run(self._target_args(device_id) + ["erase", "persist"])

    def erase_frp(self, device_id=None):
        return self._run(self._target_args(device_id) + ["erase", "frp"])

    def wipe_data_cache(self, device_id=None):
        return self._run(self._target_args(device_id) + ["-w"])

    def list_devices(self):
        try:
            output = subprocess.run(
                [self.fastboot, "devices"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout
        except Exception:
            return []
        return nphonekit_core.parse_fastboot_devices(output)
