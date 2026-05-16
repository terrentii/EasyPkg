from core.command_runner import run, run_sudo


class PackageManager:
    def __init__(self, manager: str):
        self.manager = manager

    @classmethod
    def from_manager(cls, manager: str) -> "PackageManager":
        return cls(manager)

    def search(self, query: str) -> list[dict]:
        if self.manager == "apt":
            return self._apt_search(query)
        elif self.manager == "pacman":
            return self._pacman_search(query)
        elif self.manager == "dnf":
            return self._dnf_search(query)
        return []

    def install(self, package: str, password: str) -> tuple[bool, str]:
        if self.manager == "apt":
            rc, _, err = run_sudo(["apt", "install", "-y", package], password)
        elif self.manager == "pacman":
            rc, _, err = run_sudo(["pacman", "-S", "--noconfirm", package], password)
        elif self.manager == "dnf":
            rc, _, err = run_sudo(["dnf", "install", "-y", package], password)
        else:
            return False, "Unsupported package manager"
        return rc == 0, err

    def remove(self, package: str, password: str) -> tuple[bool, str]:
        if self.manager == "apt":
            rc, _, err = run_sudo(["apt", "remove", "-y", package], password)
        elif self.manager == "pacman":
            rc, _, err = run_sudo(["pacman", "-R", "--noconfirm", package], password)
        elif self.manager == "dnf":
            rc, _, err = run_sudo(["dnf", "remove", "-y", package], password)
        else:
            return False, "Unsupported package manager"
        return rc == 0, err

    def list_installed(self) -> list[dict]:
        if self.manager == "apt":
            return self._apt_list_installed()
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
                # strip arch suffix like .x86_64
                name = name.strip().split(".")[0]
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
