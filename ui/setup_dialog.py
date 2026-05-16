import os
import tempfile
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget,
)
from PyQt6.QtCore import Qt
from core.command_runner import run_sudo


MANAGER_BINS = {
    "pacman":  "/usr/bin/pacman",
    "apt":     "/usr/bin/apt",
    "apt-get": "/usr/bin/apt-get",
    "dnf":     "/usr/bin/dnf",
}

SUDOERS_FILE = "/etc/sudoers.d/easypkg"


def is_setup_done(manager: str = "") -> bool:
    """Проверяем, работает ли sudo без пароля для пакетного менеджера."""
    bin_path = MANAGER_BINS.get(manager)
    if bin_path:
        from core.command_runner import run
        rc, _, _ = run([bin_path, "--version"])
        # Если бинарник доступен — проверяем sudo -n
        rc, _, _ = run(["sudo", "-n", bin_path, "--version"])
        return rc == 0
    # Без конкретного менеджера — пробуем любой известный
    from core.command_runner import run
    for b in MANAGER_BINS.values():
        rc, _, _ = run(["sudo", "-n", b, "--version"])
        if rc == 0:
            return True
    return False


class SetupDialog(QDialog):
    def __init__(self, manager: str, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._bin = MANAGER_BINS.get(manager, f"/usr/bin/{manager}")
        self._username = os.environ.get("USER") or os.getlogin()
        self.setWindowTitle("Настройка EasyPkg")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("// ПЕРВИЧНАЯ НАСТРОЙКА")
        header.setObjectName("setup_header")

        info = QLabel(
            f"Для установки пакетов нужен sudo. EasyPkg может настроить "
            f"автоматический доступ — пароль больше никогда не будет запрашиваться.\n\n"
            f"Пользователь <b>{self._username}</b> получит право запускать "
            f"<b>{self._bin}</b> без пароля.\n\nФайл: <code>{SUDOERS_FILE}</code>"
        )
        info.setWordWrap(True)
        info.setObjectName("setup_info")

        rule_label = QLabel("Будет добавлено правило:")
        rule_label.setObjectName("setup_dim")

        self._rule_preview = QLabel(
            f"{self._username} ALL=(ALL) NOPASSWD: {self._bin}"
        )
        self._rule_preview.setObjectName("setup_code")

        self._status = QLabel("")
        self._status.setObjectName("setup_status")
        self._status.setWordWrap(True)

        pwd_label = QLabel("Пароль sudo (один раз):")
        pwd_label.setObjectName("setup_dim")

        self._pwd_input = QLineEdit()
        self._pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_input.setPlaceholderText("Введите пароль...")
        self._pwd_input.returnPressed.connect(self._apply)

        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()

        self._btn_skip = QPushButton("ПРОПУСТИТЬ")
        self._btn_skip.setObjectName("setup_btn")
        self._btn_skip.clicked.connect(self.reject)

        self._btn_apply = QPushButton("ПРИМЕНИТЬ →")
        self._btn_apply.setObjectName("setup_btn_primary")
        self._btn_apply.clicked.connect(self._apply)

        btn_layout.addWidget(self._btn_skip)
        btn_layout.addWidget(self._btn_apply)

        for w in (header, info, rule_label, self._rule_preview,
                  self._status, pwd_label, self._pwd_input, btn_row):
            layout.addWidget(w)

    def _apply(self):
        pwd = self._pwd_input.text()
        if not pwd:
            self._set_status("Введите пароль.", error=True)
            return

        self._btn_apply.setEnabled(False)
        self._btn_apply.setText("...")
        self._set_status("Применяем...", error=False)

        rule = f"{self._username} ALL=(ALL) NOPASSWD: {self._bin}\n"

        # Создаём временный файл атомарно (защита от TOCTOU/symlink-атак)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="easypkg_", suffix=".sudoers",
                dir="/tmp", delete=False, mode="w"
            ) as f:
                tmp = f.name
                f.write(rule)
        except OSError as e:
            self._set_status(f"Ошибка записи: {e}", error=True)
            self._btn_apply.setEnabled(True)
            self._btn_apply.setText("ПРИМЕНИТЬ →")
            return

        # visudo проверяет синтаксис, install записывает с правильным владельцем (root)
        script = (
            f"visudo -cf {tmp} && "
            f"install -m 440 -o root -g root {tmp} {SUDOERS_FILE}"
        )
        rc, _, err = run_sudo(["sh", "-c", script], pwd)

        # Убираем временный файл
        try:
            os.unlink(tmp)
        except OSError:
            pass

        if rc == 0:
            self._set_status(f"✓ Готово. Пароль больше не потребуется.", error=False)
            self._btn_apply.setText("ГОТОВО")
            self._pwd_input.setEnabled(False)
        else:
            self._set_status(f"Ошибка: {err.strip() or 'неверный пароль?'}", error=True)
            self._btn_apply.setEnabled(True)
            self._btn_apply.setText("ПРИМЕНИТЬ →")

    def _set_status(self, text: str, error: bool):
        color = "#ff5555" if error else "#50fa7b"
        self._status.setStyleSheet(f"color: {color}; background: transparent;")
        self._status.setText(text)

    def _apply_styles(self):
        self.setStyleSheet("""
            * { font-family: "JetBrains Mono","Courier New",monospace; border-radius: 0; }
            QDialog { background: #0c0c0c; border: 3px solid #7c4dff; }
            QLabel { background: transparent; color: #d0d0d0; }
            QLabel#setup_header { color: #9e7bff; font-size: 12px; font-weight: 800;
                                  letter-spacing: 2px; }
            QLabel#setup_info   { font-size: 12px; line-height: 1.6; }
            QLabel#setup_dim    { color: #5a4875; font-size: 11px; }
            QLabel#setup_code   { background: #0e0b1a; border: 2px solid #2a1e3d;
                                  padding: 8px 12px; font-size: 11px; color: #9e7bff; }
            QLineEdit { background: #0c0c0c; border: 2px solid #2a1e3d;
                        padding: 10px 14px; color: #d0d0d0; font-size: 13px; }
            QLineEdit:focus { border-color: #7c4dff; }
            QPushButton#setup_btn {
                background: #0e0b1a; border: 2px solid #2a1e3d;
                padding: 8px 18px; color: #5a4875; font-size: 11px; font-weight: 800; }
            QPushButton#setup_btn:hover { background: #d0d0d0; color: #0c0c0c;
                                          border-color: #d0d0d0; }
            QPushButton#setup_btn_primary {
                background: #7c4dff; border: 2px solid #7c4dff;
                padding: 8px 18px; color: #fff; font-size: 11px; font-weight: 800; }
            QPushButton#setup_btn_primary:hover { background: #9e7bff; border-color: #9e7bff; }
            QPushButton#setup_btn_primary:disabled { background: #2a1a4a;
                                                     border-color: #2a1a4a; color: #5a4875; }
        """)
