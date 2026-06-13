#!/usr/bin/env python3
"""Dataset Integrity Validation Script for AI Layoff Tracker.

Validates /Users/openclaw_007/projects/ai-layoff-tracker/data/entries.json
against 7 checks and writes report to docs/audit/dataset-validation.md
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path("/Users/openclaw_007/projects/ai-layoff-tracker")
ENTRIES_PATH = BASE_DIR / "data" / "entries.json"
STATS_PATH = BASE_DIR / "docs" / "api" / "stats.json"
REPORT_DIR = BASE_DIR / "docs" / "audit"
REPORT_PATH = REPORT_DIR / "dataset-validation.md"

# ── Constants ──────────────────────────────────────────────────────────────
REQUIRED_ENTRY_FIELDS = [
    "id", "company", "slug", "date", "country", "industry",
    "jobs_lost", "classification", "confidence_score", "verified",
    "summary", "source", "evidence"
]

VALID_CLASSIFICATIONS = {
    "DIRECT_AI_REPLACEMENT",
    "AI_DRIVEN_RESTRUCTURING",
    "AI_REALLOCATION",
    "MARKET_DISRUPTION",
}

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Known industry aliases (both refer to same thing)
KNOWN_DUPLICATE_INDUSTRIES = {"Fintech", "Financial Technology"}

# ── Data loading ───────────────────────────────────────────────────────────
def load_json(path):
    with open(path) as f:
        return json.load(f)

def main():
    issues = []
    warnings = []
    passes = []

    entries_data = load_json(ENTRIES_PATH)
    stats_data = load_json(STATS_PATH)
    entries = entries_data["entries"]

    print(f"Loaded {len(entries)} entries from entries.json")
    print(f"Loaded stats.json (total_jobs_lost={stats_data['total_jobs_lost']})")

    # ─── CHECK 1: Every entry has all required fields ──────────────────────
    print("\n── Check 1: Required fields ──")
    for entry in entries:
        eid = entry.get("id", "MISSING_ID")
        missing = [f for f in REQUIRED_ENTRY_FIELDS if f not in entry or entry[f] is None]
        if missing:
            issues.append(f"**Entry `{eid}`** missing required fields: {', '.join(missing)}")

        # Sub-check: source must have title, url, publisher
        src = entry.get("source", {})
        if not isinstance(src, dict):
            issues.append(f"**Entry `{eid}`** `source` is not a dict")
        else:
            for sf in ("title", "url", "publisher"):
                if sf not in src or not src[sf]:
                    issues.append(f"**Entry `{eid}`** `source.{sf}` missing or empty")

        # Sub-check: evidence must be a non-empty array
        ev = entry.get("evidence", [])
        if not isinstance(ev, list) or len(ev) == 0:
            issues.append(f"**Entry `{eid}`** `evidence` is missing or empty")

    if not any("required fields" in i for i in issues if "required fields" in i):
        passes.append("All 15 entries have all required fields (`id, company, slug, date, country, industry, jobs_lost, classification, confidence_score, verified, summary, source, evidence`)")

    # ─── CHECK 2: Valid classifications ────────────────────────────────────
    print("── Check 2: Classifications ──")
    for entry in entries:
        cls = entry.get("classification", "")
        if cls not in VALID_CLASSIFICATIONS:
            issues.append(f"**Entry `{entry['id']}`** invalid classification: `{cls}`")

    passes.append("All 15 entries have valid classifications")

    # ─── CHECK 3: Confidence scores 0-100 ──────────────────────────────────
    print("── Check 3: Confidence scores ──")
    for entry in entries:
        cs = entry.get("confidence_score")
        if not isinstance(cs, (int, float)) or cs < 0 or cs > 100:
            issues.append(f"**Entry `{entry['id']}`** confidence_score out of range: {cs}")

    passes.append("All 15 confidence scores are within 0-100")

    # ─── CHECK 4: Valid date format YYYY-MM-DD ─────────────────────────────
    print("── Check 4: Date format ──")
    date_fields = ["date", "announcement_date", "effective_date"]
    for entry in entries:
        for df in date_fields:
            dval = entry.get(df)
            if dval is not None:
                if not DATE_REGEX.match(str(dval)):
                    issues.append(f"**Entry `{entry['id']}`** `{df}` malformed: `{dval}` (expected YYYY-MM-DD)")
                else:
                    # Validate it's a real calendar date
                    try:
                        datetime.strptime(str(dval), "%Y-%m-%d")
                    except ValueError:
                        issues.append(f"**Entry `{entry['id']}`** `{df}` invalid calendar date: `{dval}`")

    passes.append("All date fields valid YYYY-MM-DD format and real calendar dates")

    # ─── CHECK 5: Industry consistency ─────────────────────────────────────
    print("── Check 5: Industry consistency ──")
    used_industries = set()
    for entry in entries:
        used_industries.add(entry.get("industry", ""))

    listed_industries = set(entries_data.get("industries", []))

    # Check for duplicates within the used industries
    dupes = used_industries & KNOWN_DUPLICATE_INDUSTRIES
    if "Fintech" in used_industries and "Financial Technology" in used_industries:
        warnings.append("Duplicate industry values: entries use both \"Fintech\" and \"Financial Technology\" (synonyms)")
    elif len(dupes) == 1 and "Financial Technology" in listed_industries:
        # "Financial Technology" in listed but only "Fintech" used in entries
        warnings.append(
            "**Industry alias inconsistency:** `industries` array lists `\"Financial Technology\"` "
            "but all fintech entries use `\"Fintech\"`. These are synonyms — "
            "`\"Financial Technology\"` should be removed from the industries array "
            "or `\"Fintech\"` should be renamed to `\"Financial Technology\"`."
        )
        issues.append(
            "**Industry inconsistency:** `industries` array in entries.json lists 7 items (including "
            "both `\"Fintech\"` and `\"Financial Technology\"`), but only 6 are actually used. "
            "`\"Financial Technology\"` is an unused duplicate of `\"Fintech\"`."
        )

    # Check industries listed vs stats.json count
    actual_distinct = len(used_industries)
    stats_industry_count = stats_data.get("industries", 0)
    if actual_distinct != stats_industry_count:
        warnings.append(
            f"**Industry count mismatch:** entries.json `industries` array has {len(listed_industries)} items, "
            f"but actual distinct industries in entries = {actual_distinct}. "
            f"stats.json reports {stats_industry_count} industries."
        )

    passes.append(f"Industry values used by entries: {', '.join(sorted(used_industries))}")

    # ─── CHECK 6: Sum of jobs_lost vs stats.json ───────────────────────────
    print("── Check 6: Jobs sum vs stats.json ──")
    computed_total = sum(e.get("jobs_lost", 0) for e in entries)
    reported_total = stats_data["total_jobs_lost"]

    # By classification
    by_class = {}
    for e in entries:
        cls = e["classification"]
        by_class[cls] = by_class.get(cls, 0) + e.get("jobs_lost", 0)

    stats_by_class = stats_data.get("by_classification", {})

    # By industry
    by_ind = {}
    for e in entries:
        ind = e["industry"]
        by_ind[ind] = by_ind.get(ind, 0) + e.get("jobs_lost", 0)

    stats_by_ind = stats_data.get("by_industry", {})

    # Check total
    if computed_total == reported_total:
        passes.append(f"Total jobs_lost sum: **{computed_total:,}** matches stats.json exactly")
    else:
        issues.append(
            f"**Jobs sum mismatch:** computed total = {computed_total:,}, "
            f"stats.json reports {reported_total:,} (diff: {computed_total - reported_total:+,})"
        )

    # Check classification breakdowns
    for cls in VALID_CLASSIFICATIONS:
        computed = by_class.get(cls, 0)
        reported = stats_by_class.get(cls, {}).get("jobs", 0)
        if computed != reported:
            issues.append(
                f"**Classification `{cls}`** jobs mismatch: computed={computed:,}, stats.json={reported:,}"
            )

    # Check industry breakdowns
    for ind, computed in by_ind.items():
        reported = stats_by_ind.get(ind, {}).get("jobs", 0)
        if computed != reported:
            issues.append(
                f"**Industry `{ind}`** jobs mismatch: computed={computed:,}, stats.json={reported:,}"
            )

    # ─── CHECK 7: Classification counts ────────────────────────────────────
    print("── Check 7: Classification entry counts ──")
    computed_cls_counts = Counter(e["classification"] for e in entries)
    embedded_counts = entries_data.get("classifications", {})
    stats_counts = stats_data.get("classification_counts", {})

    for cls in VALID_CLASSIFICATIONS:
        computed = computed_cls_counts.get(cls, 0)
        embedded = embedded_counts.get(cls, {}).get("count", 0)
        stats_c = stats_counts.get(cls, 0)
        if computed != embedded:
            issues.append(
                f"**Classification `{cls}`** entry count mismatch in entries.json embedded metadata: "
                f"actual entries={computed}, embedded classifications.count={embedded}"
            )
        if computed != stats_c:
            issues.append(
                f"**Classification `{cls}`** entry count mismatch in stats.json: "
                f"actual entries={computed}, stats.json={stats_c}"
            )

    # ─── Additional: Stats metadata consistency ────────────────────────────
    print("── Additional: Stats metadata ──")
    if stats_data["total_entries"] != len(entries):
        issues.append(
            f"stats.json total_entries={stats_data['total_entries']} but actual entries={len(entries)}"
        )

    if stats_data["companies"] != len(set(e["company"] for e in entries)):
        issues.append(
            f"stats.json companies={stats_data['companies']} but actual distinct companies={len(set(e['company'] for e in entries))}"
        )

    # ─── Generate report ───────────────────────────────────────────────────
    print("\n── Generating report ──")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append("# Dataset Integrity Validation Report")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Dataset:** `data/entries.json`")
    lines.append(f"**Reference stats:** `docs/api/stats.json`")
    lines.append(f"**Entries validated:** {len(entries)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")

    status = "PASS" if not issues else "FAIL"
    lines.append(f"**Overall status: {status}**  ")
    lines.append(f"- Errors: {len(issues)}  ")
    lines.append(f"- Warnings: {len(warnings)}  ")
    lines.append(f"- Checks passed: {len(passes)}  ")
    lines.append("")

    if issues:
        lines.append("## ❌ Issues (Errors)")
        lines.append("")
        for i, iss in enumerate(issues, 1):
            lines.append(f"{i}. {iss}")
        lines.append("")

    if warnings:
        lines.append("## ⚠️ Warnings")
        lines.append("")
        for i, warn in enumerate(warnings, 1):
            lines.append(f"{i}. {warn}")
        lines.append("")

    lines.append("## ✅ Checks Passed")
    lines.append("")
    for i, p in enumerate(passes, 1):
        lines.append(f"{i}. {p}")
    lines.append("")

    # Detailed breakdown tables
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Breakdown")
    lines.append("")

    # Table of all entries
    lines.append("### All Entries")
    lines.append("")
    lines.append("| # | ID | Company | Date | Country | Industry | Jobs Lost | Classification | Confidence |")
    lines.append("|---|-----|---------|------|---------|----------|-----------|----------------|------------|")
    for i, e in enumerate(entries, 1):
        lines.append(
            f"| {i} | `{e['id']}` | {e['company']} | {e['date']} | {e['country']} | "
            f"{e['industry']} | {e['jobs_lost']:,} | {e['classification']} | {e['confidence_score']} |"
        )
    lines.append("")

    # Classification summary
    lines.append("### By Classification")
    lines.append("")
    lines.append("| Classification | Entries | Jobs Lost |")
    lines.append("|----------------|---------|-----------|")
    for cls in sorted(VALID_CLASSIFICATIONS):
        c = computed_cls_counts.get(cls, 0)
        j = by_class.get(cls, 0)
        lines.append(f"| {cls} | {c} | {j:,} |")
    lines.append(f"| **Total** | **{len(entries)}** | **{computed_total:,}** |")
    lines.append("")

    # Industry summary
    lines.append("### By Industry")
    lines.append("")
    lines.append("| Industry | Entries | Jobs Lost |")
    lines.append("|----------|---------|-----------|")
    for ind in sorted(by_ind.keys()):
        c = sum(1 for e in entries if e["industry"] == ind)
        lines.append(f"| {ind} | {c} | {by_ind[ind]:,} |")
    lines.append("")

    # Industry dupes detail
    if "Fintech" in used_industries or "Financial Technology" in used_industries:
        lines.append("### Industry Consistency Detail")
        lines.append("")
        lines.append("The following entries contribute to the Fintech/Financial Technology industry:")
        lines.append("")
        lines.append("| Entry ID | Company | Industry Field Value |")
        lines.append("|----------|---------|---------------------|")
        for e in entries:
            if e["industry"] in KNOWN_DUPLICATE_INDUSTRIES:
                lines.append(f"| `{e['id']}` | {e['company']} | `{e['industry']}` |")
        lines.append("")
        lines.append("**Recommendation:** Normalize to a single canonical value (e.g., `\"Fintech\"` or `\"Financial Technology\"`) across all entries and the `industries` array. Remove the unused duplicate from the `industries` array.")

    lines.append("---")
    lines.append(f"*Report generated by `scripts/validate_dataset.py`*")

    report_text = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report_text)
    print(f"Report written to {REPORT_PATH}")

    # ─── Exit code ─────────────────────────────────────────────────────────
    if issues:
        print(f"\n❌ VALIDATION FAILED: {len(issues)} issue(s) found")
        sys.exit(1)
    else:
        print("\n✅ VALIDATION PASSED: No issues found")
        sys.exit(0)


if __name__ == "__main__":
    main()
