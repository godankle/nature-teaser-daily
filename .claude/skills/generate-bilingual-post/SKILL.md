# Skill: generate-bilingual-post

Generates a bilingual (EN + ZH) Nature Teaser Daily post from crawled article JSON.

## When to use
- After `crawl-nature-reviews` has produced a `YYYY-MM-DD/reviews.json`
- Run daily as step 2 of the pipeline

## Usage

### Preferred: ask Claude Code directly (no API key needed)
Just say: "Generate the bilingual post for [date]" — Claude Code reads the JSON and writes the post inline. Faster, free, no setup.

### Alternative: run as a Python script
Requires `ANTHROPIC_API_KEY` set in your environment.

```bash
# Install dependencies (first time only)
pip install -r .claude/skills/generate-bilingual-post/requirements.txt

# Generate post for yesterday (default)
python .claude/skills/generate-bilingual-post/generate.py

# Generate post for a specific date
python .claude/skills/generate-bilingual-post/generate.py --date 2026-04-29
```

## Input

`projects/nature-teaser-daily/data/YYYY-MM-DD/reviews.json` (from crawl-nature-reviews skill)

Optionally reads the previous day's `YYYY-MM-DD/recap.json` to chain the recap question as the post opener.

## Output

Two files are created in `projects/nature-teaser-daily/data/YYYY-MM-DD/`:

### `post.md`
The formatted post, ready for copy-paste:
- Recap from yesterday's question (opener)
- Numbered stories with inline Chinese vocab annotations
- "Why it matters" societal benefit per story
- Original article link per story
- Full vocabulary table
- Recap answer
- Closing greeting (morning message, festival shoutout, or light joke)

### `recap.json`
```json
{
  "question": "Tomorrow's recall question",
  "answer": "The answer to that question",
  "topic": "The article title it's drawn from"
}
```
This file is automatically picked up by the next day's run as the post opener.

## Post format rules

**Length scaling**
- > 5 articles → 1-2 sentences per story (tight and punchy)
- ≤ 5 articles → 2-3 sentences per story (more context and color)

**Chinese annotations**
- Story titles: English only — no Chinese in the title
- No pinyin — Chinese characters only
- Annotate uncommon/technical terms only (e.g., clots 血凝块, pronuclei 原核, immunotherapy 免疫疗法, sycophancy 谄媚)
- Do NOT annotate: machine learning, AI, algorithm, cancer, diversity, neural networks, resource allocation
- Aim for 2-4 annotations per story

**Closing greeting**
- End every post with a short warm message: morning greeting, upcoming festival shoutout, or a light joke tied to a story

## Notes
- All articles are included — none are skipped or merged
- The recap question does NOT appear at the bottom of the post — it surfaces naturally as the opener of the next day's post
