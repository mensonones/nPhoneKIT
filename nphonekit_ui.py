"""Reusable PyQt5 components used by the nPhoneKIT desktop application."""

import re
import sys
import webbrowser
from dataclasses import dataclass
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets
from nphonekit_core import build_tab_specs


TEXT = "#EAEAEA"
OK_COLOR = "#35D07F"
FAIL_COLOR = "#FF6B6B"


class BusyOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None, text="Working…"):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.SubWindow)
        self._angle = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._label = QtWidgets.QLabel(text, self)
        self._label.setStyleSheet(f"color:{TEXT}; font-size:14px;")
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def start(self):
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._timer.start(16)

    def stop(self):
        self._timer.stop()
        self.hide()

    def resizeEvent(self, event):
        self.setGeometry(self.parent().rect())
        self._label.adjustSize()
        self._label.move(self.width() // 2 - self._label.width() // 2, self.height() // 2 + 26)
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 120))
        radius = 22
        center = QtCore.QPoint(self.width() // 2, self.height() // 2 - 8)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 220), 3))
        painter.setOpacity(0.2)
        painter.drawEllipse(center, radius, radius)
        painter.setOpacity(1.0)
        painter.save()
        painter.translate(center)
        painter.rotate(self._angle)
        rect = QtCore.QRectF(-radius, -radius, radius * 2, radius * 2)
        painter.drawArc(rect, 0, 110 * 16)
        painter.restore()


class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)


class Worker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @QtCore.pyqtSlot()
    def run(self):
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as error:
            self.signals.error.emit(str(error))
        finally:
            self.signals.finished.emit()


class QtDialogHelper(QtCore.QObject):
    request_message = QtCore.pyqtSignal(object, object, object, object, object, object)
    request_input = QtCore.pyqtSignal(object, object, object, object, object, object, object)
    request_contribution = QtCore.pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self.request_message.connect(self._show_message)
        self.request_input.connect(self._show_input)
        self.request_contribution.connect(self._show_contribution)

    def _show_message(self, x, y, title, content, result, done):
        message = QtWidgets.QMessageBox()
        message.setWindowTitle(title)
        message.setText(content)
        message.setStandardButtons(QtWidgets.QMessageBox.Ok)
        message.exec_()
        result["value"] = True
        done.set()

    def _show_input(self, title, text, placeholder, ok_text, cancel_text, result, done):
        value, ok = QtWidgets.QInputDialog.getText(None, title, text, text=placeholder)
        result["value"] = value if ok and value != placeholder else None
        done.set()

    def _show_contribution(self, uuid_str, done):
        try:
            message = QtWidgets.QMessageBox()
            message.setWindowTitle("Support nPhoneKIT")
            message.setText(
                "Want to help support nPhoneKIT, and get a special Contributor thank you "
                "message on the README? Please fill out the quick form below.\n\n"
                "You can (and should!) submit it whether the unlock worked flawlessly or "
                "failed — it helps fix bugs for the future.\n\n"
                f"Your unique submission code (prevents spam):\n{uuid_str}\n\n"
                "Turn off 'Contribution Messages' in settings to hide this."
            )
            open_button = message.addButton("Open Form", QtWidgets.QMessageBox.AcceptRole)
            message.addButton("Close", QtWidgets.QMessageBox.RejectRole)
            message.exec_()
            if message.clickedButton() == open_button:
                clipboard = QtWidgets.QApplication.clipboard()
                if clipboard is not None:
                    clipboard.setText(uuid_str)
                webbrowser.open("https://forms.gle/SM8Mjyoz43Jcwxzn8")
        finally:
            done.set()


class QtRedirectText(QtCore.QObject):
    new_text = QtCore.pyqtSignal(str)

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.pattern = re.compile(r"( FAIL| OK)")
        self.new_text.connect(self._append)

    def write(self, text):
        self.new_text.emit(text)

    def flush(self):
        pass

    def _append(self, text):
        parts = []
        last = 0
        for match in self.pattern.finditer(text):
            parts.append(text[last:match.start()])
            token = match.group(1).strip()
            color = OK_COLOR if token == "OK" else FAIL_COLOR
            parts.append(f'<span style="color:{color}; font-weight:700;"> {token}</span>')
            last = match.end()
        parts.append(text[last:])
        html = "".join(parts).replace("\n", "<br>")
        self.widget.moveCursor(QtGui.QTextCursor.End)
        self.widget.insertHtml(html)
        self.widget.moveCursor(QtGui.QTextCursor.End)


class InstantTooltips(QtCore.QObject):
    """Global tooltip accelerator with configurable delay and auto-hide."""

    def __init__(self, delay_ms=100, hide_ms=0, parent=None):
        super().__init__(parent)
        self.delay_ms = max(0, int(delay_ms))
        self.hide_ms = int(hide_ms)
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._show_pending)
        self._pending = None

    def eventFilter(self, obj, event):
        event_type = event.type()
        if event_type == QtCore.QEvent.ToolTip:
            text = obj.toolTip() if hasattr(obj, "toolTip") else ""
            if not text:
                QtWidgets.QToolTip.hideText()
                return True
            position = obj.mapToGlobal(event.pos())
            if self.delay_ms == 0:
                QtWidgets.QToolTip.showText(position, text, obj)
                if self.hide_ms > 0:
                    QtCore.QTimer.singleShot(self.hide_ms, QtWidgets.QToolTip.hideText)
            else:
                self._pending = (position, obj, text)
                self._timer.stop()
                self._timer.start(self.delay_ms)
            return True
        if event_type in (QtCore.QEvent.Leave, QtCore.QEvent.FocusOut):
            QtWidgets.QToolTip.hideText()
        return False

    def _show_pending(self):
        if not self._pending:
            return
        position, widget, text = self._pending
        self._pending = None
        if widget and widget.isVisible():
            QtWidgets.QToolTip.showText(position, text, widget)
            if self.hide_ms > 0:
                QtCore.QTimer.singleShot(self.hide_ms, QtWidgets.QToolTip.hideText)


class SettingsDialog(QtWidgets.QDialog):
    """Settings editor with application services supplied by the caller."""

    def __init__(self, parent=None, settings=None, strings=None, save_settings=None, find_logo=None):
        super().__init__(parent)
        self.strings = strings or {}
        self._save_settings = save_settings
        self._find_logo = find_logo or (lambda: None)
        self.setWindowTitle(self.strings.get("settingsMenuTitleText", "Settings"))
        self.setModal(True)
        self.resize(520, 380)
        self.settings = dict(settings or {})
        self.setStyleSheet("""
            QDialog { background-color: #000000; }
            QCheckBox { color: white; }
            QCheckBox::indicator {
                width: 18px; height: 18px; border: 2px solid #888;
                border-radius: 4px; background: black;
            }
            QCheckBox::indicator:checked {
                background: #4CAF50; border: 2px solid #4CAF50;
            }
        """)

        main_keys = [
            "dark_theme", "hacker_font", "slower_animations",
            "update_check", "enable_preload", "contributionsuggestions",
        ]
        dev_keys = ["debug_info", "basic_success_checks"]
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._logo_widget())

        grid = QtWidgets.QGridLayout()
        self.boxes = {}
        for index, key in enumerate(main_keys):
            label = "Contribution Suggestions" if key == "contributionsuggestions" else key.replace("_", " ").title()
            checkbox = QtWidgets.QCheckBox(label)
            checkbox.setChecked(bool(self.settings.get(key, False)))
            self.boxes[key] = checkbox
            grid.addWidget(checkbox, index // 2, index % 2)
        layout.addLayout(grid)

        layout.addSpacing(8)
        dev_label = QtWidgets.QLabel(self.strings.get("devSettingsTitle", "Developer Settings"))
        dev_label.setStyleSheet("color:#aaa; font-weight:600; margin-top:6px;")
        layout.addWidget(dev_label)

        dev_grid = QtWidgets.QGridLayout()
        for index, key in enumerate(dev_keys):
            checkbox = QtWidgets.QCheckBox(key.replace("_", " ").title())
            checkbox.setChecked(bool(self.settings.get(key, False)))
            self.boxes[key] = checkbox
            dev_grid.addWidget(checkbox, index // 2, index % 2)
        layout.addLayout(dev_grid)

        layout.addStretch(1)
        buttons = QtWidgets.QHBoxLayout()
        cancel_button = QtWidgets.QPushButton("Cancel")
        apply_button = QtWidgets.QPushButton(self.strings.get("applyText", "Apply"))
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(apply_button)
        layout.addLayout(buttons)
        cancel_button.clicked.connect(self.reject)
        apply_button.clicked.connect(self._apply)

    def _apply(self):
        for key, checkbox in self.boxes.items():
            self.settings[key] = bool(checkbox.isChecked())
        if self._save_settings is not None:
            self._save_settings(self.settings)
        self.accept()

    def _logo_widget(self):
        widget = QtWidgets.QFrame()
        layout = QtWidgets.QHBoxLayout(widget)
        picture = QtWidgets.QLabel()
        picture.setFixedSize(40, 40)
        path = self._find_logo()
        if path:
            pixmap = QtGui.QPixmap(path).scaled(
                40, 40, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            picture.setPixmap(pixmap)
        else:
            pixmap = QtGui.QPixmap(40, 40)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            gradient = QtGui.QLinearGradient(0, 0, 40, 40)
            gradient.setColorAt(0, QtGui.QColor(124, 77, 255))
            gradient.setColorAt(1, QtGui.QColor(3, 218, 198))
            painter.setBrush(gradient)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(0, 0, 40, 40, 8, 8)
            painter.end()
            picture.setPixmap(pixmap)
        title = QtWidgets.QLabel(self.strings.get("settingsMenuTitleText", "Settings"))
        title.setStyleSheet("font-size:18px; font-weight:700;")
        layout.addWidget(picture)
        layout.addSpacing(10)
        layout.addWidget(title)
        layout.addStretch(1)
        return widget


@dataclass
class MainWindowServices:
    strings: dict
    version: str
    actions: dict
    load_settings: object
    save_settings: object
    find_logo: object
    material_qss: object


class MainWindow(QtWidgets.QMainWindow):
    instance = None

    primary_btn_qss = """
    QPushButton {
        background: #7C4DFF; color: white; border: none; border-radius: 10px;
        font-weight: 700;
        font-family: 'Fira Sans', 'Segoe UI', 'Ubuntu', 'Inter', 'Noto Color Emoji', sans-serif;
    }
    QPushButton:hover { background: #5E35B1; }
    """
    secondary_btn_qss = """
    QPushButton {
        background: #1E1E1E; border: 1px solid #2A2A2A; border-radius: 10px;
        font-family: 'Fira Sans', 'Segoe UI', 'Ubuntu', 'Inter', 'Noto Color Emoji', sans-serif;
    }
    QPushButton:hover { background: #262626; }
    """

    def __init__(self, services):
        super().__init__()
        MainWindow.instance = self
        self.services = services
        self.setWindowTitle("nPhoneKIT")
        self.resize(1550, 860)
        self.pool = QtCore.QThreadPool.globalInstance()
        self._settings = services.load_settings()
        self.apply_theme(self._settings.get("dark_theme", True), self._settings.get("hacker_font", False))

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Horizontal)
        self.setCentralWidget(splitter)
        left = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(left)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QtWidgets.QTabWidget.North)
        layout.addWidget(self.tabs)
        splitter.addWidget(left)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 12, 12)
        right_layout.setSpacing(10)
        right_layout.addWidget(self._build_header())
        self.output = QtWidgets.QTextEdit()
        self.output.setReadOnly(True)
        right_layout.addWidget(self.output, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self._redirector = QtRedirectText(self.output)
        sys.stdout = self._redirector
        sys.stderr = self._redirector
        self.overlay = BusyOverlay(self)
        self._brand_index = {}
        self._build_brand_tabs()
        print(self.services.strings.get("nPhoneKITwelcome", "Welcome to nPhoneKIT").format(version=services.version))
        print(self.services.strings.get("newIn1.3.2", ""))
        self._fade_in()

    def showEvent(self, event):
        super().showEvent(event)
        self.centralWidget().setSizes([1, 1])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.overlay and self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())

    def _build_header(self):
        bar = QtWidgets.QFrame()
        bar.setObjectName("Header")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        logo = QtWidgets.QLabel()
        logo.setFixedSize(36, 36)
        path = self.services.find_logo()
        if path:
            logo.setPixmap(QtGui.QPixmap(path).scaled(36, 36, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            pixmap = QtGui.QPixmap(36, 36)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            gradient = QtGui.QLinearGradient(0, 0, 36, 36)
            gradient.setColorAt(0, QtGui.QColor(124, 77, 255))
            gradient.setColorAt(1, QtGui.QColor(3, 218, 198))
            painter.setBrush(gradient)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(0, 0, 36, 36, 8, 8)
            painter.end()
            logo.setPixmap(pixmap)
        title = QtWidgets.QLabel("nPhoneKIT")
        title.setObjectName("AppTitle")
        subtitle = QtWidgets.QLabel(f"v{self.services.version}")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.85); font-size:13px;")
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(0)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        settings_button = QtWidgets.QPushButton(self.services.strings.get("settingsMenuTitleText", "Settings"))
        settings_button.clicked.connect(self.open_settings)
        layout.addWidget(logo)
        layout.addSpacing(10)
        layout.addLayout(title_box)
        layout.addStretch(1)
        layout.addWidget(settings_button)
        return bar

    def _brand_tab(self, title, actions):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(16)

        def add_section(section_title, items, primary_first=False):
            label = QtWidgets.QLabel(section_title)
            label.setStyleSheet("font-size:30px; font-weight:700; font-family: 'Fira Sans', 'Segoe UI', 'Ubuntu', 'Inter', 'Noto Color Emoji', sans-serif; color:#CFCFCF; margin-left:4px;")
            layout.addWidget(label)
            grid = QtWidgets.QGridLayout()
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(12)
            for index, (text, tooltip, function) in enumerate(items):
                button = QtWidgets.QPushButton(text)
                button.setToolTip(tooltip)
                button.setMinimumHeight(48)
                button.setStyleSheet(self.primary_btn_qss if primary_first and index == 0 else self.secondary_btn_qss)
                button.clicked.connect(partial(self.run_task, function))
                card = QtWidgets.QFrame()
                card.setStyleSheet("""
                    QFrame { background: rgba(255,255,255,0.02); border: 1px solid #2A2A2A; border-radius: 12px; }
                """)
                card_layout = QtWidgets.QVBoxLayout(card)
                card_layout.setContentsMargins(10, 10, 10, 10)
                card_layout.addWidget(button)
                grid.addWidget(card, index // 2, index % 2)
            layout.addLayout(grid)

        if title == "Samsung":
            add_section("FRP Unlock", actions[:4], primary_first=True)
            add_section("Device Tools", actions[4:])
        elif title == "Feedback":
            add_section("Leave Feedback", actions, primary_first=True)
        else:
            add_section("Device Tools", actions)
        layout.addStretch(1)
        return widget

    def _build_brand_tabs(self):
        tab_specs = build_tab_specs(self.services.strings, self.services.actions)
        self.tabs.clear()
        self._brand_index.clear()
        for index, (title, actions) in enumerate(tab_specs):
            self.tabs.addTab(self._brand_tab(title, actions), title)
            self._brand_index[title] = index
        self.set_brand("Samsung")

    def set_brand(self, name):
        index = self._brand_index.get(name)
        if index is not None:
            self.tabs.setCurrentIndex(index)

    def run_task(self, function):
        self.overlay.start()
        worker = Worker(function)
        worker.signals.finished.connect(self.overlay.stop)
        worker.signals.error.connect(lambda error: print(f" FAIL {error}"))
        self.pool.start(worker)

    def open_settings(self):
        dialog = SettingsDialog(
            self,
            settings=self._settings,
            strings=self.services.strings,
            save_settings=self.services.save_settings,
            find_logo=self.services.find_logo,
        )
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._settings = dialog.settings
            self.apply_theme(self._settings.get("dark_theme", True), self._settings.get("hacker_font", False))

    def apply_theme(self, dark, hacker):
        self.setStyleSheet(self.services.material_qss(dark=dark, hacker=hacker))

    def _fade_in(self):
        self.setWindowOpacity(0.0)
        animation = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(400 if not self._settings.get("slower_animations", False) else 900)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
