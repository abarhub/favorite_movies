import json
import time
from pathlib import Path

CACHE_DIR = Path("cache")

TWELVE_HOURS = 43200
THIRTY_DAYS = 2592000


def _path(name):
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / f"{name}.json"


def read(name, ttl=None):
    p = _path(name)
    if not p.exists():
        return None
    if ttl and (time.time() - p.stat().st_mtime) > ttl:
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def write(name, data):
    _path(name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
