"""
Autogrind - Daily Automation Pipeline
Run this daily to:
1. See top idea
2. Build it (via Claude)
3. Push to GitHub
"""

from agents.scorer import sort_ideas
from agents.builder import get_top_idea

def main():
    print("=== AUTOGRIND DAILY RUN ===\n")
    
    print("Step 1: Scoring & sorting ideas...")
    ideas = sort_ideas()
    
    print(f"\nStep 2: Top 3 ideas today:")
    for i, idea in enumerate(ideas[:3]):
        print(f"  {i+1}. [{idea['score']}] {idea['title']} ({idea['status']})")
    
    print(f"\nStep 3: Building top idea...")
    top = get_top_idea()
    if top:
        print(f"  -> {top['title']}")
        print(f"  -> Ask Claude to build this now!")
    else:
        print("  -> No pending ideas. Run researcher first!")

if __name__ == "__main__":
    main()
