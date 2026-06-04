"""
Day 1 - Autogrind
HN Pain Point Scraper
----------------------
Scrapes HackerNews "Ask HN" posts using the official Firebase API,
finds pain points people mention, saves top results to JSON.

Score: 8.7 | Demand: 9 | Buildability: 9 | Value: 8
"""

import urllib.request
import json
from datetime import datetime

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_NEW = "https://hacker-news.firebaseio.com/v0/newstories.json"
HN_ASK = "https://hacker-news.firebaseio.com/v0/askstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

PAIN_KEYWORDS = [
    "frustrated", "annoying", "manually", "hate doing", "takes forever",
    "wish there was", "pain point", "tedious", "repetitive", "waste time",
    "hours doing", "broken", "no tool", "doesn't exist", "need a way",
    "how do you", "tired of", "killing me", "nightmare", "struggling"
]

def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  Error: {e}")
        return None

def get_item(item_id):
    return fetch(HN_ITEM.format(item_id))

def run():
    print("=== HN Pain Point Scraper ===")
    print(f"Running: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    print("Fetching Ask HN stories...")
    ask_ids = fetch(HN_ASK) or []
    top_ids = fetch(HN_TOP) or []

    # Take top 60 from each
    ids_to_check = list(dict.fromkeys(ask_ids[:40] + top_ids[:40]))
    print(f"Checking {len(ids_to_check)} stories...\n")

    pain_points = []

    for i, story_id in enumerate(ids_to_check):
        item = get_item(story_id)
        if not item:
            continue

        title = item.get("title", "")
        text = item.get("text", "") or ""
        combined = (title + " " + text).lower()

        matched = [kw for kw in PAIN_KEYWORDS if kw in combined]
        is_ask = title.lower().startswith("ask hn")

        if matched or is_ask:
            pain_score = len(matched) * 2 + (item.get("score", 0) // 10)
            pain_points.append({
                "title": title,
                "url": f"https://news.ycombinator.com/item?id={story_id}",
                "points": item.get("score", 0),
                "comments": item.get("descendants", 0),
                "author": item.get("by", ""),
                "matched_keywords": matched,
                "pain_score": pain_score
            })

        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(ids_to_check)}...")

    pain_points.sort(key=lambda x: x["pain_score"], reverse=True)
    top = pain_points[:10]

    print(f"\nTop {len(top)} Pain Points Found:")
    print("-" * 60)
    for i, p in enumerate(top, 1):
        print(f"{i}. {p['title']}")
        print(f"   Points: {p['points']} | Comments: {p['comments']}")
        if p['matched_keywords']:
            print(f"   Keywords: {', '.join(p['matched_keywords'])}")
        print(f"   URL: {p['url']}")
        print()

    filename = f"scripts/hn_pain_points_{datetime.now().strftime('%Y%m%d')}.json"
    output = {
        "scraped_at": datetime.now().isoformat(),
        "total_found": len(top),
        "pain_points": top
    }
    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Saved to {filename}")
    return top

if __name__ == "__main__":
    run()
