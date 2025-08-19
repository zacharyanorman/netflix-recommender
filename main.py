import requests
import pandas as pd
from genres import genres_list
from my_secrets import netflix_api_key

# Load IMDb datasets
basics = pd.read_csv("title.basics.tsv", sep="\t", na_values="\\N", low_memory=False)
ratings = pd.read_csv("title.ratings.tsv", sep="\t")

df = pd.merge(basics, ratings, on="tconst")
df = df[df["numVotes"] >= 500]  # filter out low vote counts

def clean_title(title):
    return title.lower().strip()

# Prompt user
user_input = input("What genre would you like to watch tonight? ").lower().strip()

# Optional semantic matching
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    model = SentenceTransformer('all-MiniLM-L6-v2')
    genre_names = list(genres_list.values())
    genre_embeddings = model.encode(genre_names)
    user_embedding = model.encode([user_input])
    scores = cosine_similarity(user_embedding, genre_embeddings)[0]
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
    matching_genres = [list(genres_list.keys())[i] for i in top_indices]
    print(f"Top matches: {[genre_names[i] for i in top_indices]}")
except ImportError:
    # fallback
    lowercase_genres_list = {
        k: v.lower() if isinstance(v, str) else v for k, v in genres_list.items()
    }
    matching_genres = [k for k, v in lowercase_genres_list.items() if user_input in v]

print(f"\nSearching for '{user_input}' on Netflix US...\n")

# Get Netflix titles
rec_set = set()
for genre_id in matching_genres:
    response = requests.get("https://unogsng.p.rapidapi.com/search",
                            headers={
                                "X-RapidAPI-Key": netflix_api_key,
                                "X-RapidAPI-Host": "unogsng.p.rapidapi.com"
                            },
                            params={
                                "genrelist": genre_id,
                                "countrylist": "78",
                                "limit": "20"
                            })
    data = response.json()
    titles = [movie['title'] for movie in data.get('results', [])]
    rec_set.update(titles)
    print(f"Results for genre {genre_id}: {titles}")

# Remove duplicates and clean titles
rec_clean = list({clean_title(title): title for title in rec_set}.values())

# Match against IMDb dataset
matched_titles = []
for title in rec_clean:
    cleaned = clean_title(title)
    matches = df[df['primaryTitle'].str.lower() == cleaned]
    if not matches.empty:
        top_match = matches.sort_values(by="averageRating", ascending=False).iloc[0]
        matched_titles.append((title, top_match['averageRating'], top_match['titleType']))

# Separate and sort
movies = [(t, r) for t, r, typ in matched_titles if typ == 'movie']
tv = [(t, r) for t, r, typ in matched_titles if typ in ['tvSeries', 'tvMiniSeries']]

movies_sorted = sorted(movies, key=lambda x: x[1], reverse=True)[:5]
tv_sorted = sorted(tv, key=lambda x: x[1], reverse=True)[:5]

# Display
print("\nTop 5 Movies:")
for title, rating in movies_sorted:
    print(f"{title}: {rating}")

print("\nTop 5 TV Shows:")
for title, rating in tv_sorted:
    print(f"{title}: {rating}")
