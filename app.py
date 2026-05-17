import json
from datetime import date

from flask import Flask, render_template, redirect, url_for, request

from preferences import get_preference, load_preferences, save_preference
from recommendations import get_recommendations
from tmdb import fetch_genres, fetch_movie_credits, fetch_movie_trailer, fetch_movies, get_poster_url

app = Flask(__name__)


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
    if show == "upcoming":
        display_movies = [m for m in all_movies if m.get("release_date", "") >= today]
    else:
        display_movies = all_movies

    # Genres présents dans la sélection courante, triés alphabétiquement
    genre_ids_in_use = {g for m in display_movies for g in m.get("genre_ids", [])}
    available_genres = sorted(
        [(gid, genres_map.get(gid, str(gid))) for gid in genre_ids_in_use],
        key=lambda x: x[1],
    )

    # Filtre par notation
    rating_filter = request.args.get("rating", "all")
    if rating_filter == "like":
        display_movies = [m for m in display_movies if get_preference(m["id"]) == "like"]
    elif rating_filter == "dislike":
        display_movies = [m for m in display_movies if get_preference(m["id"]) == "dislike"]
    elif rating_filter == "unrated":
        display_movies = [m for m in display_movies if get_preference(m["id"]) is None]

    # Genres présents après filtre notation, triés alphabétiquement
    genre_ids_in_use = {g for m in display_movies for g in m.get("genre_ids", [])}
    available_genres = sorted(
        [(gid, genres_map.get(gid, str(gid))) for gid in genre_ids_in_use],
        key=lambda x: x[1],
    )

    # Filtre par genre
    active_genre = request.args.get("genre", type=int)
    filtered = display_movies
    if active_genre:
        filtered = [m for m in display_movies if active_genre in m.get("genre_ids", [])]

    # Tri
    sort = request.args.get("sort", "release_date")
    if sort == "vote_average":
        filtered = sorted(filtered, key=lambda m: m.get("vote_average", 0), reverse=True)
    elif sort == "popularity":
        filtered = sorted(filtered, key=lambda m: m.get("popularity", 0), reverse=True)

    return render_template(
        "movies.html",
        movies=filtered,
        genres_map=genres_map,
        available_genres=available_genres,
        active_genre=active_genre,
        sort=sort,
        show=show,
        rating_filter=rating_filter,
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


if __name__ == "__main__":
    app.run(debug=True)
