"""Legacy Tk workflow confirmation dialog."""

import math
import multiprocessing
import threading
from datetime import datetime, timedelta
from typing import Tuple


def _stw_worker(conn, title, desc, pros, cons, minutes, execute_text, cancel_text, win_w, win_h):
    import tkinter as tk
    from tkinter import font, ttk

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
    import tkinter as tk
    from tkinter import font, ttk

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

# Check for updates
