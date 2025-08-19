# 🎬 Netflix Recommender

Get top-rated Netflix US movies and TV shows by entering any genre in plain English—like "german dramas" or "funny sci-fi." The app finds the closest genre match, fetches available Netflix titles, and ranks them using IMDb ratings.

---

## 🔍 Features

- ✅ Natural language genre input using Sentence Transformers
- ✅ Matches user input to Netflix's internal genre taxonomy
- ✅ Pulls real-time Netflix US listings by genre ID
- ✅ Cross-references IMDb public datasets for title ratings
- ✅ Separates and ranks movies vs. TV shows
- ✅ Deployed with Streamlit for easy access

---

## 🛠 How It Works

1. **Genre Matching**: Compares your input against a curated list of Netflix genres using sentence embeddings.
2. **Netflix Scraping**: Retrieves movies and shows by genre from JustWatch's Netflix US catalog.
3. **IMDb Integration**: Matches titles to IMDb's public datasets to get rating scores.
4. **Ranking**: Displays top 5 movies and top 5 shows by IMDb rating.

---

## 🚀 Getting Started

1. Clone the repo

```bash
git clone https://github.com/zacharyanorman/netflix-recommender.git
cd netflix-recommender

2. Set up virtual environment

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

3. Run the app

streamlit run main.py

📦 IMDb Data

IMDb datasets are automatically downloaded from Google Drive on first run:

    title.basics.tsv – contains title IDs, names, type (movie/tv), and release year

    title.ratings.tsv – contains IMDb ratings and vote counts

If not present locally, the app fetches them from:

    title.basics.tsv

title.ratings.tsv
📸 Screenshot

(Optional: Add a screenshot here after deploying to Streamlit Cloud)
📃 License

MIT License