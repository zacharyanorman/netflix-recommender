import os
import requests
import pandas as pd
import streamlit as st

from genres import genres_list

# Load Netflix API key from Streamlit secrets
netflix_api_key = st.secrets["netflix_api_key"]

# Streamlit UI
st.title("🎬 Netflix Recommender")
st.write("Get top-rated movies and TV shows on Netflix based on your favorite genre.")

# Load pre-trimmed IMDb basics file from local directory
try:
    basics = pd.read_csv("title.basics_reduced.tsv", sep="\t", na_values="\\N")
except FileNotFoundError:
    st.error("❌ IMDb file 'title.basics_reduced.tsv' not found.")
    st.stop()

# Load ratings (still small)
try:
    ratings = pd.read_csv("title.ratings.tsv", sep="\t", na_values="\\N")
except FileNotFoundError:
    st.error("❌ IMDb file 'title.ratings.tsv' not found.")
    st.stop()

# User input for genre
user_input = st.text_input("What genre would you like to watch tonight?").lower().strip()

if user_input:
    # Try fuzzy genre matching using sentence-transformers
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
        top_matches = [genre_names[i] for i in top_indices]

        st.markdown(f"**Top matching genres:** {', '.join(top_matches)}")

    except ImportError:
        # Fallback: simple substring match
        matching_genres = [k for k, v in genres_list.items() if user_input in v.lower()]
        st.markdown(f"**Matched genres:** {', '.join(matching_genres)}")

    if not matching_genres:
        st.warning("No matching genres found.")
    else:
        all_titles = []
        with st.spinner("Searching Netflix..."):
            for genre_id in matching_genres:
                response = requests.get(
                    "https://unogsng.p.rapidapi.com/search",
                    headers={
                        "X-RapidAPI-Key": netflix_api_key,
                        "X-RapidAPI-Host": "unogsng.p.rapidapi.com"
                    },
                    params={
                        "genrelist": genre_id,
                        "countrylist": "78",  # United States
                        "limit": "100"
                    }
                )
                data = response.json()
                if "results" in data:
                    genre_titles = [item['title'] for item in data['results']]
                    all_titles.extend(genre_titles)

        # Match with IMDb ratings
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

        rated_titles = [r for t in all_titles if (r := get_rating(t))]

        # Sort and filter top 5 for movies and TV
        movies = sorted(
            [r for r in rated_titles if r["type"] == "movie"],
            key=lambda x: x["rating"],
            reverse=True
        )[:5]

        tv_shows = sorted(
            [r for r in rated_titles if r["type"] in ["tvSeries", "tvMiniSeries"]],
            key=lambda x: x["rating"],
            reverse=True
        )[:5]

        if movies:
            st.subheader("🎬 Top 5 Movies")
            for m in movies:
                st.write(f"**{m['title']}** — IMDb: {m['rating']}")

        if tv_shows:
            st.subheader("📺 Top 5 TV Shows")
            for s in tv_shows:
                st.write(f"**{s['title']}** — IMDb: {s['rating']}")

        if not movies and not tv_shows:
            st.info("No rated results found.")
