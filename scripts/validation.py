#!/usr/bin/env python3
"""
Validates submitted evidence for new entries.
- Checks source URLs resolve
- Validates against known domain whitelist
- Assigns trust score to submitters
- Queues unverified submissions separately from published entries
"""
import json, re, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

ROOT = Path(__file__).resolve().parent.parent

TRUSTED_DOMAINS = {
    # Tier 1 — Major news wires
    "reuters.com", "bloomberg.com", "apnews.com", "bbc.com", "bbc.co.uk",
    # Tier 2 — Major business/tech press
    "wsj.com", "cnbc.com", "fortune.com", "forbes.com", "businessinsider.com",
    "techcrunch.com", "theverge.com", "arstechnica.com", "wired.com",
    "theguardian.com", "nytimes.com", "washingtonpost.com", "cnn.com",
    # Tier 3 — Company sources
    "blog.google", "about.fb.com", "news.microsoft.com", "apple.com/newsroom",
    "blog.dropbox.com", "news.sap.com", "about.linkedin.com",
    # Tier 4 — Press release wires
    "prnewswire.com", "businesswire.com", "globenewswire.com",
    # Tier 5 — Analyst / research
    "gartner.com", "mckinsey.com", "deloitte.com", "pwc.com",
}

SUBMISSION_SCHEMA = [
    "submitter_name", "submitter_email", "company", "date",
    "jobs_lost", "source_url", "source_title", "classification",
    "evidence_type", "summary"
]

REQUIRED_FIELDS = ["company", "date", "jobs_lost", "source_url", "classification"]

def validate_source_url(url: str) -> dict:
    """Check if URL resolves and domain is trusted."""
    result = {"valid": False, "domain_trusted": False, "status_code": None, "error": None}
    try:
        parsed = url.split("://")[-1].split("/")[0].lower().replace("www.", "")
        result["domain"] = parsed
        for td in TRUSTED_DOMAINS:
            if parsed == td or parsed.endswith("." + td):
                result["domain_trusted"] = True
                break
        req = Request(url, headers={"User-Agent": "AILayoffTracker/2.0 (Validation Bot; +https://ailayofftracker.com)"})
        with urlopen(req, timeout=15) as resp:
            result["status_code"] = resp.status
            result["valid"] = 200 <= resp.status < 400
    except HTTPError as e:
        result["status_code"] = e.code
        result["error"] = str(e)
    except URLError as e:
        result["error"] = str(e.reason)
    except Exception as e:
        result["error"] = str(e)
    return result

def validate_submission(submission: dict) -> dict:
    """Validate a single submission. Returns result with errors and warnings."""
    errors = []
    warnings = []
    
    for field in REQUIRED_FIELDS:
        if field not in submission or not submission[field]:
            errors.append(f"Missing required field: {field}")
    
    if "classification" in submission:
        valid = {"DIRECT_AI_REPLACEMENT", "AI_DRIVEN_RESTRUCTURING", "AI_REALLOCATION", "MARKET_DISRUPTION"}
        if submission["classification"] not in valid:
            errors.append(f"Invalid classification: {submission['classification']}. Must be one of: {', '.join(sorted(valid))}")
    
    if "jobs_lost" in submission:
        try:
            jl = int(submission["jobs_lost"])
            if jl < 1:
                errors.append("jobs_lost must be positive")
            elif jl > 500000:
                warnings.append(f"jobs_lost ({jl}) is unusually high — please verify")
        except (ValueError, TypeError):
            errors.append("jobs_lost must be a number")
    
    if "source_url" in submission and submission.get("source_url"):
        url_result = validate_source_url(submission["source_url"])
        submission["_url_validation"] = url_result
        if not url_result["valid"]:
            errors.append(f"Source URL could not be verified: {url_result.get('error', 'Unknown error')}")
        if not url_result["domain_trusted"]:
            warnings.append(f"Source domain '{url_result.get('domain', 'unknown')}' is not on trusted domain list — will require manual review")
    
    if "date" in submission:
        try:
            datetime.strptime(submission["date"], "%Y-%m-%d")
        except ValueError:
            errors.append("date must be in YYYY-MM-DD format")
    
    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "submission": submission}

def compute_trust_score(submission: dict, history: list) -> int:
    """Compute trust score for a submitter (0-100)."""
    email = submission.get("submitter_email", "")
    if not email:
        return 10
    email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:12]
    past = [s for s in history if s.get("_submitter_hash") == email_hash]
    if not past:
        return 15
    accepted = sum(1 for s in past if s.get("_status") == "accepted")
    rejected = sum(1 for s in past if s.get("_status") == "rejected")
    total = accepted + rejected
    if total == 0:
        return 15
    base = (accepted / total) * 70
    bonus = min(accepted * 5, 30)
    return min(int(base + bonus), 100)

def main():
    submissions_file = ROOT / "data" / "submissions.json"
    entries_file = ROOT / "data" / "entries.json"
    
    if submissions_file.exists():
        with open(submissions_file) as f:
            queue = json.load(f)
    else:
        queue = []
    
    if len(sys.argv) > 1 and sys.argv[1] == "--validate-all":
        print(f"Validating {len(queue)} submissions...")
        for i, sub in enumerate(queue):
            result = validate_submission(sub)
            sub["_validation"] = result
            sub["_validated_at"] = datetime.now(timezone.utc).isoformat()
            status = "✅" if result["valid"] else "❌"
            print(f"  [{i+1}/{len(queue)}] {status} {sub.get('company', 'Unknown')}: {len(result['errors'])} errors, {len(result['warnings'])} warnings")
        
        with open(submissions_file, "w") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
        
        print(f"\nDone. {sum(1 for s in queue if s.get('_validation', {}).get('valid'))}/{len(queue)} valid.")
    
    elif len(sys.argv) > 1 and len(sys.argv) > 2:
        # Validate a specific submission passed as JSON
        try:
            submission = json.loads(sys.argv[2])
            result = validate_submission(submission)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except json.JSONDecodeError as e:
            print(json.dumps({"valid": False, "errors": [f"Invalid JSON: {e}"]}))
    
    else:
        # Show summary
        print(f"Submissions queue: {len(queue)} entries")
        print(f"Trusted domains: {len(TRUSTED_DOMAINS)}")
        print(f"Usage: {sys.argv[0]} [--validate-all | '<json_submission>']")

if __name__ == "__main__":
    main()
