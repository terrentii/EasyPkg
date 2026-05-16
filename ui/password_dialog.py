from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
)
from PyQt6.QtCore import Qt


class PasswordDialog(QDialog):
    def __init__(self, parent=None, prompt: str = "Введите пароль sudo:"):
        super().__init__(parent)
        self.setWindowTitle("Требуется пароль")
        self.setModal(True)
        self.setFixedWidth(340)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._setup_ui(prompt)
        self._apply_styles()

    def _setup_ui(self, prompt: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.label = QLabel(prompt)
        self.label.setWordWrap(True)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setPlaceholderText("Пароль")
        self.input.returnPressed.connect(self._accept)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Отмена")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)

        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addLayout(btn_layout)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #111118;
                color: #e4e4e9;
            }
            QLabel {
                color: #e4e4e9;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #0a0a0f;
                border: 1px solid #1e1e28;
                border-radius: 6px;
                padding: 6px;
                color: #e4e4e9;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #7c3aed;
            }
            QPushButton {
                background-color: #1a1a24;
                border: 1px solid #1e1e28;
                border-radius: 6px;
                padding: 6px 16px;
                color: #e4e4e9;
                font-size: 13px;
            }
            QPushButton:hover {
                border-color: #7c3aed;
                color: #7c3aed;
            }
            QPushButton#btn_ok {
                background-color: #7c3aed;
                border-color: #7c3aed;
                color: white;
            }
            QPushButton#btn_ok:hover {
                background-color: #6d28d9;
            }
        """)
        self.btn_ok.setObjectName("btn_ok")

    def _accept(self):
        if self.input.text():
            self.accept()

    def get_password(self) -> str | None:
        """Show dialog and return password or None if cancelled."""
        if self.exec() == QDialog.DialogCode.Accepted:
            return self.input.text()
        return None
