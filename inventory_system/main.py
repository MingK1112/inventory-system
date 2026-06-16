import sys
import os
import platform
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.main_window import MainWindow
from config import load_config, RESOURCE_DIR


def get_system_font():
    system = platform.system()
    if system == "Darwin":
        return ["PingFang SC", "Helvetica Neue"]
    elif system == "Windows":
        return ["Microsoft YaHei", "Segoe UI"]
    else:
        return ["Noto Sans CJK SC", "DejaVu Sans"]


def apply_font(app, size):
    font = QFont()
    font.setFamilies(get_system_font())
    font.setPointSize(size)
    app.setFont(font)


def load_stylesheet(app, is_dark=True):
    filename = os.path.join(RESOURCE_DIR, 'styles.qss' if is_dark else 'styles_light.qss')
    with open(filename, 'r', encoding='utf-8') as f:
        app.setStyleSheet(f.read())


if __name__ == '__main__':
    app = QApplication(sys.argv)

    cfg = load_config()
    font_size = cfg.get("font_size", 13)
    is_dark = cfg.get("dark_mode", True)

    load_stylesheet(app, is_dark)
    apply_font(app, font_size)

    window = MainWindow(is_dark, font_size)
    window.show()

    sys.exit(app.exec())
