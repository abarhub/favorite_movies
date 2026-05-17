import os
import json
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"
PREFERENCES_FILE = Path("preferences.json")


def fetch_upcoming_movies(days=7):
    today = date.today()
    end_date = today + timedelta(days=days)

    params = {
        "api_key": API_KEY,
        "language": "fr-FR",
        "region": "FR",
        "sort_by": "primary_release_date.asc",
        "primary_release_date.gte": today.isoformat(),
        "primary_release_date.lte": end_date.isoformat(),
    }

    r = requests.get(f"{BASE_URL}/discover/movie", params=params)
    r.raise_for_status()
    return r.json().get("results", [])


def load_preferences():
    if PREFERENCES_FILE.exists():
        return json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
    return {}


def save_preferences(preferences):
    PREFERENCES_FILE.write_text(
        json.dumps(preferences, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def display_movie(movie, index, total):
    title = movie.get("title", "Titre inconnu")
    release_date = movie.get("release_date", "Date inconnue")
    vote = movie.get("vote_average", 0)
    vote_count = movie.get("vote_count", 0)
    overview = movie.get("overview") or "Pas de synopsis disponible."

    print(f"\n{'─' * 60}")
    print(f"  Film {index}/{total}")
    print(f"  {title}")
    print(f"  Sortie : {release_date}  |  Note : {vote:.1f}/10 ({vote_count} votes)")
    print()
    if len(overview) > 300:
        overview = overview[:297] + "..."
    print(f"  {overview}")
    print(f"{'─' * 60}")


def ask_preference(movie, preferences):
    movie_id = str(movie["id"])
    title = movie.get("title", "")

    already = preferences.get(movie_id)
    if already:
        label = {"like": "👍 aimé", "dislike": "👎 pas aimé", "skip": "⏭ ignoré"}.get(already, already)
        print(f"  (Déjà noté : {label})")

    print("\n  [o] J'aime   [n] Je n'aime pas   [p] Passer   [q] Quitter")
    while True:
        choix = input("  Votre choix : ").strip().lower()
        if choix == "o":
            preferences[movie_id] = "like"
            print(f"  ✓ \"{title}\" ajouté aux films aimés.")
            break
        elif choix == "n":
            preferences[movie_id] = "dislike"
            print(f"  ✓ \"{title}\" ajouté aux films non aimés.")
            break
        elif choix == "p":
            preferences[movie_id] = "skip"
            print(f"  ✓ Film ignoré.")
            break
        elif choix == "q":
            return False
        else:
            print("  Touche invalide. Utilisez o, n, p ou q.")
    return True


def main():
    print("Films à venir dans les 7 prochains jours en France")

    movies = fetch_upcoming_movies(days=7)

    if not movies:
        print("Aucun film trouvé pour cette période.")
        return

    preferences = load_preferences()
    total = len(movies)
    print(f"{total} film(s) trouvé(s). Naviguez avec o/n/p, quittez avec q.\n")

    for i, movie in enumerate(movies, start=1):
        display_movie(movie, i, total)
        continuer = ask_preference(movie, preferences)
        save_preferences(preferences)
        if not continuer:
            print("\nAu revoir !")
            break
    else:
        print("\nVous avez parcouru tous les films !")

    likes = sum(1 for v in preferences.values() if v == "like")
    dislikes = sum(1 for v in preferences.values() if v == "dislike")
    print(f"Préférences enregistrées : {likes} aimé(s), {dislikes} non aimé(s).")


if __name__ == "__main__":
    main()
