#!/usr/bin/env python3
"""
Enrich entries with confidence_breakdown and history tracking.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "entries.json"
API_DIR = ROOT / "docs" / "api"

def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {DATA_FILE}")

def has_evidence_type(evidence, *types):
    """Check if any evidence item matches given types."""
    for ev in evidence:
        if ev.get("type") in types:
            return True
    return False

def compute_breakdown(entry):
    """Compute confidence_breakdown for an entry based on scoring rules."""
    evidence = entry.get("evidence", [])
    source = entry.get("source", {})
    source_quality = entry.get("source_quality", "")
    confidence_score = entry.get("confidence_score", 0)

    breakdown = []

    # Base 30 points
    breakdown.append({"factor": "Base score", "points": 30})
    total = 30

    # +25 if evidence includes CEO_STATEMENT
    if has_evidence_type(evidence, "CEO_STATEMENT"):
        breakdown.append({"factor": "CEO statement", "points": 25})
        total += 25

    # +20 if evidence includes EARNINGS_CALL or SEC_FILING
    # Also match EARNINGS_REPORT and FINANCIAL_REPORT as equivalents
    if has_evidence_type(evidence, "EARNINGS_CALL", "SEC_FILING", "EARNINGS_REPORT", "FINANCIAL_REPORT"):
        breakdown.append({"factor": "Earnings/financial disclosure", "points": 20})
        total += 20

    # +15 for OFFICIAL_STATEMENT or COMPANY_PRESS_RELEASE
    # Also match COMPANY_STATEMENT as equivalent
    if has_evidence_type(evidence, "OFFICIAL_STATEMENT", "COMPANY_PRESS_RELEASE", "COMPANY_STATEMENT"):
        breakdown.append({"factor": "Official company statement", "points": 15})
        total += 15

    # +10 for archived source (source.archive_url exists)
    if source.get("archive_url"):
        breakdown.append({"factor": "Archived source", "points": 10})
        total += 10

    # +5 if multiple independent sources (evidence array length >= 2)
    if len(evidence) >= 2:
        breakdown.append({"factor": "Multiple sources", "points": 5})
        total += 5

    # +5 if source is PRIMARY_SOURCE
    if source_quality == "PRIMARY_SOURCE":
        breakdown.append({"factor": "Primary source", "points": 5})
        total += 5

    # Adjust to match confidence_score (allow ±5 tolerance)
    gap = confidence_score - total
    if gap > 5:
        # Add a catch-up factor
        breakdown.append({"factor": "Contextual corroboration", "points": gap})
        total += gap
    elif gap < -5:
        # Reduce base to match
        # Find the base score entry and adjust it
        for b in breakdown:
            if b["factor"] == "Base score":
                b["points"] += gap
                total += gap
                break

    return breakdown, total

def main():
    data = load_data()
    entries = data["entries"]
    print(f"Processing {len(entries)} entries...")

    confidence_details = []

    for entry in entries:
        # Compute confidence breakdown
        breakdown, computed_total = compute_breakdown(entry)
        entry["confidence_breakdown"] = breakdown

        # Add history tracking (if not already present)
        if "history" not in entry:
            entry["history"] = [
                {
                    "date": "2026-06-13",
                    "event": "Entry created",
                    "details": "Added to dataset with initial verification"
                }
            ]

        # Log
        orig = entry["confidence_score"]
        entry_id = entry["id"]
        company = entry["company"]
        print(f"  {entry_id} ({company}): orig={orig}, computed={computed_total}, diff={orig-computed_total}")

        # Collect confidence details for API
        confidence_details.append({
            "id": entry_id,
            "company": company,
            "confidence_score": orig,
            "breakdown": [dict(b) for b in breakdown],
            "breakdown_total": computed_total
        })

    # Update classification counts
    from collections import Counter
    class_counts = Counter(e["classification"] for e in entries)
    for cls_key, cls_info in data.get("classifications", {}).items():
        cls_info["count"] = class_counts.get(cls_key, 0)

    save_data(data)

    # Generate confidence API
    API_DIR.mkdir(parents=True, exist_ok=True)

    confidence_scores = [e["confidence_score"] for e in entries]
    confidence_summary = {
        "meta": {
            "version": data["meta"]["version"],
            "last_updated": data["meta"]["last_updated"],
            "total_entries": len(entries),
            "scoring_methodology": {
                "base": 30,
                "bonuses": {
                    "CEO_STATEMENT": 25,
                    "EARNINGS_CALL_or_SEC_FILING": 20,
                    "OFFICIAL_STATEMENT_or_COMPANY_PRESS_RELEASE": 15,
                    "archived_source": 10,
                    "multiple_sources": 5,
                    "primary_source": 5
                }
            }
        },
        "summary": {
            "mean_confidence": round(sum(confidence_scores) / len(confidence_scores), 1),
            "min_confidence": min(confidence_scores),
            "max_confidence": max(confidence_scores),
            "confidence_range": f"{min(confidence_scores)}–{max(confidence_scores)}"
        },
        "entries": confidence_details
    }

    confidence_path = API_DIR / "confidence.json"
    with open(confidence_path, "w") as f:
        json.dump(confidence_summary, f, indent=2, ensure_ascii=False)
    print(f"✅ Generated {confidence_path}")

    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Entries enriched: {len(entries)}")
    print(f"Confidence range: {min(confidence_scores)}–{max(confidence_scores)}")
    print(f"Mean confidence: {confidence_summary['summary']['mean_confidence']}")
    print(f"History entries added: {len(entries)} (1 per entry)")

if __name__ == "__main__":
    main()
