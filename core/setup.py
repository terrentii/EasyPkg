import getpass
import os


GROUP = "easypkg"
SUDOERS_PATH = "/etc/sudoers.d/easypkg"


def setup_done() -> bool:
    # Файл создаётся с правами 440 (root:root) — читать его мы не можем,
    # но os.path.exists() не требует прав на чтение, только на x у директории.
    # Само sudo читает файл от root — всё работает.
    return os.path.exists(SUDOERS_PATH)


def needs_wizard() -> bool:
    return not setup_done()


def needs_password() -> bool:
    return not setup_done()


def get_setup_cmd(username: str) -> list[str]:
    line1 = f"# EasyPkg — {username}"
    line2 = (
        f"{username} ALL=(ALL) NOPASSWD: "
        "/usr/bin/pacman, /usr/bin/apt, /usr/bin/apt-get, /usr/bin/dnf, /bin/dnf"
    )
    # printf надёжнее echo и не требует base64
    script = (
        f"groupadd -f {GROUP} && "
        f"usermod -aG {GROUP} {username} && "
        f"printf '%s\\n%s\\n' '{line1}' '{line2}' > {SUDOERS_PATH} && "
        f"chmod 440 {SUDOERS_PATH}"
    )
    return ["sh", "-c", script]
