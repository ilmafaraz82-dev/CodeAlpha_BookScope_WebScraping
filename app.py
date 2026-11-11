"""
CodeAlpha - Data Analytics - Task 1: Web Scraping
Web interface for the Book Catalogue Scraper.

Run from cmd:
    streamlit run app.py
"""

import logging
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import scraper

st.set_page_config(page_title="BookScope · Web Scraper", page_icon="📚", layout="wide")
logging.basicConfig(level=logging.INFO)

CSV_PATH = scraper.DATA_DIR / "books.csv"
ACCENT = "#4F46E5"

# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stButton button { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2rem; max-width: 1250px; }

.hero {
  background: linear-gradient(135deg, #312E81 0%, #4F46E5 55%, #0EA5E9 100%);
  border-radius: 20px; padding: 34px 38px; color: white; margin-bottom: 26px;
  box-shadow: 0 12px 30px rgba(79,70,229,.25);
}
.hero .tag { display:inline-block; background: rgba(255,255,255,.18); padding: 4px 12px;
  border-radius: 999px; font-size: 12px; font-weight: 600; letter-spacing: .5px; }
.hero h1 { color: white; font-size: 38px; font-weight: 800; margin: 12px 0 6px 0; }
.hero p  { color: rgba(255,255,255,.88); font-size: 16px; margin: 0; max-width: 720px; }

.kpi { background: white; border: 1px solid #E5E7EB; border-radius: 16px; padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04); }
.kpi .label { color:#6B7280; font-size: 13px; font-weight: 500; }
.kpi .value { color:#111827; font-size: 28px; font-weight: 800; margin-top: 4px; }
.kpi .sub   { color:#10B981; font-size: 12px; font-weight: 600; margin-top: 2px; }

.step { background:#F9FAFB; border:1px solid #E5E7EB; border-radius:14px; padding:16px 18px; height:100%; }
.step .num { background:#EEF2FF; color:#4F46E5; font-weight:800; width:30px; height:30px;
  border-radius:50%; display:flex; align-items:center; justify-content:center; margin-bottom:8px; }
.step b { color:#111827; } .step p { color:#4B5563; font-size:14px; margin:4px 0 0 0; }

.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { background:#F3F4F6; border-radius:10px; padding:10px 20px; font-weight:600; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }
.stTabs [aria-selected="true"] { background:#4F46E5 !important; color:white !important; }
.stButton button[kind="primary"] { border-radius: 10px; font-weight: 700; padding: .6rem 1rem; }
section[data-testid="stSidebar"] { background: #F8FAFC; }
</style>
""",
    unsafe_allow_html=True,
)


def kpi(col, label, value, sub=""):
    col.markdown(
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def style_fig(fig, height=360):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        font=dict(family="Inter, sans-serif", color="#374151"),
        plot_bgcolor="white", paper_bgcolor="white",
        title_font=dict(size=16, color="#111827"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#F3F4F6")
    return fig


@st.cache_data
def load_data(path: str, modified: float) -> pd.DataFrame:
    # "modified" is only there so the cache refreshes when the file changes
    return pd.read_csv(path)


@st.cache_data(ttl=3600)
def get_category_names() -> list:
    """Read the category list live from the website (falls back to a few if offline)."""
    import requests
    try:
        with requests.Session() as s:
            soup = scraper.get_soup(s, scraper.BASE_URL, retries=1)
        if soup:
            return sorted(scraper.get_categories(soup))
    except Exception:
        pass
    return ["Travel", "Mystery", "Poetry", "Fiction", "History", "Science"]


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="hero">
  <span class="tag">CODEALPHA · DATA ANALYTICS · TASK 1</span>
  <h1>📚 BookScope: Web Scraper</h1>
  <p>Collects a custom dataset of ~1,000 books from <b>books.toscrape.com</b>. It navigates
  50 categories, follows pagination, and extracts title, price, rating and stock status using
  Python, Requests &amp; BeautifulSoup.</p>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Sidebar: scraper settings
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Scraper settings")
    mode = st.radio("What to scrape", ["All categories", "Quick test (first 5)", "Pick categories"])
    picked = []
    if mode == "Pick categories":
        picked = st.multiselect("Categories", get_category_names(), default=["Travel", "Mystery", "Poetry"])
    delay = st.slider("Delay between requests (seconds)", 0.0, 2.0, 0.3, 0.1,
                      help="A small pause so we don't overload the website (polite scraping).")
    start = st.button("🚀 Start scraping", type="primary", width="stretch")
    st.divider()
    st.caption("Output is saved to `data/books.csv` and `data/books.json`.")

# --------------------------------------------------------------------------
# Run the scraper
# --------------------------------------------------------------------------
if start:
    bar = st.progress(0.0, text="Connecting to books.toscrape.com ...")
    status = st.empty()
    t0 = time.time()

    def on_progress(done, total, name, count):
        bar.progress(done / total, text=f"Category {done}/{total}: {name}")
        status.info(f"✅ Finished **{name}**. Total books collected so far: **{count}**")

    try:
        books = scraper.scrape_all(
            delay=delay,
            limit=5 if mode.startswith("Quick") else None,
            only=picked if mode == "Pick categories" else None,
            progress=on_progress,
        )
        scraper.save(books)
        bar.progress(1.0, text="Done!")
        status.success(f"🎉 Scraped **{len(books)} books** in {time.time() - t0:.1f} s and saved to `data/books.csv`")
        st.balloons()
    except Exception as err:
        bar.empty()
        status.error(f"Scraping failed: {err}")

# --------------------------------------------------------------------------
# Show the dataset
# --------------------------------------------------------------------------
if not CSV_PATH.exists():
    st.info("👈 No dataset yet. Choose your settings in the sidebar and press **Start scraping**.")
    st.stop()

df = load_data(str(CSV_PATH), CSV_PATH.stat().st_mtime)

c1, c2, c3, c4, c5 = st.columns(5)
kpi(c1, "Books scraped", f"{len(df):,}", "rows in dataset")
kpi(c2, "Categories", df["category"].nunique(), "navigated")
kpi(c3, "Average price", f"£{df['price_gbp'].mean():.2f}", f"£{df['price_gbp'].min():.0f} – £{df['price_gbp'].max():.0f}")
kpi(c4, "Average rating", f"{df['rating'].mean():.2f} ★", "out of 5")
kpi(c5, "In stock", f"{df['in_stock'].mean() * 100:.0f}%", "availability")
st.write("")

tab_data, tab_insights, tab_how = st.tabs(["🗂️ Dataset", "📊 Quick insights", "🧠 How it works"])

# ---- Dataset tab ---------------------------------------------------------
with tab_data:
    f1, f2, f3 = st.columns([2, 2, 1])
    search = f1.text_input("🔎 Search title", placeholder="e.g. history")
    cats = f2.multiselect("Category", sorted(df["category"].unique()))
    min_rating = f3.selectbox("Min rating", [1, 2, 3, 4, 5], index=0)
    price_range = st.slider("Price range (£)", float(df["price_gbp"].min()), float(df["price_gbp"].max()),
                            (float(df["price_gbp"].min()), float(df["price_gbp"].max())))

    view = df[
        df["title"].str.contains(search, case=False, na=False)
        & (df["category"].isin(cats) if cats else True)
        & (df["rating"] >= min_rating)
        & df["price_gbp"].between(*price_range)
    ]
    st.caption(f"Showing **{len(view):,}** of {len(df):,} books")
    st.dataframe(
        view[["image_url", "title", "category", "price_gbp", "rating", "availability", "product_url"]],
        width="stretch", hide_index=True, height=460,
        column_config={
            "image_url": st.column_config.ImageColumn("Cover", width="small"),
            "title": st.column_config.TextColumn("Title", width="large"),
            "category": st.column_config.TextColumn("Category"),
            "availability": st.column_config.TextColumn("Stock"),
            "price_gbp": st.column_config.NumberColumn("Price", format="£%.2f"),
            "rating": st.column_config.NumberColumn("Rating", format="%d ★"),
            "product_url": st.column_config.LinkColumn("Link", display_text="Open ↗"),
        },
    )
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("⬇️ Download CSV", view.to_csv(index=False).encode("utf-8-sig"),
                       "books.csv", "text/csv", width="stretch")
    d2.download_button("⬇️ Download JSON", view.to_json(orient="records", indent=2),
                       "books.json", "application/json", width="stretch")

# ---- Insights tab --------------------------------------------------------
with tab_insights:
    g1, g2 = st.columns(2)
    top = df["category"].value_counts().head(10).sort_values().reset_index()
    top.columns = ["category", "books"]
    fig = px.bar(top, x="books", y="category", orientation="h", title="Top 10 categories by number of books",
                 color_discrete_sequence=[ACCENT], text="books")
    g1.plotly_chart(style_fig(fig), width="stretch")

    ratings = df["rating"].value_counts().sort_index().reset_index()
    ratings.columns = ["rating", "books"]
    ratings["rating"] = ratings["rating"].astype(str) + " ★"
    fig = px.bar(ratings, x="rating", y="books", title="How many books got each star rating",
                 color_discrete_sequence=["#F59E0B"], text="books")
    g2.plotly_chart(style_fig(fig), width="stretch")

    g3, g4 = st.columns(2)
    fig = px.histogram(df, x="price_gbp", nbins=25, title="Price distribution (£)",
                       color_discrete_sequence=["#0EA5E9"])
    g3.plotly_chart(style_fig(fig).update_layout(bargap=0.05), width="stretch")

    avg = df.groupby("rating", as_index=False)["price_gbp"].mean()
    avg["rating"] = avg["rating"].astype(str) + " ★"
    fig = px.bar(avg, x="rating", y="price_gbp", title="Average price by star rating",
                 color_discrete_sequence=["#10B981"], text=avg["price_gbp"].round(2))
    g4.plotly_chart(style_fig(fig), width="stretch")
    st.caption("These are first-look checks that the data is sensible. The full analysis is done in Task 2 (EDA).")

# ---- How it works tab ----------------------------------------------------
with tab_how:
    steps = [
        ("Check robots.txt", "Make sure the site allows scraping before sending any request."),
        ("Read categories", "Parse the sidebar <code>div.side_categories</code> to get all 50 category links."),
        ("Follow pagination", "Open each category and keep clicking the <code>li.next</code> link until the last page."),
        ("Extract fields", "From every <code>article.product_pod</code> read title, price, rating, stock and links."),
        ("Clean the data", "“£51.77” → 51.77, class “Three” → 3, relative links → full URLs, remove duplicates."),
        ("Save dataset", "Write <code>data/books.csv</code> and <code>data/books.json</code> for analysis."),
    ]
    cols = st.columns(3)
    for i, (title, text) in enumerate(steps):
        with cols[i % 3]:
            st.markdown(f'<div class="step"><div class="num">{i + 1}</div><b>{title}</b><p>{text}</p></div>',
                        unsafe_allow_html=True)
            st.write("")

    st.markdown("#### Example: one book card in the website's HTML")
    st.code(
        """<article class="product_pod">
  <div class="image_container"><a href="../../a-light-in-the-attic_1000/index.html">
      <img src="../../media/cache/2c/da/2cdad67c.jpg" alt="A Light in the Attic"></a></div>
  <p class="star-rating Three"></p>                      <!-- rating  -> 3 -->
  <h3><a href="..." title="A Light in the Attic">A Light in the ...</a></h3>  <!-- title -->
  <div class="product_price">
      <p class="price_color">£51.77</p>                    <!-- price  -> 51.77 -->
      <p class="instock availability">In stock</p>         <!-- stock  -> True -->
  </div>
</article>""",
        language="html",
    )
    st.markdown("#### Tech stack")
    st.markdown("`Python` · `requests` (download pages) · `BeautifulSoup` (parse HTML) · "
                "`pandas` (dataset) · `Streamlit` (this interface) · `Plotly` (charts)")
