"""Reusable presentation helpers for the Qt interface."""

import os


def find_logo(exists=os.path.exists):
    """Return the first available application logo path."""
    for path in ("assets/logo.png", "logo.png", "./assets/logo.png", "./logo.png"):
        if exists(path):
            return path
    return None

ACCENT = "#7C4DFF"        # deep purple accent (material-ish)
ACCENT_HOVER = "#5E35B1"
SURFACE = "#121212"
SURFACE_2 = "#1E1E1E"
TEXT = "#EAEAEA"
TEXT_DIM = "#B9B9B9"
OK_COLOR = "#35D07F"
FAIL_COLOR = "#FF6B6B"

def material_qss(dark=True, hacker=False):
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
