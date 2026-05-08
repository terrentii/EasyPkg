import getpass
import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy, QTextEdit, QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.uic import loadUi

from core.distro_detector import get_distro_info
from core.pkg_manager import Package, get_install_cmd, get_installed_names, get_remove_cmd, list_installed, search_packages
from core.command_runner import InstallWorker
from core.setup import get_setup_cmd, needs_password, needs_wizard


DISTRO_MANAGERS: dict[str, str] = {
    "Arch Linux (pacman)": "pacman",
    "Fedora (dnf)":        "dnf",
    "Debian / Ubuntu (apt)": "apt",
    "Astra Linux (SE)":    "apt",
    "РЕД ОС":              "dnf",
    "ALT Linux / МОС":     "apt",
}

_POPULAR: dict[str, list[tuple[str, str]]] = {
    "pacman": [
        ("firefox",        "Браузер Firefox"),
        ("git",            "Система контроля версий"),
        ("neovim",         "Текстовый редактор на базе Vim"),
        ("htop",           "Интерактивный монитор процессов"),
        ("vlc",            "Медиаплеер"),
        ("docker",         "Контейнеризация приложений"),
        ("python",         "Язык программирования Python 3"),
        ("nodejs",         "Среда выполнения JavaScript"),
        ("ffmpeg",         "Обработка видео и аудио"),
        ("obs-studio",     "Запись экрана и стриминг"),
    ],
    "apt": [
        ("firefox",        "Браузер Firefox"),
        ("git",            "Система контроля версий"),
        ("neovim",         "Текстовый редактор на базе Vim"),
        ("htop",           "Интерактивный монитор процессов"),
        ("vlc",            "Медиаплеер"),
        ("docker.io",      "Контейнеризация приложений"),
        ("python3",        "Язык программирования Python 3"),
        ("nodejs",         "Среда выполнения JavaScript"),
        ("ffmpeg",         "Обработка видео и аудио"),
        ("obs-studio",     "Запись экрана и стриминг"),
    ],
    "dnf": [
        ("firefox",        "Браузер Firefox"),
        ("git",            "Система контроля версий"),
        ("neovim",         "Текстовый редактор на базе Vim"),
        ("htop",           "Интерактивный монитор процессов"),
        ("vlc",            "Медиаплеер"),
        ("docker",         "Контейнеризация приложений"),
        ("python3",        "Язык программирования Python 3"),
        ("nodejs",         "Среда выполнения JavaScript"),
        ("ffmpeg",         "Обработка видео и аудио"),
        ("obs-studio",     "Запись экрана и стриминг"),
    ],
}


def popular_packages(manager: str) -> list[Package]:
    return [Package(name=n, description=d) for n, d in _POPULAR.get(manager, [])]


class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, manager: str, query: str):
        super().__init__()
        self.manager = manager
        self.query = query

    def run(self):
        try:
            self.results_ready.emit(search_packages(self.manager, self.query))
        except Exception as e:
            self.error.emit(str(e))


class InstalledWorker(QThread):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, manager: str):
        super().__init__()
        self.manager = manager

    def run(self):
        try:
            self.results_ready.emit(list_installed(self.manager))
        except Exception as e:
            self.error.emit(str(e))


class PopularWorker(QThread):
    results_ready = pyqtSignal(list)

    def __init__(self, manager: str, packages: list):
        super().__init__()
        self.manager = manager
        self.packages = packages

    def run(self):
        try:
            installed = get_installed_names(self.manager)
            for pkg in self.packages:
                pkg.installed = pkg.name in installed
        except Exception:
            pass  # при ошибке показываем пакеты без статуса
        self.results_ready.emit(self.packages)


class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка EasyPkg")
        self.setMinimumWidth(460)
        self.setObjectName("SetupWizard")
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Первый запуск")
        title.setObjectName("WizardTitle")
        layout.addWidget(title)

        user = getpass.getuser()
        desc = QLabel(
            "EasyPkg создаст группу <b>easypkg</b> и настроит sudo, "
            "чтобы участники группы могли устанавливать и удалять пакеты "
            "без ввода пароля.<br><br>"
            "Будет выполнено:<br>"
            "&nbsp;&nbsp;• <code>groupadd easypkg</code><br>"
            f"&nbsp;&nbsp;• <code>usermod -aG easypkg {user}</code><br>"
            "&nbsp;&nbsp;• <code>/etc/sudoers.d/easypkg</code> — NOPASSWD для менеджеров пакетов"
        )
        desc.setObjectName("WizardDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Пароль sudo...")
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setObjectName("SearchbarLineEdit")
        layout.addWidget(self.password_field)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("install_output")
        self.output.setMaximumHeight(110)
        self.output.hide()
        layout.addWidget(self.output)

        btns = QHBoxLayout()
        self.skip_btn = QPushButton("Пропустить")
        self.skip_btn.setObjectName("WizardSkipBtn")
        self.skip_btn.clicked.connect(self.reject)

        self.setup_btn = QPushButton("Настроить →")
        self.setup_btn.setObjectName("install_btn")
        self.setup_btn.clicked.connect(self._run_setup)
        self.password_field.returnPressed.connect(self._run_setup)

        btns.addWidget(self.skip_btn)
        btns.addStretch()
        btns.addWidget(self.setup_btn)
        layout.addLayout(btns)

    def _run_setup(self):
        password = self.password_field.text()
        if not password:
            return

        self.password_field.hide()
        self.output.show()
        self.setup_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)

        self.worker = InstallWorker(get_setup_cmd(getpass.getuser()), password, self)
        self.worker.line_received.connect(self.output.append)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    def _on_done(self, success: bool):
        if success:
            self.output.append("\n✅ Готово. Пароль больше не потребуется.")
            self.skip_btn.setText("Закрыть")
            self.skip_btn.clicked.disconnect()
            self.skip_btn.clicked.connect(self.accept)
        else:
            self.output.append("\n❌ Ошибка. Проверьте пароль.")
            self.password_field.show()
            self.setup_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)


class SudoDialog(QDialog):
    """Диалог выполнения команды с sudo и стримингом вывода."""
    def __init__(self, title: str, cmd: list[str], password: str, success_msg: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(540, 380)
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("install_output")
        layout.addWidget(self.output)

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._success_msg = success_msg
        self.output.append(f"$ sudo {' '.join(cmd)}\n")
        self.worker = InstallWorker(cmd, password, self)
        self.worker.line_received.connect(self.output.append)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    def _on_done(self, success: bool):
        self.output.append(f"\n{self._success_msg}" if success else "\n❌ Ошибка")
        self.close_btn.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    window = loadUi("ui/main_window.ui")

    with open("assets/main_window.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window.menuBar().setVisible(False)
    window.statusBar().setVisible(False)

    info = get_distro_info()
    window.setWindowTitle(f"EasyPkg — {info['name']}")

    state: dict = {
        "manager": info["manager"] or "apt",
        "worker": None,
    }

    window.ManagersLabel.setText("Дистрибутив")
    window.SearchbarLineEdit.setPlaceholderText("Поиск пакетов...")

    distros = list(DISTRO_MANAGERS.keys())
    window.ManagersListWidget.addItems(distros)

    # Скролл-область для карточек пакетов (PkgsLayout — QGridLayout из .ui)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setObjectName("PkgsScrollArea")

    pkg_container = QWidget()
    pkg_container.setObjectName("PkgsContainer")
    pkg_layout = QVBoxLayout(pkg_container)
    pkg_layout.setContentsMargins(8, 8, 8, 8)
    pkg_layout.setSpacing(6)
    pkg_layout.addStretch()
    scroll.setWidget(pkg_container)

    window.PkgsLayout.addWidget(scroll, 0, 0)

    def clear_cards():
        # Удаляем все кроме последнего stretch
        while pkg_layout.count() > 1:
            item = pkg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_status(text: str):
        clear_cards()
        lbl = QLabel(text)
        lbl.setObjectName("StatusLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pkg_layout.insertWidget(0, lbl)

    def make_card(pkg: Package) -> QFrame:
        card = QFrame()
        card.setObjectName("package_card")

        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)

        top = QHBoxLayout()
        name_lbl = QLabel(pkg.name)
        name_lbl.setObjectName("pkg_name")
        top.addWidget(name_lbl)
        if pkg.version:
            ver_lbl = QLabel(pkg.version)
            ver_lbl.setObjectName("pkg_version")
            top.addWidget(ver_lbl)
        top.addStretch()
        v.addLayout(top)

        if pkg.description:
            desc_lbl = QLabel(pkg.description)
            desc_lbl.setObjectName("pkg_desc")
            desc_lbl.setWordWrap(True)
            v.addWidget(desc_lbl)

        bottom = QHBoxLayout()
        bottom.addStretch()
        if pkg.installed:
            badge = QLabel("Установлен")
            badge.setObjectName("InstalledBadge")
            bottom.addWidget(badge)
            btn_remove = QPushButton("Удалить")
            btn_remove.setObjectName("remove_btn")
            btn_remove.clicked.connect(lambda checked=False, p=pkg: do_remove(p.name))
            bottom.addWidget(btn_remove)
        else:
            btn = QPushButton("Установить")
            btn.setObjectName("install_btn")
            btn.clicked.connect(lambda checked=False, p=pkg: do_install(p.name))
            bottom.addWidget(btn)
        v.addLayout(bottom)

        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        return card

    def show_packages(packages: list[Package], header: str = ""):
        clear_cards()
        if not packages:
            show_status("Ничего не найдено")
            return
        offset = 0
        if header:
            lbl = QLabel(header)
            lbl.setObjectName("SectionHeader")
            pkg_layout.insertWidget(0, lbl)
            offset = 1
        for i, pkg in enumerate(packages):
            pkg_layout.insertWidget(offset + i, make_card(pkg))

    def show_popular():
        show_status("Загрузка...")
        _stop_worker()
        pkgs = popular_packages(state["manager"])
        w = PopularWorker(state["manager"], pkgs)
        w.results_ready.connect(lambda p: show_packages(p, header="Популярные пакеты"))
        w.start()
        state["worker"] = w

    def _get_password(prompt: str) -> tuple[str | None, bool]:
        """Возвращает (пароль, ok). Если NOPASSWD настроен — (None, True)."""
        if not needs_password():
            return None, True
        password, ok = QInputDialog.getText(
            window, "Авторизация", prompt, QLineEdit.EchoMode.Password,
        )
        return (password, ok) if ok else (None, False)

    def do_install(package_name: str):
        password, ok = _get_password(f"Пароль sudo для установки '{package_name}':")
        if not ok:
            return
        cmd = get_install_cmd(state["manager"], package_name)
        SudoDialog(f"Установка: {package_name}", cmd, password, "✅ Установка завершена", window).exec()

    def do_remove(package_name: str):
        password, ok = _get_password(f"Пароль sudo для удаления '{package_name}':")
        if not ok:
            return
        cmd = get_remove_cmd(state["manager"], package_name)
        SudoDialog(f"Удаление: {package_name}", cmd, password, "✅ Удаление завершено", window).exec()

    def do_search():
        query = window.SearchbarLineEdit.text().strip()
        if not query:
            show_popular()
            return
        show_status("Поиск...")
        _stop_worker()
        w = SearchWorker(state["manager"], query)
        w.results_ready.connect(lambda pkgs: show_packages(pkgs, header=f"Результаты: {query}"))
        w.error.connect(lambda msg: show_status(f"Ошибка: {msg}"))
        w.start()
        state["worker"] = w

    def on_installed_click():
        window.ManagersListWidget.clearSelection()
        window.SearchbarLineEdit.clear()
        show_status("Загрузка...")
        _stop_worker()
        w = InstalledWorker(state["manager"])
        w.results_ready.connect(lambda pkgs: show_packages(pkgs, header="Установленные пакеты"))
        w.error.connect(lambda msg: show_status(f"Ошибка: {msg}"))
        w.start()
        state["worker"] = w

    def on_distro_click(item):
        state["manager"] = DISTRO_MANAGERS.get(item.text(), "apt")
        window.SearchbarLineEdit.clear()
        show_popular()

    def _stop_worker():
        w = state.get("worker")
        if w and w.isRunning():
            w.terminate()
            w.wait()

    window.ManagersListWidget.itemClicked.connect(on_distro_click)
    window.InstalledButton.clicked.connect(on_installed_click)
    window.SearchButton.clicked.connect(do_search)
    window.SearchbarLineEdit.returnPressed.connect(do_search)

    detected = info["manager"]
    if detected:
        for i, (distro, mgr) in enumerate(DISTRO_MANAGERS.items()):
            if mgr == detected:
                window.ManagersListWidget.setCurrentRow(i)
                break

    show_popular()

    if needs_wizard():
        SetupWizard(window).exec()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
