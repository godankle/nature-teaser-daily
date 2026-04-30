# Skill: crawl-nature-reviews

Crawls Nature Reviews & Analysis for articles published on a target date (default: yesterday).
Outputs a JSON file to `projects/nature-teaser-daily/data/YYYY-MM-DD-reviews.json`.

## When to use
- At the start of each daily pipeline run to gather raw article data
- Source: https://www.nature.com/nature/reviews-and-analysis

## Usage

```bash
# Install dependencies (first time only)
pip install -r .claude/skills/crawl-nature-reviews/requirements.txt

# Crawl yesterday (default)
python .claude/skills/crawl-nature-reviews/crawl.py

# Crawl a specific date
python .claude/skills/crawl-nature-reviews/crawl.py --date 2026-04-29

# Also fetch teaser text from each article page (richer data, slower)
python .claude/skills/crawl-nature-reviews/crawl.py --full
```

## Output format

`projects/nature-teaser-daily/data/YYYY-MM-DD-reviews.json`

```json
[
  {
    "title": "Article title",
    "url": "https://www.nature.com/articles/...",
    "date": "2026-04-29",
    "type": "News & Views",
    "summary": "Abstract/teaser from the listing page",
    "authors": ["Author Name"],
    "teaser": "Extended teaser from article page (only if --full was used)"
  }
]
```

## Next steps after crawling
1. Review the JSON — pick 3–5 top stories
2. Run the hallucination-check skill (not built yet)
3. Run the generate-bilingual-post skill (not built yet)

## Notes
- Articles are sorted newest-first on the listing page; the crawler stops once it passes the target date
- Full article body is paywalled — only titles, summaries, and teasers are freely accessible
- Add a 0.5–0.7s delay between requests (already built in) to be a polite crawler
