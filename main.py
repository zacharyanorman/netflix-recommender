import os
import requests
import pandas as pd
import streamlit as st
import gdown
from genres import genres_list

from difflib import get_close_matches

st.set_page_config(page_title="Netflix Recommender", layout="centered")
st.title("🎬 Netflix Recommender")
st.write("Get top-rated movies and TV shows on Netflix by genre.")

# Load API key from Streamlit secrets
netflix_api_key = st.secrets["netflix_api_key"]

# Only download IMDb files if not already present
if not os.path.exists("title.basics.tsv"):
    gdown.download(id="18P42Sr33qRbiE91_n2J4f6nJrsWSF-mU", output="title.basics.tsv", quiet=False)
if not os.path.exists("title.ratings.tsv"):
    gdown.download(id="10Orbx6H-wQWIQ7w9t7H9s-mnAzQpEpY1", output="title.ratings.tsv", quiet=False)

# Genre input
user_input = st.text_input("What genre would you like to watch tonight?").lower().strip()

if user_input:
    # Step 1: Match genre
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
        st.markdown(f"**Top matching genres:** {', '.join([genre_names[i] for i in top_indices])}")
    except ImportError:
        matching_genres = [k for k, v in genres_list.items() if user_input in v.lower()]
        st.markdown(f"**Matched genres:** {', '.join(matching_genres)}")

    if not matching_genres:
        st.warning("No matching genres found.")
    else:
        all_titles = []
        with st.spinner("🔍 Searching Netflix..."):
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
                    titles = [item['title'] for item in data['results']]
                    all_titles.extend(titles)

        # Step 2: Lazy load only if needed
        with st.spinner("📂 Loading IMDb data..."):
            basics = pd.read_csv("title.basics.tsv", sep="\t", na_values="\\N", usecols=["tconst", "primaryTitle", "titleType"], low_memory=False)
            ratings = pd.read_csv("title.ratings.tsv", sep="\t", na_values="\\N")

        # Step 3: Filter basics for titles that might match Netflix results
        basics_subset = basics[basics["primaryTitle"].str.lower().isin([t.lower() for t in all_titles])]

        # Step 4: Fuzzy matching function
        def get_rating(title):
            candidates = get_close_matches(title, basics_subset["primaryTitle"].tolist(), n=1, cutoff=0.85)
            if candidates:
                match = candidates[0]
                row = basics_subset[basics_subset["primaryTitle"] == match]
                if not row.empty:
                    merged = row.merge(ratings, on="tconst", how="left").dropna(subset=["averageRating"])
                    if not merged.empty:
                        return {
                            "title": title,
                            "rating": merged["averageRating"].iloc[0],
                            "type": merged["titleType"].iloc[0]
                        }
            return None

        # Step 5: Match and score
        rated_titles = [r for t in all_titles if (r := get_rating(t))]
        top_movies = sorted([r for r in rated_titles if r["type"] == "movie"], key=lambda x: x["rating"], reverse=True)[:5]
        top_shows = sorted([r for r in rated_titles if r["type"] in ["tvSeries", "tvMiniSeries"]], key=lambda x: x["rating"], reverse=True)[:5]

        # Step 6: Display results
        if top_movies:
            st.subheader("🎬 Top 5 Movies")
            for m in top_movies:
                st.write(f"**{m['title']}** — IMDb: {m['rating']}")

        if top_shows:
            st.subheader("📺 Top 5 TV Shows")
            for s in top_shows:
                st.write(f"**{s['title']}** — IMDb: {s['rating']}")

        if not top_movies and not top_shows:
            st.info("No IMDb-rated titles found.")
