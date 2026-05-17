import json
from pathlib import Path

PREFERENCES_FILE = Path("preferences.json")


def load_preferences():
    if PREFERENCES_FILE.exists():
        return json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
    return {}


def save_preference(movie_id, choice):
    preferences = load_preferences()
    preferences[str(movie_id)] = choice
    PREFERENCES_FILE.write_text(
        json.dumps(preferences, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_preference(movie_id):
    return load_preferences().get(str(movie_id))
