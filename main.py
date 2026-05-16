import sys
from PyQt6 import sip
from PyQt6.QtWidgets import (
    QApplication, QFrame, QLabel, QPushButton,
    QVBoxLayout, QSizePolicy, QMessageBox,
    QScrollArea, QWidget, QGridLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi
from core.distro_detector import get_distro_info
from core.pkg_manager import PackageManager
from core.worker import SearchWorker, InstalledWorker, InstallWorker, RemoveWorker
from ui.password_dialog import PasswordDialog

# Популярные пакеты по категориям для сайдбара
POPULAR_QUERIES = {
    "Arch Linux (pacman)": "git",
    "Fedora (dnf)": "git",
    "Debian / Ubuntu (apt)": "git",
    "Astra Linux (SE)": "git",
    "РЕД ОС": "git",
    "ALT Linux / МОС": "git",
}

DISTRO_ITEM_MAP = {
    "arch": "Arch Linux (pacman)",
    "manjaro": "Arch Linux (pacman)",
    "endeavouros": "Arch Linux (pacman)",
    "fedora": "Fedora (dnf)",
    "rhel": "Fedora (dnf)",
    "centos": "Fedora (dnf)",
    "rocky": "Fedora (dnf)",
    "almalinux": "Fedora (dnf)",
    "redos": "РЕД ОС",
    "debian": "Debian / Ubuntu (apt)",
    "ubuntu": "Debian / Ubuntu (apt)",
    "mint": "Debian / Ubuntu (apt)",
    "kali": "Debian / Ubuntu (apt)",
    "astra": "Astra Linux (SE)",
    "alt": "ALT Linux / МОС",
    "rosa": "ALT Linux / МОС",
    "mos": "ALT Linux / МОС",
}

# Keep worker references alive to avoid GC during background threads
_active_workers = []


def main():
    app = QApplication(sys.argv)
    window = loadUi("ui/main_window.ui")

    with open("assets/main_window.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window.menuBar().setVisible(False)
    window.statusBar().setVisible(False)

    # Оборачиваем PkgsLayout в QScrollArea
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_content = QWidget()
    scroll_grid = QGridLayout(scroll_content)
    scroll_grid.setSpacing(8)
    scroll_grid.setContentsMargins(8, 8, 8, 8)
    scroll.setWidget(scroll_content)
    # Заменяем содержимое PkgsFrame на scroll
    old_layout = window.PkgsFrame.layout()
    while old_layout.count():
        item = old_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    old_layout.addWidget(scroll)
    # Перенаправляем window.PkgsLayout на новый grid внутри скролла
    window.PkgsLayout = scroll_grid

    info = get_distro_info()
    print(f"🐧 Система: {info['name']} | Менеджер: {info['manager']}")
    window.setWindowTitle(f"EasyPkg — {info['name']}")

    pkg = PackageManager.from_manager(info["manager"]) if info["manager"] else None

    # === НАСТРОЙКА ИНТЕРФЕЙСА ===

    window.ManagersLabel.setText("Выберите дистрибутив")

    window.ManagersListWidget.clear()
    distros = [
        "Arch Linux (pacman)",
        "Fedora (dnf)",
        "Debian / Ubuntu (apt)",
        "Astra Linux (SE)",
        "РЕД ОС",
        "ALT Linux / МОС",
    ]
    window.ManagersListWidget.addItems(distros)

    # === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

    def set_status(text: str):
        window.setWindowTitle(f"EasyPkg — {info['name']}  |  {text}")

    def reset_status():
        window.setWindowTitle(f"EasyPkg — {info['name']}")

    def clear_grid():
        layout = window.PkgsLayout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_error(msg: str):
        QMessageBox.critical(window, "Ошибка", msg)

    def make_card(name: str, desc: str, is_installed: bool = False):
        card = QFrame()
        card.setObjectName("package_card")

        v_layout = QVBoxLayout(card)
        v_layout.setContentsMargins(10, 10, 10, 10)
        v_layout.setSpacing(4)

        lbl_name = QLabel(name)
        lbl_name.setObjectName("pkg_name")

        lbl_desc = QLabel(desc or "Нет описания")
        lbl_desc.setObjectName("pkg_desc")
        lbl_desc.setWordWrap(True)

        if is_installed:
            btn = QPushButton("🗑️")
            btn.setObjectName("remove_btn")
            btn.setToolTip("Удалить пакет")
        else:
            btn = QPushButton("⬇️")
            btn.setObjectName("install_btn")
            btn.setToolTip("Установить пакет")

        btn.setFixedSize(34, 34)

        v_layout.addWidget(lbl_name)
        v_layout.addWidget(lbl_desc)
        v_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)

        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        if is_installed:
            def on_remove(checked=False, _name=name, _btn=btn):
                dialog = PasswordDialog(window, f"Введите пароль sudo для удаления «{_name}»:")
                password = dialog.get_password()
                if password is None:
                    return
                _btn.setEnabled(False)
                _btn.setText("⏳")
                set_status(f"Удаляем {_name}…")
                worker = RemoveWorker(pkg, _name, password)
                _active_workers.append(worker)

                def on_done(success: bool, msg: str, _w=worker, _b=_btn, _n=_name):
                    reset_status()
                    if not sip.isdeleted(_b):
                        if success:
                            _b.setText("✅")
                            _b.setStyleSheet("color: #34d399;")
                        else:
                            _b.setEnabled(True)
                            _b.setText("🗑️")
                            show_error(f"Не удалось удалить {_n}:\n{msg}")
                    if _w in _active_workers:
                        _active_workers.remove(_w)

                worker.finished.connect(on_done)
                worker.start()

            btn.clicked.connect(on_remove)
        else:
            def on_install(checked=False, _name=name, _btn=btn):
                dialog = PasswordDialog(window, f"Введите пароль sudo для установки «{_name}»:")
                password = dialog.get_password()
                if password is None:
                    return
                _btn.setEnabled(False)
                _btn.setText("⏳")
                set_status(f"Устанавливаем {_name}…")
                worker = InstallWorker(pkg, _name, password)
                _active_workers.append(worker)

                def on_done(success: bool, msg: str, _w=worker, _b=_btn, _n=_name):
                    reset_status()
                    if not sip.isdeleted(_b):
                        if success:
                            _b.setText("✅")
                            _b.setStyleSheet("color: #34d399;")
                        else:
                            _b.setEnabled(True)
                            _b.setText("⬇️")
                            show_error(f"Не удалось установить {_n}:\n{msg}")
                    if _w in _active_workers:
                        _active_workers.remove(_w)

                worker.finished.connect(on_done)
                worker.start()

            btn.clicked.connect(on_install)

        return card

    def show_results(results: list[dict], is_installed: bool = False):
        clear_grid()
        if not results:
            placeholder = QLabel("Ничего не найдено")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            window.PkgsLayout.addWidget(placeholder, 0, 0)
            return
        col_count = 2
        for i, pkg_info in enumerate(results):
            card = make_card(pkg_info["name"], pkg_info.get("description", ""), is_installed)
            window.PkgsLayout.addWidget(card, i // col_count, i % col_count)

    def show_search_error(msg: str):
        reset_status()
        show_error(f"Ошибка поиска:\n{msg}")

    def do_search(query: str):
        if not pkg:
            show_error("Пакетный менеджер не определён для этого дистрибутива.")
            return
        set_status(f"Поиск «{query}»…")
        worker = SearchWorker(pkg, query)
        _active_workers.append(worker)

        def on_results(results: list, _w=worker):
            reset_status()
            show_results(results, is_installed=False)
            if _w in _active_workers:
                _active_workers.remove(_w)

        def on_error(msg: str, _w=worker):
            show_search_error(msg)
            if _w in _active_workers:
                _active_workers.remove(_w)

        worker.results_ready.connect(on_results)
        worker.error.connect(on_error)
        worker.start()

    # === ОБРАБОТЧИКИ СОБЫТИЙ ===

    def on_distro_click(item):
        query = window.SearchbarLineEdit.text().strip() or "git"
        do_search(query)

    def on_installed_click():
        if not pkg:
            show_error("Пакетный менеджер не определён для этого дистрибутива.")
            return
        window.ManagersListWidget.clearSelection()
        set_status("Загружаем список установленных…")
        worker = InstalledWorker(pkg)
        _active_workers.append(worker)

        def on_results(results: list, _w=worker):
            reset_status()
            show_results(results, is_installed=True)
            if _w in _active_workers:
                _active_workers.remove(_w)

        def on_error(msg: str, _w=worker):
            show_search_error(msg)
            if _w in _active_workers:
                _active_workers.remove(_w)

        worker.results_ready.connect(on_results)
        worker.error.connect(on_error)
        worker.start()

    def on_search():
        query = window.SearchbarLineEdit.text().strip()
        if query:
            do_search(query)

    window.ManagersListWidget.itemClicked.connect(on_distro_click)
    window.InstalledButton.clicked.connect(on_installed_click)
    window.SearchButton.clicked.connect(on_search)
    window.SearchbarLineEdit.returnPressed.connect(on_search)

    # Автовыбор текущего дистрибутива в сайдбаре
    import os
    dist_id = ""
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    dist_id = line.split("=", 1)[1].strip().strip('"\'').lower()
                    break

    target_item = DISTRO_ITEM_MAP.get(dist_id, distros[0])
    for i, d in enumerate(distros):
        if d == target_item:
            window.ManagersListWidget.setCurrentRow(i)
            break

    # Начальный поиск популярных пакетов
    do_search("git")

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
