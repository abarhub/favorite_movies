import json

from flask import Flask, render_template, redirect, url_for, request

from preferences import get_preference, load_preferences, save_preference
from recommendations import get_recommendations
from tmdb import fetch_genres, fetch_movie_trailer, fetch_upcoming_movies, get_poster_url

app = Flask(__name__)


@app.route("/")
def index():
    return redirect(url_for("recommendations"))


@app.route("/movies")
def movies():
    all_movies = fetch_upcoming_movies()
    genres_map = fetch_genres()

    # Genres présents dans la liste actuelle, triés alphabétiquement
    genre_ids_in_use = {g for m in all_movies for g in m.get("genre_ids", [])}
    available_genres = sorted(
        [(gid, genres_map.get(gid, str(gid))) for gid in genre_ids_in_use],
        key=lambda x: x[1],
    )

    # Filtre par genre
    active_genre = request.args.get("genre", type=int)
    filtered = all_movies
    if active_genre:
        filtered = [m for m in all_movies if active_genre in m.get("genre_ids", [])]

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
        get_preference=get_preference,
        get_poster_url=get_poster_url,
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
    all_movies = fetch_upcoming_movies()
    preferences = load_preferences()
    genres_map = fetch_genres()

    results = get_recommendations(all_movies, preferences, genres_map)

    return render_template(
        "recommendations.html",
        results=results,
        genres_map=genres_map,
        get_poster_url=get_poster_url,
        get_preference=get_preference,
        has_preferences=bool(preferences),
    )


if __name__ == "__main__":
    app.run(debug=True)
