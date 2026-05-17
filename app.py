import json
import threading
from datetime import date
from urllib.parse import urlencode

from flask import Flask, render_template, redirect, url_for, request

from preferences import get_preference, load_preferences, save_preference
from recommendations import get_recommendations
from stats import compute_stats
from tmdb import fetch_genres, fetch_movie_credits, fetch_movie_trailer, fetch_movies, get_poster_url

app = Flask(__name__)

PER_PAGE = 20

# --- Préchargement en arrière-plan ---

_preload_lock = threading.Lock()
_preload_started = False


def _preload_credits():
    for movie in fetch_movies():
        fetch_movie_credits(movie["id"])


@app.before_request
def preload_on_first_request():
    global _preload_started
    with _preload_lock:
        if not _preload_started:
            _preload_started = True
            threading.Thread(target=_preload_credits, daemon=True).start()


# --- Helper URL ---

@app.template_global()
def update_url(**kwargs):
    params = request.args.to_dict()
    for k, v in kwargs.items():
        if v is None or v == "":
            params.pop(k, None)
        else:
            params[k] = str(v)
    return "?" + urlencode(params) if params else "?"


# --- Routes ---

@app.route("/")
def index():
    return redirect(url_for("recommendations"))


@app.route("/movies")
def movies():
    all_movies = fetch_movies()
    genres_map = fetch_genres()
    today = date.today().isoformat()

    # Filtre passé / à venir
    show = request.args.get("show", "upcoming")
    display = [m for m in all_movies if m.get("release_date", "") >= today] if show == "upcoming" else all_movies

    # Filtre par notation
    rating_filter = request.args.get("rating", "all")
    if rating_filter == "like":
        display = [m for m in display if get_preference(m["id"]) == "like"]
    elif rating_filter == "dislike":
        display = [m for m in display if get_preference(m["id"]) == "dislike"]
    elif rating_filter == "to_watch":
        display = [m for m in display if get_preference(m["id"]) == "to_watch"]
    elif rating_filter == "unrated":
        display = [m for m in display if get_preference(m["id"]) is None]

    # Recherche
    q = request.args.get("q", "").strip()
    if q:
        q_lower = q.lower()
        display = [m for m in display if q_lower in m.get("title", "").lower()]

    # Genres disponibles (après les filtres précédents)
    genre_ids_in_use = {g for m in display for g in m.get("genre_ids", [])}
    available_genres = sorted(
        [(gid, genres_map.get(gid, str(gid))) for gid in genre_ids_in_use],
        key=lambda x: x[1],
    )

    # Filtre par genre
    active_genre = request.args.get("genre", type=int)
    if active_genre:
        display = [m for m in display if active_genre in m.get("genre_ids", [])]

    # Tri
    sort = request.args.get("sort", "release_date")
    if sort == "vote_average":
        display = sorted(display, key=lambda m: m.get("vote_average", 0), reverse=True)
    elif sort == "popularity":
        display = sorted(display, key=lambda m: m.get("popularity", 0), reverse=True)

    # Pagination
    total = len(display)
    page = max(1, request.args.get("page", 1, type=int))
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    paged = display[(page - 1) * PER_PAGE : page * PER_PAGE]

    return render_template(
        "movies.html",
        movies=paged,
        genres_map=genres_map,
        available_genres=available_genres,
        active_genre=active_genre,
        sort=sort,
        show=show,
        rating_filter=rating_filter,
        q=q,
        page=page,
        total_pages=total_pages,
        total=total,
        get_preference=get_preference,
        get_poster_url=get_poster_url,
        get_credits=fetch_movie_credits,
    )


@app.route("/rate", methods=["POST"])
def rate():
    movie_id = request.form["movie_id"]
    choice = request.form["choice"]
    genre_ids = json.loads(request.form.get("genre_ids", "[]"))
    title = request.form.get("title", "")
    next_url = request.form.get("next_url", url_for("movies"))

    save_preference(movie_id, choice, genre_ids=genre_ids, title=title)
    return redirect(next_url)


@app.route("/trailer/<int:movie_id>")
def trailer(movie_id):
    url = fetch_movie_trailer(movie_id)
    if url:
        return redirect(url)
    return "Aucune bande-annonce disponible.", 404


@app.route("/recommendations")
def recommendations():
    all_movies = fetch_movies()
    preferences = load_preferences()
    genres_map = fetch_genres()

    results = get_recommendations(all_movies, preferences, genres_map)

    return render_template(
        "recommendations.html",
        results=results,
        genres_map=genres_map,
        get_poster_url=get_poster_url,
        get_preference=get_preference,
        get_credits=fetch_movie_credits,
        has_preferences=bool(preferences),
    )


@app.route("/stats")
def stats():
    preferences = load_preferences()
    genres_map = fetch_genres()
    data = compute_stats(preferences, genres_map)

    return render_template("stats.html", **data)


if __name__ == "__main__":
    app.run(debug=True)
