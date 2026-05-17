def build_genre_weights(preferences):
    """Calcule un poids par genre à partir des préférences : +2 par like, -1 par dislike."""
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


def get_recommendations(movies, preferences, genres_map):
    """
    Retourne les films non notés triés par score décroissant.
    Chaque entrée contient le film, son score et les genres correspondants.
    """
    weights = build_genre_weights(preferences)
    if not weights:
        return []

    rated_ids = set(preferences.keys())
    result = []

    for movie in movies:
        if str(movie["id"]) in rated_ids:
            continue

        score = sum(weights.get(g, 0) for g in movie.get("genre_ids", []))
        if score <= 0:
            continue

        matching_genres = [
            genres_map.get(g, str(g))
            for g in movie.get("genre_ids", [])
            if weights.get(g, 0) > 0
        ]
        result.append({
            "movie": movie,
            "score": score,
            "matching_genres": matching_genres,
        })

    result.sort(key=lambda x: x["score"], reverse=True)
    return result
