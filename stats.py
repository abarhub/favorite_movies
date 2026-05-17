from collections import Counter

from tmdb import fetch_movie_credits


def compute_stats(preferences, genres_map):
    counts = {"like": 0, "dislike": 0, "to_watch": 0, "skip": 0}
    genre_counts = Counter()
    director_counts = Counter()
    actor_counts = Counter()

    for movie_id, data in preferences.items():
        choice = data if isinstance(data, str) else data.get("choice", "")
        genre_ids = [] if isinstance(data, str) else data.get("genre_ids", [])

        if choice in counts:
            counts[choice] += 1

        if choice == "like":
            for gid in genre_ids:
                name = genres_map.get(gid)
                if name:
                    genre_counts[name] += 1

            credits = fetch_movie_credits(int(movie_id))
            if credits.get("director"):
                director_counts[credits["director"]] += 1
            for actor in credits.get("cast", []):
                actor_counts[actor["name"]] += 1

    def with_pct(counter, n):
        top = counter.most_common(n)
        max_count = top[0][1] if top else 1
        return [(name, count, int(count / max_count * 100)) for name, count in top]

    return {
        "counts": counts,
        "total_rated": sum(counts.values()),
        "top_genres":    with_pct(genre_counts, 8),
        "top_directors": with_pct(director_counts, 5),
        "top_actors":    with_pct(actor_counts, 5),
    }
