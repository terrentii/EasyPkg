import re
from core.command_runner import run, run_sudo

_PKG_NAME_RE = re.compile(r'^[a-zA-Z0-9._+@-]+$')


class PackageManager:
    def __init__(self, manager: str):
        self.manager = manager

    @classmethod
    def from_manager(cls, manager: str) -> "PackageManager":
        return cls(manager)

    def search(self, query: str) -> list[dict]:
        if self.manager in ("apt", "apt-get"):
            return self._apt_search(query)
        elif self.manager == "pacman":
            return self._pacman_search(query)
        elif self.manager == "dnf":
            return self._dnf_search(query)
        return []

    def _validate_package(self, package: str) -> tuple[bool, str]:
        if not _PKG_NAME_RE.fullmatch(package):
            return False, f"Недопустимое имя пакета: {package!r}"
        return True, ""

    def install(self, package: str, password: str) -> tuple[bool, str]:
        ok, err = self._validate_package(package)
        if not ok:
            return False, err
        if self.manager == "apt":
            rc, out, err = run_sudo(["apt", "install", "-y", package], password, timeout=300)
        elif self.manager == "apt-get":
            rc, out, err = run_sudo(["apt-get", "install", "-y", package], password, timeout=300)
        elif self.manager == "pacman":
            rc, out, err = run_sudo(
                ["pacman", "-Sy", "--noconfirm", "--needed", package], password, timeout=300
            )
        elif self.manager == "dnf":
            rc, out, err = run_sudo(["dnf", "install", "-y", package], password, timeout=300)
        else:
            return False, "Неподдерживаемый пакетный менеджер"
        if rc == 0:
            return True, ""
        return False, (err.strip() or out.strip() or "Неизвестная ошибка")

    def remove(self, package: str, password: str) -> tuple[bool, str]:
        ok, err = self._validate_package(package)
        if not ok:
            return False, err
        if self.manager == "apt":
            rc, out, err = run_sudo(["apt", "remove", "-y", package], password, timeout=300)
        elif self.manager == "apt-get":
            rc, out, err = run_sudo(["apt-get", "remove", "-y", package], password, timeout=300)
        elif self.manager == "pacman":
            rc, out, err = run_sudo(["pacman", "-R", "--noconfirm", package], password, timeout=300)
        elif self.manager == "dnf":
            rc, out, err = run_sudo(["dnf", "remove", "-y", package], password, timeout=300)
        else:
            return False, "Неподдерживаемый пакетный менеджер"
        if rc == 0:
            return True, ""
        return False, (err.strip() or out.strip() or "Неизвестная ошибка")

    def list_installed(self) -> list[dict]:
        if self.manager == "apt":
            return self._apt_list_installed()
        elif self.manager == "apt-get":
            return self._rpm_list_installed()
        elif self.manager == "pacman":
            return self._pacman_list_installed()
        elif self.manager == "dnf":
            return self._dnf_list_installed()
        return []

    # --- apt ---

    def _apt_search(self, query: str) -> list[dict]:
        rc, out, _ = run(["apt-cache", "search", query])
        if rc != 0:
            return []
        results = []
        for line in out.splitlines():
            if " - " in line:
                name, desc = line.split(" - ", 1)
                results.append({"name": name.strip(), "description": desc.strip()})
        return results[:20]

    def _apt_list_installed(self) -> list[dict]:
        rc, out, _ = run(["dpkg-query", "-W", "-f=${Package}\t${binary:Summary}\n"])
        if rc != 0:
            return []
        results = []
        for line in out.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                results.append({"name": parts[0].strip(), "description": parts[1].strip()})
        return results

    def _rpm_list_installed(self) -> list[dict]:
        rc, out, _ = run(["rpm", "-qa", "--queryformat", "%{NAME}\t%{SUMMARY}\n"])
        if rc != 0:
            return []
        results = []
        for line in out.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                results.append({"name": parts[0].strip(), "description": parts[1].strip()})
        return results

    # --- pacman ---

    def _pacman_search(self, query: str) -> list[dict]:
        rc, out, _ = run(["pacman", "-Ss", query])
        if rc != 0:
            return []
        results = []
        lines = out.splitlines()
        i = 0
        while i < len(lines) - 1:
            header = lines[i].strip()
            desc = lines[i + 1].strip()
            # header format: "repo/name version [installed]"
            if "/" in header:
                pkg_part = header.split("/", 1)[1]
                name = pkg_part.split()[0] if pkg_part.split() else pkg_part
                results.append({"name": name, "description": desc})
            i += 2
        return results[:20]

    def _pacman_list_installed(self) -> list[dict]:
        rc, out, _ = run(["pacman", "-Q"])
        if rc != 0:
            return []
        results = []
        for line in out.splitlines():
            parts = line.split()
            if parts:
                results.append({"name": parts[0], "description": parts[1] if len(parts) > 1 else ""})
        return results

    # --- dnf ---

    def _dnf_search(self, query: str) -> list[dict]:
        rc, out, _ = run(["dnf", "search", query])
        if rc != 0:
            return []
        results = []
        for line in out.splitlines():
            if " : " in line:
                name, desc = line.split(" : ", 1)
                # strip arch suffix like .x86_64, .noarch, .i686
                _ARCHES = {"x86_64", "noarch", "i686", "aarch64", "armv7hl", "s390x", "ppc64le"}
                name = name.strip()
                if "." in name and name.rsplit(".", 1)[-1] in _ARCHES:
                    name = name.rsplit(".", 1)[0]
                results.append({"name": name, "description": desc.strip()})
        return results[:20]

    def _dnf_list_installed(self) -> list[dict]:
        rc, out, _ = run(["dnf", "list", "installed"])
        if rc != 0:
            return []
        results = []
        for line in out.splitlines():
            parts = line.split()
            if parts and not line.startswith("Installed"):
                name = parts[0].split(".")[0]
                results.append({"name": name, "description": ""})
        return results
