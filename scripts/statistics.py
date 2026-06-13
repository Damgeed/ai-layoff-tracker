#!/usr/bin/env python3
"""Statistics computation for AI Layoff Tracker."""
import json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    with open(ROOT / "data" / "entries.json") as f:
        data = json.load(f)
    entries = data["entries"]
    total = sum(e["jobs_lost"] for e in entries)
    companies = len(set(e["company"] for e in entries))
    
    by_ind = {}
    for e in entries:
        ind = e["industry"]
        by_ind[ind] = by_ind.get(ind, {"jobs": 0, "entries": 0})
        by_ind[ind]["jobs"] += e["jobs_lost"]
        by_ind[ind]["entries"] += 1
    
    by_class = {}
    for e in entries:
        c = e["classification"]
        by_class[c] = by_class.get(c, {"jobs": 0, "entries": 0})
        by_class[c]["jobs"] += e["jobs_lost"]
        by_class[c]["entries"] += 1
    
    print(f"Total jobs lost: {total:,}")
    print(f"Companies: {companies}")
    print(f"Entries: {len(entries)}")
    print(f"\nBy Industry:")
    for k, v in sorted(by_ind.items(), key=lambda x: x[1]["jobs"], reverse=True):
        print(f"  {k}: {v['jobs']:,} jobs ({v['entries']} entries)")
    print(f"\nBy Classification:")
    for k, v in sorted(by_class.items(), key=lambda x: x[1]["jobs"], reverse=True):
        print(f"  {k}: {v['jobs']:,} jobs ({v['entries']} entries)")

if __name__ == "__main__":
    main()
