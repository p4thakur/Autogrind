# 🤖 Autogrind

> A self-running micro-product factory. Every day, it finds what people want automated, scores the ideas, and builds the top one.

## How It Works

```
Research → Score → Build → Push
```

1. **Research** — Claude searches HN/Reddit for automation pain points
2. **Score** — Ideas rated on Demand + Buildability + Value
3. **Build** — Top scored idea gets turned into a working Python script
4. **Push** — Script lands in this repo

## Scoring Formula

| Criteria | Weight | Description |
|---|---|---|
| Demand | 40% | Are people asking for this? |
| Buildability | 30% | Can it be built in <2 hours? |
| Value | 30% | Would someone pay for it? |

## Structure

```
Autogrind/
├── ideas/
│   └── ideas.json        ← scored idea backlog
├── agents/
│   ├── researcher.py     ← manages idea intake
│   ├── scorer.py         ← scores & ranks ideas
│   └── builder.py        ← picks top idea to build
├── scripts/
│   └── (daily built scripts)
├── run.py                ← daily runner
└── README.md
```

## Daily Workflow

1. Claude researches new pain points
2. Adds them to `ideas.json`
3. Scores and sorts
4. Builds top script
5. Push to GitHub

---
Built with Claude 🤖
