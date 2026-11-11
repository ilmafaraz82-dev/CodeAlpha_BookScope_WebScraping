# 📚 BookScope: Web Scraper
### CodeAlpha · Data Analytics Internship · Task 1: Web Scraping

A Python web scraper that builds a **custom dataset of ~1,000 books** from
[books.toscrape.com](https://books.toscrape.com), a public website made for scraping practice.
It comes with a **Streamlit web interface** for running the scraper, watching its progress,
browsing and filtering the data, and downloading it as CSV / JSON.

---

## 🎯 Task requirements → what this project does

| CodeAlpha requirement | How it is done here |
|---|---|
| Use Python libraries like BeautifulSoup | `requests` downloads pages, `BeautifulSoup` parses the HTML |
| Collect datasets from public web pages | Scrapes all 1,000 books from books.toscrape.com |
| Handle HTML structure | Uses CSS selectors (`article.product_pod`, `p.price_color`, `p.star-rating` …) |
| Handle web navigation | Reads 50 category links from the sidebar, then follows the **next** button on every page |
| Create custom datasets for analysis | Cleans the values and saves `data/books.csv` + `data/books.json` (used in Task 2 & 3) |

---

## 📁 Project structure

```
CodeAlpha_ProjectName - data analytics (task 1)/
├── scraper.py            # the scraper (can run on its own from cmd)
├── app.py                # Streamlit web interface
├── requirements.txt      # Python libraries needed
├── .streamlit/config.toml# UI theme (colours)
├── .gitignore
├── README.md
└── data/                 # created when you run the scraper
    ├── books.csv
    └── books.json
```

---

## ⚙️ Setup (Windows cmd / PowerShell)

```cmd
cd "C:\Users\ILMA FARAZ\OneDrive\Desktop\CodeAlpha_ProjectName -  data analytics (task 1)"

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```
> Needs **Python 3.10+** and an internet connection.

## 🚀 How to run

**Option A: Web interface (best for demo)**
```cmd
streamlit run app.py
```
The browser opens at `http://localhost:8501`. Choose settings in the sidebar → **Start scraping**.

**Option B: Command line only**
```cmd
python scraper.py              :: all 50 categories (~1000 books, about 1 minute)
python scraper.py --limit 5    :: quick test with 5 categories
python scraper.py --delay 1    :: wait 1 s between requests
```

---

## 🗂️ Dataset columns

| Column | Example | Meaning |
|---|---|---|
| `title` | A Light in the Attic | Full book title |
| `category` | Poetry | Category it was found in |
| `price_gbp` | 51.77 | Price in £ (number, cleaned from "£51.77") |
| `rating` | 3 | Star rating 1–5 (cleaned from CSS class "Three") |
| `in_stock` | True | Is the book available |
| `availability` | In stock | Original text from the site |
| `product_url` | https://books.toscrape.com/catalogue/… | Link to the book page |
| `image_url` | https://books.toscrape.com/media/… | Cover image link |
| `scraped_at` | 2026-11-11 10:15:00 | When the data was collected |

---

## 🧠 How the scraper works (step by step)

1. **robots.txt check**: confirms the site allows scraping (ethical scraping).
2. **Read categories**: from the home page sidebar `div.side_categories ul li ul li a` → 50 links.
3. **Pagination**: opens each category page; if `li.next a` exists, goes to the next page; stops on the last page.
4. **Extract**: each book is an `<article class="product_pod">`. From it:
   - title → `h3 a` `title` attribute (the visible text is cut with "...")
   - price → `p.price_color` → regex keeps the number
   - rating → class name of `p.star-rating` (`One`…`Five` → 1…5)
   - stock → `p.availability` text
5. **Clean**: relative links (`../../x/index.html`) → full URLs using `urljoin`; duplicate books removed.
6. **Save**: CSV (with `utf-8-sig` so Excel shows `£` correctly) and JSON.

**Good practices used:** browser User-Agent header, polite delay between requests,
automatic retry if a request fails, a broken book card is skipped instead of crashing,
type hints, and a dataclass for the data model.

---

## 🖥️ Interface features

- Hero header + 5 KPI cards (books, categories, avg price, avg rating, % in stock)
- Live progress bar while scraping
- **Dataset tab**: search, filter by category / rating / price, cover images, download CSV/JSON
- **Quick insights tab**: 4 charts to sanity-check the data
- **How it works tab**: visual explanation of the scraping steps and HTML structure

---

## 🛠️ Tech stack
`Python` · `requests` · `BeautifulSoup4` · `pandas` · `Streamlit` · `Plotly`

## 👤 Author
**Ilma Faraz**, CodeAlpha Data Analytics Intern
