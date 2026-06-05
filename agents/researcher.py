"""
Autogrind - Researcher Agent v4
---------------------------------
Sources:
- HackerNews Ask HN  (free, no auth)
- GitHub Issues      (free, no auth)
- Claude web search  (done manually each session)

Run daily by calling: python agents/researcher.py
"""

import json
import time
import urllib.request
from datetime import datetime

IDEAS_FILE = "ideas/ideas.json"

PAIN_KEYWORDS = [
    "manually", "by hand", "every day", "waste time", "takes forever",
    "sick of", "tired of", "tedious", "annoying", "kills me",
    "hours on", "hate doing", "repetitive", "nightmare", "still doing this"
]

DEMAND_KEYWORDS = [
    "wish there was", "would be great if", "someone should build",
    "would pay for", "would love a tool", "need a tool", "if only",
    "is there a way to automate", "i would use", "take my money",
    "please build", "would save so much time", "anyone built",
    "has anyone made", "looking for a tool"
]

AUTOMATION_KEYWORDS = [
    "automate", "automation", "script", "workflow", "schedule",
    "batch", "integrate", "sync", "trigger", "notify", "alert", "monitor"
]

HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
HN_ASK_URL  = "https://hacker-news.firebaseio.com/v0/askstories.json"

# ── Helpers ───────────────────────────────────────────────────────────────
def fetch_json(url, headers=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Autogrind/4.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  {str(e)[:60]}")
        return None

def pain_score(text, upvotes=0, comments=0):
    t = text.lower()
    pain   = sum(1 for kw in PAIN_KEYWORDS if kw in t)
    demand = sum(1 for kw in DEMAND_KEYWORDS if kw in t)
    return round((pain * 2) + (demand * 3) + (upvotes // 20) + (comments // 5), 2)

def is_relevant(text):
    t = text.lower()
    has_pain   = any(kw in t for kw in PAIN_KEYWORDS)
    has_demand = any(kw in t for kw in DEMAND_KEYWORDS)
    return has_pain or has_demand

def load_ideas():
    with open(IDEAS_FILE) as f:
        return json.load(f)

def save_ideas(data):
    data["last_updated"] = datetime.now().isoformat()
    with open(IDEAS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def next_id(data):
    return max((i["id"] for i in data["ideas"]), default=0) + 1

def is_duplicate(title, existing):
    words = set(title.lower().split())
    for idea in existing:
        existing_words = set(idea["title"].lower().split())
        if len(words & existing_words) / max(len(words), 1) > 0.55:
            return True
    return False

def make_idea(title, source, url, upvotes, comments, pain, idea_id):
    demand       = min(10, 5 + int(pain))
    buildability = 7
    value        = min(10, 4 + int(upvotes / 50))
    return {
        "id":           idea_id,
        "title":        title[:80],
        "description":  f"Pain point from {source}. Source: {url}",
        "source":       source,
        "source_url":   url,
        "demand":       demand,
        "buildability": buildability,
        "value":        value,
        "score":        round((demand * 0.4) + (buildability * 0.3) + (value * 0.3), 2),
        "status":       "pending",
        "added_at":     datetime.now().isoformat()
    }

def add_idea_manually(title, description, source, source_url,
                      demand, buildability, value):
    """
    Called by Claude after doing web research.
    Claude finds pain points, scores them, and adds via this function.
    """
    data = load_ideas()
    if is_duplicate(title, data["ideas"]):
        print(f"  ⚠️  Duplicate skipped: {title[:50]}")
        return None

    idea = {
        "id":           next_id(data),
        "title":        title[:80],
        "description":  description,
        "source":       source,
        "source_url":   source_url,
        "demand":       demand,
        "buildability": buildability,
        "value":        value,
        "score":        round((demand * 0.4) + (buildability * 0.3) + (value * 0.3), 2),
        "status":       "pending",
        "added_at":     datetime.now().isoformat()
    }
    data["ideas"].append(idea)
    data["ideas"].sort(key=lambda x: x["score"], reverse=True)
    save_ideas(data)
    print(f"  + [{idea['score']}] {idea['title']}")
    return idea

# ── HackerNews ────────────────────────────────────────────────────────────
def scrape_hackernews():
    print("\n📰 HackerNews")
    found = []
    ask_ids = fetch_json(HN_ASK_URL) or []

    for sid in ask_ids[:60]:
        item = fetch_json(HN_ITEM_URL.format(sid))
        if not item:
            continue
        title = item.get("title", "")
        text  = item.get("text", "") or ""
        if not is_relevant(title + " " + text):
            continue
        ps = pain_score(title + " " + text,
                        item.get("score", 0),
                        item.get("descendants", 0))
        if ps > 1:
            found.append({
                "raw_title":   title,
                "url":         f"https://news.ycombinator.com/item?id={sid}",
                "source":      "HackerNews",
                "upvotes":     item.get("score", 0),
                "comments":    item.get("descendants", 0),
                "pain_signal": ps
            })

    found.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"  ✅ {len(found)} signals")
    return found[:10]

# ── GitHub Issues ─────────────────────────────────────────────────────────
def scrape_github():
    print("\n🐙 GitHub Issues")
    found = []
    queries = [
        "automate+workflow+feature+request+label:enhancement",
        "manual+process+automate+wish+label:enhancement",
    ]
    for q in queries:
        data = fetch_json(
            f"https://api.github.com/search/issues?q={q}&sort=reactions&order=desc&per_page=8",
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        if not data:
            continue
        for issue in data.get("items", []):
            title = issue.get("title", "")
            body  = (issue.get("body", "") or "")[:300]
            if not is_relevant(title + " " + body):
                continue
            reactions = issue.get("reactions", {}).get("total_count", 0)
            comments  = issue.get("comments", 0)
            ps = pain_score(title + " " + body, reactions * 5, comments)
            if ps > 1:
                found.append({
                    "raw_title":   title,
                    "url":         issue.get("html_url", ""),
                    "source":      "GitHub Issues",
                    "upvotes":     reactions,
                    "comments":    comments,
                    "pain_signal": ps
                })
        time.sleep(0.5)

    found.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"  ✅ {len(found)} signals")
    return found[:10]

# ── Main ──────────────────────────────────────────────────────────────────
def run():
    print("=" * 50)
    print("🔍 AUTOGRIND RESEARCHER v4")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("   Sources: HackerNews + GitHub Issues")
    print("   + Claude web research (done in session)")
    print("=" * 50)

    hn_signals     = scrape_hackernews()
    github_signals = scrape_github()

    signals = hn_signals + github_signals
    signals.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"\n📊 Total signals: {len(signals)}")

    data  = load_ideas()
    added = 0

    print("\n➕ Adding to backlog...")
    for s in signals:
        if is_duplicate(s["raw_title"], data["ideas"]):
            continue
        idea = make_idea(s["raw_title"], s["source"], s["url"],
                         s["upvotes"], s["comments"],
                         s["pain_signal"], next_id(data))
        data["ideas"].append(idea)
        print(f"  + [{idea['score']}] {idea['title'][:60]}")
        added += 1

    data["ideas"].sort(key=lambda x: x["score"], reverse=True)
    save_ideas(data)

    print(f"\n✅ Added {added} ideas | Total backlog: {len(data['ideas'])}")
    pending = [i for i in data["ideas"] if i["status"] == "pending"]
    print("\n🏆 Top 3 to build next:")
    for i, idea in enumerate(pending[:3], 1):
        print(f"   {i}. [{idea['score']}] {idea['title'][:60]}")

if __name__ == "__main__":
    run()
