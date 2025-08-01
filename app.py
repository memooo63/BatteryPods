import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QWidget,
    QVBoxLayout,
)

SETTINGS_FILE = Path.home() / ".battery_pods_settings.json"
DEFAULT_SETTINGS = {"theme": "dark", "autostart": False}


def load_settings() -> Dict:
    """Load persisted settings or return defaults."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {**DEFAULT_SETTINGS, **data}
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict) -> None:
    """Persist settings to JSON file."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
    except Exception as exc:
        print(f"Failed to save settings: {exc}")


def set_autostart(enabled: bool) -> None:
    """Register/unregister autostart on Windows using the registry."""
    if not sys.platform.startswith("win"):
        return
    try:
        import winreg  # type: ignore

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        if enabled:
            exe_path = os.path.abspath(sys.argv[0])
            winreg.SetValueEx(key, "BatteryPods", 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, "BatteryPods")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as exc:  # pragma: no cover - platform dependent
        print(f"Autostart configuration failed: {exc}")


def _create_icon(kind: str) -> QPixmap:
    """Create a simple placeholder icon for a given AirPods component."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(Qt.black)
    if kind == "left":
        painter.drawRoundedRect(8, 4, 12, 24, 4, 4)
        painter.drawEllipse(6, 10, 6, 12)
    elif kind == "right":
        painter.drawRoundedRect(12, 4, 12, 24, 4, 4)
        painter.drawEllipse(20, 10, 6, 12)
    else:  # case
        painter.drawRoundedRect(4, 4, 24, 24, 6, 6)
    painter.end()
    return pix


class BatteryWorker(QThread):
    """Background thread polling AirPods battery status via Bluetooth."""

    data_ready = Signal(dict)

    async def _get_battery(self) -> Dict[str, Optional[int]]:
        from bleak import BleakScanner

        devices = await BleakScanner.discover(timeout=5.0)
        for device in devices:
            name = device.name or ""
            if "AirPods" in name:
                md = device.metadata.get("manufacturer_data", {})
                data = md.get(76)  # Apple vendor ID
                if data and len(data) >= 10:
                    left = data[7]
                    right = data[8]
                    case = data[9]
                    return {
                        "left": None if left in (0, 255) else int(left),
                        "right": None if right in (0, 255) else int(right),
                        "case": None if case in (0, 255) else int(case),
                    }
        return {}

    def run(self) -> None:  # pragma: no cover - involves asyncio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while not self.isInterruptionRequested():
            try:
                data = loop.run_until_complete(self._get_battery())
                self.data_ready.emit(data)
            except Exception as exc:
                print(f"Battery scan failed: {exc}")
                self.data_ready.emit({})
            for _ in range(30):
                if self.isInterruptionRequested():
                    break
                self.msleep(1000)


class MainWindow(QMainWindow):
    """Minimalistic GUI showing AirPods battery status."""

    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self._build_ui()
        self.apply_theme(self.settings["theme"])

        self.worker = BatteryWorker()
        self.worker.data_ready.connect(self.update_battery)
        self.worker.start()

    def _build_ui(self) -> None:
        self.setWindowTitle("BatteryPods")
        self.setWindowIcon(QIcon.fromTheme("battery"))

        central = QWidget(self)
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        battery_layout = QHBoxLayout()
        self._battery_labels: Dict[str, QLabel] = {}
        for part in ("left", "right", "case"):
            col = QVBoxLayout()
            icon = QLabel()
            icon.setPixmap(_create_icon(part))
            icon.setAlignment(Qt.AlignCenter)
            perc = QLabel("–")
            perc.setAlignment(Qt.AlignCenter)
            col.addWidget(icon)
            col.addWidget(perc)
            battery_layout.addLayout(col)
            self._battery_labels[part] = perc
        layout.addLayout(battery_layout)

        self.theme_box = QCheckBox("Dark Mode")
        self.theme_box.setChecked(self.settings.get("theme") == "dark")
        self.theme_box.toggled.connect(self.on_theme_toggle)
        layout.addWidget(self.theme_box, alignment=Qt.AlignCenter)

        self.autostart_box = QCheckBox("Autostart mit Windows")
        self.autostart_box.setChecked(self.settings.get("autostart", False))
        self.autostart_box.toggled.connect(self.on_autostart_toggle)
        layout.addWidget(self.autostart_box, alignment=Qt.AlignCenter)

        layout.addStretch()
        self.resize(300, 200)

    def on_theme_toggle(self, checked: bool) -> None:
        theme = "dark" if checked else "light"
        self.apply_theme(theme)
        self.settings["theme"] = theme
        save_settings(self.settings)

    def on_autostart_toggle(self, checked: bool) -> None:
        set_autostart(checked)
        self.settings["autostart"] = checked
        save_settings(self.settings)

    def apply_theme(self, theme: str) -> None:
        app = QApplication.instance()
        assert app is not None
        if theme == "dark":
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(35, 35, 35))
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.Highlight, QColor(142, 45, 197))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            app.setPalette(palette)
        else:
            app.setPalette(app.style().standardPalette())

    def update_battery(self, data: Dict[str, Optional[int]]) -> None:
        if not data:
            for lbl in self._battery_labels.values():
                lbl.setText("–")
            return
        for part, lbl in self._battery_labels.items():
            val = data.get(part)
            lbl.setText(f"{val}%" if val is not None else "–")

    def closeEvent(self, event) -> None:  # pragma: no cover - GUI callback
        self.worker.requestInterruption()
        self.worker.wait(2000)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
