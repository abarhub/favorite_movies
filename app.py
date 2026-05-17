from flask import Flask, render_template, redirect, url_for, request

from preferences import get_preference, save_preference
from tmdb import fetch_upcoming_movies, get_poster_url

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
    movie_id = movie["id"]

    return render_template(
        "index.html",
        movie=movie,
        poster_url=get_poster_url(movie.get("poster_path")),
        preference=get_preference(movie_id),
        index=current,
        total=len(movies),
    )


@app.route("/rate", methods=["POST"])
def rate():
    movie_id = request.form["movie_id"]
    choice = request.form["choice"]
    next_index = int(request.form["next_index"])

    save_preference(movie_id, choice)
    return redirect(url_for("index", index=next_index))


@app.route("/reset")
def reset():
    return redirect(url_for("index", index=0))


if __name__ == "__main__":
    app.run(debug=True)
