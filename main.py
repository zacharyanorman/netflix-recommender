import os
import requests
import pandas as pd
import streamlit as st
import gdown

from genres import genres_list

# Load Netflix API key
netflix_api_key = st.secrets["netflix_api_key"]

# Page title
st.title("🎬 Netflix Recommender")
st.write("Get top-rated movies and TV shows from Netflix by entering your favorite genre.")

# Download IMDb files if not present
if not os.path.exists("title.basics.tsv"):
    gdown.download(id="18P42Sr33qRbiE91_n2J4f6nJrsWSF-mU", output="title.basics.tsv", quiet=False)

if not os.path.exists("title.ratings.tsv"):
    gdown.download(id="10Orbx6H-wQWIQ7w9t7H9s-mnAzQpEpY1", output="title.ratings.tsv", quiet=False)

# Genre input
user_input = st.text_input("What genre would you like to watch tonight?").lower().strip()

if user_input:
    # Try matching genre
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
                        "countrylist": "78",
                        "limit": "100"
                    }
                )
                data = response.json()
                if "results" in data:
                    genre_titles = [item['title'] for item in data['results']]
                    all_titles.extend(genre_titles)

        all_titles_set = set(title.lower() for title in all_titles)

        # Stream matching IMDb basics rows
        imdb_data = {}
        with open("title.basics.tsv", encoding="utf-8") as f:
            next(f)  # skip header
            for line in f:
                fields = line.strip().split("\t")
                if len(fields) < 3:
                    continue
                tconst, titleType, primaryTitle = fields[0], fields[1], fields[2]
                if primaryTitle.lower() in all_titles_set:
                    imdb_data[primaryTitle.lower()] = {"tconst": tconst, "type": titleType}

        # Stream matching ratings
        for_ratings = set([v["tconst"] for v in imdb_data.values()])
        tconst_to_rating = {}
        with open("title.ratings.tsv", encoding="utf-8") as f:
            next(f)  # skip header
            for line in f:
                fields = line.strip().split("\t")
                if len(fields) < 2:
                    continue
                tconst, rating = fields[0], fields[1]
                if tconst in for_ratings:
                    tconst_to_rating[tconst] = float(rating)

        # Match ratings back to titles
        rated_titles = []
        for title_lower, info in imdb_data.items():
            rating = tconst_to_rating.get(info["tconst"])
            if rating:
                rated_titles.append({
                    "title": title_lower.title(),
                    "rating": rating,
                    "type": info["type"]
                })

        # Sort and display
        movies = sorted(
            [r for r in rated_titles if r["type"] == "movie"],
            key=lambda x: x["rating"], reverse=True
        )[:5]

        shows = sorted(
            [r for r in rated_titles if r["type"] in ["tvSeries", "tvMiniSeries"]],
            key=lambda x: x["rating"], reverse=True
        )[:5]

        if movies:
            st.subheader("🎬 Top 5 Movies")
            for m in movies:
                st.write(f"**{m['title']}** — IMDb: {m['rating']}")

        if shows:
            st.subheader("📺 Top 5 TV Shows")
            for s in shows:
                st.write(f"**{s['title']}** — IMDb: {s['rating']}")

        if not movies and not shows:
            st.info("No rated matches found for this genre.")
