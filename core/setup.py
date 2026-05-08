import os
import subprocess


GROUP = "easypkg"
SUDOERS_PATH = "/etc/sudoers.d/easypkg"


def _sudo_nopasswd_works() -> bool:
    """Проверяет, действительно ли sudo работает без пароля."""
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def setup_done() -> bool:
    return os.path.exists(SUDOERS_PATH)


def needs_wizard() -> bool:
    return not setup_done()


def needs_password() -> bool:
    if _sudo_nopasswd_works():
        return False
    return True


def get_setup_cmd(username: str) -> list[str]:
    allowed = ", ".join([
        "/usr/bin/pacman",
        "/usr/bin/apt", "/usr/bin/apt-get",
        "/usr/bin/dnf", "/bin/dnf",
    ])
    content = (
        f"# EasyPkg — NOPASSWD для пакетных менеджеров\\n"
        f"{username} ALL=(ALL) NOPASSWD: {allowed}\\n"
    )
    tmp = f"{SUDOERS_PATH}.tmp"
    script = (
        f"printf '{content}' > {tmp} && "
        f"chmod 440 {tmp} && "
        f"visudo -c -f {tmp} && "
        f"mv {tmp} {SUDOERS_PATH}"
    )
    return ["sh", "-c", script]
