from PySide6.QtWidgets import QLineEdit


class SearchBar(QLineEdit):
    def __init__(self, placeholder='搜索...'):
        super().__init__()

        self.setPlaceholderText(placeholder)
