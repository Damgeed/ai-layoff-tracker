#!/usr/bin/env python3
"""
Archive Recovery — Automated archive discovery for AI Layoff Tracker.

For every source URL in entries.json, attempts to find archived copies at:
  1. Archive.org (Wayback Machine) — CDX API + available API
  2. Archive.today — direct URL check
  3. Updates entries.json with best archive URLs found
  4. Generates docs/api/archive-coverage.json

Usage:
  python3 scripts/archive_recovery.py                    # full run
  python3 scripts/archive_recovery.py --entry google-2023-01  # single entry
  python3 scripts/archive_recovery.py --dry-run          # scan only, no writes

Design: Uses only stdlib (urllib). Rate-limited to 1 req / 0.5s.
"""
import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = ROOT / "data" / "entries.json"
OUTPUT_PATH = ROOT / "docs" / "api" / "archive-coverage.json"
USER_AGENT = "AI-Layoff-Tracker-ArchiveRecovery/1.0 (research bot; contact via GitHub)"

# Domains where automated HEAD/GET is unreliable (paywalls, bot-blockers)
SKIP_DOMAINS = {
    "reuters.com", "wsj.com", "ft.com", "nytimes.com",
    "washingtonpost.com", "bloomberg.com", "economist.com",
    "forbes.com", "barrons.com",
}

# Rate limiting
MIN_DELAY = 0.5  # seconds between requests


def load_entries():
    with open(ENTRIES_PATH) as f:
        return json.load(f)


def save_entries(data):
    """Write updated entries.json atomically."""
    tmp = ENTRIES_PATH.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.rename(ENTRIES_PATH)


def domain_skip(url):
    """Check if a URL's domain should be skipped."""
    if not url or not url.startswith("http"):
        return True
    domain = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    return any(blocked in domain for blocked in SKIP_DOMAINS)


def check_wayback_available(url, timeout=15):
    """
    Check Archive.org's /wayback/available API.
    Returns the closest snapshot URL or None.
    """
    api_url = f"https://archive.org/wayback/available?url={urllib.parse.quote(url)}"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
        snapshots = data.get("archived_snapshots", {})
        closest = snapshots.get("closest", {})
        if closest and closest.get("available") and closest.get("url"):
            return closest["url"]
    except Exception:
        pass
    return None


def check_wayback_cdx(url, timeout=15):
    """
    Check Archive.org's CDX API for any snapshot.
    Returns the latest snapshot URL or None.
    """
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={urllib.parse.quote(url)}&output=json&limit=1&fl=timestamp,original"
    try:
        req = urllib.request.Request(cdx_url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
        if len(data) > 1:  # First row is header
            timestamp = data[1][0]
            orig_url = data[1][1]
            return f"https://web.archive.org/web/{timestamp}/{orig_url}"
    except Exception:
        pass
    return None


def check_archive_today(url, timeout=10):
    """
    Check if archive.today has a snapshot by trying a HEAD request.
    Note: archive.today blocks HEAD from non-browsers, so this is best-effort.
    Returns the archive.today URL if accessible, else None.
    """
    archive_url = f"https://archive.ph/{url}"
    try:
        req = urllib.request.Request(archive_url, method="HEAD",
                                     headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                                            "AppleWebKit/537.36 (KHTML, like Gecko)"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        if resp.status == 200:
            return archive_url
    except Exception:
        pass
    return None


def recover_sources(data, dry_run=False, single_entry=None):
    """
    Main recovery logic. Iterates all entries and attempts archive discovery.
    Returns coverage report dict.
    """
    entries = data["entries"]
    if single_entry:
        entries = [e for e in entries if e["id"] == single_entry]
        if not entries:
            print(f"❌ Entry '{single_entry}' not found.")
            sys.exit(1)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries),
        "total_sources": 0,
        "primary_sources": {"total": 0, "archived": 0, "missing": 0, "newly_discovered": 0},
        "secondary_sources": {"total": 0, "archived": 0, "missing": 0, "newly_discovered": 0},
        "entry_coverage": {},
        "new_archives": [],
        "still_missing": [],
    }

    for entry in entries:
        eid = entry["id"]
        primary = entry.get("source", {})
        secondary = entry.get("secondary_sources", [])

        entry_result = {"primary": None, "secondary": []}

        # --- Primary source ---
        if primary and isinstance(primary, dict) and primary.get("url"):
            report["total_sources"] += 1
            report["primary_sources"]["total"] += 1
            url = primary["url"]

            if domain_skip(url):
                entry_result["primary"] = {
                    "url": url, "archive_url": primary.get("archive_url"),
                    "status": "skipped", "note": "paywall_or_blocked"
                }
                report["primary_sources"]["missing"] += 1
            else:
                existing = primary.get("archive_url")
                if existing and existing.strip():
                    entry_result["primary"] = {
                        "url": url, "archive_url": existing,
                        "status": "already_archived"
                    }
                    report["primary_sources"]["archived"] += 1
                else:
                    # Try discovery
                    archive_url = check_wayback_available(url)
                    time.sleep(MIN_DELAY)
                    if not archive_url:
                        archive_url = check_wayback_cdx(url)
                        time.sleep(MIN_DELAY)
                    if not archive_url:
                        archive_url = check_archive_today(url)
                        time.sleep(MIN_DELAY)

                    if archive_url:
                        if not dry_run:
                            primary["archive_url"] = archive_url
                            entry["source"] = primary
                        entry_result["primary"] = {
                            "url": url, "archive_url": archive_url,
                            "status": "newly_archived"
                        }
                        report["primary_sources"]["newly_discovered"] += 1
                        report["primary_sources"]["archived"] += 1
                        report["new_archives"].append({
                            "entry_id": eid, "type": "primary",
                            "url": url, "archive_url": archive_url
                        })
                    else:
                        entry_result["primary"] = {
                            "url": url, "archive_url": None,
                            "status": "missing", "note": "no_snapshot_found"
                        }
                        report["primary_sources"]["missing"] += 1
                        report["still_missing"].append({
                            "entry_id": eid, "type": "primary",
                            "url": url, "reason": "no_snapshot_found"
                        })

        # --- Secondary sources ---
        if secondary and isinstance(secondary, list):
            for idx, src in enumerate(secondary):
                if not isinstance(src, dict) or not src.get("url"):
                    continue
                url = src["url"]
                report["total_sources"] += 1
                report["secondary_sources"]["total"] += 1

                if domain_skip(url):
                    entry_result["secondary"].append({
                        "url": url, "archive_url": src.get("archive_url"),
                        "status": "skipped", "note": "paywall_or_blocked"
                    })
                    report["secondary_sources"]["missing"] += 1
                else:
                    existing = src.get("archive_url")
                    if existing and existing.strip():
                        entry_result["secondary"].append({
                            "url": url, "archive_url": existing,
                            "status": "already_archived"
                        })
                        report["secondary_sources"]["archived"] += 1
                    else:
                        archive_url = check_wayback_available(url)
                        time.sleep(MIN_DELAY)
                        if not archive_url:
                            archive_url = check_wayback_cdx(url)
                            time.sleep(MIN_DELAY)
                        if not archive_url:
                            archive_url = check_archive_today(url)
                            time.sleep(MIN_DELAY)

                        if archive_url:
                            if not dry_run:
                                src["archive_url"] = archive_url
                                secondary[idx] = src
                            entry_result["secondary"].append({
                                "url": url, "archive_url": archive_url,
                                "status": "newly_archived"
                            })
                            report["secondary_sources"]["newly_discovered"] += 1
                            report["secondary_sources"]["archived"] += 1
                            report["new_archives"].append({
                                "entry_id": eid, "type": "secondary",
                                "url": url, "archive_url": archive_url
                            })
                        else:
                            entry_result["secondary"].append({
                                "url": url, "archive_url": None,
                                "status": "missing", "note": "no_snapshot_found"
                            })
                            report["secondary_sources"]["missing"] += 1
                            report["still_missing"].append({
                                "entry_id": eid, "type": "secondary",
                                "url": url, "reason": "no_snapshot_found"
                            })

        report["entry_coverage"][eid] = entry_result

    # Update entries.json with new archive URLs
    if not dry_run and (report["primary_sources"]["newly_discovered"] > 0 or
                        report["secondary_sources"]["newly_discovered"] > 0):
        save_entries(data)
        print(f"   ✅ Saved updated entries.json with {report['primary_sources']['newly_discovered'] + report['secondary_sources']['newly_discovered']} new archive URLs")

    # Compute percentages
    total_primary = report["primary_sources"]["total"]
    total_secondary = report["secondary_sources"]["total"]
    report["overall_coverage_pct"] = round(
        ((report["primary_sources"]["archived"] + report["secondary_sources"]["archived"])
         / max(report["total_sources"], 1)) * 100, 1
    ) if report["total_sources"] > 0 else 0
    report["primary_coverage_pct"] = round(
        (report["primary_sources"]["archived"] / max(total_primary, 1)) * 100, 1
    )
    report["secondary_coverage_pct"] = round(
        (report["secondary_sources"]["archived"] / max(total_secondary, 1)) * 100, 1
    )

    return report


def print_report(report):
    """Print a human-readable summary."""
    ps = report["primary_sources"]
    ss = report["secondary_sources"]
    print(f"\n{'='*60}")
    print(f"📦 ARCHIVE COVERAGE REPORT")
    print(f"{'='*60}")
    print(f"   Generated: {report['generated_at']}")
    print(f"   Entries:   {report['total_entries']}")
    print(f"   Sources:   {report['total_sources']}")
    print(f"\n   {'':30s} {'Total':>8s} {'Archived':>10s} {'Missing':>10s}")
    print(f"   {'─'*60}")
    print(f"   {'Primary Sources':30s} {ps['total']:>8d} {ps['archived']:>10d} {ps['missing']:>10d}")
    print(f"   {'Secondary Sources':30s} {ss['total']:>8d} {ss['archived']:>10d} {ss['missing']:>10d}")
    print(f"\n   {'─'*60}")
    print(f"   {'Overall Coverage':30s} {report['overall_coverage_pct']:>8.1f}%")
    print(f"   {'Primary Coverage':30s} {report['primary_coverage_pct']:>8.1f}%")
    print(f"   {'Secondary Coverage':30s} {report['secondary_coverage_pct']:>8.1f}%")
    print(f"\n   ✅ New archives discovered: {ps['newly_discovered'] + ss['newly_discovered']}")
    print(f"   ❌ Still missing:           {len(report['still_missing'])}")

    if report["new_archives"]:
        print(f"\n   📋 NEW ARCHIVES:")
        for a in report["new_archives"]:
            print(f"     [{a['entry_id']}] ({a['type']}) {a['archive_url'][:90]}")

    if report["still_missing"]:
        print(f"\n   ⚠️  STILL MISSING:")
        for m in report["still_missing"]:
            print(f"     [{m['entry_id']}] ({m['type']}) {m['url'][:80]} — {m['reason']}")


def main():
    dry_run = "--dry-run" in sys.argv
    single_entry = None
    if "--entry" in sys.argv:
        idx = sys.argv.index("--entry")
        single_entry = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None

    print(f"{'🔍 DRY RUN' if dry_run else '🔍 ARCHIVE RECOVERY'} — AI Layoff Tracker")
    print(f"   Entries: {ENTRIES_PATH}")
    if single_entry:
        print(f"   Single entry: {single_entry}")

    data = load_entries()
    report = recover_sources(data, dry_run=dry_run, single_entry=single_entry)

    # Write report
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Report written to {OUTPUT_PATH}")

    print_report(report)

    if dry_run:
        print(f"\n   💡 Run without --dry-run to save new archive URLs to entries.json")


if __name__ == "__main__":
    main()
