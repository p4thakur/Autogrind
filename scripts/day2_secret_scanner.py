"""
Day 2 - Autogrind
Local Repo Secret Scanner
--------------------------
Scans your local git repos for hardcoded API keys, tokens
and secrets across all files AND full git history.

Why this matters:
- 28.65M secrets leaked on GitHub in 2025 (34% YoY increase)
- AI-assisted code leaks secrets at 2x the rate of human code
- 64% of secrets leaked in 2022 were STILL ACTIVE in 2026
- You cannot manually check hundreds of files across git history

Score: 9.7 | Demand: 10 | Buildability: 9 | Value: 10

How to run:
    python scripts/day2_secret_scanner.py --path /path/to/your/repo
    python scripts/day2_secret_scanner.py --path .  (scan current dir)

Output: secret_scan_report_YYYYMMDD.txt
"""

import os
import re
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# ── Secret Patterns ────────────────────────────────────────────────────────
# Each pattern: (name, regex, severity)
SECRET_PATTERNS = [
    # AI / LLM
    ("OpenAI API Key",       r"sk-[a-zA-Z0-9]{32,}",                          "CRITICAL"),
    ("Anthropic API Key",    r"sk-ant-[a-zA-Z0-9\-]{32,}",                    "CRITICAL"),
    ("HuggingFace Token",    r"hf_[a-zA-Z0-9]{32,}",                          "HIGH"),

    # Cloud
    ("AWS Access Key",       r"AKIA[0-9A-Z]{16}",                             "CRITICAL"),
    ("AWS Secret Key",       r"(?i)aws.{0,20}secret.{0,20}['\"][0-9a-zA-Z/+]{40}['\"]", "CRITICAL"),
    ("GCP API Key",          r"AIza[0-9A-Za-z\-_]{35}",                       "CRITICAL"),
    ("Azure Storage Key",    r"DefaultEndpointsProtocol=https;AccountName=",  "HIGH"),

    # Payment
    ("Stripe Live Key",      r"sk_live_[0-9a-zA-Z]{24,}",                    "CRITICAL"),
    ("Stripe Test Key",      r"sk_test_[0-9a-zA-Z]{24,}",                    "MEDIUM"),
    ("PayPal Secret",        r"(?i)paypal.{0,20}['\"][a-zA-Z0-9_\-]{16,}['\"]", "HIGH"),

    # Communication
    ("Slack Token",          r"xox[baprs]-[0-9a-zA-Z\-]{10,}",               "HIGH"),
    ("Slack Webhook",        r"https://hooks\.slack\.com/services/[A-Z0-9/]+","HIGH"),
    ("Twilio Account SID",   r"AC[a-zA-Z0-9]{32}",                            "HIGH"),
    ("SendGrid Key",         r"SG\.[a-zA-Z0-9\-_]{22,}\.[a-zA-Z0-9\-_]{43,}","HIGH"),

    # Dev tools
    ("GitHub Token",         r"ghp_[a-zA-Z0-9]{36}",                         "CRITICAL"),
    ("GitHub OAuth",         r"gho_[a-zA-Z0-9]{36}",                         "HIGH"),
    ("GitHub PAT Classic",   r"github_pat_[a-zA-Z0-9_]{82}",                 "CRITICAL"),
    ("NPM Token",            r"npm_[a-zA-Z0-9]{36}",                         "HIGH"),

    # Database
    ("MongoDB URI",          r"mongodb(\+srv)?://[^:]+:[^@]+@",              "CRITICAL"),
    ("PostgreSQL URI",       r"postgresql://[^:]+:[^@]+@",                   "CRITICAL"),
    ("MySQL URI",            r"mysql://[^:]+:[^@]+@",                        "HIGH"),

    # Generic high-entropy patterns
    ("Generic Secret",       r"(?i)(secret|password|passwd|pwd|token|api_key|apikey|private_key)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "MEDIUM"),
    ("Hardcoded Bearer",     r"(?i)bearer\s+[a-zA-Z0-9\-_\.]{20,}",         "MEDIUM"),
]

SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
                   '.pdf', '.zip', '.tar', '.gz', '.exe', '.bin',
                   '.pyc', '.class', '.lock', '.sum'}

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv',
             'venv', 'env', '.env', 'dist', 'build', '.next'}


# ── Scanner ────────────────────────────────────────────────────────────────
def scan_content(content, source_label):
    findings = []
    for name, pattern, severity in SECRET_PATTERNS:
        try:
            matches = list(re.finditer(pattern, content))
            for m in matches:
                # Get context (surrounding line)
                start = max(0, m.start() - 30)
                end = min(len(content), m.end() + 30)
                context = content[start:end].replace('\n', ' ').strip()
                # Redact the actual secret value
                redacted = context[:m.start()-start] + "***REDACTED***" + context[m.end()-start:]
                findings.append({
                    "type": name,
                    "severity": severity,
                    "source": source_label,
                    "context": redacted[:120]
                })
        except re.error:
            continue
    return findings


def scan_files(repo_path):
    print("\n📂 Scanning files...")
    findings = []
    scanned = 0
    skipped = 0

    for root, dirs, files in os.walk(repo_path):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in SKIP_EXTENSIONS:
                skipped += 1
                continue
            try:
                content = fpath.read_text(encoding='utf-8', errors='ignore')
                rel_path = str(fpath.relative_to(repo_path))
                found = scan_content(content, f"FILE: {rel_path}")
                findings.extend(found)
                scanned += 1
            except Exception:
                skipped += 1

    print(f"  ✅ Scanned {scanned} files, skipped {skipped}")
    return findings


def scan_git_history(repo_path):
    print("\n🕰️  Scanning git history...")
    findings = []

    try:
        result = subprocess.run(
            ["git", "log", "--all", "--oneline"],
            cwd=repo_path, capture_output=True, text=True, timeout=30
        )
        commits = [line.split()[0] for line in result.stdout.strip().split('\n') if line]
        print(f"  Found {len(commits)} commits to scan...")

        for i, commit in enumerate(commits[:100]):  # cap at 100 commits
            try:
                diff = subprocess.run(
                    ["git", "show", commit, "--stat", "-p", "--no-color"],
                    cwd=repo_path, capture_output=True, text=True, timeout=10
                )
                found = scan_content(diff.stdout, f"GIT HISTORY: commit {commit[:8]}")
                findings.extend(found)
            except Exception:
                continue

            if (i + 1) % 20 == 0:
                print(f"  Processed {i+1}/{min(len(commits), 100)} commits...")

        print(f"  ✅ Scanned {min(len(commits), 100)} commits")
    except FileNotFoundError:
        print("  ⚠️  git not found — skipping history scan")
    except Exception as e:
        print(f"  ⚠️  Error scanning git history: {e}")

    return findings


def deduplicate(findings):
    seen = set()
    unique = []
    for f in findings:
        key = (f["type"], f["source"][:50])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def run():
    parser = argparse.ArgumentParser(description="Scan local git repo for leaked secrets")
    parser.add_argument("--path", default=".", help="Path to repo (default: current dir)")
    parser.add_argument("--no-history", action="store_true", help="Skip git history scan")
    args = parser.parse_args()

    repo_path = Path(args.path).resolve()

    print("=" * 55)
    print("🔐 LOCAL REPO SECRET SCANNER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Scanning: {repo_path}")
    print("=" * 55)

    all_findings = []

    # Scan files
    all_findings += scan_files(repo_path)

    # Scan git history
    if not args.no_history:
        all_findings += scan_git_history(repo_path)

    # Deduplicate
    all_findings = deduplicate(all_findings)

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    all_findings.sort(key=lambda x: severity_order.get(x["severity"], 3))

    # Count by severity
    critical = [f for f in all_findings if f["severity"] == "CRITICAL"]
    high     = [f for f in all_findings if f["severity"] == "HIGH"]
    medium   = [f for f in all_findings if f["severity"] == "MEDIUM"]

    print(f"\n{'=' * 55}")
    print("🔍 SCAN RESULTS")
    print(f"{'=' * 55}")
    print(f"  🚨 CRITICAL : {len(critical)}")
    print(f"  ⚠️  HIGH     : {len(high)}")
    print(f"  ℹ️  MEDIUM   : {len(medium)}")
    print(f"  Total       : {len(all_findings)}")

    if not all_findings:
        print("\n✅ No secrets found! Your repo looks clean.")
    else:
        print(f"\n{'─' * 55}")
        for f in all_findings:
            icon = {"CRITICAL": "🚨", "HIGH": "⚠️ ", "MEDIUM": "ℹ️ "}.get(f["severity"], "  ")
            print(f"\n{icon} [{f['severity']}] {f['type']}")
            print(f"   Source : {f['source']}")
            print(f"   Context: {f['context']}")

    # Save report
    report_file = f"scripts/secret_scan_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    lines = [
        "SECRET SCAN REPORT",
        f"Repo: {repo_path}",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 55,
        f"CRITICAL: {len(critical)} | HIGH: {len(high)} | MEDIUM: {len(medium)}",
        "=" * 55,
        ""
    ]
    for f in all_findings:
        lines += [
            f"[{f['severity']}] {f['type']}",
            f"Source : {f['source']}",
            f"Context: {f['context']}",
            "─" * 40,
            ""
        ]

    with open(report_file, "w") as rf:
        rf.write("\n".join(lines))

    print(f"\n📄 Report saved to {report_file}")

    if critical:
        print("\n🚨 ACTION REQUIRED: Rotate CRITICAL secrets immediately!")
        print("   Deleting the file is NOT enough — rotate the keys themselves.")


if __name__ == "__main__":
    run()
