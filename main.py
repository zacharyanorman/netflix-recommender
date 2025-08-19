# import the requests module and API values from secrets.py
import requests
from genres import genres_list
from secrets import netflix_api_key
from secrets import omdb_api_key

# asks user for genre and makes lower case and strips
genre = input("What genre would you like to watch tonight? ").lower().strip()

# makes imported genre list lowercase
lowercase_genres_list = {
    k: v.lower() if isinstance(v, str) else v
    for k, v in genres_list.items()
}

# finds all genres that contain user input of genre
matching_genres = []
for key, value in lowercase_genres_list.items():
    if isinstance(value, str) and genre in value:
        matching_genres.append(key)

# tells user that it is searching for the genre in question
print(
    f"OK, {genre}. Let's see what is available in the United States on Netflix..."
)

# run search based on genre matches (currently only searches one value)
rec = []
for i in matching_genres:
    response = requests.get("https://unogsng.p.rapidapi.com/search",
                            headers={
                                "X-RapidAPI-Key": netflix_api_key,
                                "X-RapidAPI-Host": "unogsng.p.rapidapi.com"
                            },
                            params={
                                "genrelist": i,
                                "countrylist": "78",
                                "limit": "10"
                            })
    # appends the total list of recommendations to the "rec" variable
    data = response.json()
    if 'results' in data:
        for movie in data['results']:
            rec.append(movie['title'])
    else:
        continue
        #print(f"No results for genre ID {i}. API response was: {data}")

# replace all spaces with + in new var "rec_plus"
rec_plus = []
for i in range(len(rec)):
    rec_plus.append(rec[i].replace(" ", "+"))

# pulls imdb review values from omdb API
rec_ratings = []
for i in rec:
    response_omdb = requests.get("http://www.omdbapi.com/?t=" + i +
                                 "&apikey=" + omdb_api_key)
    data_omdb = response_omdb.json()
    if 'Ratings' in data_omdb:
        for rating in data_omdb['Ratings']:
            if rating['Source'] == 'Internet Movie Database':
                rec_ratings.append((rating['Value']))
                break  # stop search after finding RT rating
        else:
            rec_ratings.append(("No Ratings found"))
    else:
        rec_ratings.append(("No Ratings found"))

# Take list of movies and ratings and combine into single dictionary
zipped_rec = zip(rec, rec_ratings)
final_recs_dict = dict(zipped_rec)

# removies entries without ratings
final_recs_dict = {
    k: v
    for k, v in final_recs_dict.items() if v != "No Ratings found"
}

# organizes list by reverse alphabetical order
sorted_final = sorted(final_recs_dict.items(),
                      key=lambda item: float(item[1].split('/')[0]),
                      reverse=True)

# prints recommendations
print("Here are the movies and TV in that genre, sorted by IMDb rating:\n")
for key, value in sorted_final:
    print(f"{key}: {value}")
