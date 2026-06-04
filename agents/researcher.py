"""
Autogrind - Researcher Agent (v2)
----------------------------------
Pulls pain points from multiple sources:
- Reddit (r/entrepreneur, r/freelance, r/SideProject, r/productivity)
- HackerNews Ask HN posts
- GitHub Issues (automation feature requests only)

No API keys needed. Run daily.
"""

import urllib.request
import urllib.parse
import json
import time
from datetime import datetime

IDEAS_FILE = "ideas/ideas.json"

PAIN_KEYWORDS = [
    "frustrated", "annoying", "manually", "hate doing", "takes forever",
    "wish there was", "pain point", "tedious", "repetitive", "waste time",
    "hours doing", "no tool", "doesn't exist", "need a way", "tired of",
    "killing me", "nightmare", "struggling", "can't find", "why isn't there",
    "someone should build", "would pay for", "does anyone else", "every single day"
]

AUTOMATION_KEYWORDS = [
    "automate", "automation", "script", "workflow", "schedule", "cron",
    "batch", "integrate", "sync", "trigger", "notify", "alert", "monitor"
]

REDDIT_SUBREDDITS = [
    "entrepreneur", "freelance", "SideProject",
    "Productivity", "smallbusiness", "webdev",
    "learnprogramming", "startups"
]

REDDIT_QUERIES = [
    "automate", "wish there was a tool",
    "manually every day", "pain point"
]

def fetch(url, headers=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Autogrind Research Bot/2.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  {url[:55]}... → {e}")
        return None

def score_pain(text, upvotes=0, comments=0):
    text_lower = text.lower()
    keyword_hits = sum(1 for kw in PAIN_KEYWORDS if kw in text_lower)
    engagement = (upvotes // 20) + (comments // 5)
    return round((keyword_hits * 2) + engagement, 2)

def is_automation_relevant(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in AUTOMATION_KEYWORDS + PAIN_KEYWORDS)

def load_ideas():
    with open(IDEAS_FILE) as f:
        return json.load(f)

def save_ideas(data):
    data["last_updated"] = datetime.now().isoformat()
    with open(IDEAS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def next_id(data):
    if not data["ideas"]:
        return 1
    return max(i["id"] for i in data["ideas"]) + 1

def is_duplicate(title, existing_ideas):
    title_words = set(title.lower().split())
    for idea in existing_ideas:
        existing_words = set(idea["title"].lower().split())
        overlap = len(title_words & existing_words) / max(len(title_words), 1)
        if overlap > 0.55:
            return True
    return False

def signal_to_idea(signal, idea_id):
    pain = signal["pain_signal"]
    demand = min(10, 5 + int(pain))
    buildability = 7
    value = min(10, 4 + int(signal["upvotes"] / 50))
    return {
        "id": idea_id,
        "title": signal["raw_title"][:80],
        "description": f"Pain point from {signal['source']}. Source: {signal['url']}",
        "source": signal["source"],
        "source_url": signal["url"],
        "demand": demand,
        "buildability": buildability,
        "value": value,
        "score": round((demand * 0.4) + (buildability * 0.3) + (value * 0.3), 2),
        "status": "pending",
        "added_at": datetime.now().isoformat()
    }

# ── Reddit ────────────────────────────────────────────────────────────────
def scrape_reddit():
    print("\n📡 Reddit")
    found = []
    for sub in REDDIT_SUBREDDITS:
        for query in REDDIT_QUERIES[:2]:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={urllib.parse.quote(query)}&sort=top&t=week&limit=10&restrict_sr=1"
            data = fetch(url)
            if not data:
                continue
            for post in data.get("data", {}).get("children", []):
                p = post["data"]
                title = p.get("title", "")
                body = p.get("selftext", "")
                combined = title + " " + body
                if not is_automation_relevant(combined):
                    continue
                pain = score_pain(combined, p.get("score", 0), p.get("num_comments", 0))
                if pain > 2:
                    found.append({
                        "raw_title": title,
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                        "source": f"r/{sub}",
                        "upvotes": p.get("score", 0),
                        "comments": p.get("num_comments", 0),
                        "pain_signal": pain
                    })
            time.sleep(0.5)
    found.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"  ✅ {len(found)} signals")
    return found[:10]

# ── HackerNews ────────────────────────────────────────────────────────────
def scrape_hackernews():
    print("\n📡 HackerNews")
    found = []
    ask_ids = fetch("https://hacker-news.firebaseio.com/v0/askstories.json") or []
    for story_id in ask_ids[:50]:
        item = fetch(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        if not item:
            continue
        title = item.get("title", "")
        text = item.get("text", "") or ""
        combined = title + " " + text
        if not is_automation_relevant(combined):
            continue
        pain = score_pain(combined, item.get("score", 0), item.get("descendants", 0))
        if pain > 1:
            found.append({
                "raw_title": title,
                "url": f"https://news.ycombinator.com/item?id={story_id}",
                "source": "HackerNews",
                "upvotes": item.get("score", 0),
                "comments": item.get("descendants", 0),
                "pain_signal": pain
            })
    found.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"  ✅ {len(found)} signals")
    return found[:10]

# ── GitHub Issues ─────────────────────────────────────────────────────────
def scrape_github_issues():
    print("\n📡 GitHub Issues")
    found = []
    queries = [
        "automate+workflow+feature+request",
        "automation+script+wish+feature",
        "manual+process+automate+request"
    ]
    for q in queries:
        url = f"https://api.github.com/search/issues?q={q}+label:enhancement&sort=reactions&order=desc&per_page=8"
        data = fetch(url, headers={"Accept": "application/vnd.github.v3+json"})
        if not data:
            continue
        for issue in data.get("items", []):
            title = issue.get("title", "")
            body = issue.get("body", "") or ""
            combined = title + " " + body[:300]
            if not is_automation_relevant(combined):
                continue
            reactions = issue.get("reactions", {}).get("total_count", 0)
            comments = issue.get("comments", 0)
            pain = score_pain(combined, reactions * 5, comments)
            if pain > 1:
                found.append({
                    "raw_title": title,
                    "url": issue.get("html_url", ""),
                    "source": "GitHub Issues",
                    "upvotes": reactions,
                    "comments": comments,
                    "pain_signal": pain
                })
        time.sleep(0.5)
    found.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"  ✅ {len(found)} signals")
    return found[:10]

# ── Main ──────────────────────────────────────────────────────────────────
def run():
    print("=" * 50)
    print("🔍 AUTOGRIND RESEARCHER v2")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    reddit_signals = scrape_reddit()
    hn_signals     = scrape_hackernews()
    github_signals = scrape_github_issues()

    all_signals = reddit_signals + hn_signals + github_signals
    all_signals.sort(key=lambda x: x["pain_signal"], reverse=True)
    print(f"\n📊 Total signals: {len(all_signals)}")

    data = load_ideas()
    added = 0

    print("\n➕ Adding to backlog...")
    for signal in all_signals:
        if is_duplicate(signal["raw_title"], data["ideas"]):
            continue
        idea = signal_to_idea(signal, next_id(data))
        data["ideas"].append(idea)
        print(f"  + [{idea['score']}] {idea['title'][:60]}")
        added += 1

    data["ideas"].sort(key=lambda x: x["score"], reverse=True)
    save_ideas(data)

    print(f"\n✅ Added {added} new ideas | Total: {len(data['ideas'])}")
    pending = [i for i in data["ideas"] if i["status"] == "pending"]
    print(f"\n🏆 Top 3 to build next:")
    for i, idea in enumerate(pending[:3], 1):
        print(f"   {i}. [{idea['score']}] {idea['title'][:60]}")

if __name__ == "__main__":
    run()
