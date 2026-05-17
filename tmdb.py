import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

_movies_cache = None


def fetch_movies(days_back=90, days_ahead=30):
    global _movies_cache
    if _movies_cache is not None:
        return _movies_cache

    today = date.today()
    start_date = today - timedelta(days=days_back)
    end_date = today + timedelta(days=days_ahead)

    params = {
        "api_key": API_KEY,
        "language": "fr-FR",
        "region": "FR",
        "sort_by": "release_date.asc",
        "with_release_type": "3",
        "release_date.gte": start_date.isoformat(),
        "release_date.lte": end_date.isoformat(),
        "page": 1,
    }

    all_results = []
    while True:
        r = requests.get(f"{BASE_URL}/discover/movie", params=params)
        r.raise_for_status()
        data = r.json()
        all_results.extend(data.get("results", []))
        if params["page"] >= data.get("total_pages", 1):
            break
        params["page"] += 1

    _movies_cache = all_results
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


_credits_cache = {}


def fetch_movie_credits(movie_id):
    if movie_id in _credits_cache:
        return _credits_cache[movie_id]

    r = requests.get(
        f"{BASE_URL}/movie/{movie_id}/credits",
        params={"api_key": API_KEY, "language": "fr-FR"},
    )
    r.raise_for_status()
    data = r.json()

    director = next(
        (p["name"] for p in data.get("crew", []) if p["job"] == "Director"),
        None,
    )
    cast = [
        {"name": p["name"], "character": p.get("character", "")}
        for p in data.get("cast", [])[:4]
    ]

    result = {"director": director, "cast": cast}
    _credits_cache[movie_id] = result
    return result


_tmdb_reco_cache = {}


def fetch_tmdb_recommendations(movie_id):
    if movie_id in _tmdb_reco_cache:
        return _tmdb_reco_cache[movie_id]

    r = requests.get(
        f"{BASE_URL}/movie/{movie_id}/recommendations",
        params={"api_key": API_KEY, "language": "fr-FR"},
    )
    r.raise_for_status()
    movie_ids = {m["id"] for m in r.json().get("results", [])}
    _tmdb_reco_cache[movie_id] = movie_ids
    return movie_ids


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
