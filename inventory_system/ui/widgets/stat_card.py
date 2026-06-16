from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class StatCard(QWidget):
    def __init__(self, title, value):
        super().__init__()

        self.setObjectName('Card')
        self.setFixedSize(200, 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(title)
        title_label.setStyleSheet('font-size:14px;color:#999;')

        value_label = QLabel(str(value))
        value_label.setStyleSheet('font-size:28px;font-weight:bold;color:#19C37D;')

        layout.addWidget(title_label)
        layout.addWidget(value_label)
