import os
import requests
import pandas as pd
import gdown
import streamlit as st

from genres import genres_list

# Load API key from Streamlit secrets
netflix_api_key = st.secrets["netflix_api_key"]

# Download IMDb TSVs from Google Drive if not already present
if not os.path.exists("title.basics.tsv"):
    gdown.download(id="18P42Sr33qRbiE91_n2J4f6nJrsWSF-mU", output="title.basics.tsv", quiet=False)

if not os.path.exists("title.ratings.tsv"):
    gdown.download(id="10Orbx6H-wQWIQ7w9t7H9s-mnAzQpEpY1", output="title.ratings.tsv", quiet=False)

# Load IMDb datasets
basics = pd.read_csv("title.basics.tsv", sep="\t", na_values="\\N", low_memory=False)
ratings = pd.read_csv("title.ratings.tsv", sep="\t", na_values="\\N")

# --- UI Setup ---
st.title("🎬 Netflix Recommender")
user_input = st.text_input("What genre are you in the mood for tonight?").lower().strip()

if user_input:
    # Optional: sentence-transformers fuzzy matching
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
        st.write("Top matches:", [genre_names[i] for i in top_indices])
    except ImportError:
        # Fallback: basic substring match
        matching_genres = [k for k, v in genres_list.items() if user_input in v.lower()]

    st.write(f"Searching for *{user_input}* on Netflix US...")

    # Collect titles
    all_titles = []
    for genre_id in matching_genres:
        response = requests.get(
            "https://unogsng.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": netflix_api_key,
                "X-RapidAPI-Host": "unogsng.p.rapidapi.com"
            },
            params={
                "genrelist": genre_id,
                "countrylist": "78",
                "limit": "100"
            }
        )
        data = response.json()
        if "results" in data:
            genre_titles = [item['title'] for item in data['results']]
            all_titles.extend(genre_titles)

    # IMDb rating match
    def get_rating(title):
        matches = basics[basics['primaryTitle'].str.lower() == title.lower()]
        if not matches.empty:
            merged = matches.merge(ratings, on='tconst', how='left')
            merged = merged.dropna(subset=['averageRating'])
            if not merged.empty:
                return {
                    "title": title,
                    "rating": merged['averageRating'].iloc[0],
                    "type": merged['titleType'].iloc[0]
                }
        return None

    rated_titles = []
    for t in all_titles:
        r = get_rating(t)
        if r:
            rated_titles.append(r)

    # Sort and split
    movies = sorted(
        [r for r in rated_titles if r["type"] == "movie"],
        key=lambda x: x["rating"], reverse=True)[:5]
    tv_shows = sorted(
        [r for r in rated_titles if r["type"] in ["tvSeries", "tvMiniSeries"]],
        key=lambda x: x["rating"], reverse=True)[:5]

    # Show results
    if movies:
        st.subheader("🎬 Top 5 Movies:")
        for m in movies:
            st.write(f"**{m['title']}** — {m['rating']} ⭐")

    if tv_shows:
        st.subheader("📺 Top 5 TV Shows:")
        for s in tv_shows:
            st.write(f"**{s['title']}** — {s['rating']} ⭐")

    if not movies and not tv_shows:
        st.info("No IMDb ratings found for these titles.")