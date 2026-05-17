import math
import re
from collections import Counter

from tmdb import fetch_movie_credits, fetch_movie_details, fetch_movie_keywords, fetch_tmdb_recommendations

# Catalogue des algorithmes disponibles (ordre d'affichage)
ALGORITHMS = [
    ("combined",    "🔀 Combiné"),
    ("genres",      "🎭 Genres"),
    ("tmdb",        "🌐 Similarité TMDB"),
    ("credits",     "🎬 Réalisateurs & Acteurs"),
    ("keywords",    "🏷 Mots-clés"),
    ("collections", "📚 Collections"),
    ("origin",      "🌍 Pays & Langue"),
    ("synopsis",    "📝 Synopsis"),
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


def _algo_keywords(movies, preferences, genres_map):
    """Recommande selon la fréquence des mots-clés TMDB des films aimés."""
    keyword_counts = Counter()
    for movie_id in _liked_ids(preferences):
        for kw in fetch_movie_keywords(movie_id):
            keyword_counts[kw] += 1
    if not keyword_counts:
        return []

    rated = _rated_ids(preferences)
    result = []
    for movie in movies:
        if str(movie["id"]) in rated:
            continue
        kws = fetch_movie_keywords(movie["id"])
        score = sum(keyword_counts[kw] for kw in kws if kw in keyword_counts)
        if score > 0:
            top_kws = sorted((kw for kw in kws if kw in keyword_counts),
                             key=lambda k: keyword_counts[k], reverse=True)[:3]
            result.append(_make_entry(movie, score, [f"mots-clés : {', '.join(top_kws)}"]))
    return sorted(result, key=lambda x: x["score"], reverse=True)


def _algo_collections(movies, preferences, genres_map):
    """Recommande les films appartenant aux mêmes franchises/collections que les films aimés."""
    liked_collection_ids = set()
    for movie_id in _liked_ids(preferences):
        details = fetch_movie_details(movie_id)
        col = details.get("belongs_to_collection")
        if col:
            liked_collection_ids.add(col["id"])
    if not liked_collection_ids:
        return []

    rated = _rated_ids(preferences)
    result = []
    for movie in movies:
        if str(movie["id"]) in rated:
            continue
        details = fetch_movie_details(movie["id"])
        col = details.get("belongs_to_collection")
        if col and col["id"] in liked_collection_ids:
            result.append(_make_entry(movie, 5, [f"collection : {col['name']}"]))
    return sorted(result, key=lambda x: x["score"], reverse=True)


def _algo_origin(movies, preferences, genres_map):
    """Recommande selon la langue originale et les pays de production des films aimés."""
    lang_counts = Counter()
    country_counts = Counter()
    for movie_id in _liked_ids(preferences):
        details = fetch_movie_details(movie_id)
        lang = details.get("original_language")
        if lang:
            lang_counts[lang] += 1
        for country in details.get("production_countries", []):
            country_counts[country] += 1
    if not lang_counts and not country_counts:
        return []

    rated = _rated_ids(preferences)
    result = []
    for movie in movies:
        if str(movie["id"]) in rated:
            continue
        details = fetch_movie_details(movie["id"])
        score = 0
        reasons = []
        lang = details.get("original_language")
        if lang and lang in lang_counts:
            score += lang_counts[lang] * 2
            reasons.append(f"langue : {lang}")
        for country in details.get("production_countries", []):
            if country in country_counts:
                score += country_counts[country]
                if len(reasons) < 3:
                    reasons.append(f"pays : {country}")
        if score > 0:
            result.append(_make_entry(movie, score, reasons))
    return sorted(result, key=lambda x: x["score"], reverse=True)


# --- TF-IDF synopsis ---

def _tokenize(text):
    return re.findall(r'\b[a-zàâäéèêëîïôùûüç]{3,}\b', (text or "").lower())


def _tf(tokens):
    counts = Counter(tokens)
    total = len(tokens) or 1
    return {t: c / total for t, c in counts.items()}


def _cosine(vec_a, vec_b):
    keys = set(vec_a) & set(vec_b)
    if not keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _algo_synopsis(movies, preferences, genres_map):
    """Recommande par similarité TF-IDF des synopses (sans librairie ML)."""
    liked = _liked_ids(preferences)
    if not liked:
        return []

    # Construire les vecteurs TF des synopses des films aimés
    liked_set = set(liked)
    movie_by_id = {m["id"]: m for m in movies}

    liked_vecs = []
    for mid in liked:
        movie = movie_by_id.get(mid)
        if not movie:
            continue
        tokens = _tokenize(movie.get("overview", ""))
        if tokens:
            liked_vecs.append(_tf(tokens))

    if not liked_vecs:
        return []

    # Vecteur moyen des films aimés
    all_keys = set(k for v in liked_vecs for k in v)
    avg_vec = {k: sum(v.get(k, 0) for v in liked_vecs) / len(liked_vecs) for k in all_keys}

    rated = _rated_ids(preferences)
    result = []
    for movie in movies:
        if str(movie["id"]) in rated or movie["id"] in liked_set:
            continue
        tokens = _tokenize(movie.get("overview", ""))
        if not tokens:
            continue
        vec = _tf(tokens)
        score = _cosine(avg_vec, vec)
        if score > 0.01:
            result.append(_make_entry(movie, score, ["similarité des synopsis"]))
    return sorted(result, key=lambda x: x["score"], reverse=True)


# --- Point d'entrée ---

_ALGOS = {
    "genres":       _algo_genres,
    "tmdb":         _algo_tmdb,
    "credits":      _algo_credits,
    "combined":     _algo_combined,
    "keywords":     _algo_keywords,
    "collections":  _algo_collections,
    "origin":       _algo_origin,
    "synopsis":     _algo_synopsis,
}


def get_recommendations(movies, preferences, genres_map, algo="combined"):
    fn = _ALGOS.get(algo, _algo_combined)
    return fn(movies, preferences, genres_map)
