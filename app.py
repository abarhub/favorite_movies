import json

from flask import Flask, render_template, redirect, url_for, request

from preferences import get_preference, load_preferences, save_preference
from recommendations import get_recommendations
from tmdb import fetch_genres, fetch_upcoming_movies, get_poster_url

app = Flask(__name__)


@app.route("/")
def index():
    movies = fetch_upcoming_movies()
    current = int(request.args.get("index", 0))

    if not movies or current >= len(movies):
        likes = sum(1 for m in movies if get_preference(m["id"]) == "like")
        dislikes = sum(1 for m in movies if get_preference(m["id"]) == "dislike")
        return render_template("done.html", total=len(movies), likes=likes, dislikes=dislikes)

    movie = movies[current]

    return render_template(
        "index.html",
        movie=movie,
        poster_url=get_poster_url(movie.get("poster_path")),
        preference=get_preference(movie["id"]),
        index=current,
        total=len(movies),
    )


@app.route("/rate", methods=["POST"])
def rate():
    movie_id = request.form["movie_id"]
    choice = request.form["choice"]
    next_index = int(request.form["next_index"])
    genre_ids = json.loads(request.form.get("genre_ids", "[]"))
    title = request.form.get("title", "")

    save_preference(movie_id, choice, genre_ids=genre_ids, title=title)
    return redirect(url_for("index", index=next_index))


@app.route("/recommendations")
def recommendations():
    movies = fetch_upcoming_movies()
    preferences = load_preferences()
    genres_map = fetch_genres()

    results = get_recommendations(movies, preferences, genres_map)

    return render_template(
        "recommendations.html",
        results=results,
        genres_map=genres_map,
        get_poster_url=get_poster_url,
        has_preferences=bool(preferences),
    )


@app.route("/reset")
def reset():
    return redirect(url_for("index", index=0))


if __name__ == "__main__":
    app.run(debug=True)
