from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication, QInputDialog, QMessageBox, QLineEdit
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from config import save_config, load_config

ADMIN_PASSWORD = "Delong@1168"


class Topbar(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.setObjectName('TopBar')
        self.setFixedHeight(54)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel('德隆石化仓储系统')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        layout.addStretch()

        # undo hint
        hint = QLabel('Ctrl+Z 撤销')
        hint_font = QFont()
        hint_font.setPointSize(10)
        hint.setFont(hint_font)
        hint.setObjectName('MutedLabel')
        layout.addWidget(hint)
        layout.addSpacing(16)

        # ---- font size ----
        font_icon = QLabel('Aa')
        font_icon_font = QFont()
        font_icon_font.setPointSize(13)
        font_icon_font.setBold(True)
        font_icon.setFont(font_icon_font)
        font_icon.setObjectName('MutedLabel')
        layout.addWidget(font_icon)

        btn_out = QPushButton('−')
        btn_out.setObjectName('ToolBtn')
        btn_out.setFixedSize(28, 28)
        btn_out.clicked.connect(lambda: self.adjust_font(-1))
        layout.addWidget(btn_out)

        self.size_label = QLabel(str(self.main_window.font_size))
        self.size_label.setAlignment(Qt.AlignCenter)
        self.size_label.setFixedWidth(30)
        layout.addWidget(self.size_label)

        btn_in = QPushButton('+')
        btn_in.setObjectName('ToolBtn')
        btn_in.setFixedSize(28, 28)
        btn_in.clicked.connect(lambda: self.adjust_font(1))
        layout.addWidget(btn_in)

        layout.addSpacing(16)

        # ---- edit lock toggle ----
        self.lock_btn = QPushButton()
        self.lock_btn.setObjectName('ToolBtn')
        self.lock_btn.setFixedHeight(28)
        self.lock_btn.clicked.connect(self.toggle_lock)
        self._update_lock_label()
        layout.addWidget(self.lock_btn)

        layout.addSpacing(8)

        # ---- theme toggle ----
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName('ToolBtn')
        self.theme_btn.setFixedHeight(28)
        self.theme_btn.setCheckable(False)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self._update_theme_label()
        layout.addWidget(self.theme_btn)

    def _update_theme_label(self):
        if self.main_window.is_dark:
            self.theme_btn.setText('浅色模式')
        else:
            self.theme_btn.setText('深色模式')

    def toggle_lock(self):
        # 管理者模式:关 → 开，需要验证密码
        if self.main_window.edit_locked:
            password, ok = QInputDialog.getText(
                self, '管理者模式验证', '请输入管理者密码：',
                QLineEdit.EchoMode.Password, ''
            )
            if not ok:
                return
            if password != ADMIN_PASSWORD:
                QMessageBox.critical(self, '密码错误', '密码不正确，无法开启管理者模式。')
                return
        self.main_window.toggle_edit_lock()
        self._update_lock_label()

    def _update_lock_label(self):
        if self.main_window.edit_locked:
            self.lock_btn.setText('管理者模式:关')
        else:
            self.lock_btn.setText('管理者模式:开')

    def adjust_font(self, delta):
        new_size = self.main_window.font_size + delta
        if not (9 <= new_size <= 22):
            return

        self.main_window.font_size = new_size
        self.size_label.setText(str(new_size))

        app = QApplication.instance()
        font = app.font()
        font.setPointSize(new_size)
        app.setFont(font)
        # force QSS to re-evaluate with new font
        app.setStyleSheet(app.styleSheet())

        cfg = load_config()
        cfg["font_size"] = new_size
        save_config(cfg)

    def toggle_theme(self):
        self.main_window.is_dark = not self.main_window.is_dark
        self._update_theme_label()
        cfg = load_config()
        cfg["dark_mode"] = self.main_window.is_dark
        save_config(cfg)

        from main import load_stylesheet
        app = QApplication.instance()
        load_stylesheet(app, self.main_window.is_dark)
        # re-apply font after stylesheet change (stylesheet reset clears fonts)
        font = app.font()
        font.setPointSize(self.main_window.font_size)
        app.setFont(font)
