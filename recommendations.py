from collections import Counter

from tmdb import fetch_movie_credits, fetch_tmdb_recommendations

# Catalogue des algorithmes disponibles (ordre d'affichage)
ALGORITHMS = [
    ("combined", "🔀 Combiné"),
    ("genres",   "🎭 Genres"),
    ("tmdb",     "🌐 Similarité TMDB"),
    ("credits",  "🎬 Réalisateurs & Acteurs"),
]


# --- Helpers communs ---

def _rated_ids(preferences):
    return set(preferences.keys())


def _liked_ids(preferences):
    return [
        int(mid) for mid, data in preferences.items()
        if isinstance(data, dict) and data.get("choice") == "like"
    ]


def _build_genre_weights(preferences):
    weights = {}
    for data in preferences.values():
        if isinstance(data, str):
            continue
        choice = data.get("choice")
        if choice not in ("like", "dislike"):
            continue
        delta = 2 if choice == "like" else -1
        for genre_id in data.get("genre_ids", []):
            weights[genre_id] = weights.get(genre_id, 0) + delta
    return weights


def _build_credit_weights(preferences):
    director_counts = Counter()
    actor_counts = Counter()
    for movie_id in _liked_ids(preferences):
        credits = fetch_movie_credits(movie_id)
        if credits.get("director"):
            director_counts[credits["director"]] += 1
        for actor in credits.get("cast", []):
            actor_counts[actor["name"]] += 1
    return director_counts, actor_counts


def _get_tmdb_recommended_ids(preferences):
    recommended = set()
    for movie_id in _liked_ids(preferences):
        recommended.update(fetch_tmdb_recommendations(movie_id))
    return recommended


def _make_entry(movie, score, reasons, matching_genres=None):
    return {
        "movie": movie,
        "score": score,
        "matching_genres": matching_genres or [],
        "reason": " · ".join(reasons),
    }


# --- Algorithmes ---

def _algo_genres(movies, preferences, genres_map):
    weights = _build_genre_weights(preferences)
    if not weights:
        return []

    rated = _rated_ids(preferences)
    result = []
    for movie in movies:
        if str(movie["id"]) in rated:
            continue
        score = sum(weights.get(g, 0) for g in movie.get("genre_ids", []))
        if score <= 0:
            continue
        matching = [genres_map.get(g, str(g)) for g in movie.get("genre_ids", []) if weights.get(g, 0) > 0]
        result.append(_make_entry(movie, score, [f"genres : {', '.join(matching)}"], matching))

    return sorted(result, key=lambda x: x["score"], reverse=True)


def _algo_tmdb(movies, preferences, genres_map):
    recommended = _get_tmdb_recommended_ids(preferences)
    if not recommended:
        return []

    rated = _rated_ids(preferences)
    result = []
    for movie in movies:
        if str(movie["id"]) in rated or movie["id"] not in recommended:
            continue
        result.append(_make_entry(movie, 1, ["similaire à un film que vous aimez"]))

    return result


def _algo_credits(movies, preferences, genres_map):
    director_counts, actor_counts = _build_credit_weights(preferences)
    if not director_counts and not actor_counts:
        return []

    rated = _rated_ids(preferences)
    result = []
    for movie in movies:
        if str(movie["id"]) in rated:
            continue
        credits = fetch_movie_credits(movie["id"])
        score = 0
        reasons = []

        director = credits.get("director")
        if director and director in director_counts:
            score += director_counts[director] * 3
            reasons.append(f"réalisateur : {director}")

        for actor in credits.get("cast", []):
            if actor["name"] in actor_counts:
                score += actor_counts[actor["name"]]
                if len(reasons) < 3:
                    reasons.append(f"acteur : {actor['name']}")

        if score > 0:
            result.append(_make_entry(movie, score, reasons))

    return sorted(result, key=lambda x: x["score"], reverse=True)


def _algo_combined(movies, preferences, genres_map):
    weights = _build_genre_weights(preferences)
    recommended = _get_tmdb_recommended_ids(preferences)
    director_counts, actor_counts = _build_credit_weights(preferences)

    if not weights and not recommended and not director_counts and not actor_counts:
        return []

    rated = _rated_ids(preferences)
    result = []

    for movie in movies:
        if str(movie["id"]) in rated:
            continue

        score = 0
        reasons = []

        # Genres
        genre_score = sum(weights.get(g, 0) for g in movie.get("genre_ids", []))
        matching = [genres_map.get(g, str(g)) for g in movie.get("genre_ids", []) if weights.get(g, 0) > 0]
        if genre_score > 0:
            score += genre_score
            reasons.append(f"genres : {', '.join(matching)}")

        # TMDB
        if movie["id"] in recommended:
            score += 3
            reasons.append("similarité TMDB")

        # Crédits
        credits = fetch_movie_credits(movie["id"])
        director = credits.get("director")
        if director and director in director_counts:
            score += director_counts[director] * 3
            reasons.append(f"réalisateur : {director}")
        for actor in credits.get("cast", []):
            if actor["name"] in actor_counts and len(reasons) < 4:
                score += actor_counts[actor["name"]]
                reasons.append(f"acteur : {actor['name']}")

        if score > 0:
            result.append(_make_entry(movie, score, reasons, matching))

    return sorted(result, key=lambda x: x["score"], reverse=True)


# --- Point d'entrée ---

_ALGOS = {
    "genres":   _algo_genres,
    "tmdb":     _algo_tmdb,
    "credits":  _algo_credits,
    "combined": _algo_combined,
}


def get_recommendations(movies, preferences, genres_map, algo="combined"):
    fn = _ALGOS.get(algo, _algo_combined)
    return fn(movies, preferences, genres_map)
