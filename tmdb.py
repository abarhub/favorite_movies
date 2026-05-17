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


def fetch_movie_trailer(movie_id):
    for lang in ("fr-FR", "en-US"):
        r = requests.get(
            f"{BASE_URL}/movie/{movie_id}/videos",
            params={"api_key": API_KEY, "language": lang},
        )
        r.raise_for_status()
        for video in r.json().get("results", []):
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return f"https://www.youtube.com/watch?v={video['key']}"
    return None


_genres_cache = None


def fetch_genres():
    global _genres_cache
    if _genres_cache is not None:
        return _genres_cache

    r = requests.get(
        f"{BASE_URL}/genre/movie/list",
        params={"api_key": API_KEY, "language": "fr-FR"},
    )
    r.raise_for_status()
    _genres_cache = {g["id"]: g["name"] for g in r.json().get("genres", [])}
    return _genres_cache
