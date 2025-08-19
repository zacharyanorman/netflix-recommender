import os
import requests
import pandas as pd
import streamlit as st
import gdown

from genres import genres_list

# Load Netflix API key from secrets
netflix_api_key = st.secrets["netflix_api_key"]

# Page title
st.title("🎬 Netflix Recommender")
st.write("Get top-rated movies and TV shows from Netflix by entering your favorite genre.")

# Download IMDb files from Google Drive if not present
if not os.path.exists("title.basics.tsv"):
    gdown.download(id="18P42Sr33qRbiE91_n2J4f6nJrsWSF-mU", output="title.basics.tsv", quiet=False)

if not os.path.exists("title.ratings.tsv"):
    gdown.download(id="10Orbx6H-wQWIQ7w9t7H9s-mnAzQpEpY1", output="title.ratings.tsv", quiet=False)

# Load IMDb datasets
basics = pd.read_csv("title.basics.tsv", sep="\t", na_values="\\N", low_memory=False)
ratings = pd.read_csv("title.ratings.tsv", sep="\t", na_values="\\N")

# Preprocess IMDb title map once
title_map = basics[['primaryTitle', 'tconst', 'titleType']].dropna()
title_map['primaryTitle_lower'] = title_map['primaryTitle'].str.lower()
title_map = title_map.drop_duplicates(subset=['primaryTitle_lower'])
title_map = title_map.merge(ratings, on='tconst', how='left').dropna(subset=['averageRating'])

# Genre input box
user_input = st.text_input("What genre would you like to watch tonight?").lower().strip()

if user_input:
    # Match input to genres
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

        # Fast IMDb title lookup
        def get_rating(title):
            match = title_map[title_map['primaryTitle_lower'] == title.lower()]
            if not match.empty:
                row = match.iloc[0]
                return {
                    "title": row['primaryTitle'],
                    "rating": row['averageRating'],
                    "type": row['titleType']
                }
            return None

        rated_titles = [r for t in all_titles if (r := get_rating(t)) is not None]

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

        # Show results
        if movies:
            st.subheader("🎬 Top 5 Movies")
            for m in movies:
                st.write(f"**{m['title']}** — IMDb: {m['rating']}")

        if tv_shows:
            st.subheader("📺 Top 5 TV Shows")
            for s in tv_shows:
                st.write(f"**{s['title']}** — IMDb: {s['rating']}")

        if not movies and not tv_shows:
            st.info("No rated results found for the matched titles.")
