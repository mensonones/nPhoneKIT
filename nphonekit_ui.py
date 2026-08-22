"""Reusable PyQt5 components used by the nPhoneKIT desktop application."""

import re
import webbrowser

from PyQt5 import QtCore, QtGui, QtWidgets


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
