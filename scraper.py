"""
CodeAlpha - Data Analytics - Task 1: Web Scraping
==================================================
Book Catalogue Scraper for https://books.toscrape.com

What it does
------------
1. Opens the home page and reads the list of book categories
   from the sidebar (web navigation).
2. Visits every category and follows the "next" button through
   all of its pages (pagination).
3. From each book card it extracts: title, category, price,
   star rating, availability, product link and image link.
4. Cleans the values (e.g. "£51.77" -> 51.77, "Three" -> 3).
5. Saves the custom dataset to data/books.csv and data/books.json.

Run from cmd:
    python scraper.py                  # scrape everything (~1000 books)
    python scraper.py --limit 5        # only first 5 categories (quick test)
    python scraper.py --delay 1        # wait 1 second between requests
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
import urllib.robotparser
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
BASE_URL = "https://books.toscrape.com/"
DATA_DIR = Path(__file__).parent / "data"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
# The site writes star ratings as words inside the CSS class: <p class="star-rating Three">
RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

log = logging.getLogger("scraper")


# --------------------------------------------------------------------------
# Data model: one row of our dataset
# --------------------------------------------------------------------------
@dataclass
class Book:
    title: str
    category: str
    price_gbp: float
    rating: int
    in_stock: bool
    availability: str
    product_url: str
    image_url: str


# --------------------------------------------------------------------------
# Step 0: check robots.txt (ethical scraping)
# --------------------------------------------------------------------------
def scraping_allowed(url: str = BASE_URL) -> bool:
    """Return True if robots.txt allows us to scrape this site."""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(BASE_URL, "robots.txt"))
    try:
        rp.read()
    except Exception:
        # No robots.txt reachable -> treat as allowed (site is made for practice)
        return True
    return rp.can_fetch(HEADERS["User-Agent"], url)


# --------------------------------------------------------------------------
# Step 1: download a page and turn it into a BeautifulSoup object
# --------------------------------------------------------------------------
def get_soup(session: requests.Session, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    """Download one page. Retries a few times if the network fails."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            response.encoding = "utf-8"  # so "£" is read correctly
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as err:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, err)
            time.sleep(attempt)  # wait a bit longer each time
    log.error("Giving up on %s", url)
    return None


# --------------------------------------------------------------------------
# Step 2: read all categories from the sidebar
# --------------------------------------------------------------------------
def get_categories(soup: BeautifulSoup) -> dict[str, str]:
    """
    Sidebar HTML looks like:
        <div class="side_categories"><ul><li><a>Books</a>
            <ul> <li><a href="catalogue/category/books/travel_2/index.html">Travel</a></li> ...
    Returns {"Travel": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html", ...}
    """
    categories = {}
    for link in soup.select("div.side_categories ul li ul li a"):
        name = link.get_text(strip=True)
        categories[name] = urljoin(BASE_URL, link["href"])
    return categories


# --------------------------------------------------------------------------
# Step 3: extract the books from one page
# --------------------------------------------------------------------------
def parse_price(text: str) -> float:
    """'£51.77' -> 51.77  (keeps only digits and the dot)"""
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group()) if match else 0.0


def parse_rating(tag) -> int:
    """<p class="star-rating Three"> -> 3"""
    if tag is None:
        return 0
    for cls in tag.get("class", []):
        if cls in RATING_WORDS:
            return RATING_WORDS[cls]
    return 0


def parse_books(soup: BeautifulSoup, page_url: str, category: str) -> list[Book]:
    """Every book on the page sits inside <article class="product_pod">."""
    books = []
    for card in soup.select("article.product_pod"):
        try:
            link = card.select_one("h3 a")
            price_tag = card.select_one("p.price_color")
            stock_tag = card.select_one("p.availability")
            img_tag = card.select_one("div.image_container img")

            availability = stock_tag.get_text(strip=True) if stock_tag else "Unknown"
            books.append(
                Book(
                    # the visible text is shortened with "...", the full title is in the title attribute
                    title=link.get("title") or link.get_text(strip=True),
                    category=category,
                    price_gbp=parse_price(price_tag.get_text() if price_tag else ""),
                    rating=parse_rating(card.select_one("p.star-rating")),
                    in_stock="in stock" in availability.lower(),
                    availability=availability,
                    # links on the page are relative ("../../x/index.html") -> make them absolute
                    product_url=urljoin(page_url, link["href"]),
                    image_url=urljoin(page_url, img_tag["src"]) if img_tag else "",
                )
            )
        except (AttributeError, KeyError, TypeError) as err:
            # one broken card should not stop the whole scraper
            log.warning("Skipped a book card on %s: %s", page_url, err)
    return books


def next_page_url(soup: BeautifulSoup, page_url: str) -> Optional[str]:
    """<li class="next"><a href="page-2.html">next</a></li> -> absolute URL, or None on the last page."""
    nxt = soup.select_one("li.next a")
    return urljoin(page_url, nxt["href"]) if nxt else None


# --------------------------------------------------------------------------
# Step 4: walk through one whole category (all of its pages)
# --------------------------------------------------------------------------
def scrape_category(session, name: str, url: str, delay: float) -> list[Book]:
    books, page = [], 1
    while url:
        soup = get_soup(session, url)
        if soup is None:
            break
        found = parse_books(soup, url, name)
        books.extend(found)
        log.info("   %-22s page %d -> %d books", name, page, len(found))
        url = next_page_url(soup, url)
        page += 1
        if url:
            time.sleep(delay)  # be polite to the server
    return books


# --------------------------------------------------------------------------
# Step 5: the full run
# --------------------------------------------------------------------------
def scrape_all(
    delay: float = 0.5,
    limit: Optional[int] = None,
    only: Optional[list[str]] = None,
    progress: Optional[Callable[[int, int, str, int], None]] = None,
) -> list[Book]:
    """
    Scrape all categories (or only some of them).
    progress(done, total, category_name, books_so_far) is called after each
    category - the Streamlit app uses it to move its progress bar.
    """
    if not scraping_allowed():
        raise PermissionError("robots.txt does not allow scraping this site.")

    with requests.Session() as session:
        home = get_soup(session, BASE_URL)
        if home is None:
            raise ConnectionError("Could not open the website. Check your internet connection.")

        categories = get_categories(home)
        log.info("Found %d categories", len(categories))
        if only:
            categories = {k: v for k, v in categories.items() if k in only}
        if limit:
            categories = dict(list(categories.items())[:limit])

        all_books: list[Book] = []
        total = len(categories)
        for i, (name, url) in enumerate(categories.items(), start=1):
            all_books.extend(scrape_category(session, name, url, delay))
            if progress:
                progress(i, total, name, len(all_books))
            time.sleep(delay)

    return remove_duplicates(all_books)


def remove_duplicates(books: list[Book]) -> list[Book]:
    """Same product URL = same book. Keep the first one."""
    seen, unique = set(), []
    for b in books:
        if b.product_url not in seen:
            seen.add(b.product_url)
            unique.append(b)
    return unique


# --------------------------------------------------------------------------
# Step 6: save the dataset
# --------------------------------------------------------------------------
def save(books: list[Book], folder: Optional[Path] = None) -> tuple[Path, Path]:
    folder = folder or DATA_DIR
    folder.mkdir(parents=True, exist_ok=True)
    csv_path, json_path = folder / "books.csv", folder / "books.json"
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [{**asdict(b), "scraped_at": scraped_at} for b in books]

    if rows:
        # utf-8-sig so Excel on Windows shows special characters correctly
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, json_path


# --------------------------------------------------------------------------
# Command-line entry point
# --------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com into a CSV dataset.")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds to wait between requests")
    parser.add_argument("--limit", type=int, default=None, help="only scrape the first N categories")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
    start = time.time()
    log.info("Starting scraper -> %s", BASE_URL)

    books = scrape_all(delay=args.delay, limit=args.limit)
    csv_path, json_path = save(books)

    log.info("-" * 50)
    log.info("Done in %.1f s | %d books | %d categories",
             time.time() - start, len(books), len({b.category for b in books}))
    log.info("Saved: %s", csv_path)
    log.info("Saved: %s", json_path)


if __name__ == "__main__":
    main()
