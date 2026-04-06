import subprocess
import sys
import importlib
import json
import os

REQUIRED_MAP = {
    "requests": "requests[socks]",
    "bs4": "beautifulsoup4",
    "stem": "stem"
}

CONFIG_FILE = os.path.expanduser("~/.veilscrape_config.json")


def ensure_dependencies():
    missing = []
    for pkg, install_name in REQUIRED_MAP.items():
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(install_name)
    if missing:
        print(f"[VEILSCRAPE] Installing: {missing}")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--quiet", "--break-system-packages"
        ] + missing)
        print("[VEILSCRAPE] Done.")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


ensure_dependencies()

from gui import launch

if __name__ == "__main__":
    launch()