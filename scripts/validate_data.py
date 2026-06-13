#!/usr/bin/env python3
"""
validate_data.py — Automated Data Validator for AI Layoff Tracker

Validates data/entries.json with 7 checks:

  1. Required fields per entry:
     id, company, date, jobs_lost, classification, confidence_score,
     source.url, source.archive_url, evidence (non-empty array), source_quality

  2. No duplicate IDs or company+date combos

  3. All source URLs return HTTP 200 (HEAD request with timeout)

  4. All archive URLs are valid (start with https://web.archive.org)

  5. Confidence scores are 0–100 (inclusive)

  6. Classifications must be one of:
     DIRECT_AI_REPLACEMENT, AI_DRIVEN_RESTRUCTURING,
     AI_REALLOCATION, MARKET_DISRUPTION

  7. source_quality must be one of:
     PRIMARY_SOURCE, SECONDARY_SOURCE, TERTIARY_SOURCE

Output: Clean PASS/FAIL per check, list of broken entries.

Usage:
    python scripts/validate_data.py               # run all checks
    python scripts/validate_data.py --no-url      # skip URL HEAD requests
"""

import json
import sys
import ssl
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
ENTRIES_PATH = BASE_DIR / "data" / "entries.json"

# ── Constants ──────────────────────────────────────────────────────────────
REQUIRED_FIELDS = [
    "id",
    "company",
    "date",
    "jobs_lost",
    "classification",
    "confidence_score",
    # source sub-fields checked separately
    # evidence checked separately
    # source_quality checked separately
]

REQUIRED_SOURCE_FIELDS = ["url", "archive_url"]

VALID_CLASSIFICATIONS = {
    "DIRECT_AI_REPLACEMENT",
    "AI_DRIVEN_RESTRUCTURING",
    "AI_REALLOCATION",
    "MARKET_DISRUPTION",
}

VALID_SOURCE_QUALITIES = {
    "PRIMARY_SOURCE",
    "SECONDARY_SOURCE",
    "TERTIARY_SOURCE",
}

URL_TIMEOUT = 15  # seconds per URL

# ── SSL workaround ─────────────────────────────────────────────────────────
ssl._create_default_https_context = ssl._create_unverified_context

# ═══════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_entries():
    with open(ENTRIES_PATH) as f:
        data = json.load(f)
    return data.get("entries", [])


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 1: Required fields
# ═══════════════════════════════════════════════════════════════════════════

def check_required_fields(entries):
    """Every entry must have required top-level fields, source.url,
    source.archive_url, non-empty evidence array, and source_quality."""
    broken = []
    for entry in entries:
        eid = entry.get("id", "MISSING_ID")
        problems = []

        # Top-level required fields
        for field in REQUIRED_FIELDS:
            if field not in entry or entry[field] is None:
                problems.append(f"missing or null field: `{field}`")

        # source is a dict with url and archive_url
        source = entry.get("source")
        if not isinstance(source, dict):
            problems.append("`source` is not a dict or is missing")
        else:
            for sf in REQUIRED_SOURCE_FIELDS:
                val = source.get(sf)
                if not val or not isinstance(val, str) or not val.strip():
                    problems.append(f"`source.{sf}` is missing or empty")

        # evidence must be a non-empty array
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or len(evidence) == 0:
            problems.append("`evidence` is missing, not an array, or empty")

        # source_quality must be present and valid
        sq = entry.get("source_quality")
        if sq is None:
            problems.append("`source_quality` is missing")
        elif sq not in VALID_SOURCE_QUALITIES:
            problems.append(
                f"`source_quality` has invalid value: `{sq}` "
                f"(must be one of: {', '.join(sorted(VALID_SOURCE_QUALITIES))})"
            )

        if problems:
            broken.append({"id": eid, "problems": problems})

    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 2: No duplicate IDs or company+date combos
# ═══════════════════════════════════════════════════════════════════════════

def check_duplicates(entries):
    """Ensure no duplicate IDs and no duplicate company+date combinations."""
    broken = []

    # Duplicate IDs
    id_counts = Counter(e.get("id", "MISSING_ID") for e in entries)
    for eid, count in id_counts.items():
        if count > 1:
            broken.append(
                f"Duplicate ID `{eid}` appears {count} times"
            )

    # Duplicate company+date
    combo_counts = Counter(
        f"{e.get('company', 'UNKNOWN')}||{e.get('date', 'UNKNOWN')}" for e in entries
    )
    for combo, count in combo_counts.items():
        if count > 1:
            company, date = combo.split("||")
            broken.append(
                f"Duplicate company+date: `{company}` on `{date}` appears {count} times"
            )

    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 3: Source URLs return HTTP 200 (HEAD request)
# ═══════════════════════════════════════════════════════════════════════════

def check_url(url):
    """HEAD-request a URL, return (ok: bool, status_code: int, error: str)."""
    try:
        req = Request(
            url,
            method="HEAD",
            headers={
                "User-Agent": (
                    "AILayoffTracker/3.0 (Data Validator; "
                    "+https://ailayofftracker.com)"
                )
            },
        )
        with urlopen(req, timeout=URL_TIMEOUT) as resp:
            return True, resp.status, None
    except HTTPError as e:
        # Some servers reject HEAD — return the status code anyway
        return False, e.code, f"HTTP {e.code}: {e.reason}"
    except URLError as e:
        return False, None, f"Connection error: {e.reason}"
    except Exception as e:
        return False, None, str(e)


def check_source_urls(entries, skip_urls=False):
    """All source.url values must return HTTP 200."""
    broken = []
    total = 0
    ok = 0

    for entry in entries:
        eid = entry.get("id", "MISSING_ID")
        source = entry.get("source", {})
        url = source.get("url", "")

        if not url:
            continue  # already caught by check_required_fields

        total += 1

        if skip_urls:
            continue

        url_ok, status, error = check_url(url)
        if url_ok and status == 200:
            ok += 1
        else:
            status_str = str(status) if status else "N/A"
            err_str = error or f"status {status_str}"
            broken.append({
                "id": eid,
                "url": url,
                "status": status_str,
                "error": err_str,
            })

    if not skip_urls:
        print(f"  → Checked {total} URLs: {ok} OK, {len(broken)} failed")

    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 4: Archive URLs start with https://web.archive.org
# ═══════════════════════════════════════════════════════════════════════════

ARCHIVE_PREFIX = "https://web.archive.org"

def check_archive_urls(entries):
    """All source.archive_url values must start with https://web.archive.org."""
    broken = []

    for entry in entries:
        eid = entry.get("id", "MISSING_ID")
        source = entry.get("source", {})
        archive_url = source.get("archive_url", "")

        if not archive_url:
            continue  # already caught by check_required_fields

        if not archive_url.startswith(ARCHIVE_PREFIX):
            broken.append({
                "id": eid,
                "archive_url": archive_url,
                "error": f"archive_url does not start with '{ARCHIVE_PREFIX}'",
            })

    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 5: Confidence scores in 0–100
# ═══════════════════════════════════════════════════════════════════════════

def check_confidence_scores(entries):
    """All confidence_score values must be numeric and in [0, 100]."""
    broken = []

    for entry in entries:
        eid = entry.get("id", "MISSING_ID")
        cs = entry.get("confidence_score")

        if cs is None:
            continue  # already caught by check_required_fields

        if not isinstance(cs, (int, float)):
            broken.append({
                "id": eid,
                "value": repr(cs),
                "error": f"confidence_score is not a number: {type(cs).__name__}",
            })
        elif cs < 0 or cs > 100:
            broken.append({
                "id": eid,
                "value": cs,
                "error": f"confidence_score {cs} is outside range 0–100",
            })

    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 6: Valid classifications
# ═══════════════════════════════════════════════════════════════════════════

def check_classifications(entries):
    """All classification values must be in the allowed set."""
    broken = []

    for entry in entries:
        eid = entry.get("id", "MISSING_ID")
        cls = entry.get("classification", "")

        if not cls:
            continue  # already caught by check_required_fields

        if cls not in VALID_CLASSIFICATIONS:
            broken.append({
                "id": eid,
                "value": cls,
                "error": f"Invalid classification: `{cls}`. "
                         f"Must be one of: {', '.join(sorted(VALID_CLASSIFICATIONS))}",
            })

    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 7: source_quality values
# ═══════════════════════════════════════════════════════════════════════════

def check_source_quality(entries):
    """All source_quality values must be in the allowed set."""
    broken = []

    for entry in entries:
        eid = entry.get("id", "MISSING_ID")
        sq = entry.get("source_quality")

        if sq is None:
            # Missing source_quality caught by check_required_fields
            continue

        if sq not in VALID_SOURCE_QUALITIES:
            broken.append({
                "id": eid,
                "value": sq,
                "error": f"Invalid source_quality: `{sq}`. "
                         f"Must be one of: {', '.join(sorted(VALID_SOURCE_QUALITIES))}",
            })

    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 8: confidence breakdowns
# ═══════════════════════════════════════════════════════════════════════════
def check_confidence_breakdowns(entries):
    broken = []
    for e in entries:
        breakdown = e.get("confidence_breakdown", [])
        if not breakdown:
            broken.append({"entry": e["company"], "error": "No confidence breakdown"})
            continue
        total = sum(b.get("points", 0) for b in breakdown)
        expected = e.get("confidence_score", 0)
        if abs(total - expected) > 5:
            broken.append({
                "entry": e["company"],
                "error": f"Breakdown sum ({total}) ≠ confidence_score ({expected})"
            })
    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  CHECK 9: entry history
# ═══════════════════════════════════════════════════════════════════════════
def check_entry_history(entries):
    broken = []
    for e in entries:
        history = e.get("history", [])
        if not history:
            broken.append({"entry": e["company"], "error": "No history entries"})
    return broken


# ═══════════════════════════════════════════════════════════════════════════
#  REPORT & MAIN
# ═══════════════════════════════════════════════════════════════════════════

def print_divider(char="=", width=70):
    print(char * width)


def print_header(title):
    print()
    print_divider()
    print(f"  {title}")
    print_divider()


def format_entry_list(items, max_show=10):
    """Format a list of broken entries for display."""
    if not items:
        return
    for i, item in enumerate(items[:max_show]):
        if isinstance(item, str):
            print(f"    {i+1}. {item}")
        elif isinstance(item, dict):
            eid = item.get("id", "?")
            extra = ""
            if "company" in item:
                extra = f" | {item['company']} | {item.get('date', '?')}"
            if "problems" in item:
                for prob in item["problems"]:
                    print(f"    - [{eid}] {prob}")
            elif "url" in item:
                print(f"    - [{eid}] {item.get('error', '?')}")
                print(f"      URL: {item['url'][:100]}")
            elif "archive_url" in item:
                print(f"    - [{eid}] {item.get('error', '?')}")
                print(f"      archive_url: {item['archive_url'][:100]}")
            elif "value" in item:
                print(f"    - [{eid}] {item.get('error', '?')}  (value: {item['value']})")
            else:
                print(f"    - [{eid}] {item}")
    if len(items) > max_show:
        print(f"    ... and {len(items) - max_show} more")


def main():
    skip_urls = "--no-url" in sys.argv

    # ── Load data ───────────────────────────────────────────────────────
    entries = load_entries()
    print_header(f"AI LAYOFF TRACKER — DATA VALIDATOR")
    print(f"  Data file : {ENTRIES_PATH}")
    print(f"  Entries   : {len(entries)}")
    print(f"  Timestamp : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if skip_urls:
        print(f"  URL check : SKIPPED (--no-url)")

    # ── Run all checks ──────────────────────────────────────────────────
    checks = OrderedDict([
        ("1. Required Fields",            ("PASS", lambda: check_required_fields(entries))),
        ("2. Duplicate IDs / Company+Date", ("PASS", lambda: check_duplicates(entries))),
        ("3. Source URLs (HTTP 200)",      ("PASS", lambda: check_source_urls(entries, skip_urls=skip_urls))),
        ("4. Valid Archive URLs",          ("PASS", lambda: check_archive_urls(entries))),
        ("5. Confidence Scores (0–100)",   ("PASS", lambda: check_confidence_scores(entries))),
        ("6. Valid Classifications",       ("PASS", lambda: check_classifications(entries))),
        ("7. Valid source_quality",        ("PASS", lambda: check_source_quality(entries))),
        ("8. Confidence Breakdowns",       ("PASS", lambda: check_confidence_breakdowns(entries))),
        ("9. Entry History",               ("PASS", lambda: check_entry_history(entries))),
    ])

    total_broken = 0
    all_failed_checks = []

    for check_name, (_, check_fn) in checks.items():
        print_header(f"Check {check_name}")
        broken = check_fn()
        if broken:
            status = "FAIL"
            all_failed_checks.append(check_name)
            count = len(broken)
            total_broken += count
            print(f"  ❌ FAIL — {count} issue(s) found:")
            format_entry_list(broken)
        else:
            status = "PASS"
            print(f"  ✅ PASS — No issues found")

    # ── Summary ─────────────────────────────────────────────────────────
    print_header("SUMMARY")

    # ── Weekly Report ──────────────────────────────────────────────────
    report_path = Path(__file__).parent.parent / "docs" / "api" / "weekly-validation-report.json"
    report = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "dataset": {
            "total_entries": len(entries),
            "total_jobs": sum(e.get("jobs_lost", 0) for e in entries),
            "companies": len(set(e["company"] for e in entries)),
            "countries": len(set(e.get("country", "") for e in entries)),
            "industries": len(set(e.get("industry", "") for e in entries)),
        },
        "checks": {name: {"status": "PASS" if name not in all_failed_checks else "FAIL", "issues": sum(1 for b in broken if b) if name in all_failed_checks else 0} for name, (_, broken) in zip(checks.keys(), [(None, [])] * len(checks))},
        "overall": {"passed": len(checks) - len(all_failed_checks), "total": len(checks), "all_pass": len(all_failed_checks) == 0},
    }
    # Fix check result data
    for check_name, (_, check_fn) in checks.items():
        result = check_fn()
        report["checks"][check_name] = {"status": "PASS" if not result else "FAIL", "issues": len(result) if result else 0}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(report_path, "w"), indent=2)
    print(f"\n  📄 Weekly report: {report_path}")

    if not all_failed_checks:
        print("  🎉 ALL CHECKS PASSED")
        print()
        print(f"  Total entries validated : {len(entries)}")
        print(f"  Checks passed           : {len(checks)} / {len(checks)}")
        sys.exit(0)
    else:
        print(f"  ❌ {len(all_failed_checks)} CHECKS FAILED")
        print()
        for fc in all_failed_checks:
            print(f"     - Check {fc}")
        print()
        print(f"  Total entries validated : {len(entries)}")
        print(f"  Checks passed           : {len(checks) - len(all_failed_checks)} / {len(checks)}")
        print(f"  Total issues            : {total_broken}")
        sys.exit(1)


# ── OrderedDict for Python 3.6 compatibility ───────────────────────────
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

if __name__ == "__main__":
    main()
