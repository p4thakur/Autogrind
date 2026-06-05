"""
Autogrind - Researcher Agent v3
---------------------------------
Sources:
- Twitter/X  → real-time pain points
- HackerNews → developer pain points
- GitHub Issues → feature requests

Credentials stored as env vars or GitHub Secrets.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime

try:
    import requests
    from requests_oauthlib import OAuth1
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

IDEAS_FILE = "ideas/ideas.json"

# Pain + automation signal words
PAIN_KEYWORDS = [
    "frustrated", "annoying", "manually", "hate doing", "takes forever",
    "wish there was", "pain point", "tedious", "repetitive", "waste time",
    "hours doing", "no tool", "need a way", "tired of", "killing me",
    "nightmare", "struggling", "can't find", "why isn't there",
    "someone should build", "would pay for", "does anyone else", "every single day",
    "automate this", "sick of", "still doing this", "by hand"
]

AUTOMATION_KEYWORDS = [
    "automate", "automation", "script", "workflow", "schedule",
    "batch", "integrate", "sync", "trigger", "notify", "alert", "monitor"
]

X_QUERIES = [
    "hate doing manually automate -is:retweet lang:en",
    "wish there was a tool automate -is:retweet lang:en",
    "still doing this manually script -is:retweet lang:en",
    "why is there no tool automate workflow -is:retweet lang:en",
    "hours wasted manually automate -is:retweet lang:en",
    "someone should build tool automate -is:retweet lang:en",
]

HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
HN_ASK_URL  = "https://hacker-news.firebaseio.com/v0/askstories.json"

# ── Helpers ───────────────────────────────────────────────────────────────
def fetch_json(url, headers=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Autogrind/3.0")
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
    hits = sum(1 for kw in PAIN_KEYWORDS if kw in t)
    return round((hits * 2) + (upvotes // 20) + (comments // 5), 2)

def is_relevant(text):
    t = text.lower()
    has_pain = any(kw in t for kw in PAIN_KEYWORDS)
    has_automation = any(kw in t for kw in AUTOMATION_KEYWORDS)
    return has_pain and has_automation

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

# ── Twitter/X ─────────────────────────────────────────────────────────────
def scrape_twitter():
    print("\n🐦 Twitter/X")

    if not HAS_REQUESTS:
        print("  ⚠️  requests library not installed. Run: pip install requests requests-oauthlib")
        return []

    api_key     = os.getenv("X_API_KEY")
    api_secret  = os.getenv("X_API_SECRET")
    acc_token   = os.getenv("X_ACCESS_TOKEN")
    acc_secret  = os.getenv("X_ACCESS_SECRET")

    if not all([api_key, api_secret, acc_token, acc_secret]):
        print("  ⚠️  Missing X credentials. Set env vars:")
        print("       X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET")
        return []

    auth = OAuth1(api_key, api_secret, acc_token, acc_secret)
    found = []
    seen = set()

    for query in X_QUERIES:
        try:
            resp = requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                auth=auth,
                params={
                    "query": query,
                    "max_results": 10,
                    "tweet.fields": "public_metrics,created_at"
                },
                timeout=10
            )
            if resp.status_code != 200:
                print(f"  ⚠️  X API error {resp.status_code}: {resp.text[:80]}")
                continue

            for tweet in resp.json().get("data", []):
                tid = tweet["id"]
                if tid in seen:
                    continue
                seen.add(tid)
                text    = tweet.get("text", "")
                metrics = tweet.get("public_metrics", {})
                likes   = metrics.get("like_count", 0)
                replies = metrics.get("reply_count", 0)
                ps      = pain_score(text, likes, replies)
                if ps > 0 and is_relevant(text):
                    found.append({
                        "raw_title":   text[:80],
                        "url":         f"https://x.com/i/web/status/{tid}",
                        "source":      "Twitter/X",
                        "upvotes":     likes,
                        "comments":    replies,
                        "pain_signal": ps
                    })
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️  {e}")

    found.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"  ✅ {len(found)} signals")
    return found[:10]

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
        ps = pain_score(title + " " + text, item.get("score", 0), item.get("descendants", 0))
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
    print("🔍 AUTOGRIND RESEARCHER v3")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    signals = scrape_twitter() + scrape_hackernews() + scrape_github()
    signals.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"\n📊 Total signals: {len(signals)}")

    data  = load_ideas()
    added = 0

    print("\n➕ Adding to backlog...")
    for s in signals:
        if is_duplicate(s["raw_title"], data["ideas"]):
            continue
        idea = make_idea(s["raw_title"], s["source"], s["url"],
                         s["upvotes"], s["comments"], s["pain_signal"], next_id(data))
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
