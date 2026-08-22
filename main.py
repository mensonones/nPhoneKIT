#
#             ███████████  █████                                   █████   ████ █████ ███████████
#            ░░███░░░░░███░░███                                   ░░███   ███░ ░░███ ░█░░░███░░░█
#  ████████   ░███    ░███ ░███████    ██████  ████████    ██████  ░███  ███    ░███ ░   ░███  ░
# ░░███░░███  ░██████████  ░███░░███  ███░░███░░███░░███  ███░░███ ░███████     ░███     ░███
#  ░███ ░███  ░███░░░░░░   ░███ ░███ ░███ ░███ ░███ ░███ ░███████  ░███░░███    ░███     ░███
#  ░███ ░███  ░███         ░███ ░███ ░███ ░███ ░███ ░███ ░███░░░   ░███ ░░███   ░███     ░███
#  ████ █████ █████        ████ █████░░██████  ████ █████░░██████  █████ ░░████ █████    █████
# ░░░░ ░░░░░ ░░░░░        ░░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░░   ░░░░ ░░░░░    ░░░░░
#

# IMPORTS AND WHY EACH ONE IS NEEDED

import time # Waiting before executing something
import math
import multiprocessing
import os # Executing most commands
import tkinter as tk # Main GUI (deprecated, slowly being removed)
from tkinter import ttk # Styling for GUI (deprecated)
from tkinter import messagebox # Opening message/warning boxes
from tkinter import font # Customizing GUI font
from pathlib import Path # Importing settings
import sys # Getting basic system info
import re # Finding strings within text
import platform # Checking the current OS
import threading # Using multiple threads
import json # Parsing and creating JSON
import webbrowser # Opening browser to any page
import xml.etree.ElementTree as ET # Importing strings.xml
from PyQt5 import QtCore, QtGui, QtWidgets # GUI
from PyQt5.QtGui import QFont
from nphonekit_ui import (
    InstantTooltips,
    MainWindow as UiMainWindow,
    MainWindowServices,
    QtDialogHelper,
)
from datetime import datetime, timedelta
import nphonekit_core # Pure, unit-tested core logic (parsing, settings merge, device guards)
from nphonekit_services import (
    FeedbackClient,
    TelemetryClient,
    UpdateClient,
    public_hardware_uuid,
)
from nphonekit_maintenance import get_os_info, self_fix_serial
from nphonekit_runtime import initialize_runtime
from nphonekit_settings import DEFAULT_SETTINGS, SettingsStore
from typing import Tuple

## nPhoneKIT permissions (these are the things that nPhoneKIT is capable of doing):

# Communicate with USB devices using ADB, MTP, and AT commands.
# Communicate with external servers to verify whether an action worked or not.
# Open a new tab in the default browser
# Checking and getting basic information about the current system

# ===========================================================================================================
# CONFIGURATION VARIABLES
# ===========================================================================================================

VERSION = "1.6.8"
DEBUGMODE = False

# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE (included in the nPhoneKIT source) for more details.

# ===========================================================================================================

# Requirements:
#
# Ubuntu >=20.0.4-LTS
# Windows support exists but is not well-supported yet.
# At least 1 USB A or USB C port
# Python
# Everything in requirements.txt
#

# ============================================================================= #
# You shouldn't edit anything below this line unless you know what you're doing #
# ============================================================================= #

SETTINGS_PATH = Path("settings.json") # Load settings externally
settings_store = SettingsStore(SETTINGS_PATH, DEFAULT_SETTINGS)
settings = settings_store.load_effective()

dark_theme = settings['dark_theme']
hacker_font = settings['hacker_font']
slower_animations = settings['slower_animations']
update_check = settings['update_check']
enable_preload = settings['enable_preload']
debug_info = settings['debug_info']
basic_success_checks = settings['basic_success_checks']
contributionsuggestions = settings['contributionsuggestions']

def load_strings(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    return {
        elem.attrib['name']: elem.text.replace('\\n', '\n') if elem.text else ''
        for elem in root.findall('string')
    }

# Load strings
strings = load_strings("strings.xml") # Load almost every string from strings.xml (ez translations)

# Load settings
def load_settings():
    return settings_store.load_saved()

# Save settings
def save_settings(new_settings):
    settings_store.save(new_settings)


def persist_settings():
    settings_store.persist(settings)

if platform.system() == "Windows":
    os_config = "WINDOWS"
elif platform.system() == "Darwin":
    os_config = "MACOS"
else:
    os_config = "LINUX"  # Linux and other POSIX systems

if os_config == "WINDOWS":
    enable_preload = False # Preload doesn't work on Windows; disable it

preload_done = threading.Event() # Event variable to check whether the Samsung modem preload has completed

# Imports that have error handling because they are sometimes not installed or are the cause of another error
try:
    import serial  # Communicating with device; late for self-fix bootstrap  # noqa: E402,F401
except ModuleNotFoundError:
    print("[nPhoneKIT] PySerial Error, wasn't able to import serial module.")
    x = input("Run Self-Fix Diagnostics? (RECOMMENDED, THIS USUALLY FIXES THE ISSUE) (y/n):")
    if x == "y" or x == "Y":
        self_fix_serial()

from nphonekit_devices import (  # noqa: E402
    ADB,
    AT,
    FastbootPartitionEraser,
    log_command_output,
    readOutput,
    rt,
    SamsungBloatwareRemover,
    SamsungDownloadModeClient,
    SamsungDeviceInfoClient,
    SamsungRebootClient,
    SamsungWifiTestClient,
    MtkClientRunner,
    BatteryLevelClient,
    SerialManager,
    SerialManagerWindows,
    SamsungPreloader,
    SamsungModemUnlocker,
    check_serial_permissions,
    is_root,
)  # noqa: E402

MAIN_SCRIPT = os.path.abspath(__file__)

# --- PRIVACY_UPDATER_START ---

def privacyupdate():
    # The original "Privacy Mode" wrote a temporary .py file, executed it, and
    # rewrote main.py in place to strip out networking. That self-modifying /
    # dynamic-exec machinery has been removed. Automatic telemetry is already
    # disabled at the source (see TELEMETRY_ENABLED / success_checks), so no
    # self-rewrite is needed to keep this copy from phoning home.
    try:
        messagebox.showinfo(
            "nPhoneKIT",
            "Privacy Mode is not needed in this build: automatic telemetry is "
            "already disabled and nPhoneKIT does not contact external servers "
            "on its own."
        )
    except Exception:
        print("[nPhoneKIT] Automatic telemetry is disabled in this build.")

# --- PRIVACY_UPDATER_END ---


def show_serial_permission_fix(command):
    """Present the platform-specific serial permission command to the user."""
    root = tk.Tk()
    root.title("Serial Permission Fix Required")
    root.geometry("500x250")
    label = tk.Label(root, text="To enable serial access, run this command in your terminal:", font=("Arial", 12))
    label.pack(pady=10)
    text_box = tk.Text(root, height=2, font=("Courier", 12))
    text_box.pack(padx=20, pady=10, fill="both")
    text_box.insert("1.0", command)
    text_box.config(state="disabled")
    reboot_label = tk.Label(root, text="After running the command, reboot your system.", font=("Arial", 10))
    reboot_label.pack(pady=10)
    ok_button = tk.Button(root, text="OK", command=root.destroy)
    ok_button.pack(pady=10)
    root.mainloop()

# Helper: worker used when we need to run the dialog in a new process.
# This must be a top-level function for multiprocessing to work reliably.
def _stw_worker(conn, title, desc, pros, cons, minutes, execute_text, cancel_text, win_w, win_h):
    """
    Runs in child process: constructs a Tk window, shows it, sends result (True/False)
    back through the connection, and exits.
    """
    try:
        root = tk.Tk()
        #root.withdraw()  # we'll show our Toplevel dialog
    except Exception:
        # If tk can't initialize, return False
        try:
            conn.send(False)
        except Exception:
            pass
        conn.close()
        return

    # Local stw implementation for child (almost same as parent inline version)
    # Colors & sizes
    bg = "#F5F7FB"
    card_bg = "#FFFFFF"
    text_primary = "#0F172A"
    text_secondary = "#374151"
    accent1 = "#2563EB"
    accent2 = "#0EA5E9"
    cons_red = "#B45309"
    pad = 14

    # Fonts (best-effort)
    try:
        title_font = font.nametofont("TkHeadingFont").copy()
        title_font.configure(size=18, weight="bold", family="Segoe UI")
    except Exception:
        title_font = ("Segoe UI", 18, "bold")
    desc_font = ("Segoe UI", 12)
    list_font = ("Segoe UI", 12)
    emoji_font = ("Noto Color Emoji", 14)

    # result container
    result = {"value": False}

    # build dialog
    win = root
    win.title("nPhoneKIT")
    win.geometry(f"{win_w}x{win_h}")
    win.configure(bg=bg)
    win.resizable(False, False)

    # When closed without pressing buttons
    def _on_close():
        result["value"] = False
        try:
            win.quit()
        except Exception:
            pass

    win.protocol("WM_DELETE_WINDOW", _on_close)

    # layout
    content = tk.Frame(win, bg=bg)
    content.place(relx=0, rely=0, relwidth=1, relheight=1)

    left_w = int((win_w - pad*3) * 0.66)
    right_w = (win_w - pad*3) - left_w

    left_frame_outer = tk.Frame(content, bg=bg)
    left_frame_outer.place(x=pad, y=pad, width=left_w, height=win_h - pad*4 - 60)

    right_frame = tk.Frame(content, bg=bg)
    right_frame.place(x=pad + left_w + pad, y=pad, width=right_w, height=win_h - pad*4 - 60)

    # Scrollable left card
    canvas = tk.Canvas(left_frame_outer, borderwidth=0, highlightthickness=0, bg=bg)
    vscroll = ttk.Scrollbar(left_frame_outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    vscroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    left_card = tk.Frame(canvas, bg=card_bg)
    canvas.create_window((0,0), window=left_card, anchor="nw")

    def _on_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    left_card.bind("<Configure>", _on_configure)

    # --- turn OFF scrolling (quick toggle) ---
    try:
        # hide the scrollbar widget so it isn't visible
        vscroll.pack_forget()
    except Exception:
        pass

    # stop the canvas from driving the scrollbar
    try:
        canvas.configure(yscrollcommand=lambda *args: None)
    except Exception:
        pass

    # stop adjusting scrollregion when left_card resizes (disable the handler if present)
    # if you previously bound left_card to update scrollregion, replace it with a no-op:
    try:
        left_card.unbind("<Configure>")
    except Exception:
        pass

    # disable mousewheel scrolling that may have been bound globally
    try:
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")
    except Exception:
        pass

    # optionally make the canvas non-expand so it won't try to scroll content
    try:
        canvas.pack_configure(expand=False, fill="both")
    except Exception:
        pass

    # Title
    lbl_title = tk.Label(left_card, text=title, font=title_font, bg=card_bg, fg=text_primary, wraplength=left_w-40, justify="left")
    lbl_title.pack(anchor="w", pady=(6,4))

    # Description (wrapped)
    desc_lbl = tk.Label(left_card, text=desc, font=desc_font, bg=card_bg, fg=text_secondary, wraplength=left_w-40, justify="left")
    desc_lbl.pack(anchor="w", pady=(0,8))

    # Pros
    pros_hdr = tk.Label(left_card, text="Pros", font=("Segoe UI", 13, "bold"), bg=card_bg, fg=text_primary)
    pros_hdr.pack(anchor="w", pady=(6,2))
    if not pros:
        pros = []
    for p in pros:
        row = tk.Frame(left_card, bg=card_bg)
        row.pack(fill="x", anchor="w", pady=2)
        em = tk.Label(row, text="✅", font=emoji_font, bg=card_bg)
        em.pack(side="left", anchor="n")
        txt = tk.Label(row, text=str(p), font=list_font, bg=card_bg, fg="#0B1720", wraplength=left_w-80, justify="left", anchor="w")
        txt.pack(side="left", anchor="w", padx=(8,0))

    # Cons
    cons_hdr = tk.Label(left_card, text="Cons", font=("Segoe UI", 13, "bold"), bg=card_bg, fg=text_primary)
    cons_hdr.pack(anchor="w", pady=(10,2))
    if not cons:
        cons = []
    for c in cons:
        row = tk.Frame(left_card, bg=card_bg)
        row.pack(fill="x", anchor="w", pady=2)
        em = tk.Label(row, text="❌", font=emoji_font, bg=card_bg)
        em.pack(side="left", anchor="n")
        txt = tk.Label(row, text=str(c), font=list_font, bg=card_bg, fg=cons_red, wraplength=left_w-80, justify="left")
        txt.pack(side="left", anchor="w", padx=(8,0))

    left_card.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")

    # Buttons area
    btn_area = tk.Frame(content, bg=bg)
    btn_area.place(x=pad, y=win_h - pad - 56, width=win_w - pad*2, height=56)

    def _on_cancel():
        result["value"] = False
        win.quit()

    cancel_btn = tk.Button(btn_area, text=cancel_text, command=_on_cancel,
                           bg=card_bg, fg=text_secondary, bd=1, relief="solid", padx=12, pady=6)
    cancel_btn.place(x=pad, y=6, width=120, height=44)

    # execute button canvas (gradient)
    exec_canvas = tk.Canvas(btn_area, bd=0, highlightthickness=0)
    exec_canvas.place(x=win_w - pad - 160, y=6, width=160, height=44)

    # draw gradient approximation
    def _draw_gradient(cnv, x0, y0, x1, y1, color1, color2, steps=48):
        def _hex_to_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0,2,4))
        def _rgb_to_hex(rgb):
            return "#{:02x}{:02x}{:02x}".format(*rgb)
        c1 = _hex_to_rgb(color1)
        c2 = _hex_to_rgb(color2)
        width = x1 - x0
        for i in range(steps):
            t = i / steps
            r = int(c1[0] + (c2[0]-c1[0]) * t)
            g = int(c1[1] + (c2[1]-c1[1]) * t)
            b = int(c1[2] + (c2[2]-c1[2]) * t)
            cnv.create_rectangle(x0 + i*(width/steps), y0, x0 + (i+1)*(width/steps), y1, outline="", fill=_rgb_to_hex((r,g,b)))
    _draw_gradient(exec_canvas, 0, 0, 160, 44, accent1, accent2, steps=64)
    exec_canvas.create_text(80, 22, text=execute_text, fill="white", font=("Segoe UI", 11, "bold"))

    def _on_execute(event=None):
        result["value"] = True
        win.quit()

    exec_canvas.bind("<Button-1>", _on_execute)
    exec_canvas.bind("<Return>", _on_execute)

    # Right column: clock canvas
    clock_w = right_w - 24
    clock_h = (win_h - pad*4 - 60)//2
    clock_canvas = tk.Canvas(right_frame, width=clock_w, height=clock_h, bg=card_bg, bd=0, highlightthickness=0)
    clock_canvas.pack(pady=(0,8))

    def _draw_clock():
        clock_canvas.delete("all")
        w = max(1, clock_canvas.winfo_width())
        h = max(1, clock_canvas.winfo_height())
        cx = w//2
        cy = h//2
        radius = int(min(w,h)*0.42)

        clock_canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, fill="#FFFFFF", outline="#D1D5DB", width=2)
        for i in range(60):
            ang = math.radians(i * 6)
            outer_x = cx + radius * math.sin(ang)
            outer_y = cy - radius * math.cos(ang)
            inner_len = radius * (0.90 if (i % 5 == 0) else 0.96)
            inner_x = cx + inner_len * math.sin(ang)
            inner_y = cy - inner_len * math.cos(ang)
            clock_canvas.create_line(inner_x, inner_y, outer_x, outer_y, fill="#9CA3AF", width=1)

        now = datetime.now()
        end = now + timedelta(minutes=minutes)
        minute_now = now.minute + now.second/60.0
        minute_end = end.minute + end.second/60.0

        def to_tk_angle(deg_clockwise_from_12):
            return 90 - deg_clockwise_from_12

        span_clockwise = (minute_end - minute_now) % 60.0
        span_deg = span_clockwise * 6.0
        start_angle = to_tk_angle(minute_now)
        # tkinter create_arc accepts floats but better cast to ints for some backends
        try:
            clock_canvas.create_arc(cx-radius+8, cy-radius+8, cx+radius-8, cy+radius-8,
                                    start=start_angle, extent=-span_deg, fill="#93C5FD", outline="")
        except Exception:
            clock_canvas.create_arc(int(cx-radius+8), int(cy-radius+8), int(cx+radius-8), int(cy+radius-8),
                                    start=int(start_angle), extent=int(-span_deg), fill="#93C5FD", outline="")

        def draw_hand(angle_deg, length_factor, color, width=4):
            rad = math.radians(angle_deg)
            x = cx + length_factor * radius * math.sin(rad)
            y = cy - length_factor * radius * math.cos(rad)
            clock_canvas.create_line(cx, cy, x, y, fill=color, width=width, capstyle="round")

        draw_hand(minute_now*6.0, 0.78, "#2563EB", 4)
        draw_hand(minute_end*6.0, 0.78, "#F59E0B", 4)
        clock_canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="#111827", outline="")

    # initial draw & periodic refresh
    win.update_idletasks()
    _draw_clock()
    def _tick():
        try:
            _draw_clock()
            win.after(1000, _tick)
        except tk.TclError:
            pass
    win.after(1000, _tick)

    eta_time = (datetime.now() + timedelta(minutes=minutes)).strftime("%I:%M %p").lstrip("0")
    eta_label = tk.Label(right_frame, text=f"⏱ {minutes} min\n🕓 Ends at: {eta_time}", bg=card_bg, fg=text_primary, font=("Segoe UI", 12), justify="center")
    eta_label.pack(pady=(6,0))

    # keyboard handling
    def _on_key(event):
        if event.keysym == "Return":
            _on_execute()
        elif event.keysym == "Escape":
            _on_cancel()
    win.bind_all("<Key>", _on_key)

    # center window on screen
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - win_w) // 2
    y = (sh - win_h) // 2
    win.geometry(f"+{x}+{y}")

    # run modal mainloop
    try:
        win.grab_set()
    except Exception:
        pass
    try:
        root.deiconify()
        win.focus_force()
        root.mainloop()
    except Exception:
        # if mainloop crashes, ensure we still send a result
        pass

    # after mainloop ends, send result back
    try:
        conn.send(bool(result["value"]))
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass

def stw(
    title: str,
    desc: str,
    pros,
    cons,
    minutes: int,
    execute_text: str = "Execute",
    cancel_text: str = "Cancel",
    win_size: Tuple[int,int] = (660, 880),
) -> bool:
    """
    Revised stw() — Pros and Cons are shown in two distinct sections (separate headers/frames).
    Keeps multiprocessing fallback for non-main-thread calls. Window title "nPhoneKIT".
    """
    #pros = ["test", "test2"]
    # normalize
    if pros is None:
        pros = []
    if cons is None:
        cons = []
    win_w, win_h = win_size
    win_h = 500

    # If caller not main thread -> spawn child (reuse existing worker implementation)
    if threading.current_thread() is not threading.main_thread():
        parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
        p = multiprocessing.Process(
            target=_stw_worker,
            args=(child_conn, title, desc, pros, cons, minutes, execute_text, cancel_text, win_w, win_h),
        )
        p.start()
        child_conn.close()
        try:
            res = parent_conn.recv()
        except EOFError:
            res = False
        finally:
            try:
                parent_conn.close()
            except Exception:
                pass
            p.join(timeout=0.1)
            if p.is_alive():
                try:
                    p.terminate()
                except Exception:
                    pass
        return bool(res)

    # Main-thread path: inline dialog without extra empty root
    created_root = False
    parent_root = tk._default_root
    if parent_root is None:
        root = tk.Tk()
        created_root = True
        root.withdraw()
    else:
        root = parent_root

    # Colors & fonts
    bg = "#F5F7FB"
    card_bg = "#FFFFFF"
    text_primary = "#0F172A"
    text_secondary = "#374151"
    accent1 = "#2563EB"
    accent2 = "#0EA5E9"
    cons_red = "#B45309"
    pad = 14

    try:
        title_font = font.nametofont("TkHeadingFont").copy()
        title_font.configure(size=18, weight="bold", family="Segoe UI")
    except Exception:
        title_font = ("Segoe UI", 18, "bold")
    desc_font = ("Segoe UI", 12)
    list_font = ("Segoe UI", 12)
    emoji_font = ("Noto Color Emoji", 14)

    result = {"value": False}

    win = tk.Toplevel(root)
    win.title("nPhoneKIT")
    win.geometry(f"{win_w}x{win_h}")
    win.configure(bg=bg)
    win.resizable(False, False)

    def _on_close():
        result["value"] = False
        try:
            if created_root:
                win.quit()
            else:
                win.quit()
        except Exception:
            pass

    win.protocol("WM_DELETE_WINDOW", _on_close)

    content = tk.Frame(win, bg=bg)
    content.place(relx=0, rely=0, relwidth=1, relheight=1)
    left_w = int((win_w - pad*3) * 0.66)
    right_w = (win_w - pad*3) - left_w

    left_frame_outer = tk.Frame(content, bg=bg)
    left_frame_outer.place(x=pad, y=pad, width=left_w, height=win_h - pad*4 - 60)
    right_frame = tk.Frame(content, bg=bg)
    right_frame.place(x=pad + left_w + pad, y=pad, width=right_w, height=win_h - pad*4 - 60)

    # Scrollable left card (keeps content from overflowing)
    canvas = tk.Canvas(left_frame_outer, borderwidth=0, highlightthickness=0, bg=bg)
    vscroll = ttk.Scrollbar(left_frame_outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    vscroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    left_card = tk.Frame(canvas, bg=card_bg)
    # set fixed width for left_card so wraplengths behave predictably
    left_card.pack_propagate(False)
    canvas.create_window((0,0), window=left_card, anchor="nw", width=left_w)

    def _on_config(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    left_card.bind("<Configure>", _on_config)

    # Title and description
    lbl_title = tk.Label(left_card, text=title, font=title_font, bg=card_bg, fg=text_primary, wraplength=left_w-40, justify="left")
    lbl_title.pack(anchor="w", pady=(12,6), padx=12)
    desc_lbl = tk.Label(left_card, text=desc, font=desc_font, bg=card_bg, fg=text_secondary, wraplength=left_w-40, justify="left")
    desc_lbl.pack(anchor="w", pady=(0,10), padx=12)

    # Horizontal separator
    sep1 = ttk.Separator(left_card, orient="horizontal")
    sep1.pack(fill="x", padx=12, pady=(4,10))

    # --- PROS SECTION (distinct frame) ---
    pros_frame = tk.Frame(left_card, bg=card_bg)
    pros_frame.pack(fill="x", padx=12, pady=(0,8))

    pros_hdr = tk.Label(pros_frame, text="PROS", font=("Segoe UI", 13, "bold"), bg=card_bg, fg=text_primary, anchor="w")
    pros_hdr.pack(anchor="w", pady=(0,6))

    # If no pros provided, show subtle 'None' label
    if not pros:
        none_lbl = tk.Label(pros_frame, text="(None)", font=list_font, bg=card_bg, fg=text_secondary, wraplength=left_w-40, justify="left")
        none_lbl.pack(anchor="w", pady=2)
    else:
        for p in pros:
            # Each item gets its own row with an emoji label and a text label that wraps
            item_row = tk.Frame(pros_frame, bg=card_bg)
            item_row.pack(fill="x", anchor="w", pady=4)
            em = tk.Label(item_row, text="✅", font=emoji_font, bg=card_bg)
            em.pack(side="left", anchor="n", padx=(0,6))
            txt = tk.Label(item_row, text=str(p), font=list_font, bg=card_bg, fg="#0B1720",
                           wraplength=left_w-80, justify="left", anchor="w")
            txt.pack(side="left", anchor="w", fill="x", expand=True)

    # separator between pros and cons
    sep2 = ttk.Separator(left_card, orient="horizontal")
    sep2.pack(fill="x", padx=12, pady=(10,10))

    # --- CONS SECTION (distinct frame) ---
    cons_frame = tk.Frame(left_card, bg=card_bg)
    cons_frame.pack(fill="x", padx=12, pady=(0,12))

    cons_hdr = tk.Label(cons_frame, text="CONS", font=("Segoe UI", 13, "bold"), bg=card_bg, fg=text_primary, anchor="w")
    cons_hdr.pack(anchor="w", pady=(0,6))

    if not cons:
        none_lbl2 = tk.Label(cons_frame, text="(None)", font=list_font, bg=card_bg, fg=text_secondary, wraplength=left_w-40, justify="left")
        none_lbl2.pack(anchor="w", pady=2)
    else:
        for c in cons:
            item_row = tk.Frame(cons_frame, bg=card_bg)
            item_row.pack(fill="x", anchor="w", pady=4)
            em = tk.Label(item_row, text="❌", font=emoji_font, bg=card_bg)
            em.pack(side="left", anchor="n", padx=(0,6))
            txt = tk.Label(item_row, text=str(c), font=list_font, bg=card_bg, fg=cons_red,
                           wraplength=left_w-80, justify="left", anchor="w")
            txt.pack(side="left", anchor="w", fill="x", expand=True)

    # finalize scroll region
    left_card.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")

    # Buttons area
    btn_area = tk.Frame(content, bg=bg)
    btn_area.place(x=pad, y=win_h - pad - 56, width=win_w - pad*2, height=56)

    def _on_cancel_local():
        result["value"] = False
        try:
            if created_root:
                win.quit()
            else:
                win.quit()
        except Exception:
            pass

    cancel_btn = tk.Button(btn_area, text=cancel_text, command=_on_cancel_local,
                           bg=card_bg, fg=text_secondary, bd=1, relief="solid", padx=12, pady=6)
    cancel_btn.place(x=pad, y=6, width=120, height=44)

    # execute gradient button (canvas)
    exec_canvas = tk.Canvas(btn_area, bd=0, highlightthickness=0)
    exec_canvas.place(x=win_w - pad - 160, y=6, width=160, height=44)
    def _draw_gradient_canvas(cnv, x0, y0, x1, y1, color1, color2, steps=48):
        def _hex_to_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0,2,4))
        def _rgb_to_hex(rgb):
            return "#{:02x}{:02x}{:02x}".format(*rgb)
        c1 = _hex_to_rgb(color1)
        c2 = _hex_to_rgb(color2)
        width = x1 - x0
        for i in range(steps):
            t = i / steps
            r = int(c1[0] + (c2[0]-c1[0]) * t)
            g = int(c1[1] + (c2[1]-c1[1]) * t)
            b = int(c1[2] + (c2[2]-c1[2]) * t)
            cnv.create_rectangle(x0 + i*(width/steps), y0, x0 + (i+1)*(width/steps), y1, outline="", fill=_rgb_to_hex((r,g,b)))
    _draw_gradient_canvas(exec_canvas, 0, 0, 160, 44, accent1, accent2, steps=64)
    exec_canvas.create_text(80, 22, text=execute_text, fill="white", font=("Segoe UI", 11, "bold"))

    def _on_execute_local(event=None):
        result["value"] = True
        try:
            if created_root:
                win.quit()
            else:
                win.quit()
        except Exception:
            pass
    exec_canvas.bind("<Button-1>", _on_execute_local)
    exec_canvas.bind("<Return>", _on_execute_local)

    # Clock area (right)
    clock_w = right_w - 24
    clock_h = (win_h - pad*4 - 60)//2
    clock_canvas = tk.Canvas(right_frame, width=clock_w, height=clock_h, bg=card_bg, bd=0, highlightthickness=0)
    clock_canvas.pack(pady=(0,8))

    def _draw_clock_local():
        clock_canvas.delete("all")
        w = max(1, clock_canvas.winfo_width())
        h = max(1, clock_canvas.winfo_height())
        cx = w//2
        cy = h//2
        radius = int(min(w,h)*0.42)
        clock_canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, fill="#FFFFFF", outline="#D1D5DB", width=2)
        for i in range(60):
            ang = math.radians(i * 6)
            outer_x = cx + radius * math.sin(ang)
            outer_y = cy - radius * math.cos(ang)
            inner_len = radius * (0.90 if (i % 5 == 0) else 0.96)
            inner_x = cx + inner_len * math.sin(ang)
            inner_y = cy - inner_len * math.cos(ang)
            clock_canvas.create_line(inner_x, inner_y, outer_x, outer_y, fill="#9CA3AF", width=1)

        now = datetime.now()
        end = now + timedelta(minutes=minutes)
        minute_now = now.minute + now.second/60.0
        minute_end = end.minute + end.second/60.0
        span_clockwise = (minute_end - minute_now) % 60.0
        span_deg = span_clockwise * 6.0
        start_angle = 90 - (minute_now * 6.0)
        try:
            clock_canvas.create_arc(cx-radius+8, cy-radius+8, cx+radius-8, cy+radius-8, start=start_angle, extent=-span_deg, fill="#93C5FD", outline="")
        except Exception:
            clock_canvas.create_arc(int(cx-radius+8), int(cy-radius+8), int(cx+radius-8), int(cy+radius-8), start=int(start_angle), extent=int(-span_deg), fill="#93C5FD", outline="")
        def draw_hand(angle_deg, length_factor, color, width=4):
            rad = math.radians(angle_deg)
            x = cx + length_factor * radius * math.sin(rad)
            y = cy - length_factor * radius * math.cos(rad)
            clock_canvas.create_line(cx, cy, x, y, fill=color, width=width, capstyle="round")
        draw_hand(minute_now*6.0, 0.78, "#2563EB", 4)
        draw_hand(minute_end*6.0, 0.78, "#F59E0B", 4)
        clock_canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="#111827", outline="")

    win.update_idletasks()
    _draw_clock_local()
    def _tick_local():
        try:
            _draw_clock_local()
            win.after(1000, _tick_local)
        except tk.TclError:
            pass
    win.after(1000, _tick_local)

    eta_time = (datetime.now() + timedelta(minutes=minutes)).strftime("%I:%M %p").lstrip("0")
    eta_label = tk.Label(right_frame, text=f"⏱ {minutes} min\n🕓 Ends at: {eta_time}", bg=card_bg, fg=text_primary, font=("Segoe UI", 12), justify="center")
    eta_label.pack(pady=(6,0))

    def _on_key(event):
        if event.keysym == "Return":
            _on_execute_local()
        elif event.keysym == "Escape":
            _on_cancel_local()
    win.bind_all("<Key>", _on_key)

    # center
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - win_w) // 2
    y = (sh - win_h) // 2
    win.geometry(f"+{x}+{y}")

    try:
        win.grab_set()
    except Exception:
        pass

    # Run modal/blocking logic
    if created_root:
        try:
            root.focus_force()
            root.mainloop()
        except Exception:
            try:
                win.wait_window()
            except Exception:
                pass
    else:
        try:
            win.wait_window()
        except Exception:
            try:
                root.update()
            except Exception:
                pass

    # cleanup
    try:
        win.destroy()
    except Exception:
        pass
    if created_root:
        try:
            root.destroy()
        except Exception:
            pass

    return bool(result["value"])

def pullerrors():
    if UiMainWindow.instance is None:
        return ""
    return UiMainWindow.instance.output.toPlainText()

# Check for updates

def check_for_update():
    try:
        latest_version_raw, latest_version = UpdateClient().latest()

        # If the tag is different then the current version, assume it's newer, and prompt update.

        # Based on the unicode "v", depending on whether it's normal or U+2174, prompt for normal update and FORCE for critical update

        # *************************************************************************
        # It's not reccomended to change this in order to bypass a critical update.
        # *************************************************************************

        if latest_version != VERSION:
            # Note: the upstream project could force-quit the app here for a
            # "critical" update (the U+2174 trick). That remote lockout has
            # been removed so an update notice can never block local use.
            if "ⅴ" in latest_version_raw:
                messagebox.showinfo(
                    strings['updateReqd'],
                    strings['updateReqdString'].format(version=VERSION, latest_version=latest_version)
                )
            else:
                messagebox.showinfo(
                    strings['updateAvail'],
                    strings['updateAvailString'].format(version=VERSION, latest_version=latest_version)
                )
    except Exception:
        print(strings['updateCheckFailed'])

def get_public_hardware_uuid():
    return public_hardware_uuid()

FIREBASE_URL = "https://nphonekit-default-rtdb.firebaseio.com/" # URL for success checks

# --- Automatic telemetry hard-disabled ---
# nPhoneKIT normally phones home to Firebase on startup and after actions,
# sending a hashed-MAC UUID, model, action, status, captured errors and OS info.
# This is not required for any device (ADB/serial/FRP/MTK) functionality, so it
# is disabled here. Set to True to re-enable the automatic success checks.
TELEMETRY_ENABLED = False

def success_checks(uuid, model, action, status, first=True):
    TelemetryClient(
        FIREBASE_URL, TELEMETRY_ENABLED, basic_success_checks, VERSION,
        pull_errors=pullerrors, get_os_info=get_os_info,
        marker_path=Path(__file__).parent / ".notfirst",
    ).submit(uuid, model, action, status, first)

# =============================================
#  Different instructions for the user
# =============================================

def MTPmenu():
    show_messagebox_at(500, 200, "nPhoneKIT", strings['mtpMenu'])
    # Show user instructions to enable MTP mode

def adbMenu():
    ADB.send("devices")
    show_messagebox_at(500, 200, "nPhoneKIT", strings['adbMenu'])
    # Show user instructions to enable ADB mode

def show_messagebox_at(x, y, title, content): # Show a customizable message box
    app = QtWidgets.QApplication.instance()
    if app is not None:
        if qt_dialog_helper is None:
            init_qt_dialog_helper()
        if app.thread() != QtCore.QThread.currentThread():
            done = threading.Event()
            result = {}
            qt_dialog_helper.request_message.emit(x, y, title, content, result, done)
            done.wait()
            return
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(content)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.exec_()
        return

    # Create a new top-level window
    box = tk.Tk()
    box.title(title)
    box.geometry(f"+{x}+{y}")
    box.resizable(False, False)

    # Frame and Label
    tk.Label(box, text=content, font=("Segoe UI", 12), padx=20, pady=20).pack()

    # OK button that closes the window
    tk.Button(box, text="OK", width=10, command=box.destroy).pack(pady=(0, 15))

    # Keep it modal — BLOCK everything until this window closes
    box.attributes("-topmost", True)
    box.grab_set()
    box.wait_window()  # <--- THIS is what blocks until closed

def smbdelay(x, y, title, content, delay=8):  # Show a message box with a delayed close button and disabled X button
    box = tk.Tk()
    box.title(title)
    box.geometry(f"+{x}+{y}")
    box.resizable(False, False)

    tk.Label(box, text=content, font=("Segoe UI", 12), padx=20, pady=20).pack()

    # Button starts disabled
    ok_button = tk.Button(box, text=f"OK ({delay})", width=10, state="disabled", command=box.destroy)
    ok_button.pack(pady=(0, 15))

    # Disable the X button — do nothing on close request
    box.protocol("WM_DELETE_WINDOW", lambda: None)

    # Countdown logic
    def countdown(remaining):
        if remaining > 0:
            ok_button.config(text=f"OK ({remaining})")
            box.after(1000, countdown, remaining - 1)
        else:
            ok_button.config(text="OK", state="normal")

    countdown(delay)

    # Keep it modal — BLOCK everything until this window closes
    box.attributes("-topmost", True)
    box.grab_set()
    box.wait_window()

def contribution_prompt(x, y):  # Nicely formatted contribution/support message box
    uuid_str = str(get_public_hardware_uuid())

    # If the Qt app is running, show a Qt dialog on the main thread. Creating a raw Tk window here
    # (this is usually called from a worker thread after an unlock) hard-crashes the process on macOS.
    app = QtWidgets.QApplication.instance()
    if app is not None:
        if qt_dialog_helper is None:
            init_qt_dialog_helper()
        if app.thread() != QtCore.QThread.currentThread():
            done = threading.Event()
            qt_dialog_helper.request_contribution.emit(uuid_str, done)
            done.wait()
        else:
            qt_dialog_helper._show_contribution(uuid_str, threading.Event())
        return

    box = tk.Tk()
    box.title("Support nPhoneKIT")
    box.geometry(f"+{x}+{y}")
    box.resizable(False, False)

    message = (
        "PLEASE DO NOT IGNORE THIS MESSAGE:\n\n"
        "Want to help support nPhoneKIT, and get a special Contributor\n"
        "thank you message on the README? Simply fill out the quick\n"
        "and simple form linked below.\n\n"
        "Remember, you can (and should!) submit the form, whether the\n"
        "unlock worked flawlessly or failed horribly! This helps fix\n"
        "bugs and errors for the future.\n\n"
        f"Your unique submission code (prevents spam):\n{uuid_str}\n\n"
        "Want to turn off this message? Turn off 'Contribution Messages'\n"
        "in settings."
    )

    tk.Label(
        box, text=message, font=("Segoe UI", 11),
        padx=25, pady=20, justify="left"
    ).pack()

    # Notification label (hidden until button is clicked)
    notice_label = tk.Label(box, text="", font=("Segoe UI", 9, "italic"), fg="green")
    notice_label.pack(pady=(0, 5))

    def open_form():
        box.clipboard_clear()
        box.clipboard_append(uuid_str)
        box.update()  # keep clipboard content after window closes
        notice_label.config(text="✅ UUID copied to clipboard! Opening form in your browser...")
        webbrowser.open("https://forms.gle/SM8Mjyoz43Jcwxzn8")

    support_button = tk.Button(
        box, text="Support nPhoneKIT — Open Form", width=30, height=2,
        bg="#1a73e8", fg="white", font=("Segoe UI", 11, "bold"),
        activebackground="#1558b0", activeforeground="white",
        command=open_form
    )
    support_button.pack(pady=(0, 15))

    # Small delayed decline link
    decline_label = tk.Label(
        box, text="", font=("Segoe UI", 8), fg="gray50", cursor="hand2"
    )
    decline_label.pack(pady=(0, 15))

    def countdown(remaining):
        if remaining > 0:
            decline_label.config(text=f"(decline available in {remaining}s)")
            box.after(1000, countdown, remaining - 1)
        else:
            decline_label.config(text="No, I don't want to support open-source developers.")
            decline_label.bind("<Button-1>", lambda e: box.destroy())

    countdown(5)

    box.attributes("-topmost", True)
    box.grab_set()
    box.wait_window()

def modemUnlock(manufacturer, softUnlock=False): # Unlock the modem per-action if preload wasn't enabled
    if samsung_modem_unlocker is not None:
        samsung_modem_unlocker.unlock(manufacturer, softUnlock)

# Function that can parse DEVCONINFO in order to make it more readable
parse_devconinfo = nphonekit_core.parse_devconinfo

def lu(path="unlocks.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def formrequest():
    if contributionsuggestions is True:
        contribution_prompt(500, 500)
# =============================================
#  Unlocking methods for different devices
# =============================================

def frp_unlock_pre_aug2022(): # FRP unlock for pre-aug2022 security patch update
    methods = lu("unlocks.json")
    for m in methods:
        if m["id"] == "sam_pre_2022":
            picked = stw(m["title"], m["desc"], m["pros"], m["cons"], m["minutes"])
            if picked:
                print(strings['getVerInfo'], end="")
                info = verinfo(False)
                model = re.search(r'Model:\s*(\S+)', info) # Extract only the model no. from the output

                if info == "Fail":
                    print(strings['deviceCheckPluggedIn2'])
                    tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_Pre_2022", "Fail"))
                    tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                else:
                    ATcommands = [
                        "AT+DUMPCTRL=1,0",
                        "AT+DEBUGLVC=0,5",
                        "AT+SWATD=0", # Removes some kind of proprietary SAMSUNG modem lock
                        "AT+ACTIVATE=0,0,0", # So that you can ACTIVATE
                        "AT+SWATD=1", # Then relocks it.
                        "AT+DEBUGLVC=0,5"
                    ]

                    ADBcommands = [ # Run list of commands in order to complete the unlock with newly-enabled ADB
                        "shell settings put global setup_wizard_has_run 1",
                        "shell settings put secure user_setup_complete 1",
                        "shell content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1",
                        "shell content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:i:1",
                        "shell content insert --uri content://settings/secure --bind name:s:INSTALL_NON_MARKET_APPS --bind value:i:1",
                        "shell am start -c android.intent.category.HOME -a android.intent.action.MAIN"
                    ]

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['misuseFrpGuidance'])

                    print(strings['attemptingEnableAdb'], end="")

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['frpUnlockStepsPre2022'])

                    for command in ATcommands:
                        AT.send(command)

                    output = log_command_output("AT", "AT")

                    if "error" in output.lower():
                        print(strings['failText'])
                        print(strings['frpNotCompatible'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_Pre_2022", "Fail"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()
                    else:
                        print(strings['okText'])
                        print(strings['runUnlock'], end="")
                        show_messagebox_at(500, 200, "nPhoneKIT", strings['usbDebuggingPromptCheck'])
                        for command in ADBcommands:
                            ADB.send(command)
                        print(strings['okText'])
                        print(strings['unlockSuccess'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_Pre_2022", "Success"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()

def frp_unlock_aug2022_to_dec2022(): # FRP unlock for aug2022-dec2022 security patch update
    methods = lu("unlocks.json")
    for m in methods:
        if m["id"] == "sam_2022_23":
            picked = stw(m["title"], m["desc"], m["pros"], m["cons"], m["minutes"])
            if picked:
                print(strings['getVerInfo'], end="")
                info = verinfo(False)
                model = re.search(r'Model:\s*(\S+)', info) # Extract only the model no. from the output

                if info == "Fail":
                    print(strings['deviceCheckPluggedIn2'])
                    tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_Aug_To_Dec_2022", "Fail"))
                    tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                else:
                    commands = ['AT+SWATD=0', 'AT+ACTIVATE=0,0,0', 'AT+DEVCONINFO','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0', 'AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5']
                    # These commands are supposed to overwhelm the phone and trick it into enabling ADB. The rest after this is the same as the other unlock method.

                    ADBcommands = [ # Run list of commands in order to complete the unlock with newly-enabled ADB
                        "shell settings put global setup_wizard_has_run 1",
                        "shell settings put secure user_setup_complete 1",
                        "shell content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1",
                        "shell content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:i:1",
                        "shell content insert --uri content://settings/secure --bind name:s:INSTALL_NON_MARKET_APPS --bind value:i:1",
                        "shell am start -c android.intent.category.HOME -a android.intent.action.MAIN"
                    ]

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['misuseFrpGuidance2022'])

                    print(strings['attemptingEnableAdb'], end="")

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['frpUnlockSteps2022'])

                    for command in commands:
                        AT.send(command)

                    output = log_command_output("AT", "AT")

                    if "error" in output.lower():
                        print(strings['failText'])
                        print(strings['frpNotCompatible'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_Aug_To_Dec_2022", "Fail"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()
                    else:
                        print(strings['okText'])
                        print(strings['runUnlock'], end="")
                        show_messagebox_at(500, 200, "nPhoneKIT", strings['usbDebuggingPromptCheck'])
                        for command in ADBcommands:
                            ADB.send(command)
                            log_command_output("ADB", f"ADB {command}")
                        print(strings['okText'])
                        print(strings['unlockSuccess'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_Aug_To_Dec_2022", "Success"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()

def frp_unlock_2024(): # FRP unlock for early 2024-ish security patch update
    methods = lu("unlocks.json")
    for m in methods:
        if m["id"] == "sam_2024":
            picked = stw(m["title"], m["desc"], m["pros"], m["cons"], m["minutes"])
            if picked:
                print(strings['getVerInfo'], end="")
                info = verinfo(False)
                model = re.search(r'Model:\s*(\S+)', info) # Extract only the model no. from the output

                if info == "Fail":
                    print(strings['deviceCheckPluggedIn2'])
                    tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_2024", "Fail"))
                    tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                else:
                    commands = [
                        "AT+SWATD=0", # Modem unlocking
                        "AT+ACTIVATE=0,0,0", # Modem unlocking
                        "AT+DEVCONINFO", # Get device info
                        "AT+VERSNAME=3,2,3", # FRP version query
                        "AT+FRPUNLCK=3,0,0", # Query FRP lock status
                        "AT+SWATD=0", # Re-Modem unlocking
                        "AT+ACTIVATE=0,0,0", # Re-Modem unlocking
                        "AT+SWATD=1", # Lock quickly
                        "AT+SWATD=1", # Lock again
                        "AT+PRECONFG=2,VZW", # Quickly change CSC
                        "AT+PRECONFG=1,0", # Quickly change it back
                    ]

                    ADBcommands = [ # Run list of commands in order to complete the unlock with newly-enabled ADB
                        "shell settings put global setup_wizard_has_run 1",
                        "shell settings put secure user_setup_complete 1",
                        "shell content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1",
                        "shell content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:i:1",
                        "shell content insert --uri content://settings/secure --bind name:s:INSTALL_NON_MARKET_APPS --bind value:i:1",
                        "shell am start -c android.intent.category.HOME -a android.intent.action.MAIN"
                    ]

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['misuseFrpGuidance2024'])

                    print(strings['attemptingEnableAdb'], end="")

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['frpUnlockSteps2024'])

                    for command in commands:
                        AT.send(command)

                    output = readOutput("AT")

                    if "error" in output.lower():
                        print(strings['failText'])
                        print(strings['frpNotCompatible'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_2024", "Fail"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()
                    else:
                        print(strings['okText'])
                        print(strings['runUnlock'], end="")
                        show_messagebox_at(500, 200, "nPhoneKIT", strings['usbDebuggingPromptCheck'])
                        # Wait for the phone to re-enumerate into ADB mode and for the user to accept the USB debugging prompt.
                        # Without this, the adb commands below run before the device is ready (or authorized) and silently do nothing.
                        state = ADB.wait_for_device()
                        adb_failed = state != "device"
                        if not adb_failed:
                            for command in ADBcommands:
                                ADB.send(command)
                                out = log_command_output("ADB", f"ADB {command}")
                                if "error:" in out.lower() or "no devices" in out.lower() or "unauthorized" in out.lower():
                                    adb_failed = True
                                    break
                        if adb_failed:
                            print(strings['failText'])
                            print(strings['frpNotCompatible'])
                            tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_2024", "Fail"))
                            tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                            formrequest()
                            return
                        print(strings['okText'])
                        print(strings['unlockSuccess'])
                        if model == "" or model is None:
                            # Retry get model
                            info = verinfo(False, False)
                            model = re.search(r'Model:\s*(\S+)', info) # Extract only the model no. from the output
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_2024", "Success"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()

def frp_unlock_android15_16(): # FRP unlock for early 2024-ish security patch update
    methods = lu("unlocks.json")
    for m in methods:
        if m["id"] == "sam_15_16":
            picked = stw(m["title"], m["desc"], m["pros"], m["cons"], m["minutes"])
            if picked:
                print(strings['getVerInfo'], end="")
                info = verinfo(False)
                model = re.search(r'Model:\s*(\S+)', info) # Extract only the model no. from the output

                if info == "Fail":
                    print(strings['deviceCheckPluggedIn2'])
                    tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_15_16", "Fail"))
                    tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                else:
                    commands = [
                        "AT",                 # Verify AT is working
                        "AT+KSTRINGB=0,3",    # Work with Knox
                        "AT+DUMPCTRL=1,0",    # Activate dev mode
                        "AT+DEBUGLVL=0,4",    # Debug Level High
                        "AT+SWATD=0",         # Disable modem lock
                        "AT+ACTIVATE=0,0,0",  # Activate unlock
                        "AT+SWATD=1"          # Re-enable modem lock (Triggers the popup)
                    ]

                    ADBcommands = [ # Run list of commands in order to complete the unlock with newly-enabled ADB
                        "shell content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:s:1",
                        "shell pm uninstall -k --user 0 com.google.android.gsf",
                        "shell am start -n com.android.settings/com.android.settings.Settings"
                    ]

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['misuseFrpGuidance2024'])

                    print(strings['attemptingEnableAdb'], end="")

                    show_messagebox_at(500, 200, "nPhoneKIT", strings['frpUnlockSteps2024'])

                    for command in commands:
                        AT.send(command)

                    log_command_output("AT", "AT")

                    try:
                        print(strings['okText'])
                        print(strings['runUnlock'], end="")
                        show_messagebox_at(500, 200, "nPhoneKIT", strings['usbDebuggingPromptCheck'])
                        # Wait for the phone to re-enumerate into ADB mode and for the user to accept the USB debugging prompt.
                        # Without this, the adb commands below run before the device is ready (or authorized) and silently do nothing.
                        state = ADB.wait_for_device()
                        if state != "device":
                            raise RuntimeError(f"No authorized ADB device (state: {state})")
                        for command in ADBcommands:
                            ADB.send(command)
                            out = log_command_output("ADB", f"ADB {command}")
                            if "error:" in out.lower() or "no devices" in out.lower() or "unauthorized" in out.lower():
                                raise RuntimeError(f"ADB command failed: {command}")
                        print(strings['okText'])
                        print(strings['unlockSuccess'])
                        if model == "" or model is None:
                            # Retry get model
                            info = verinfo(False, False)
                            model = re.search(r'Model:\s*(\S+)', info) # Extract only the model no. from the output
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_15_16", "Success"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()
                    except Exception:
                        print(strings['failText'])
                        print(strings['frpNotCompatible'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "FRP_Unlock_15_16", "Fail"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                        formrequest()

def general_frp_unlock(): # Not completed yet
    raise NotImplementedError("This function is not yet implemented.")
    info = verinfo(False)
    if "Model: SM" in info:
        frp_unlock_pre_aug2022()
    else:
        # to do, add FULLY universal FRP unlock
        print(strings['deviceNotSupportedUniversal'])

def LG_screen_unlock(): # Screen unlock on supported LG devices *untested*
    methods = lu("unlocks.json")
    for m in methods:
        if m["id"] == "lg_unlock":
            picked = stw(m["title"], m["desc"], m["pros"], m["cons"], m["minutes"])
            if picked:
                info = verinfo(False)
                model = re.search(r'Model:\s*(\S+)', info) # Extract only the model no. from the output (may not work)

                show_messagebox_at(500, 200, "nPhoneKIT", strings['lgScreenUnlockSupportedDevs'])
                print(strings['lgRunningScreenUnlock'], end="")
                # Prepare phone for unlock
                show_messagebox_at(600, 100, "nPhoneKIT", strings['lgScreenUnlockSteps'])

                time.sleep(1)
                if AT.usbswitch("-l", "LG Screen Unlock"):
                    rt() # Flush the output buffer
                    AT.send('AT%KEYLOCK=0') # This AT command SHOULD unlock the screen instantly. (yes, one command.)
                    with open("tmp_output.txt", "r") as f:
                        output = f.read()
                    # debug only: print("\n\nOutput: \n\n" + output + "\n\n")
                    if "error" in output or "Error" in output:
                        print(strings['failText'] + "\n")
                        print(strings['lgScreenUnlockError'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "LG_Screen_Unlock", "Fail"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.
                    else:
                        rt()
                        print(strings['okText'] + "\n")
                        print(strings['lgScreenUnlockSuccess'])
                        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "LG_Screen_Unlock", "Success"))
                        tthread.start() # Sends basic, anonymized success_checks info with only the model number. This is so we know what devices are compatible with which unlocks.

def MotoFastbootFRP1():
    methods = lu("unlocks.json")
    for m in methods:
        if m["id"] == "moto_fastboot_frp_unlock":
            picked = stw(m["title"], m["desc"], m["pros"], m["cons"], m["minutes"])
            if picked:
                show_messagebox_at(200,200,"nPhoneKIT",strings["motoFastbootGuide"])
                # erase frp partitions upon fastboot access granted
                try:
                    eraser = FastbootPartitionEraser()
                except FileNotFoundError as e:
                    print(f"Aborting: {e}")
                    show_messagebox_at(200, 200, "nPhoneKIT", str(e))
                    return

                # Pre-flight: refuse to erase/wipe unless exactly one device is
                # in fastboot. With 0 or several connected, `fastboot` would act
                # on an ambiguous target -- and wipe_data_cache is `fastboot -w`,
                # which erases userdata. Target the chosen serial explicitly.
                serial, reason = nphonekit_core.select_target_device(
                    [(s, "device") for s in eraser.list_devices()]
                )
                if reason:
                    msg = nphonekit_core.describe_selection_reason(reason)
                    print(f"Aborting fastboot FRP erase: {msg}")
                    show_messagebox_at(200, 200, "nPhoneKIT", msg)
                    return

                eraser.erase_config(serial)
                eraser.erase_persist(serial)
                eraser.erase_frp(serial)
                eraser.wipe_data_cache(serial)

# ==============================================
#  Simple functions that do stuff to the device
# ==============================================

def verinfo(gui=True, showtext=True): # Get version info on the device. Pretty simple. (not simple, this has taken me hours.)
    info_client = SamsungDeviceInfoClient(AT, readOutput, rt, samsung_modem_unlocker)
    if gui:
        print(strings['getVerInfo'], end="")
        output = info_client.fetch(enable_preload, gui=True)
        if not output:
            print(strings['failText'])
            print(strings['verInfoCheckConn'])
            model = re.search(r'Model:\s*(\S+)', output)
            tthread = threading.Thread(target=success_checks, args=(
                get_public_hardware_uuid(), model, "VersionInfo", "Fail"
            ))
            tthread.start()
        else:
            print(strings['okText'])
            model = re.search(r'Model:\s*(\S+)', output)
            tthread = threading.Thread(target=success_checks, args=(
                get_public_hardware_uuid(), model, "VersionInfo", "Success"
            ))
            tthread.start()
        output = parse_devconinfo(output)
        print(output)
    else:
        #print(strings['getVerInfo'], end="")
        if 1 == 1: # We should verify AT is working before running the below code (deprecated)
            output = info_client.fetch(enable_preload)
            if not output and showtext:
                print(strings['failText'])
            elif output and showtext:
                print(strings['okText'])
            output = parse_devconinfo(output) # Make the output actually readable (parse the output)
            model = re.search(r'Model:\s*(\S+)', output) # Extract only the model no. from the output
            if output == "" or output is None:
                tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "VersionInfo", "Fail"))
                tthread.start() # Sends basic, anonymized success_checks info with only the model number.
                return "Fail"
            else:
                tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "VersionInfo", "Success"))
                tthread.start() # Sends basic, anonymized success_checks info with only the model number.
                return output # Return the version info

def wifitest(): # Opens a hidden WLANTEST menu on Samsung devices
    info = verinfo(False)
    model = re.search(r'Model:\s*(\S+)', info)

    print(strings['openingWifitest'], end="")
    MTPmenu()
    if SamsungWifiTestClient(
        AT, samsung_modem_unlocker, rt, readOutput
    ).open():
        print(strings['okText'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "WIFITEST", "Success"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.
    else:
        print(strings['failText'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "WIFITEST", "Fail"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.

def reboot(): # Crash an android phone to reboot
    print(strings['crashingToReboot'], end="")
    MTPmenu()
    info = verinfo(False)
    model = re.search(r'Model:\s*(\S+)', info)
    result = SamsungRebootClient(AT, rt, readOutput).crash_reboot()
    if result is False:
        print(strings['failText'])
        print(strings['crashRebootFailed'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "REBOOT", "Fail"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.
    elif result is True:
        print(strings['okText'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "REBOOT", "Success"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.

def reboot_sam(): # Crash a Samsung phone to reboot
    print(strings['crashingToReboot'], end="")
    MTPmenu()
    modemUnlock("SAMSUNG", True)
    info = verinfo(False)
    model = re.search(r'Model:\s*(\S+)', info)
    result = SamsungRebootClient(AT, rt, readOutput).crash_reboot()
    if result is False:
        print(strings['failText'])
        print(strings['crashRebootFailed'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "REBOOT_SAM", "Fail"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.
    elif result is True:
        print(strings['okText'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "REBOOT_SAM", "Success"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.

def bloatRemove():
    print(strings['uninstallingPackages'], end="")
    adbMenu()

    # Pre-flight: only debloat when exactly one ready device is connected, so
    # `pm uninstall` can't run against the wrong phone. Target it explicitly.
    serial, reason = nphonekit_core.select_target_device(ADB.devices())
    if reason:
        msg = nphonekit_core.describe_selection_reason(reason)
        print(strings['failText'])
        print(msg)
        return

    remover = SamsungBloatwareRemover(ADB, readOutput)
    if remover.remove(serial):
        print(strings['okText'])
        print(strings['debloatSucceeded'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), None, "DEBLOAT_SAM", "Success"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.
    else:
        print(strings['failText'])
        print(strings['devNotConnectedOrOtherErr'])
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), None, "DEBLOAT_SAM", "Fail"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.

def reboot_download_sam(): # Reboot Samsung device to download mode
    print(strings['rebootingDownloadMode'], end="")
    MTPmenu()
    SamsungDownloadModeClient(AT, samsung_modem_unlocker).enter(basic_success_checks)
    if basic_success_checks:
        info = verinfo(False)
        model = re.search(r'Model:\s*(\S+)', info)
        tthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), model, "REBOOT_DOWNLOAD_SAM", "Fail"))
        tthread.start() # Sends basic, anonymized success_checks info with only the model number.
    print(" OK")

def imeicheck():
    info = verinfo(False)
    imei = nphonekit_core.parse_imei(info)
    if imei:
        messagebox.showinfo("nPhoneKIT", strings['imeiCheckGuide'])
        if os_config in ("WINDOWS", "MACOS"): # macOS opens the browser the same way Windows does; without this the IMEI page never opens on Mac
            webbrowser.open_new_tab(f"https://www.imei.info/services/blacklist-simple/samsung/check-free/?imei={str(imei)}")
        elif os_config == "LINUX":
            url = f"https://www.imei.info/services/blacklist-simple/samsung/check-free/?imei={str(imei)}"
            original_user = os.environ.get("SUDO_USER", "yourusername")  # linux is complicated :/
            cmd = f'su - {original_user} -c "DISPLAY=$DISPLAY DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS xdg-open \\"{url}\\""'
            os.system(cmd)
        print(strings['imeiChecked'])
    else:
        print(strings['imeiNotFound'])

def macos_libusb_present(): # Check whether libusb is installed so mtkclient can actually reach USB devices on macOS
    import ctypes.util
    if ctypes.util.find_library("usb-1.0") or ctypes.util.find_library("usb"):
        return True
    # find_library doesn't always search Homebrew's prefixes, so check the common install locations directly
    candidates = [
        "/opt/homebrew/lib/libusb-1.0.dylib",  # Apple Silicon Homebrew
        "/usr/local/lib/libusb-1.0.dylib",     # Intel Homebrew
        "/opt/local/lib/libusb-1.0.dylib",     # MacPorts
    ]
    return any(os.path.exists(p) for p in candidates)

def mtkclient():
    runner = MtkClientRunner(os_config, sys.executable, macos_libusb_present)
    if not runner.available():
        print(strings['mtkLibusbMissing'])
        show_messagebox_at(500, 200, "nPhoneKIT", strings['mtkLibusbMissing'])
        return
    runner.run()

def tkinput(title="Enter Value", text="Please enter a value:", placeholder="", ok_text="OK", cancel_text="Cancel"):
    app = QtWidgets.QApplication.instance()
    if app is not None:
        if qt_dialog_helper is None:
            init_qt_dialog_helper()
        if app.thread() != QtCore.QThread.currentThread():
            done = threading.Event()
            result = {}
            qt_dialog_helper.request_input.emit(title, text, placeholder, ok_text, cancel_text, result, done)
            done.wait()
            return result.get("value")
        value, ok = QtWidgets.QInputDialog.getText(None, title, text, text=placeholder)
        if ok and value != placeholder:
            return value
        return None

    result = {"value": None}

    def on_submit():
        val = entry.get()
        if val != placeholder:
            result["value"] = val
        popup.quit()

    def on_cancel():
        popup.quit()

    popup = tk.Tk()
    popup.title(title)
    popup.geometry("300x150")
    popup.resizable(False, False)

    label = tk.Label(popup, text=text)
    label.pack(pady=(15, 5))

    entry = tk.Entry(popup, width=30)
    entry.insert(0, placeholder)
    entry.pack(pady=5)
    entry.focus()
    entry.config(fg='grey')

    def on_focus_in(event):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg='black')

    def on_focus_out(event):
        if entry.get() == "":
            entry.insert(0, placeholder)
            entry.config(fg='grey')

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

    button_frame = tk.Frame(popup)
    button_frame.pack(pady=10)

    tk.Button(button_frame, text=ok_text, command=on_submit, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text=cancel_text, command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)

    popup.protocol("WM_DELETE_WINDOW", on_cancel)
    popup.mainloop()
    popup.destroy()

    return result["value"]

def featureRequest():
    featureDesc = tkinput(
        title="nPhoneKIT",
        text="Feature Request:",
        placeholder="detailed feature description...",
        ok_text="Submit",
        cancel_text="Cancel"
    )

    if featureDesc is not None:
        print("Submitting request: ", featureDesc)
    else:
        print("Canceled.")

    submitted = FeedbackClient(FIREBASE_URL).feature_request(
        featureDesc, get_public_hardware_uuid(), VERSION
    )
    status = (
        "Feature request submitted successfully!  OK"
        if submitted else
        "Error: Feature request failed to send. Check your connection?  FAIL"
    )
    print(status)

def bugReport():
    bugDesc = tkinput(
        title="nPhoneKIT",
        text="Bug Report:",
        placeholder="detailed bug description...",
        ok_text="Submit",
        cancel_text="Cancel"
    )

    if bugDesc is not None:
        print("Submitting request: ", bugDesc)
    else:
        print("Canceled.")

    submitted = FeedbackClient(FIREBASE_URL).bug_report(
        bugDesc, get_public_hardware_uuid(), VERSION
    )
    status = (
        "Bug report submitted successfully!  OK"
        if submitted else
        "Error: Bug report failed to send. Check your connection?  FAIL"
    )
    print(status)

def setFakeBatteryPercent():
    percent = tkinput(
        title="nPhoneKIT",
        text="Fake Battery Percent:",
        placeholder="e.g: 101",
        ok_text="Submit",
        cancel_text="Cancel"
    )
    adbMenu()
    print(f"Setting percentage to {percent}%...", end="")
    output = BatteryLevelClient(ADB, readOutput).set_level(percent)
    if BatteryLevelClient.unauthorized(output):
        print("  FAIL (You need to authorize the device via the USB Debugging prompt. Unplugging and replugging the device may help with this.)")
    else:
        print("  OK  (Restarting your phone should undo this.)")

def resetBatteryPercent():
    adbMenu()
    print("Resetting percentage...", end="")
    output = BatteryLevelClient(ADB, readOutput).reset()
    if BatteryLevelClient.unauthorized(output):
        print("  FAIL (You need to authorize the device via the USB Debugging prompt. Unplugging and replugging the device may help with this.)")
    else:
        print("  OK  (Restarting your phone should undo this.)")

# ===================================
#  PyQt5 GUI Stuff
# ===================================

# ------------ theme & assets helpers ------------
ACCENT = "#7C4DFF"        # deep purple accent (material-ish)
ACCENT_HOVER = "#5E35B1"
SURFACE = "#121212"
SURFACE_2 = "#1E1E1E"
TEXT = "#EAEAEA"
TEXT_DIM = "#B9B9B9"
OK_COLOR = "#35D07F"
FAIL_COLOR = "#FF6B6B"

def _find_logo():
    for p in ("assets/logo.png", "logo.png", "./assets/logo.png", "./logo.png"):
        if os.path.exists(p):
            return p
    return None

def _material_qss(dark=True, hacker=False):
    #base_font = "JetBrains Mono" if hacker else "Inter, 'Segoe UI', Roboto, Helvetica, Arial"
    base_font = "'Fira Sans', 'JetBrains Mono', 'Segoe UI', 'Ubuntu', sans-serif"
    mono_font = "JetBrains Mono" if hacker else "Fira Code, Consolas, 'Courier New'"
    if dark:
        return f"""
        * {{
            font-family: {base_font};
            color: {TEXT};
        }}
        QMainWindow {{
            background: {SURFACE};
        }}
        QToolTip {{
            background: #FFD54F;            /* warm yellow */
            color: #111111;                 /* readable text */
            border: 1px solid #E6B800;      /* subtle darker yellow border */
            padding: 6px 10px;
            border-radius: 8px;
            font-weight: 600;
            font-family: "Noto Color Emoji", Inter, 'Segoe UI', Roboto, Helvetica, Arial;
        }}
        QPushButton {{
            background: {SURFACE_2};
            border: 1px solid #2A2A2A;
            padding: 10px 14px;
            border-radius: 10px;
        }}
        QPushButton:hover {{ background: #262626; border-color: #333; }}
        QPushButton:pressed {{ background: {ACCENT}; color: white; }}
        QTabWidget::pane {{
            border: 1px solid #2A2A2A; border-radius: 12px; background: {SURFACE_2};
        }}
        QTabBar::tab {{
            background: transparent; color: {TEXT_DIM};
            padding: 10px 18px; margin: 6px; border-radius: 10px;
        }}
        QTabBar::tab:hover {{ background: #262626; color: {TEXT}; }}
        QTabBar::tab:selected {{ background: {ACCENT}; color: white; }}
        QFrame#Header {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_HOVER});
            border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
        }}
        QLabel#AppTitle {{ color: white; font-size: 22px; font-weight: 700; }}
        QPlainTextEdit, QTextEdit {{
            background: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 12px; padding: 10px;
            font-family: {mono_font}; font-size: 13px;
        }}
        QProgressBar {{
            border: 1px solid #2A2A2A; border-radius: 8px;
            background: #0E0E0E; text-align: center; color: {TEXT_DIM};
        }}
        QProgressBar::chunk {{ background: {ACCENT}; border-radius: 8px; }}
        QCheckBox::indicator {{
            width: 36px; height: 20px; border-radius: 10px; background: #2A2A2A;
        }}
        QCheckBox::indicator:checked {{ background: {ACCENT}; }}
        QCheckBox::indicator::handle {{
            width: 16px; height: 16px; margin: 2px; border-radius: 8px; background: #B0B0B0;
        }}
        QSplitter::handle {{ background: #1A1A1A; width: 6px; }}
        QPushButton {{
            font-family: 'Fira Sans', 'Segoe UI', 'Ubuntu', 'Inter', 'Noto Color Emoji', sans-serif;
            font-size: 13.5px;
            font-weight: 600;
            padding: 6px 10px;
            min-height: 36px;
            border-radius: 8px;
        }}
        """
    else:
        # light mode (kept simple)
        return f"""
        * {{ color: #1A1A1A; font-family: {base_font}; }}
        QMainWindow {{ background: #FAFAFA; }}
        QToolTip {{
            background: #FFEB3B;            /* bright yellow for light theme */
            color: #111111;
            border: 1px solid #E6B800;
            padding: 6px 10px;
            border-radius: 8px;
            font-weight: 600;
            font-family: "Noto Color Emoji", Inter, 'Segoe UI', Roboto, Helvetica, Arial;
        }}
        QPushButton {{
            background: #FFFFFF; border: 1px solid #E0E0E0; padding: 10px 14px; border-radius: 10px;
        }}
        QPushButton:hover {{ background: #F2F2F2; }}
        QPushButton:pressed {{ background: {ACCENT}; color: white; }}
        QTabWidget::pane {{ border: 1px solid #E0E0E0; border-radius: 12px; background: #FFFFFF; }}
        QTabBar::tab {{
            background: transparent; color: #666;
            padding: 10px 18px; margin: 6px; border-radius: 10px;
        }}
        QTabBar::tab:hover {{ background: #F2F2F2; color: #222; }}
        QTabBar::tab:selected {{ background: {ACCENT}; color: white; }}
        QFrame#Header {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_HOVER});
        }}
        QLabel#AppTitle {{ color: white; font-size: 22px; font-weight: 700; }}
        QPlainTextEdit, QTextEdit {{
            background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; padding: 10px;
            font-family: {mono_font}; font-size: 13px; color: #222;
        }}
        QProgressBar {{
            border: 1px solid #E0E0E0; border-radius: 8px; background: #FFF; text-align: center; color: #555;
        }}
        QProgressBar::chunk {{ background: {ACCENT}; border-radius: 8px; }}
        QCheckBox::indicator {{
            width: 36px; height: 20px; border-radius: 10px; background: #DDD;
        }}
        QCheckBox::indicator:checked {{ background: {ACCENT}; }}
        QCheckBox::indicator::handle {{
            width: 16px; height: 16px; margin: 2px; border-radius: 8px; background: #FFF;
        }}
        QSplitter::handle {{ background: #EEE; width: 6px; }}
        QPushButton {{
            font-family: "Noto Color Emoji";
        }}
        """


current_brand = strings.get('brandCurrent', 'Samsung')

def build_ui_actions():
    return {
        "frp_unlock_android15_16": frp_unlock_android15_16,
        "frp_unlock_2024": frp_unlock_2024,
        "frp_unlock_2022": frp_unlock_aug2022_to_dec2022,
        "frp_unlock_pre_2022": frp_unlock_pre_aug2022,
        "verinfo": verinfo,
        "reboot_sam": reboot_sam,
        "reboot_download_sam": reboot_download_sam,
        "wifitest": wifitest,
        "imeicheck": imeicheck,
        "bloat_remove": bloatRemove,
        "lg_screen_unlock": LG_screen_unlock,
        "moto_fastboot_frp": MotoFastbootFRP1,
        "mtkclient": mtkclient,
        "reboot": reboot,
        "set_fake_battery": setFakeBatteryPercent,
        "reset_fake_battery": resetBatteryPercent,
        "feature_request": featureRequest,
        "bug_report": bugReport,
    }

def select_brand(name):
    global current_brand
    current_brand = name
    if UiMainWindow.instance:
        UiMainWindow.instance.set_brand(name)

def set_brand(name):
    select_brand(name)

# ------------- entry point -------------
def init_qt_dialog_helper():
    global qt_dialog_helper
    if qt_dialog_helper is None:
        qt_dialog_helper = QtDialogHelper()


def main():
    app = QtWidgets.QApplication(sys.argv)
    init_qt_dialog_helper()
    # apply tooltip palette for visibility
    pal = app.palette()
    pal.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(42,42,42))
    pal.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(240,240,240))
    app.setPalette(pal)
    app.setFont(QFont("Sans Serif"))

    fast_tips = InstantTooltips(delay_ms=1, hide_ms=299000)
    app.installEventFilter(fast_tips)

    services = MainWindowServices(
        strings=strings,
        version=VERSION,
        actions=build_ui_actions(),
        load_settings=load_settings,
        save_settings=save_settings,
        find_logo=_find_logo,
        material_qss=_material_qss,
    )
    win = UiMainWindow(services)
    win.show()
    sys.exit(app.exec_())

# ===================================
#  Preparing to start the app
# ===================================

serman1 = None
preloader = None
samsung_modem_unlocker = None


def disable_preload():
    global enable_preload
    enable_preload = False


def set_preload_error(value):
    global preload_error
    preload_error = value

def run_app():
    """Perform runtime setup and start the GUI.

    Importing this module defines the application API only. Settings
    persistence, permission checks, serial connections, update checks, and
    background threads belong to the executable entrypoint and therefore
    happen only when the app is launched.
    """
    global serman, serman1, preloader, samsung_modem_unlocker

    persist_settings()

    if os_config == "LINUX":
        if not check_serial_permissions(os_config, show_serial_permission_fix):
            return
    elif os_config == "WINDOWS" and not is_root(os_config) and not DEBUGMODE:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("nPhoneKIT", strings['sudoReqdError'])
        sys.exit(1)

    if update_check:
        check_for_update()

    runtime = initialize_runtime(
        os_config=os_config,
        strings=strings,
        debug_info=debug_info,
        adb=ADB,
        at=AT,
        rt=rt,
        serial_manager=SerialManager,
        serial_manager_windows=SerialManagerWindows,
        modem_unlocker=SamsungModemUnlocker,
        preloader_factory=SamsungPreloader,
        enable_preload=lambda: enable_preload,
        preload_error=lambda: preload_error,
        preload_done=preload_done,
        disable_preload=disable_preload,
        set_preload_error=set_preload_error,
        set_brand=set_brand,
    )
    serman = runtime.serman
    serman1 = runtime.serman1
    preloader = runtime.preloader
    samsung_modem_unlocker = runtime.samsung_modem_unlocker

    ttthread = threading.Thread(target = success_checks, args = (get_public_hardware_uuid(), "NOT_First", "NOT_First", "Success", False))
    ttthread.start() # Sends basic, anonymized success_checks info with only the model number.
    rt() # Flush the buffer from previous runs of nPhoneKIT just in case
    main() # Start the main GUI (with a cool animation)


if __name__ == "__main__":
    run_app()
