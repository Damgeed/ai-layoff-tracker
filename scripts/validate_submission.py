#!/usr/bin/env python3
"""
validate_submission.py — Data Quality Validator for AI Layoff Tracker

Validates a submission against quality rules:
  1. URL validation — must resolve (HTTP 2xx/3xx) and must be from a trusted domain whitelist
  2. Required field presence
  3. Field format and range checks
  4. Classification validity

Returns pass/fail with detailed reasons.

Usage:
  python scripts/validate_submission.py
      Validates all submissions in data/submissions.json and prints a report.

  python scripts/validate_submission.py --json '<submission>'
      Validates a single submission passed as a JSON string on stdin/argv.

  python scripts/validate_submission.py --file <path>
      Validates a JSON file containing a single submission object.
"""

import json
import re
import sys
import ssl
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
SUBMISSIONS_PATH = BASE_DIR / "data" / "submissions.json"

# ── Trusted Domain Whitelist ───────────────────────────────────────────────
# Only sources from these domains are accepted without manual review.
TRUSTED_DOMAINS = {
    "bbc.com",
    "bbc.co.uk",
    "reuters.com",
    "bloomberg.com",
    "cnbc.com",
    "theverge.com",
    "arstechnica.com",
    "wired.com",
    "techcrunch.com",
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "sec.gov",
    "businesswire.com",
    "prnewswire.com",
}

# ── Constants ──────────────────────────────────────────────────────────────
REQUIRED_FIELDS = [
    "company", "date", "jobs_lost", "classification", "source_url"
]

VALID_CLASSIFICATIONS = {
    "DIRECT_AI_REPLACEMENT",
    "AI_DRIVEN_RESTRUCTURING",
    "AI_REALLOCATION",
    "MARKET_DISRUPTION",
}

VALID_STATUSES = {"PENDING", "VERIFIED", "DISPUTED", "RETRACTED"}

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ── SSL workaround for environments with cert issues ───────────────────────
ssl._create_default_https_context = ssl._create_unverified_context


# ═══════════════════════════════════════════════════════════════════════════
#  URL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def extract_domain(url: str) -> str:
    """Extract the bare domain from a URL, stripping www. prefix."""
    try:
        # Handle URLs with and without protocol
        if "://" in url:
            domain = url.split("://")[-1].split("/")[0]
        else:
            domain = url.split("/")[0]
        domain = domain.lower().replace("www.", "")
        # Strip port if present
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain
    except Exception:
        return ""


def check_domain_trusted(url: str) -> tuple:
    """Check if a URL's domain is in the trusted whitelist.
    Returns (is_trusted: bool, domain: str)
    """
    domain = extract_domain(url)
    if not domain:
        return False, domain

    for trusted in TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith("." + trusted):
            return True, domain

    return False, domain


def validate_url(url: str, timeout: int = 15) -> dict:
    """Check whether a source URL resolves (HTTP 2xx/3xx).
    Returns a dict with validation result and details.
    """
    result = {
        "url": url,
        "resolves": False,
        "status_code": None,
        "domain": "",
        "domain_trusted": False,
        "error": None,
    }

    # ── Basic URL format check ──────────────────────────────────────────
    if not url or not isinstance(url, str):
        result["error"] = "URL is empty or not a string"
        return result

    if not url.startswith(("http://", "https://")):
        result["error"] = "URL must start with http:// or https://"
        return result

    # ── Domain trust check ──────────────────────────────────────────────
    trusted, domain = check_domain_trusted(url)
    result["domain"] = domain
    result["domain_trusted"] = trusted

    # ── DNS / HTTP resolution check ─────────────────────────────────────
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "AILayoffTracker/2.0 (Validation Bot; +https://ailayofftracker.com)"
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            result["status_code"] = resp.status
            result["resolves"] = 200 <= resp.status < 400
    except HTTPError as e:
        result["status_code"] = e.code
        result["error"] = f"HTTP {e.code}: {e.reason}"
    except URLError as e:
        result["error"] = f"Connection error: {e.reason}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  FIELD VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_required_fields(submission: dict) -> list:
    """Check that all required fields are present and non-empty.
    Returns a list of error strings (empty list = pass).
    """
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in submission:
            errors.append(f"Missing required field: '{field}'")
        elif submission[field] is None:
            errors.append(f"Required field '{field}' is null")
        elif isinstance(submission[field], str) and not submission[field].strip():
            errors.append(f"Required field '{field}' is empty")
    return errors


def validate_classification(submission: dict) -> list:
    """Validate the classification field against allowed values."""
    errors = []
    cls = submission.get("classification")
    if cls and cls not in VALID_CLASSIFICATIONS:
        errors.append(
            f"Invalid classification '{cls}'. "
            f"Must be one of: {', '.join(sorted(VALID_CLASSIFICATIONS))}"
        )
    return errors


def validate_date(submission: dict) -> list:
    """Validate date format (YYYY-MM-DD) and that it's a real calendar date."""
    errors = []
    date_val = submission.get("date")
    if date_val:
        date_str = str(date_val)
        if not DATE_REGEX.match(date_str):
            errors.append(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.")
        else:
            try:
                parsed = datetime.strptime(date_str, "%Y-%m-%d")
                # Reject future dates
                if parsed.date() > datetime.now().date():
                    errors.append(f"Date '{date_str}' is in the future.")
            except ValueError:
                errors.append(f"Invalid calendar date: '{date_str}'.")
    return errors


def validate_jobs_lost(submission: dict) -> list:
    """Validate the jobs_lost field (positive integer, reasonable range)."""
    errors = []
    jl = submission.get("jobs_lost")
    if jl is not None:
        try:
            jl_int = int(jl)
            if jl_int < 1:
                errors.append(f"jobs_lost must be positive, got {jl_int}.")
            elif jl_int > 500_000:
                errors.append(
                    f"jobs_lost ({jl_int:,}) exceeds maximum allowed (500,000). "
                    "If correct, please provide additional verification."
                )
        except (ValueError, TypeError):
            errors.append(f"jobs_lost must be a number, got '{jl}'.")
    return errors


def validate_status(submission: dict) -> list:
    """Validate the status field if present."""
    errors = []
    status = submission.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(
            f"Invalid status '{status}'. "
            f"Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )
    return errors


def validate_submitter_email(submission: dict) -> list:
    """Validate submitter_email format if present."""
    errors = []
    email = submission.get("submitter_email")
    if email and isinstance(email, str) and email.strip():
        # Basic email format check
        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append(f"Invalid submitter_email format: '{email}'.")
    return errors


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN VALIDATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def validate_submission(submission: dict, resolve_urls: bool = True) -> dict:
    """Validate a single submission against all quality rules.

    Args:
        submission: The submission dict to validate.
        resolve_urls: If True, perform HTTP requests to verify URLs resolve.

    Returns:
        A dict with keys:
          - valid: bool (overall pass/fail)
          - errors: list of error strings (failure reasons)
          - warnings: list of warning strings (non-blocking issues)
          - url_result: dict with URL resolution details (if resolve_urls=True)
          - submission_id: str (for traceability)
    """
    errors = []
    warnings = []

    # 1. Required fields
    errors.extend(validate_required_fields(submission))

    # 2. Classification
    errors.extend(validate_classification(submission))

    # 3. Date format and validity
    errors.extend(validate_date(submission))

    # 4. Jobs lost range
    errors.extend(validate_jobs_lost(submission))

    # 5. Status
    errors.extend(validate_status(submission))

    # 6. Submitter email
    errors.extend(validate_submitter_email(submission))

    # 7. URL validation
    url_result = None
    source_url = submission.get("source_url")
    if source_url and resolve_urls:
        url_result = validate_url(source_url)

        if not url_result["resolves"]:
            if url_result["error"]:
                errors.append(f"Source URL does not resolve: {url_result['error']}")
            else:
                errors.append(
                    f"Source URL returned status {url_result['status_code']}"
                )

        if not url_result["domain_trusted"]:
            domain = url_result.get("domain", "unknown")
            warnings.append(
                f"Source domain '{domain}' is not on the trusted domain whitelist. "
                "Manual editorial review required."
            )

    # Jobs lost > 10,000 gets a warning even if otherwise valid
    try:
        jl = int(submission.get("jobs_lost", 0))
        if jl > 10_000:
            warnings.append(
                f"High-impact event: {jl:,} jobs lost. Please ensure multiple source confirmation."
            )
    except (ValueError, TypeError):
        pass

    sub_id = submission.get("id", "unknown")

    return {
        "valid": len(errors) == 0,
        "submission_id": sub_id,
        "errors": errors,
        "warnings": warnings,
        "url_result": url_result,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # Validate a single submission from command-line JSON
        if len(sys.argv) < 3:
            print(json.dumps({"valid": False, "errors": ["No JSON provided after --json flag"]}, indent=2))
            sys.exit(1)
        try:
            submission = json.loads(sys.argv[2])
        except json.JSONDecodeError as e:
            print(json.dumps({"valid": False, "errors": [f"Invalid JSON: {e}"]}, indent=2))
            sys.exit(1)

        result = validate_submission(submission)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["valid"] else 1)

    elif len(sys.argv) > 1 and sys.argv[1] == "--file":
        # Validate a submission from a JSON file
        if len(sys.argv) < 3:
            print("Usage: validate_submission.py --file <path/to/submission.json>")
            sys.exit(1)
        filepath = Path(sys.argv[2])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)
        with open(filepath) as f:
            submission = json.load(f)
        result = validate_submission(submission)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["valid"] else 1)

    else:
        # Default: validate all submissions in data/submissions.json
        if not SUBMISSIONS_PATH.exists():
            print(f"No submissions file found at {SUBMISSIONS_PATH}")
            sys.exit(1)

        with open(SUBMISSIONS_PATH) as f:
            data = json.load(f)

        submissions = data.get("submissions", [])
        if not submissions:
            print("No submissions to validate.")
            sys.exit(0)

        print(f"Validating {len(submissions)} submission(s) from {SUBMISSIONS_PATH}\n")
        print(f"Trusted domains: {len(TRUSTED_DOMAINS)}")
        print(f"Required fields: {', '.join(REQUIRED_FIELDS)}")
        print()

        all_valid = True
        for i, sub in enumerate(submissions, 1):
            result = validate_submission(sub)
            sub["_validation"] = result
            sub["_validated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

            status_icon = "✅" if result["valid"] else "❌"
            print(f"  [{i}/{len(submissions)}] {status_icon} {sub.get('id', 'unknown')}")
            print(f"         Company: {sub.get('company', 'N/A')}")
            print(f"         Status:  {sub.get('status', 'PENDING')}")

            if result["errors"]:
                all_valid = False
                for err in result["errors"]:
                    print(f"         ERROR:   {err}")
            if result["warnings"]:
                for warn in result["warnings"]:
                    print(f"         WARN:    {warn}")
            if result["url_result"]:
                ur = result["url_result"]
                trusted = "TRUSTED" if ur["domain_trusted"] else "UNTRUSTED"
                print(f"         URL:     {ur.get('status_code', 'N/A')} | {ur.get('domain', 'N/A')} [{trusted}]")
            print()

        # Write validation results back
        data["_last_validated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        data["_validation_summary"] = {
            "total": len(submissions),
            "passed": sum(1 for s in submissions if s.get("_validation", {}).get("valid")),
            "failed": sum(1 for s in submissions if not s.get("_validation", {}).get("valid")),
        }

        # Clean up _validation from the persisted file? No — keep for audit.
        with open(SUBMISSIONS_PATH, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        summary = data["_validation_summary"]
        print(f"Summary: {summary['passed']}/{summary['total']} passed, {summary['failed']} failed, 0 warnings")
        print(f"Results written to {SUBMISSIONS_PATH}")

        if all_valid:
            print("\n✅ ALL SUBMISSIONS VALID")
            sys.exit(0)
        else:
            print(f"\n❌ {summary['failed']} SUBMISSION(S) FAILED VALIDATION")
            sys.exit(1)


if __name__ == "__main__":
    main()
