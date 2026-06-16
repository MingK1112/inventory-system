from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QPushButton,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from database import Database


class HomePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()
        self._value_labels = {}
        self._build()

    def _make_card(self, icon, label, key):
        card = QPushButton()
        card.setObjectName('HomeCard')
        card.setMinimumSize(280, 150)
        card.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        icon_lbl = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(36)
        icon_lbl.setFont(icon_font)
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(icon_lbl)

        val_lbl = QLabel('—')
        val_font = QFont()
        val_font.setPointSize(32)
        val_font.setBold(True)
        val_lbl.setFont(val_font)
        val_lbl.setObjectName('HomeCardValue')
        val_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(val_lbl)

        name_lbl = QLabel(label)
        name_font = QFont()
        name_font.setPointSize(13)
        name_lbl.setFont(name_font)
        name_lbl.setObjectName('MutedLabel')
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(name_lbl)

        if key == 'warning_count':
            card.clicked.connect(self._on_warning_clicked)
        elif key == 'total_batches':
            card.clicked.connect(lambda: self.main_window.switch_page(1))
        elif key == 'category_count':
            card.clicked.connect(lambda: self.main_window.switch_page(4))

        self._value_labels[key] = val_lbl
        return card

    def _on_warning_clicked(self):
        self.main_window.switch_page(5)
        self.main_window.pages['statistics'].show_warnings()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 30, 32, 30)
        root.setSpacing(28)

        title = QLabel('德隆石化仓储系统')
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        subtitle = QLabel('库存管理概览')
        sub_font = QFont()
        sub_font.setPointSize(13)
        subtitle.setFont(sub_font)
        subtitle.setObjectName('MutedLabel')
        root.addWidget(subtitle)

        root.addSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(20)

        cards = [
            ('📦', '总批次数', 'total_batches'),
            ('✅', '在库数量', 'in_stock'),
            ('📤', '已出库数量', 'out_stock'),
            ('⚖️', '总库存重量 (kg)', 'total_weight'),
            ('⚠️', '预警品种', 'warning_count'),
            ('🏷️', '油品种类', 'category_count'),
        ]

        for idx, (icon, label, key) in enumerate(cards):
            card = self._make_card(icon, label, key)
            row, col = divmod(idx, 3)
            grid.addWidget(card, row, col)

        root.addLayout(grid)
        root.addSpacing(16)

        action_label = QLabel('快捷入口')
        action_font = QFont()
        action_font.setPointSize(13)
        action_font.setBold(True)
        action_label.setFont(action_font)
        root.addWidget(action_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        quick_pages = [
            ('📥 入库登记', 1),
            ('📤 出库登记', 2),
            ('📜 出入库查询', 3),
            ('📊 库存统计', 5),
        ]
        for text, page_idx in quick_pages:
            btn = QPushButton(text)
            btn.setObjectName('HomeQuickBtn')
            btn.setCursor(Qt.PointingHandCursor)
            btn_font = QFont()
            btn_font.setPointSize(14)
            btn.setFont(btn_font)
            btn.setMinimumHeight(44)
            btn.clicked.connect(lambda checked, i=page_idx: self.main_window.switch_page(i))
            btn_row.addWidget(btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addStretch()
        self.refresh()

    def refresh(self):
        containers = self.db.get_all_containers()
        total = len(containers)
        in_stock = sum(1 for c in containers if c['状态'] == '在库')
        out_stock = total - in_stock
        total_w = sum((c['重量'] or 0) for c in containers)
        warning = sum(1 for r in self.db.get_stat_summary() if (r[4] or 0) < r[6])
        categories = len(set(c['类别'] for c in containers if c['类别']))

        values = {
            'total_batches': str(total),
            'in_stock': str(in_stock),
            'out_stock': str(out_stock),
            'total_weight': f'{total_w:,.2f}',
            'warning_count': str(warning),
            'category_count': str(categories),
        }
        for key, lbl in self._value_labels.items():
            lbl.setText(values.get(key, '—'))
