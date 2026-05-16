from PyQt6.QtCore import QThread, pyqtSignal


class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, pkg_manager, query: str):
        super().__init__()
        self.pkg_manager = pkg_manager
        self.query = query

    def run(self):
        try:
            results = self.pkg_manager.search(self.query)
            self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class InstalledWorker(QThread):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, pkg_manager):
        super().__init__()
        self.pkg_manager = pkg_manager

    def run(self):
        try:
            results = self.pkg_manager.list_installed()
            self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class InstallWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, pkg_manager, package: str, password: str):
        super().__init__()
        self.pkg_manager = pkg_manager
        self.package = package
        self.password = password

    def run(self):
        try:
            success, msg = self.pkg_manager.install(self.package, self.password)
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class RemoveWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, pkg_manager, package: str, password: str):
        super().__init__()
        self.pkg_manager = pkg_manager
        self.package = package
        self.password = password

    def run(self):
        try:
            success, msg = self.pkg_manager.remove(self.package, self.password)
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))
