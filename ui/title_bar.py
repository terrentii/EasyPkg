from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QEvent


class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(0)

        self._title = QLabel("◈ EasyPkg")
        self._title.setObjectName("titlebar_label")
        # Пропускаем события мыши сквозь лейбл на TitleBar
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._title)
        layout.addStretch()

        self._btn_min = QPushButton("_")
        self._btn_min.setObjectName("btn_wm")
        self._btn_min.setFixedSize(32, 26)
        self._btn_min.clicked.connect(lambda: self.window().showMinimized())

        self._btn_max = QPushButton("□")
        self._btn_max.setObjectName("btn_wm")
        self._btn_max.setFixedSize(32, 26)
        self._btn_max.clicked.connect(self._toggle_maximize)

        self._btn_close = QPushButton("✕")
        self._btn_close.setObjectName("btn_wm_close")
        self._btn_close.setFixedSize(32, 26)
        self._btn_close.clicked.connect(lambda: self.window().close())

        for btn in (self._btn_min, self._btn_max, self._btn_close):
            layout.addWidget(btn)

    def set_title(self, text: str):
        self._title.setText(text)

    def _toggle_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self._btn_max.setText("□")
        else:
            win.showMaximized()
            self._btn_max.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            if not win.isMaximized():
                # Работает и на X11, и на Wayland
                win.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
