import json
import threading
from datetime import date, timedelta
from urllib.parse import urlencode

from flask import Flask, render_template, redirect, url_for, request

from preferences import get_preference, load_preferences, save_preference
from recommendations import ALGORITHMS, get_recommendations
from stats import compute_stats
from tmdb import fetch_genres, fetch_movie_credits, fetch_movie_details, fetch_movie_keywords, fetch_movie_trailer, fetch_movies, get_poster_url

app = Flask(__name__)

PER_PAGE = 20

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# --- Préchargement en arrière-plan ---

_preload_lock = threading.Lock()
_preload_started = False


def _preload_all():
    for movie in fetch_movies():
        mid = movie["id"]
        fetch_movie_credits(mid)
        fetch_movie_keywords(mid)
        fetch_movie_details(mid)


@app.before_request
def preload_on_first_request():
    global _preload_started
    with _preload_lock:
        if not _preload_started:
            _preload_started = True
            threading.Thread(target=_preload_all, daemon=True).start()


# --- Helpers ---

@app.template_global()
def update_url(**kwargs):
    params = request.args.to_dict()
    for k, v in kwargs.items():
        if v is None or v == "":
            params.pop(k, None)
        else:
            params[k] = str(v)
    return "?" + urlencode(params) if params else "?"


def _week_start(d):
    return d - timedelta(days=d.weekday())


def _format_week(ws):
    we = ws + timedelta(days=6)
    if ws.month == we.month:
        return f"Semaine du {ws.day} au {we.day} {MONTHS_FR[we.month - 1]} {we.year}"
    return (f"Semaine du {ws.day} {MONTHS_FR[ws.month - 1]}"
            f" au {we.day} {MONTHS_FR[we.month - 1]} {we.year}")


# --- Routes ---

@app.route("/")
def index():
    return redirect(url_for("upcoming"))


@app.route("/upcoming")
def upcoming():
    all_movies = fetch_movies()
    genres_map = fetch_genres()
    today = date.today()

    # Films à venir uniquement
    future = [m for m in all_movies if m.get("release_date", "") >= today.isoformat()]

    # Grouper par semaine
    weeks_dict = {}
    for movie in future:
        ws = _week_start(date.fromisoformat(movie["release_date"]))
        weeks_dict.setdefault(ws, []).append(movie)
    sorted_weeks = sorted(weeks_dict.items())

    # Semaine sélectionnée
    week_idx = request.args.get("week", 0, type=int)
    week_idx = max(0, min(week_idx, len(sorted_weeks) - 1)) if sorted_weeks else 0

    if sorted_weeks:
        selected_ws, selected_movies = sorted_weeks[week_idx]
    else:
        selected_ws, selected_movies = today, []

    week_labels = [(i, _format_week(ws), len(movies))
                   for i, (ws, movies) in enumerate(sorted_weeks)]

    return render_template(
        "upcoming.html",
        week_labels=week_labels,
        selected_week=week_idx,
        selected_week_label=_format_week(selected_ws) if sorted_weeks else "",
        selected_movies=selected_movies,
        genres_map=genres_map,
        get_preference=get_preference,
        get_poster_url=get_poster_url,
        get_credits=fetch_movie_credits,
    )


@app.route("/movies")
def movies():
    all_movies = fetch_movies()
    genres_map = fetch_genres()

    display = list(all_movies)

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

    # Genres disponibles
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
    paged = display[(page - 1) * PER_PAGE: page * PER_PAGE]

    return render_template(
        "movies.html",
        movies=paged,
        genres_map=genres_map,
        available_genres=available_genres,
        active_genre=active_genre,
        sort=sort,
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
    next_url = request.form.get("next_url", url_for("upcoming"))

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
    today = date.today().isoformat()

    show = request.args.get("show", "all")
    if show == "upcoming":
        filtered_movies = [m for m in all_movies if m.get("release_date", "") >= today]
    elif show == "past":
        filtered_movies = [m for m in all_movies if m.get("release_date", "") < today]
    else:
        filtered_movies = all_movies

    algo = request.args.get("algo", "combined")
    if algo not in {a for a, _ in ALGORITHMS}:
        algo = "combined"

    results = get_recommendations(filtered_movies, preferences, genres_map, algo=algo)

    return render_template(
        "recommendations.html",
        results=results,
        genres_map=genres_map,
        get_poster_url=get_poster_url,
        get_preference=get_preference,
        get_credits=fetch_movie_credits,
        has_preferences=bool(preferences),
        show=show,
        algo=algo,
        algorithms=ALGORITHMS,
    )


@app.route("/stats")
def stats():
    preferences = load_preferences()
    genres_map = fetch_genres()
    data = compute_stats(preferences, genres_map)
    return render_template("stats.html", **data)


if __name__ == "__main__":
    app.run(debug=True)
