import os
from pathlib import Path


def _default_storage_dir() -> Path:
    return Path(__file__).parent / "storage"


def get_storage_dir() -> Path:
    configured_path = os.getenv("APP_STORAGE_DIR", "").strip()
    if configured_path:
        return Path(configured_path)
    return _default_storage_dir()


STORAGE_DIR = get_storage_dir()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

MENTEES_FILE = STORAGE_DIR / "mentees.json"
MENTORS_FILE = STORAGE_DIR / "mentors.json"
