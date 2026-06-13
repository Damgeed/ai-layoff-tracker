#!/usr/bin/env python3
"""Source preservation for AI Layoff Tracker.
Constructs archive.org URLs for every source citation and generates
a consolidated sources.json for the public API.

Does NOT make HTTP calls — archive.org can be flaky/slow.
The archive URL construction is deterministic and verifiable.
"""
import json
from pathlib import Path
from datetime import date, datetime

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "entries.json"
OUTPUT_DIR = ROOT / "docs" / "api"


def load_entries():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def generate_sources(entries_data):
    sources = []
    today = date.today().isoformat()

    for entry in entries_data["entries"]:
        src = entry.get("source", {})
        source_entry = {
            "entry_id": entry["id"],
            "company": entry["company"],
            "date": entry["date"],
            "classification": entry["classification"],
            "source_title": src.get("title", ""),
            "source_url": src.get("url", ""),
            "archive_url": f"https://web.archive.org/web/*/{src.get('url', '')}",
            "publisher": src.get("publisher", ""),
            "published_date": src.get("published_date", ""),
            "retrieved_date": src.get("retrieved_date", ""),
            "is_archived": False,  # set to True once confirmed via archive.org
        }
        sources.append(source_entry)

    return sources


def main():
    entries_data = load_entries()
    sources = generate_sources(entries_data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sources_path = OUTPUT_DIR / "sources.json"
    with open(sources_path, "w") as f:
        json.dump({
            "project": "AI Layoff Tracker",
            "description": "Source citations with archive.org links for every entry.",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "total_sources": len(sources),
            "sources": sources,
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ sources.json generated: {len(sources)} sources → {sources_path}")


if __name__ == "__main__":
    main()
