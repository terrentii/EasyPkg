import os

def get_distro_info():
    os_release = "/etc/os-release"
    if not os.path.exists(os_release):
        return {"family": "unknown", "manager": None, "name": "Non-Linux"}

    info = {}
    with open(os_release, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                info[key] = value.strip('"\'')

    dist_id = info.get("ID", "").lower()
    dist_like = info.get("ID_LIKE", "").lower()
    dist_name = info.get("NAME", "Unknown Linux")

    if dist_id in ["debian", "ubuntu", "astra", "mint", "kali"]:
        return {"family": "debian", "manager": "apt", "name": dist_name}
        
    if dist_id in ["fedora", "rhel", "centos", "rocky", "almalinux", "redos"]:
        return {"family": "rpm", "manager": "dnf", "name": dist_name}
        
    if dist_id in ["arch", "manjaro", "endeavouros"]:
        return {"family": "arch", "manager": "pacman", "name": dist_name}
        
    if dist_id in ["alt", "rosa", "mos"] or "alt" in dist_like or "rosa" in dist_like:
        return {"family": "rpm", "manager": "apt-get", "name": dist_name}

    return {"family": "unknown", "manager": None, "name": dist_name}

if __name__ == "__main__":
    res = get_distro_info()
    print(f"Система: {res['name']}")
    print(f"Семейство: {res['family']}")
    print(f"Менеджер: {res['manager'] or 'не найден'}")