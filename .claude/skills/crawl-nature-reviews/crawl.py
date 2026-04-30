#!/usr/bin/env python3
"""
Crawl Nature Reviews & Analysis for articles published on a given date.
Default: yesterday (t-1).

Usage:
    python crawl.py                        # crawls yesterday
    python crawl.py --date 2026-04-29      # crawls a specific date
    python crawl.py --date 2026-04-29 --full  # also fetches teaser from each article page
"""

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.nature.com"
LIST_URL = f"{BASE}/nature/reviews-and-analysis"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
OUTPUT_DIR = Path(__file__).parents[3] / "projects" / "nature-teaser-daily" / "data"


def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_article_card(art) -> dict:
    title_el = art.select_one("h3.c-card__title a")
    date_el = art.select_one("time[datetime]")
    type_el = art.select_one("[data-test='article.type'] .c-meta__type")
    summary_el = art.select_one("[data-test='article-description'] p")
    authors = [s.get_text(strip=True) for s in art.select("[itemprop='name']")]

    return {
        "title": title_el.get_text(strip=True) if title_el else "",
        "url": BASE + title_el["href"] if title_el else "",
        "date": date_el["datetime"] if date_el else "",
        "type": type_el.get_text(strip=True) if type_el else "",
        "summary": summary_el.get_text(strip=True) if summary_el else "",
        "authors": authors,
        "teaser": "",  # populated by --full flag
    }


def fetch_teaser(article_url: str) -> str:
    """Fetch the freely accessible teaser paragraph from an article page."""
    try:
        soup = fetch_soup(article_url)
        el = soup.select_one("div.c-article-teaser-text") or soup.select_one("p.article__teaser")
        return el.get_text(strip=True) if el else ""
    except Exception:
        return ""


def crawl(target_date: str, fetch_full: bool = False) -> list[dict]:
    print(f"Crawling Nature Reviews & Analysis for {target_date}...")
    results = []
    page = 1

    while True:
        url = f"{LIST_URL}?searchType=journalSearch&sort=PubDate&page={page}"
        print(f"  Fetching page {page}...", end=" ", flush=True)
        soup = fetch_soup(url)

        articles = soup.select("article.c-card")
        if not articles:
            print("no articles found, stopping.")
            break

        found_any_on_date = False
        past_date = False

        for art in articles:
            item = parse_article_card(art)
            if not item["date"]:
                continue
            if item["date"] == target_date:
                found_any_on_date = True
                if fetch_full and item["url"]:
                    item["teaser"] = fetch_teaser(item["url"])
                    time.sleep(0.5)
                results.append(item)
            elif item["date"] < target_date:
                # Articles are sorted newest-first; once we're past the date, stop
                past_date = True
                break

        print(f"found {sum(1 for r in results if r['date'] == target_date)} matching.")

        if past_date:
            break

        # Check if there's a next page
        next_btn = soup.select_one("li[data-page='next'] a")
        if not next_btn:
            break

        page += 1
        time.sleep(0.7)

    return results


def main():
    parser = argparse.ArgumentParser(description="Crawl Nature Reviews & Analysis")
    parser.add_argument("--date", default=str(date.today() - timedelta(days=1)),
                        help="Target date (YYYY-MM-DD). Default: yesterday.")
    parser.add_argument("--full", action="store_true",
                        help="Also fetch teaser text from each article page.")
    args = parser.parse_args()

    articles = crawl(args.date, fetch_full=args.full)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{args.date}-reviews.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(articles)} articles saved to {out_file}")
    if articles:
        print("\nArticles found:")
        for i, a in enumerate(articles, 1):
            print(f"  {i}. [{a['type']}] {a['title']}")
            print(f"     {a['url']}")


if __name__ == "__main__":
    main()
