#!/bin/bash
# Nature Teaser Daily — full pipeline
# Runs every morning via LaunchAgent at 7 AM.
# On wake after sleep/shutdown, catches up on any missed days (up to 7 days back).

set -uo pipefail

PYTHON=/opt/homebrew/bin/python3
CLAUDE=$(ls ~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1)
if [[ -z "$CLAUDE" ]]; then
  echo "ERROR: Claude Code binary not found. Is the VS Code extension installed?"
  exit 1
fi
PROJECT=/Users/nibo/nature-teaser-daily
DATA="$PROJECT/projects/nature-teaser-daily/data"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

cd "$PROJECT"

run_for_date() {
  local d="$1"
  local reviews="$DATA/${d}/reviews.json"
  local post="$DATA/${d}/post.md"

  if [[ -f "$post" ]]; then
    log "$d — post already exists, skipping."
    return
  fi

  log "=== Processing $d ==="

  # Crawl if we don't have the data yet
  if [[ ! -f "$reviews" ]]; then
    log "Crawling Nature Reviews & Analysis for $d..."
    "$PYTHON" .claude/skills/crawl-nature-reviews/crawl.py --date "$d" || {
      log "ERROR: Crawl failed for $d — skipping."
      return
    }
  else
    log "Crawl data already exists for $d, skipping crawl."
  fi

  # Skip days with no articles (weekends, holidays)
  local count
  count=$("$PYTHON" -c "import json; data=json.load(open('$reviews')); print(len(data))")
  if [[ "$count" -eq 0 ]]; then
    log "$d — no articles published (weekend/holiday), skipping."
    return
  fi

  log "Generating bilingual post for $d ($count articles)..."
  "$CLAUDE" --dangerously-skip-permissions -p \
    "Generate the Nature Teaser Daily bilingual post for $d. \
Read the crawled articles from projects/nature-teaser-daily/data/${d}/reviews.json, \
follow all rules in the generate-bilingual-post skill and CLAUDE.md, \
then save the finished post to projects/nature-teaser-daily/data/${d}/post.md \
and the recap to projects/nature-teaser-daily/data/${d}/recap.json." || {
    log "ERROR: Post generation failed for $d — will retry next run."
    return
  }

  log "Done — $d post saved."
}

# Check the last 7 days and fill in any gaps (handles multi-day sleep/shutdown)
log "Checking for missed days (up to 7 days back)..."
missed=0
for i in 1 2 3 4 5 6 7; do
  d=$(date -v-${i}d +%Y-%m-%d)
  if [[ ! -f "$DATA/${d}/post.md" ]]; then
    missed=$((missed + 1))
    run_for_date "$d"
  fi
done

if [[ $missed -eq 0 ]]; then
  log "All caught up — nothing to do."
fi
