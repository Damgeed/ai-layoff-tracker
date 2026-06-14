#!/usr/bin/env python3
"""
Source Monitor — Weekly dead-link checker for AI Layoff Tracker.

Checks every source URL from entries.json:
- Resolves URLs (HEAD request, follows redirects)
- Flags: dead (4xx/5xx), redirected (3xx), missing archive
- Generates: docs/api/source-health.json
- Can be run standalone or during build

Usage:
  python3 scripts/source_monitor.py           # check all entries
  python3 scripts/source_monitor.py --sample 10 # check 10 random entries
  python3 scripts/source_monitor.py --entry klarna-2024-08  # single entry
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = ROOT / "data" / "entries.json"
OUTPUT_PATH = ROOT / "docs" / "api" / "source-health.json"

# Known false-positives (sites that block automated HEAD requests)
SKIP_URL_CHECK = {
    "reuters.com",         # 401 on HEAD
    "wsj.com",             # paywall
    "ft.com",              # paywall
    "nytimes.com",         # paywall
    "washingtonpost.com",  # paywall
    "bloomberg.com",       # paywall
    "economist.com",       # paywall
    "forbes.com",          # sometimes blocks
}


def load_entries():
    with open(ENTRIES_PATH) as f:
        return json.load(f)


def check_url(url, timeout=15):
    """HEAD request, follows redirects. Returns (status, final_url, error)."""
    if not url or not url.startswith("http"):
        return None, url, "invalid_url"

    domain = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    if any(blocked in domain for blocked in SKIP_URL_CHECK):
        return "SKIPPED", url, "paywall_or_blocked"

    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "AI-Layoff-Tracker-SourceMonitor/1.0 (research bot; contact via GitHub)")
        resp = urllib.request.urlopen(req, timeout=timeout)
        final_url = resp.geturl()
        if final_url != url and not final_url.rstrip("/") == url.rstrip("/"):
            return resp.status, final_url, "redirected"
        return resp.status, final_url, None
    except urllib.error.HTTPError as e:
        return e.code, url, f"HTTP_{e.code}"
    except urllib.error.URLError as e:
        return None, url, f"network_error: {e.reason}"
    except Exception as e:
        return None, url, f"error: {str(e)[:80]}"


def check_archive(url):
    """Check if archive.org has a snapshot."""
    if not url:
        return False
    try:
        archive_url = f"https://archive.org/wayback/available?url={urllib.parse.quote(url)}"
        req = urllib.request.Request(archive_url)
        req.add_header("User-Agent", "AI-Layoff-Tracker/1.0")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return bool(data.get("archived_snapshots"))
    except Exception:
        return False


def run_checks(entries, sample=None):
    """Check all sources across all entries."""
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries),
        "total_sources_checked": 0,
        "summary": {
            "healthy": 0,
            "dead": 0,
            "redirected": 0,
            "skipped": 0,
            "missing_archive": 0,
        },
        "entries": {},
        "broken_urls": [],
    }

    entry_list = entries
    if sample and sample < len(entries):
        import random
        entry_list = random.sample(entries, sample)

    for entry in entry_list:
        eid = entry["id"]
        all_sources = []

        # Primary source (dict with url, title, archive_url, etc.)
        primary = entry.get("source")
        if primary and isinstance(primary, dict) and primary.get("url"):
            all_sources.append(primary)

        # Secondary sources (list of dicts)
        secondary = entry.get("secondary_sources", [])
        if isinstance(secondary, list):
            for s in secondary:
                if isinstance(s, dict) and s.get("url"):
                    all_sources.append(s)

        entry_health = {"id": eid, "company": entry["company"], "sources": []}

        for src in all_sources:
            url = src.get("url", src if isinstance(src, str) else "")
            if not url:
                continue

            status, final_url, error = check_url(url)
            has_archive = src.get("archive_url") is not None or check_archive(url)
            results["total_sources_checked"] += 1

            health = {
                "url": url,
                "status": status,
                "final_url": final_url if final_url != url else None,
                "error": error,
                "has_archive": has_archive,
            }
            entry_health["sources"].append(health)

            if isinstance(status, int) and 200 <= status < 300:
                results["summary"]["healthy"] += 1
            elif isinstance(status, int) and 300 <= status < 400:
                results["summary"]["redirected"] += 1
            elif status == "SKIPPED":
                results["summary"]["skipped"] += 1
            else:
                results["summary"]["dead"] += 1
                results["broken_urls"].append({
                    "entry_id": eid,
                    "company": entry["company"],
                    "url": url,
                    "error": error,
                })

            if not has_archive:
                results["summary"]["missing_archive"] += 1

        results["entries"][eid] = entry_health
        time.sleep(0.3)  # Be polite

    return results


def main():
    sample = None
    single_entry = None
    args = sys.argv[1:]

    if "--sample" in args:
        idx = args.index("--sample")
        sample = int(args[idx + 1]) if idx + 1 < len(args) else 10
    if "--entry" in args:
        idx = args.index("--entry")
        single_entry = args[idx + 1] if idx + 1 < len(args) else None

    data = load_entries()
    entries = data["entries"]
    if single_entry:
        entries = [e for e in entries if e["id"] == single_entry]
        if not entries:
            print(f"Entry '{single_entry}' not found.")
            sys.exit(1)

    print(f"🔍 Checking {len(entries)} entries...")
    results = run_checks(entries, sample=sample)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    s = results["summary"]
    print(f"\n📊 Source Health Report")
    print(f"   Total sources checked: {results['total_sources_checked']}")
    print(f"   ✅ Healthy:     {s['healthy']}")
    print(f"   ❌ Dead:        {s['dead']}")
    print(f"   ↩  Redirected:  {s['redirected']}")
    print(f"   ⏭  Skipped:     {s['skipped']}")
    print(f"   📦 No Archive:  {s['missing_archive']}")
    print(f"\n📄 Report: {OUTPUT_PATH}")

    if s["dead"] > 0:
        print(f"\n🚨 Broken URLs:")
        for b in results["broken_urls"]:
            print(f"   [{b['entry_id']}] {b['url']}")
            print(f"   → {b['error']}")


if __name__ == "__main__":
    main()
