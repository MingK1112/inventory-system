from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QFrame,
)
from PySide6.QtGui import QShortcut, QKeySequence

from config import APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT
from .sidebar import Sidebar
from .topbar import Topbar
from .home_page import HomePage
from .inventory_page import InventoryPage
from .transaction_page import TransactionPage
from .log_page import LogPage
from .category_page import CategoryPage
from .statistics_page import StatisticsPage
from .settings_page import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self, is_dark=True, font_size=12):
        super().__init__()
        self.is_dark = is_dark
        self.font_size = font_size
        self.edit_locked = True

        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        self.content_frame = QFrame()
        self.content_frame.setObjectName('ContentFrame')
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.topbar = Topbar(self)
        content_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()

        self.pages = {}
        self._create_pages()

        content_layout.addWidget(self.stack)
        root_layout.addWidget(self.content_frame, 1)

        self._connect_sidebar()
        self.sidebar.buttons[0].setChecked(True)

        QShortcut(QKeySequence("Ctrl+Z"), self, self.perform_undo)

    def _create_pages(self):
        page_classes = {
            "home": HomePage,
            "inventory": InventoryPage,
            "transaction": TransactionPage,
            "log": LogPage,
            "category": CategoryPage,
            "statistics": StatisticsPage,
            "settings": SettingsPage,
        }
        for key, cls in page_classes.items():
            page = cls(self)
            self.pages[key] = page
            self.stack.addWidget(page)

    def _connect_sidebar(self):
        nav_keys = [
            "home", "inventory", "transaction",
            "log", "category", "statistics", "settings"
        ]
        for i, key in enumerate(nav_keys):
            self.sidebar.buttons[i].clicked.connect(
                lambda checked, idx=i: self.stack.setCurrentIndex(idx)
            )

    def perform_undo(self):
        current_page = self.stack.currentWidget()
        if hasattr(current_page, 'perform_undo'):
            current_page.perform_undo()

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)

    def toggle_edit_lock(self):
        self.edit_locked = not self.edit_locked
        for page in self.pages.values():
            if hasattr(page, 'set_edit_mode'):
                page.set_edit_mode(self.edit_locked)
