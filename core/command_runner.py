import subprocess


def run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Timeout expired"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"


def run_sudo(cmd: list[str], password: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run a command with sudo using the provided password via stdin."""
    try:
        full_cmd = ["sudo", "-S", "-p", ""] + cmd
        result = subprocess.run(
            full_cmd,
            input=password + "\n",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout: команда выполнялась дольше {timeout} секунд"
    except FileNotFoundError:
        return 1, "", f"Команда не найдена: {cmd[0]}"
