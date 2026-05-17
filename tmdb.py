import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

_movies_cache = None


def fetch_upcoming_movies(days=30):
    global _movies_cache
    if _movies_cache is not None:
        return _movies_cache

    today = date.today()
    end_date = today + timedelta(days=days)

    params = {
        "api_key": API_KEY,
        "language": "fr-FR",
        "region": "FR",
        "sort_by": "release_date.asc",
        "with_release_type": "3",
        "release_date.gte": today.isoformat(),
        "release_date.lte": end_date.isoformat(),
    }

    r = requests.get(f"{BASE_URL}/discover/movie", params=params)
    r.raise_for_status()
    _movies_cache = r.json().get("results", [])
    return _movies_cache


def get_poster_url(poster_path):
    if poster_path:
        return f"{IMAGE_BASE_URL}{poster_path}"
    return None
