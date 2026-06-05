"""
Day 2 - Autogrind
Overdue Invoice WhatsApp Reminder
-----------------------------------
Small businesses manually send WhatsApp reminders when accounting
software auto-reminders don't work. This script reads a CSV of
overdue invoices and generates ready-to-send WhatsApp message links.

No API needed. Just a CSV file.

Score: 9.0 | Demand: 9 | Buildability: 9 | Value: 9

How to run:
    python scripts/day2_invoice_whatsapp_reminder.py

Input:  invoices.csv (created automatically if missing)
Output: whatsapp_reminders_YYYYMMDD.txt + prints clickable links
"""

import csv
import json
import urllib.parse
from datetime import datetime, date
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────────────
SAMPLE_CSV = "invoices.csv"

REMINDER_TEMPLATES = {
    "gentle": (
        "Hi {name}, hope you're doing well! "
        "Just a friendly reminder that invoice #{invoice_id} for {currency}{amount} "
        "was due on {due_date}. "
        "Please let me know if you have any questions. Thanks!"
    ),
    "firm": (
        "Hi {name}, this is a reminder that invoice #{invoice_id} "
        "for {currency}{amount} is now {days_overdue} days overdue (due {due_date}). "
        "Please arrange payment at your earliest convenience."
    ),
    "urgent": (
        "Hi {name}, URGENT: Invoice #{invoice_id} for {currency}{amount} "
        "is {days_overdue} days overdue. "
        "Please make payment immediately or contact us to discuss. "
        "Due date was {due_date}."
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────
def create_sample_csv():
    """Create a sample CSV if none exists"""
    rows = [
        ["invoice_id", "client_name", "phone", "amount", "currency", "due_date"],
        ["INV-001", "Rahul Sharma", "919876543210", "15000", "₹", "2026-05-15"],
        ["INV-002", "Priya Patel",  "919812345678", "8500",  "₹", "2026-05-20"],
        ["INV-003", "Amit Kumar",   "919898765432", "32000", "₹", "2026-04-30"],
        ["INV-004", "Neha Singh",   "919911223344", "5000",  "₹", "2026-05-28"],
    ]
    with open(SAMPLE_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"📄 Created sample {SAMPLE_CSV} — edit it with your real invoices!\n")


def days_overdue(due_date_str):
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        return (date.today() - due).days
    except Exception:
        return 0


def pick_template(days):
    if days <= 7:
        return "gentle"
    elif days <= 21:
        return "firm"
    else:
        return "urgent"


def make_whatsapp_link(phone, message):
    """Generate a wa.me link — click to open WhatsApp with pre-filled message"""
    clean_phone = "".join(filter(str.isdigit, phone))
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded}"


def run():
    print("=" * 55)
    print("📱 OVERDUE INVOICE WHATSAPP REMINDER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    # Create sample CSV if needed
    if not Path(SAMPLE_CSV).exists():
        create_sample_csv()

    # Read invoices
    invoices = []
    with open(SAMPLE_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            invoices.append(row)

    print(f"📋 Found {len(invoices)} invoices in {SAMPLE_CSV}\n")

    overdue = []
    for inv in invoices:
        d = days_overdue(inv["due_date"])
        if d > 0:
            inv["days_overdue"] = d
            overdue.append(inv)

    if not overdue:
        print("✅ No overdue invoices! All payments are on time.")
        return

    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    print(f"⚠️  {len(overdue)} overdue invoices found:\n")

    results = []
    output_lines = [
        f"WHATSAPP REMINDERS — {datetime.now().strftime('%Y-%m-%d')}",
        "=" * 55,
        ""
    ]

    for inv in overdue:
        days = inv["days_overdue"]
        tone = pick_template(days)
        template = REMINDER_TEMPLATES[tone]

        message = template.format(
            name=inv["client_name"],
            invoice_id=inv["invoice_id"],
            amount=inv["amount"],
            currency=inv.get("currency", ""),
            due_date=inv["due_date"],
            days_overdue=days,
        )

        link = make_whatsapp_link(inv["phone"], message)

        tone_emoji = {"gentle": "😊", "firm": "⏰", "urgent": "🚨"}[tone]
        print(f"{tone_emoji} {inv['client_name']} — {inv['currency']}{inv['amount']} — {days} days overdue")
        print(f"   Tone: {tone.upper()}")
        print(f"   Link: {link[:80]}...")
        print()

        results.append({
            "client": inv["client_name"],
            "invoice": inv["invoice_id"],
            "amount": f"{inv['currency']}{inv['amount']}",
            "days_overdue": days,
            "tone": tone,
            "whatsapp_link": link,
            "message": message
        })

        output_lines += [
            f"Client: {inv['client_name']}",
            f"Invoice: #{inv['invoice_id']} | Amount: {inv['currency']}{inv['amount']} | Overdue: {days} days",
            f"Tone: {tone.upper()}",
            f"Message: {message}",
            f"WhatsApp Link: {link}",
            "-" * 55,
            ""
        ]

    # Save output
    txt_file = f"scripts/whatsapp_reminders_{datetime.now().strftime('%Y%m%d')}.txt"
    json_file = f"scripts/whatsapp_reminders_{datetime.now().strftime('%Y%m%d')}.json"

    with open(txt_file, "w") as f:
        f.write("\n".join(output_lines))

    with open(json_file, "w") as f:
        json.dump({"generated_at": datetime.now().isoformat(), "reminders": results}, f, indent=2)

    print(f"✅ Saved to:")
    print(f"   {txt_file}  ← copy-paste ready messages")
    print(f"   {json_file} ← structured data")
    print(f"\n💡 Tip: Click any WhatsApp link to open the chat with message pre-filled!")


if __name__ == "__main__":
    run()
