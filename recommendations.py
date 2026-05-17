from tmdb import fetch_tmdb_recommendations


def build_genre_weights(preferences):
    weights = {}
    for data in preferences.values():
        if isinstance(data, str):
            continue  # ancien format sans genres
        choice = data.get("choice")
        if choice not in ("like", "dislike"):
            continue
        for genre_id in data.get("genre_ids", []):
            delta = 2 if choice == "like" else -1
            weights[genre_id] = weights.get(genre_id, 0) + delta
    return weights


def _get_tmdb_recommended_ids(preferences):
    liked_ids = [
        int(mid) for mid, data in preferences.items()
        if isinstance(data, dict) and data.get("choice") == "like"
    ]
    recommended = set()
    for movie_id in liked_ids:
        recommended.update(fetch_tmdb_recommendations(movie_id))
    return recommended


def get_recommendations(movies, preferences, genres_map):
    weights = build_genre_weights(preferences)
    tmdb_recommended = _get_tmdb_recommended_ids(preferences)

    if not weights and not tmdb_recommended:
        return []

    rated_ids = set(preferences.keys())
    result = []

    for movie in movies:
        if str(movie["id"]) in rated_ids:
            continue

        genre_score = sum(weights.get(g, 0) for g in movie.get("genre_ids", []))
        tmdb_bonus = 3 if movie["id"] in tmdb_recommended else 0
        score = genre_score + tmdb_bonus

        if score <= 0:
            continue

        matching_genres = [
            genres_map.get(g, str(g))
            for g in movie.get("genre_ids", [])
            if weights.get(g, 0) > 0
        ]

        reasons = []
        if matching_genres:
            reasons.append(f"genres : {', '.join(matching_genres)}")
        if tmdb_bonus:
            reasons.append("similaire à un film que vous aimez")

        result.append({
            "movie": movie,
            "score": score,
            "matching_genres": matching_genres,
            "reason": " · ".join(reasons),
        })

    result.sort(key=lambda x: x["score"], reverse=True)
    return result
