from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
)


class InventoryCard(QWidget):
    def __init__(self, data, delete_callback):
        super().__init__()

        self.setObjectName('Card')

        self.data = data
        self.delete_callback = delete_callback

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        left = QVBoxLayout()

        title = QLabel(f"{data['name']}  ·  {data['batch_no']}")
        title.setStyleSheet('font-size:18px;font-weight:bold;')

        desc = QLabel(
            f"类别：{data['category']}\n"
            f"规格：{data['spec']}\n"
            f"位置：{data['location']}"
        )

        left.addWidget(title)
        left.addWidget(desc)

        root.addLayout(left)

        root.addStretch()

        right = QVBoxLayout()

        weight = QLabel(f"{data['weight']} KG")
        weight.setStyleSheet('font-size:22px;font-weight:bold;color:#19C37D;')

        delete_btn = QPushButton('删除')
        delete_btn.clicked.connect(
            lambda: self.delete_callback(data['id'])
        )

        right.addWidget(weight)
        right.addWidget(delete_btn)

        root.addLayout(right)
