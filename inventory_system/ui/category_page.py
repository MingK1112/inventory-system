from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QMenu,
    QAbstractItemView, QApplication,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont

from database import Database
from config import CONTAINER_FIELDS


class CategoryPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # title + search
        header = QHBoxLayout()
        title = QLabel('类别明细')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()

        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText('批号/位置/类别/名称/规格...')
        self.cat_input.setFixedWidth(260)
        header.addWidget(self.cat_input)

        search_btn = QPushButton('查询')
        search_btn.setObjectName('ToolBtn')
        search_btn.clicked.connect(self.query)
        header.addWidget(search_btn)
        root.addLayout(header)

        # table
        self.cols = CONTAINER_FIELDS
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(len(self.cols))
        self.table.setHorizontalHeaderLabels(self.cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_menu)
        root.addWidget(self.table, 1)

    def query(self):
        kw = self.cat_input.text().strip()
        rows = self.db.search_by_category(kw)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(val) if val is not None else ''))
        self.table.setUpdatesEnabled(True)

    def _show_menu(self, pos):
        row = self.table.currentRow()
        if row < 0:
            return
        batch = self.table.item(row, 0).text()
        menu = QMenu(self)
        menu.addAction('复制批号', lambda: QApplication.clipboard().setText(batch))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def set_edit_mode(self, locked):
        trigger = QAbstractItemView.EditTrigger.NoEditTriggers if locked else QAbstractItemView.EditTrigger.DoubleClicked
        self.table.setEditTriggers(trigger)
