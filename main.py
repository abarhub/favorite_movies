# This is a sample Python script.
import os


# Press Maj+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


import requests
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_TOKEN")

today = date.today()
next_week = today + timedelta(days=7)

url = "https://api.themoviedb.org/3/discover/movie"

params = {
    "api_key": API_KEY,
    "language": "fr-FR",
    "region": "FR",
    "sort_by": "primary_release_date.asc",
    "primary_release_date.gte": today.isoformat(),
    "primary_release_date.lte": next_week.isoformat()
}

r = requests.get(url, params=params)
movies = r.json()["results"]

print(movies)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
