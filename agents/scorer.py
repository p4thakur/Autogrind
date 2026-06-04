"""
Scorer Agent
Scores ideas based on:
- demand: are people complaining about this? (1-10)
- buildability: can it be done in <2 hours? (1-10)
- value: would someone pay for this? (1-10)
Final score = weighted average
"""

import json
from datetime import datetime

def score_idea(idea: dict) -> dict:
    demand = idea.get("demand", 5)
    buildability = idea.get("buildability", 5)
    value = idea.get("value", 5)
    idea["score"] = round((demand * 0.4) + (buildability * 0.3) + (value * 0.3), 2)
    return idea

def sort_ideas(ideas_path="ideas/ideas.json"):
    with open(ideas_path, "r") as f:
        data = json.load(f)
    
    data["ideas"] = [score_idea(i) for i in data["ideas"]]
    data["ideas"].sort(key=lambda x: x["score"], reverse=True)
    data["last_updated"] = datetime.now().isoformat()

    with open(ideas_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Scored and sorted {len(data['ideas'])} ideas.")
    return data["ideas"]

if __name__ == "__main__":
    sort_ideas()
