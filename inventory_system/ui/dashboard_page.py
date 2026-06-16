from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from database import Database


class DashboardPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()
        self._build()

    def _build(self):
        if self.layout():
            QWidget().setLayout(self.layout())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 30, 0, 0)
        root.setSpacing(120)

        title = QLabel('仪表盘')
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setContentsMargins(32, 0, 0, 0)
        root.addWidget(title)

        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(8, 0, 8, 0)
        cards_row.setSpacing(0)

        self._value_labels = []
        for label_text in ['总批次数', '总库存 (kg)', '预警品种']:
            wrapper = QHBoxLayout()
            wrapper.setAlignment(Qt.AlignCenter)

            circle = QWidget()
            circle.setObjectName('StatCircle')
            circle.setFixedSize(242, 242)

            inner = QVBoxLayout(circle)
            inner.setAlignment(Qt.AlignCenter)
            inner.setSpacing(9)

            val_lbl = QLabel('—')
            val_font = QFont()
            val_font.setPointSize(44)
            val_font.setBold(True)
            val_lbl.setFont(val_font)
            val_lbl.setObjectName('StatValue')
            val_lbl.setAlignment(Qt.AlignCenter)
            inner.addWidget(val_lbl)

            name_lbl = QLabel(label_text)
            name_font = QFont()
            name_font.setPointSize(16)
            name_lbl.setFont(name_font)
            name_lbl.setObjectName('MutedLabel')
            name_lbl.setAlignment(Qt.AlignCenter)
            inner.addWidget(name_lbl)

            wrapper.addWidget(circle)
            cards_row.addLayout(wrapper, 1)
            self._value_labels.append(val_lbl)

        root.addLayout(cards_row)
        root.addStretch()
        self.refresh()

    def refresh(self):
        containers = self.db.get_all_containers()
        values = [
            str(len(containers)),
            f'{sum((row[10] or 0) for row in containers):.2f}',
            str(sum(1 for row in self.db.get_stat_summary() if (row[4] or 0) < row[6])),
        ]
        for lbl, val in zip(self._value_labels, values):
            lbl.setText(val)
