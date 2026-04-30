#!/usr/bin/env python3
"""
Generate a bilingual (EN + ZH) Nature Teaser Daily post from crawled article JSON.

Usage:
    python generate.py                        # uses yesterday's crawl
    python generate.py --date 2026-04-29      # uses a specific date's crawl

Output:
    projects/nature-teaser-daily/data/{date}-post.md     — the formatted post
    projects/nature-teaser-daily/data/{date}-recap.json  — tomorrow's recap question
"""

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import anthropic

DATA_ROOT = Path(__file__).parents[3] / "projects" / "nature-teaser-daily" / "data"

SYSTEM_PROMPT = """\
You are the author of "Nature Teaser Daily", a bilingual (English + Chinese) science newsletter
that makes cutting-edge research accessible and delightful for a general audience.

## Tone & Voice
- Curious, playful, warm — like a brilliant friend explaining science at dinner
- Accessible: no jargon without explanation
- English-first with inline Chinese vocabulary annotations

## Post Format (STRICT — follow exactly)

---
**Recap from yesterday:** [Yesterday's recap question, verbatim from context]

**Today's stories:**

1. **[Article title in English]**
   [Story summary with inline Chinese annotations for uncommon terms — see length rules below]
   **Why it matters:** [1-2 sentences on societal benefit]
   [Original Article]({url})

[... repeat for all articles ...]

---
**Vocabulary Table**

| English | 中文 | Notes |
|---------|------|-------|
| [term] | [中文] | [brief note] |
[... all terms annotated inline, collected here ...]

---
**Recap answer:** [Answer to yesterday's question]

---

[A short, warm closing — Good morning + one of: seasonal/festival shoutout, light joke tied to a story, or a simple have-a-good-day. Keep it human and fun. 1-2 lines max.]

---

TOMORROW_RECAP_QUESTION: [An intriguing question based on ONE story from today — answerable from the post but not obvious]
TOMORROW_RECAP_ANSWER: [the answer]
TOMORROW_RECAP_TOPIC: [the article title it's drawn from]

## Length Rules
- If there are MORE THAN 5 articles: each story gets 1-2 sentences max (tight and punchy)
- If there are 5 OR FEWER articles: each story gets 2-3 sentences (more context and color)

## Chinese Vocabulary Annotations
- NO Chinese translations in story titles — English titles only
- NO pinyin — just Chinese characters
- Inline format: English term (中文) — only for terms a general Chinese reader would find unfamiliar or hard to visualize
- Annotate UNCOMMON terms. Examples of words that SHOULD be annotated:
  clots (血凝块), trauma (创伤), tissue regeneration (组织再生), pronuclei (原核),
  cytoplasmic factors (细胞质因子), IVF (试管婴儿), miscarriage (流产),
  immunotherapy (免疫疗法), immune toxicity (免疫毒性), sycophancy (谄媚),
  single-cell sequencing (单细胞测序), de novo protein design (从头蛋白质设计),
  molecules (分子), genome (基因组), embryonic (胚胎的)
- Do NOT annotate widely-known terms: machine learning, AI, algorithm, cancer, diversity, resource allocation, data, neural networks, etc.
- Aim for 2-4 annotations per story
- Vocabulary table at the end collects ALL annotated terms

## Critical Rules
1. Include EVERY article from the input — do not skip or merge any
2. The TOMORROW_RECAP_* lines must appear at the very end, after the closing ---
3. Do NOT include a "Tomorrow's question" line in the visible post — only in the TOMORROW_RECAP_* metadata lines
4. The recap answer at the bottom answers YESTERDAY's question (from context), not today's
"""


def load_articles(target_date: str) -> list[dict]:
    path = DATA_ROOT / target_date / "reviews.json"
    if not path.exists():
        print(f"Error: No crawl data found at {path}", file=sys.stderr)
        print(f"Run: python .claude/skills/crawl-nature-reviews/crawl.py --date {target_date}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_yesterday_recap(target_date: str) -> dict | None:
    yesterday = str(date.fromisoformat(target_date) - timedelta(days=1))
    path = DATA_ROOT / yesterday / "recap.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def build_user_message(articles: list[dict], recap: dict | None, target_date: str) -> str:
    count = len(articles)
    length_note = (
        "NOTE: There are MORE THAN 5 articles today — use 1-2 sentences per story."
        if count > 5
        else f"NOTE: There are {count} articles today (5 or fewer) — use 2-3 sentences per story."
    )

    lines = [
        f"Date: {target_date}",
        f"Total articles: {count}",
        length_note,
        "",
    ]

    if recap:
        lines += [
            "## Yesterday's Recap (use verbatim in the post)",
            f"Question: {recap['question']}",
            f"Answer: {recap['answer']}",
            f"Topic: {recap['topic']}",
            "",
        ]
    else:
        lines += [
            "## Yesterday's Recap",
            "No previous recap found. Use a generic opener like:",
            f'"Did you know Nature published {count} studies yesterday? Let\'s find out what they discovered."',
            "",
        ]

    lines.append("## Articles to cover (include ALL of them)")
    for i, a in enumerate(articles, 1):
        lines += [
            f"\n### {i}. {a['title']}",
            f"Type: {a['type']}",
            f"URL: {a['url']}",
            f"Summary: {a['summary']}",
        ]
        if a.get("teaser") and a["teaser"] != a["summary"]:
            lines.append(f"Teaser: {a['teaser']}")
        if a.get("authors"):
            lines.append(f"Authors: {', '.join(a['authors'])}")

    lines += [
        "",
        "Now write the full Nature Teaser Daily post following the exact format from your instructions.",
        "End with the TOMORROW_RECAP_QUESTION / TOMORROW_RECAP_ANSWER / TOMORROW_RECAP_TOPIC lines.",
    ]

    return "\n".join(lines)


def extract_recap(post_text: str) -> dict | None:
    q = re.search(r"TOMORROW_RECAP_QUESTION:\s*(.+)", post_text)
    a = re.search(r"TOMORROW_RECAP_ANSWER:\s*(.+)", post_text)
    t = re.search(r"TOMORROW_RECAP_TOPIC:\s*(.+)", post_text)
    if q and a and t:
        return {
            "question": q.group(1).strip(),
            "answer": a.group(1).strip(),
            "topic": t.group(1).strip(),
        }
    return None


def strip_recap_lines(post_text: str) -> str:
    lines = post_text.splitlines()
    clean = [l for l in lines if not l.startswith("TOMORROW_RECAP_")]
    return "\n".join(clean).rstrip() + "\n"


def generate(target_date: str) -> None:
    articles = load_articles(target_date)
    recap = load_yesterday_recap(target_date)
    user_msg = build_user_message(articles, recap, target_date)

    print(f"Generating post for {target_date} ({len(articles)} articles)...")
    if recap:
        print(f"  Using recap from yesterday: \"{recap['question'][:60]}...\"")
    else:
        print("  No previous recap — using generic opener.")

    client = anthropic.Anthropic()

    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text

    print("\n")

    # Save the clean post (without TOMORROW_RECAP_* lines)
    out_dir = DATA_ROOT / target_date
    out_dir.mkdir(parents=True, exist_ok=True)
    post_path = out_dir / "post.md"
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(strip_recap_lines(full_text))
    print(f"Post saved to {post_path}")

    # Save tomorrow's recap
    recap_data = extract_recap(full_text)
    if recap_data:
        recap_path = out_dir / "recap.json"
        with open(recap_path, "w", encoding="utf-8") as f:
            json.dump(recap_data, f, ensure_ascii=False, indent=2)
        print(f"Recap saved to {recap_path}")
        print(f"  Tomorrow's question: \"{recap_data['question'][:70]}...\"")
    else:
        print("Warning: Could not extract TOMORROW_RECAP_* lines from output. Check the post manually.")


def main():
    parser = argparse.ArgumentParser(description="Generate bilingual Nature Teaser Daily post")
    parser.add_argument(
        "--date",
        default=str(date.today() - timedelta(days=1)),
        help="Target date (YYYY-MM-DD). Default: yesterday.",
    )
    args = parser.parse_args()
    generate(args.date)


if __name__ == "__main__":
    main()
