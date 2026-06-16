from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QButtonGroup
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve


class Sidebar(QWidget):
    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 60

    def __init__(self):
        super().__init__()
        self.setObjectName('Sidebar')
        self._expanded = True
        self.setFixedWidth(self.EXPANDED_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(2)

        # ---- top: logo + toggle button ----
        self.toggle_row = QHBoxLayout()
        self.toggle_row.setContentsMargins(12, 6, 0, 0)

        self.logo_widget = QWidget()
        logo_layout = QVBoxLayout(self.logo_widget)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(0)

        self.logo_main = QLabel('德隆石化')
        logo_main_font = QFont()
        logo_main_font.setPointSize(16)
        logo_main_font.setBold(True)
        self.logo_main.setFont(logo_main_font)
        self.logo_main.setObjectName('SidebarBrand')
        logo_layout.addWidget(self.logo_main)

        self.logo_sub = QLabel('仓储系统')
        logo_sub_font = QFont()
        logo_sub_font.setPointSize(10)
        self.logo_sub.setFont(logo_sub_font)
        self.logo_sub.setObjectName('MutedLabel')
        logo_layout.addWidget(self.logo_sub)

        self.toggle_row.addWidget(self.logo_widget)
        self.toggle_row.addStretch()

        self.toggle_btn = QPushButton('☰')
        self.toggle_btn.setObjectName('SidebarToggle')
        self.toggle_btn.setFixedSize(48, 40)
        toggle_font = QFont()
        toggle_font.setPointSize(30)
        toggle_font.setStretch(120)
        self.toggle_btn.setFont(toggle_font)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle)
        self.toggle_row.addWidget(self.toggle_btn, alignment=Qt.AlignRight)

        layout.addLayout(self.toggle_row)
        layout.addSpacing(6)

        # ---- middle: nav items ----
        nav_data = [
            ('🏠', '首页'),
            ('📦', '入库登记'),
            ('🚚', '出库登记'),
            ('📜', '出入库查询'),
            ('📋', '类别明细'),
            ('📈', '库存统计'),
            ('📂', '数据管理'),
        ]

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.buttons = []
        self._button_texts = []

        for i, (icon, text) in enumerate(nav_data):
            btn = QPushButton(f'  {icon}    {text}')
            btn.setCheckable(True)
            btn.setObjectName('SidebarButton')
            btn.setCursor(Qt.PointingHandCursor)
            icon_font = QFont()
            icon_font.setPointSize(16)
            btn.setFont(icon_font)
            self.button_group.addButton(btn, i)
            self.buttons.append(btn)
            self._button_texts.append((icon, text))
            layout.addWidget(btn)

        layout.addStretch()

        # ---- bottom: brand ----
        self.brand = QLabel('德隆石化仓储系统')
        brand_font = QFont()
        brand_font.setPointSize(11)
        self.brand.setFont(brand_font)
        self.brand.setAlignment(Qt.AlignCenter)
        self.brand.setObjectName('SidebarBrand')
        self.brand.setFixedHeight(44)
        layout.addWidget(self.brand)

    def toggle(self):
        self._expanded = not self._expanded

        if self._expanded:
            target_w = self.EXPANDED_WIDTH
            self.brand.show()
            self.logo_widget.show()
            self.toggle_row.setAlignment(self.toggle_btn, Qt.AlignRight)
            for i, btn in enumerate(self.buttons):
                icon, text = self._button_texts[i]
                btn.setText(f'  {icon}    {text}')
        else:
            target_w = self.COLLAPSED_WIDTH
            self.brand.hide()
            self.logo_widget.hide()
            self.toggle_row.setAlignment(self.toggle_btn, Qt.AlignCenter)
            for i, btn in enumerate(self.buttons):
                icon, _ = self._button_texts[i]
                btn.setText(f'{icon}')

        self.anim = QPropertyAnimation(self, b"minimumWidth")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(target_w)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.anim_max = QPropertyAnimation(self, b"maximumWidth")
        self.anim_max.setDuration(200)
        self.anim_max.setStartValue(self.width())
        self.anim_max.setEndValue(target_w)
        self.anim_max.setEasingCurve(QEasingCurve.InOutCubic)

        self.anim.start()
        self.anim_max.start()
