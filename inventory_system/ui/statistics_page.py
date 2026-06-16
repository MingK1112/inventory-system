from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QDoubleSpinBox, QDialogButtonBox, QMenu,
    QAbstractItemView, QApplication, QSplitter, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from database import Database
from config import CONTAINER_FIELDS


class StatisticsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # title + refresh
        header = QHBoxLayout()
        title = QLabel('库存统计')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton('刷新')
        refresh_btn.setObjectName('ToolBtn')
        refresh_btn.clicked.connect(self.refresh_stat)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        # splitter: summary on top, detail on bottom
        splitter = QSplitter(Qt.Vertical)

        # summary
        self.summary_cols = ['类别', '名称', '规格', '桶数', '总重(kg)', '预警(kg)', '更新日期']
        self.summary_table = QTableWidget()
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setColumnCount(len(self.summary_cols))
        self.summary_table.setHorizontalHeaderLabels(self.summary_cols)
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.summary_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.summary_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.summary_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.summary_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.summary_table.customContextMenuRequested.connect(self._summary_menu)
        self.summary_table.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self.summary_table)

        # detail
        self.detail_cols = CONTAINER_FIELDS
        self.detail_table = QTableWidget()
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setColumnCount(len(self.detail_cols))
        self.detail_table.setHorizontalHeaderLabels(self.detail_cols)
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.detail_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.detail_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.detail_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.detail_table)

        root.addWidget(splitter, 1)

        self.refresh_stat()

    def refresh_stat(self):
        rows = self.db.get_stat_summary()
        self.summary_table.setUpdatesEnabled(False)
        self.summary_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            cat, name, spec, count, total_w, last_date, thresh = row
            total_w = total_w or 0.0
            values = [cat, name, spec, str(count), f"{total_w:.2f}", f"{thresh:.2f}", str(last_date or '')]
            for c, val in enumerate(values):
                item = QTableWidgetItem(val)
                if total_w < thresh:
                    item.setBackground(QBrush(QColor('#FFD6D6')))
                    item.setForeground(QBrush(QColor('#CC0000')))
                self.summary_table.setItem(r, c, item)
        self.summary_table.setUpdatesEnabled(True)
        self.detail_table.setRowCount(0)

    def _on_select(self):
        rows = self.summary_table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        cat = self.summary_table.item(r, 0).text()
        name = self.summary_table.item(r, 1).text()
        spec = self.summary_table.item(r, 2).text()
        details = self.db.get_stat_detail(cat, name, spec)
        self.detail_table.setRowCount(len(details))
        for dr, row in enumerate(details):
            for dc, val in enumerate(row):
                self.detail_table.setItem(dr, dc, QTableWidgetItem(str(val) if val is not None else ''))

    def _summary_menu(self, pos):
        r = self.summary_table.currentRow()
        if r < 0:
            return
        cat = self.summary_table.item(r, 0).text()
        name = self.summary_table.item(r, 1).text()
        spec = self.summary_table.item(r, 2).text()
        current = float(self.summary_table.item(r, 5).text())
        menu = QMenu(self)
        menu.addAction('修改预警值', lambda: self._edit_threshold(cat, name, spec, current))
        menu.exec(self.summary_table.viewport().mapToGlobal(pos))

    def _edit_threshold(self, cat, name, spec, current):
        dlg = QDialog(self)
        dlg.setWindowTitle(f'预警值 - {cat}/{name}/{spec}')
        dlg.resize(320, 140)
        layout = QVBoxLayout(dlg)
        lbl = QLabel('库存预警阈值 (kg):')
        lbl.setObjectName('MutedLabel')
        layout.addWidget(lbl)
        spin = QDoubleSpinBox()
        spin.setRange(0, 999999)
        spin.setValue(current)
        spin.setDecimals(2)
        layout.addWidget(spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._save_threshold(cat, name, spec, spin.value(), dlg))
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.exec()

    def _save_threshold(self, cat, name, spec, val, dlg):
        try:
            self.db.set_threshold(cat, name, spec, val)
            self.refresh_stat()
            dlg.accept()
            QMessageBox.information(self, '成功', '预警值已更新')
        except Exception as e:
            QMessageBox.critical(dlg, '错误', str(e))

    def show_warnings(self):
        """Auto-select and scroll to the first warning row."""
        self.refresh_stat()
        for r in range(self.summary_table.rowCount()):
            item = self.summary_table.item(r, 0)
            if item and item.background().color() == QColor('#FFD6D6'):
                self.summary_table.selectRow(r)
                self.summary_table.scrollToItem(item)
                self._on_select()
                break

    def set_edit_mode(self, locked):
        trigger = QAbstractItemView.EditTrigger.NoEditTriggers if locked else QAbstractItemView.EditTrigger.DoubleClicked
        self.summary_table.setEditTriggers(trigger)
        self.detail_table.setEditTriggers(trigger)
