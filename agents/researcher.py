"""
Researcher Agent
- Searches HN / Reddit for automation pain points
- Claude (via claude.ai) does the actual research and scoring
- This script just manages the ideas.json file
"""

import json
from datetime import datetime

def add_idea(title, description, source, demand, buildability, value, ideas_path="ideas/ideas.json"):
    with open(ideas_path, "r") as f:
        data = json.load(f)

    idea = {
        "id": len(data["ideas"]) + 1,
        "title": title,
        "description": description,
        "source": source,
        "demand": demand,
        "buildability": buildability,
        "value": value,
        "score": 0,
        "status": "pending",
        "added_at": datetime.now().isoformat()
    }

    data["ideas"].append(idea)
    data["last_updated"] = datetime.now().isoformat()

    with open(ideas_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Added idea: {title}")
    return idea

if __name__ == "__main__":
    print("Researcher ready. Use add_idea() to add ideas from Claude research.")
