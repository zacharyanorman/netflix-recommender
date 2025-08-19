import os
import requests
import pandas as pd
import streamlit as st
import gdown
from genres import genres_list
from difflib import get_close_matches

# --- Load API Key ---
netflix_api_key = st.secrets["netflix_api_key"]

# --- Streamlit UI ---
st.title("🎬 Netflix Recommender")
st.write("Enter a genre to get top-rated Netflix movies and TV shows (IMDb-sorted).")

# --- Download IMDb files (only if needed) ---
basics_file = "title.basics.tsv"
ratings_file = "title.ratings.tsv"

if not os.path.exists(basics_file):
    gdown.download(id="18P42Sr33qRbiE91_n2J4f6nJrsWSF-mU", output=basics_file, quiet=False)

if not os.path.exists(ratings_file):
    gdown.download(id="10Orbx6H-wQWIQ7w9t7H9s-mnAzQpEpY1", output=ratings_file, quiet=False)

# --- Get User Input ---
user_input = st.text_input("What genre would you like to watch tonight?").lower().strip()

if user_input:
    # --- Genre Matching ---
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity

        model = SentenceTransformer("all-MiniLM-L6-v2")
        genre_names = list(genres_list.values())
        genre_embeddings = model.encode(genre_names)
        user_embedding = model.encode([user_input])
        scores = cosine_similarity(user_embedding, genre_embeddings)[0]
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
        matching_genres = [list(genres_list.keys())[i] for i in top_indices]
        st.markdown(f"**Top matching genres:** {', '.join([genre_names[i] for i in top_indices])}")
    except Exception:
        matching_genres = [k for k, v in genres_list.items() if user_input in v.lower()]
        st.markdown(f"**Matched genres:** {', '.join(matching_genres)}")

    if not matching_genres:
        st.warning("No matching genres found.")
    else:
        # --- Query Netflix API ---
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
                        "countrylist": "78",
                        "limit": "100"
                    }
                )
                if response.ok:
                    data = response.json()
                    if "results" in data:
                        titles = [item['title'] for item in data['results'] if 'title' in item]
                        all_titles.extend(titles)

        # --- Load Only Required IMDb Columns ---
        basics = pd.read_csv(basics_file, sep="\t", usecols=["tconst", "primaryTitle", "titleType"], na_values="\\N", low_memory=False)
        ratings = pd.read_csv(ratings_file, sep="\t", usecols=["tconst", "averageRating"], na_values="\\N")

        # --- Fuzzy Matching and Rating Lookup ---
        imdb_titles = basics["primaryTitle"].dropna().unique().tolist()

        results = []
        for title in all_titles:
            match = get_close_matches(title, imdb_titles, n=1, cutoff=0.8)
            if match:
                matched_title = match[0]
                entry = basics[basics["primaryTitle"] == matched_title]
                merged = entry.merge(ratings, on="tconst", how="left").dropna(subset=["averageRating"])
                if not merged.empty:
                    results.append({
                        "title": matched_title,
                        "rating": merged["averageRating"].iloc[0],
                        "type": merged["titleType"].iloc[0]
                    })

        # --- Display Results ---
        movies = sorted([r for r in results if r["type"] == "movie"], key=lambda x: x["rating"], reverse=True)[:5]
        shows = sorted([r for r in results if r["type"] in ["tvSeries", "tvMiniSeries"]], key=lambda x: x["rating"], reverse=True)[:5]

        if movies:
            st.subheader("🎬 Top 5 Movies")
            for m in movies:
                st.write(f"**{m['title']}** — IMDb: {m['rating']}")

        if shows:
            st.subheader("📺 Top 5 TV Shows")
            for s in shows:
                st.write(f"**{s['title']}** — IMDb: {s['rating']}")

        if not movies and not shows:
            st.info("No matching IMDb ratings found.")
