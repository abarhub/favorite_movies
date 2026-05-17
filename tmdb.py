import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

import cache as disk_cache

load_dotenv()

API_KEY = os.getenv("API_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

_movies_cache = None


def fetch_movies(days_back=90, days_ahead=30):
    global _movies_cache
    if _movies_cache is not None:
        return _movies_cache

    cached = disk_cache.read("movies", ttl=disk_cache.TWELVE_HOURS)
    if cached is not None:
        _movies_cache = cached
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
    disk_cache.write("movies", _movies_cache)
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


_credits_cache = None


def fetch_movie_credits(movie_id):
    global _credits_cache
    if _credits_cache is None:
        _credits_cache = disk_cache.read("credits") or {}

    key = str(movie_id)
    if key in _credits_cache:
        return _credits_cache[key]

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
    _credits_cache[key] = result
    disk_cache.write("credits", _credits_cache)
    return result


_tmdb_reco_cache = None


def fetch_tmdb_recommendations(movie_id):
    global _tmdb_reco_cache
    if _tmdb_reco_cache is None:
        saved = disk_cache.read("tmdb_reco") or {}
        _tmdb_reco_cache = {k: set(v) for k, v in saved.items()}

    key = str(movie_id)
    if key in _tmdb_reco_cache:
        return _tmdb_reco_cache[key]

    r = requests.get(
        f"{BASE_URL}/movie/{movie_id}/recommendations",
        params={"api_key": API_KEY, "language": "fr-FR"},
    )
    r.raise_for_status()
    movie_ids = {m["id"] for m in r.json().get("results", [])}

    _tmdb_reco_cache[key] = movie_ids
    disk_cache.write("tmdb_reco", {k: list(v) for k, v in _tmdb_reco_cache.items()})
    return movie_ids


_keywords_cache = None


def fetch_movie_keywords(movie_id):
    global _keywords_cache
    if _keywords_cache is None:
        _keywords_cache = disk_cache.read("keywords") or {}

    key = str(movie_id)
    if key in _keywords_cache:
        return _keywords_cache[key]

    r = requests.get(
        f"{BASE_URL}/movie/{movie_id}/keywords",
        params={"api_key": API_KEY},
    )
    r.raise_for_status()
    keywords = [kw["name"] for kw in r.json().get("keywords", [])]

    _keywords_cache[key] = keywords
    disk_cache.write("keywords", _keywords_cache)
    return keywords


_details_cache = None


def fetch_movie_details(movie_id):
    global _details_cache
    if _details_cache is None:
        _details_cache = disk_cache.read("details") or {}

    key = str(movie_id)
    if key in _details_cache:
        return _details_cache[key]

    r = requests.get(
        f"{BASE_URL}/movie/{movie_id}",
        params={"api_key": API_KEY, "language": "fr-FR"},
    )
    r.raise_for_status()
    data = r.json()
    result = {
        "original_language": data.get("original_language", ""),
        "production_countries": [c["name"] for c in data.get("production_countries", [])],
        "belongs_to_collection": data.get("belongs_to_collection"),
    }

    _details_cache[key] = result
    disk_cache.write("details", _details_cache)
    return result


_genres_cache = None


def fetch_genres():
    global _genres_cache
    if _genres_cache is not None:
        return _genres_cache

    cached = disk_cache.read("genres", ttl=disk_cache.THIRTY_DAYS)
    if cached is not None:
        _genres_cache = {int(k): v for k, v in cached.items()}
        return _genres_cache

    r = requests.get(
        f"{BASE_URL}/genre/movie/list",
        params={"api_key": API_KEY, "language": "fr-FR"},
    )
    r.raise_for_status()
    _genres_cache = {g["id"]: g["name"] for g in r.json().get("genres", [])}
    disk_cache.write("genres", _genres_cache)
    return _genres_cache
