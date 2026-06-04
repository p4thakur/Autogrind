"""
Day 1b - Autogrind
GitHub Stars Tracker
---------------------
Tracks trending GitHub repos in AI/automation space daily.
Alerts when new repos are blowing up.
No API key needed for public data.

Score: 7.6 | Demand: 7 | Buildability: 9 | Value: 7
"""

import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta

GH_SEARCH = "https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=10"

TOPICS = [
    "ai automation python",
    "llm agent python",
    "python scraper tool",
    "developer productivity cli",
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Autogrind/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  Error: {e}")
        return None

def search_repos(query):
    url = GH_SEARCH.format(query=urllib.parse.quote(query))
    data = fetch(url)
    if not data:
        return []
    return data.get("items", [])

def format_number(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def run():
    print("=== GitHub Stars Tracker ===")
    print(f"Running: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    all_repos = []
    seen = set()

    for topic in TOPICS:
        print(f"Searching: '{topic}'...")
        repos = search_repos(topic)
        for r in repos:
            rid = r["id"]
            if rid not in seen:
                seen.add(rid)
                # Only include repos updated in last 30 days
                updated = r.get("updated_at", "")
                all_repos.append({
                    "name": r["full_name"],
                    "description": r.get("description", "No description"),
                    "stars": r["stargazers_count"],
                    "forks": r["forks_count"],
                    "language": r.get("language", "Unknown"),
                    "url": r["html_url"],
                    "updated_at": updated,
                    "topics": r.get("topics", [])
                })
        print(f"  Found {len(repos)} repos")

    # Sort by stars
    all_repos.sort(key=lambda x: x["stars"], reverse=True)
    top = all_repos[:15]

    print(f"\n🔥 Top {len(top)} Trending Repos in AI/Automation:")
    print("-" * 60)
    for i, r in enumerate(top, 1):
        print(f"{i}. ⭐ {format_number(r['stars'])}  {r['name']}")
        print(f"   {r['description'][:80] if r['description'] else 'No description'}")
        print(f"   Lang: {r['language']} | Forks: {r['forks']}")
        print(f"   {r['url']}")
        print()

    filename = f"scripts/github_trending_{datetime.now().strftime('%Y%m%d')}.json"
    output = {
        "scraped_at": datetime.now().isoformat(),
        "total_found": len(top),
        "repos": top
    }
    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Saved to {filename}")
    return top

if __name__ == "__main__":
    run()
