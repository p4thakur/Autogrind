# 🤖 Autogrind

> A self-running micro-product factory. Every day, Claude researches what people want automated, scores the ideas, and builds the top one.

---

## How It Works

```
Research → Score → Build → Push
```

1. **Research** — Claude searches HN/Reddit/GitHub for automation pain points
2. **Score** — Ideas rated on Demand + Buildability + Value
3. **Build** — Top scored idea gets turned into a working Python script
4. **Push** — Script lands in this repo automatically

## Scoring Formula

| Criteria | Weight | Description |
|---|---|---|
| Demand | 40% | Are people asking for this? |
| Buildability | 30% | Can it be built in <2 hours? |
| Value | 30% | Would someone pay for it? |

---

## 📦 Scripts Built

### Day 1a — HN Pain Point Scraper
**File:** `scripts/day1_hn_pain_scraper.py`
**Score:** 8.7 ⭐⭐⭐⭐⭐

Scrapes HackerNews "Ask HN" posts and finds real pain points people are complaining about. Looks for keywords like "frustrated", "tedious", "wish there was a tool" — ranks posts by pain score and saves top 10 to JSON.

**Run it:**
```bash
python scripts/day1_hn_pain_scraper.py
```
**Output:** `hn_pain_points_YYYYMMDD.json`

---

### Day 1b — GitHub Stars Tracker
**File:** `scripts/day1b_github_stars_tracker.py`
**Score:** 7.6 ⭐⭐⭐⭐

Tracks trending GitHub repos in the AI/automation space daily. Searches across topics like `ai automation`, `llm agent`, `python scraper` — surfaces repos blowing up before everyone else finds them. No API key needed.

**Run it:**
```bash
python scripts/day1b_github_stars_tracker.py
```
**Output:** `github_trending_YYYYMMDD.json`

---

## 🗂️ Repo Structure

```
Autogrind/
├── ideas/
│   └── ideas.json        ← scored idea backlog (8 ideas queued)
├── agents/
│   ├── researcher.py     ← manages idea intake
│   ├── scorer.py         ← scores & ranks ideas
│   └── builder.py        ← picks top idea to build
├── scripts/
│   ├── day1_hn_pain_scraper.py
│   └── day1b_github_stars_tracker.py
├── run.py                ← daily runner
└── README.md
```

---

## 💡 Idea Backlog

| # | Idea | Score | Status |
|---|---|---|---|
| 1 | HN Pain Point Scraper | 8.7 | ✅ Built |
| 2 | Gmail Receipt Organizer | 8.1 | 🔜 Next |
| 3 | Reddit Trend Monitor | 8.0 | Pending |
| 4 | Meeting Notes Formatter | 8.0 | Pending |
| 5 | Inbox Zero Digest | 7.9 | Pending |
| 6 | Job Board Scraper (HN) | 7.7 | Pending |
| 7 | Twitter/X AI Buzz Monitor | 7.7 | Pending |
| 8 | GitHub Stars Tracker | 7.6 | ✅ Built |

---

## Daily Workflow

```bash
# 1. Pull latest
git pull origin main

# 2. Run today's script
python scripts/day1_hn_pain_scraper.py

# 3. Check ideas backlog
python run.py
```

---

*Built daily with Claude 🤖 | One automation per day*

---

### Day 2 — Local Repo Secret Scanner
**File:** `scripts/day2_secret_scanner.py`
**Score:** 9.7 ⭐⭐⭐⭐⭐

28.65 million secrets were leaked on GitHub in 2025 — 64% still active years later. AI-assisted "vibe coding" doubles the leak rate. You cannot manually check hundreds of files and thousands of git commits. This script scans your entire local repo — every file AND full git history — for hardcoded API keys, tokens and credentials across 20+ patterns (OpenAI, AWS, GitHub, Stripe, Slack, MongoDB and more).

**How to use:**
1. Clone or navigate to any repo you want to scan
2. Run the script pointing at that repo
3. Review the report — CRITICAL findings need immediate action
4. Rotate any exposed keys — deleting the file is NOT enough

**Run it:**
```bash
# Scan a specific repo
python scripts/day2_secret_scanner.py --path /path/to/your/repo

# Scan current directory
python scripts/day2_secret_scanner.py --path .

# Skip git history (faster)
python scripts/day2_secret_scanner.py --path . --no-history
```
**Output:** `secret_scan_report_YYYYMMDD_HHMM.txt` with severity-ranked findings
