import os
import requests
import pandas as pd
import streamlit as st

from genres import genres_list

# Load Netflix API key from Streamlit secrets
netflix_api_key = st.secrets["netflix_api_key"]

# Page title
st.title("🎬 Netflix Recommender")
st.write("Get top-rated movies and TV shows from Netflix by entering your favorite genre.")

# Load reduced IMDb datasets
@st.cache_data
def load_datasets():
    basics = pd.read_csv("title.basics_reduced.tsv", sep="\t", na_values="\\N")
    ratings = pd.read_csv("title.ratings.tsv", sep="\t", na_values="\\N")
    return basics, ratings

basics, ratings = load_datasets()

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
                        "countrylist": "78",  # US
                        "limit": "100"
                    }
                )
                data = response.json()
                if "results" in data:
                    genre_titles = [item['title'] for item in data['results']]
                    all_titles.extend(genre_titles)

        # Match titles with IMDb ratings
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

        # Deduplicate by title (keep highest-rated version)
        def dedupe_by_title(entries):
            seen = {}
            for entry in entries:
                title = entry["title"]
                if title not in seen or entry["rating"] > seen[title]["rating"]:
                    seen[title] = entry
            return list(seen.values())

        # Apply deduplication and sort
        movies = dedupe_by_title([r for r in rated_titles if r["type"] == "movie"])
        movies = sorted(movies, key=lambda x: x["rating"], reverse=True)[:5]

        tv_shows = dedupe_by_title([r for r in rated_titles if r["type"] in ["tvSeries", "tvMiniSeries"]])
        tv_shows = sorted(tv_shows, key=lambda x: x["rating"], reverse=True)[:5]

        # Display results
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
