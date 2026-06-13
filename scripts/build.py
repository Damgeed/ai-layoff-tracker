#!/usr/bin/env python3
"""
AI Layoff Tracker — Static Site Generator v2.0
Reads data/entries.json → generates complete static site in public/
"""
import json, os, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "docs"
TEMPLATE_DIR = ROOT / "templates"

def load_data():
    with open(DATA_DIR / "entries.json") as f:
        return json.load(f)

def compute_stats(data):
    entries = data["entries"]
    classifications = data.get("classifications", {})
    total_jobs = sum(e["jobs_lost"] for e in entries)
    companies = len(set(e["company"] for e in entries))
    countries = len(set(e["country"] for e in entries))
    industries = len(set(e["industry"] for e in entries))
    
    by_classification = {}
    for e in entries:
        c = e["classification"]
        if c not in by_classification:
            by_classification[c] = {"jobs": 0, "entries": 0}
        by_classification[c]["jobs"] += e["jobs_lost"]
        by_classification[c]["entries"] += 1
    
    by_industry = {}
    for e in entries:
        ind = e["industry"]
        if ind not in by_industry:
            by_industry[ind] = {"jobs": 0, "entries": 0}
        by_industry[ind]["jobs"] += e["jobs_lost"]
        by_industry[ind]["entries"] += 1
    
    by_country = {}
    for e in entries:
        c = e["country"]
        if c not in by_country:
            by_country[c] = {"jobs": 0, "entries": 0}
        by_country[c]["jobs"] += e["jobs_lost"]
        by_country[c]["entries"] += 1
    
    newest = max(e["date"] for e in entries)
    oldest = min(e["date"] for e in entries)
    
    months_span = max(1, (datetime.strptime(newest, "%Y-%m-%d") - datetime.strptime(oldest, "%Y-%m-%d")).days / 30.44)
    monthly_rate = round(total_jobs / months_span)
    
    return {
        "total_jobs_lost": total_jobs,
        "companies": companies,
        "countries": countries,
        "industries": industries,
        "total_entries": len(entries),
        "by_classification": by_classification,
        "by_industry": dict(sorted(by_industry.items(), key=lambda x: x[1]["jobs"], reverse=True)),
        "by_country": dict(sorted(by_country.items(), key=lambda x: x[1]["jobs"], reverse=True)),
        "date_range": {"oldest": oldest, "newest": newest},
        "monthly_rate": monthly_rate,
        "annualized_projection": monthly_rate * 12,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "classification_counts": {k: v["entries"] for k, v in by_classification.items()},
        "classification_jobs": {k: v["jobs"] for k, v in by_classification.items()}
    }

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_api(data, stats):
    """Generate API JSON files."""
    api_dir = PUBLIC_DIR / "api"
    os.makedirs(api_dir, exist_ok=True)
    
    write_json(api_dir / "entries.json", data)
    write_json(api_dir / "stats.json", stats)
    
    # Per-company JSON endpoints
    company_api_dir = api_dir / "company"
    os.makedirs(company_api_dir, exist_ok=True)
    for entry in data["entries"]:
        write_json(company_api_dir / f"{entry['slug']}.json", entry)
    print(f"   ✅ {len(data['entries'])} per-company API files")

    # Per-industry JSON endpoints
    industry_api_dir = api_dir / "industry"
    os.makedirs(industry_api_dir, exist_ok=True)
    by_industry = {}
    for entry in data["entries"]:
        ind_slug = entry["industry"].lower().replace(" ", "-").replace("&", "and")
        if ind_slug not in by_industry:
            by_industry[ind_slug] = {"industry": entry["industry"], "slug": ind_slug, "entries": [], "total_jobs": 0, "companies": set()}
        by_industry[ind_slug]["entries"].append(entry)
        by_industry[ind_slug]["total_jobs"] += entry["jobs_lost"]
        by_industry[ind_slug]["companies"].add(entry["company"])
    for slug, ind_data in by_industry.items():
        ind_data["companies"] = sorted(list(ind_data["companies"]))
        ind_data["company_count"] = len(ind_data["companies"])
        ind_data["entry_count"] = len(ind_data["entries"])
        write_json(industry_api_dir / f"{slug}.json", ind_data)
    print(f"   ✅ {len(by_industry)} per-industry API files")

    # Per-country JSON endpoints
    country_api_dir = api_dir / "country"
    os.makedirs(country_api_dir, exist_ok=True)
    by_country = {}
    for entry in data["entries"]:
        c_slug = entry["country"].lower().replace(" ", "-")
        if c_slug not in by_country:
            by_country[c_slug] = {"country": entry["country"], "slug": c_slug, "entries": [], "total_jobs": 0, "companies": set()}
        by_country[c_slug]["entries"].append(entry)
        by_country[c_slug]["total_jobs"] += entry["jobs_lost"]
        by_country[c_slug]["companies"].add(entry["company"])
    for slug, c_data in by_country.items():
        c_data["companies"] = sorted(list(c_data["companies"]))
        c_data["company_count"] = len(c_data["companies"])
        c_data["entry_count"] = len(c_data["entries"])
        write_json(country_api_dir / f"{slug}.json", c_data)
    print(f"   ✅ {len(by_country)} per-country API files")

    # Downloadable CSV
    csv_path = PUBLIC_DIR / "api" / "entries.csv"
    entries = data["entries"]
    fields = ["id", "company", "date", "country", "industry", "jobs_lost", 
              "impact_percent", "classification", "confidence_score", "summary", "source_url"]
    with open(csv_path, "w") as f:
        f.write(",".join(fields) + "\n")
        for e in entries:
            row = []
            for field in fields:
                val = str(e.get(field, "")).replace('"', '""')
                row.append(f'"{val}"')
            f.write(",".join(row) + "\n")

def generate_company_pages(data):
    """Generate individual company pages."""
    company_dir = PUBLIC_DIR / "company"
    entries = data["entries"]
    
    for entry in entries:
        slug = entry["slug"]
        page_dir = company_dir / slug
        os.makedirs(page_dir, exist_ok=True)
        
        class_info = data["classifications"].get(entry["classification"], {})
        
        evidence_html = ""
        for ev in entry.get("evidence", []):
            evidence_html += f'<li class="evidence-item"><strong>{ev["type"].replace("_", " ").title()}:</strong> {ev["description"]}</li>'
        
        secondary_html = ""
        for src in entry.get("secondary_sources", []):
            secondary_html += f'<li><a href="{src["url"]}" target="_blank" rel="noopener">{src["title"]} <span class="source-pub">({src["publisher"]})</span></a></li>'
        
        archive_html = ""
        source_obj = entry.get("source", {})
        if source_obj.get("archive_url"):
            archive_html = f'<li>📦 <a href="{source_obj["archive_url"]}" target="_blank" rel="noopener">Archived Source <span class="source-pub">(archive.org)</span></a></li>'
        
        tags_html = " ".join(f'<span class="tag">{t}</span>' for t in entry.get("tags", []))
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{entry["company"]} — {entry["jobs_lost"]:,} Jobs Impacted | AI Layoff Tracker</title>
<meta name="description" content="{entry["summary"]}">
<meta property="og:title" content="{entry["company"]}: {entry["jobs_lost"]:,} Jobs Impacted by AI">
<meta property="og:description" content="{entry["summary"][:200]}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://ailayofftracker.com/company/{slug}/">
<link rel="stylesheet" href="/assets/css/main.css">
<link rel="stylesheet" href="/assets/css/timeline.css">
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header">
  <div class="container">
    <a href="/" class="logo">AI<span class="logo-accent">LAYOFF</span>TRACKER</a>
    <nav><a href="/methodology.html">Methodology</a><a href="/api/stats.json">API</a></nav>
  </div>
</header>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb"><a href="/">← Back to tracker</a></nav>
  <article class="entry-detail">
    <div class="entry-header">
      <div class="entry-classification" style="background:{class_info.get("color", "#ff4444")}">
        {class_info.get("label", entry["classification"])}
      </div>
      <h1>{entry["company"]}</h1>
      <div class="entry-stats">
        <div class="stat">
          <span class="stat-value">{entry["jobs_lost"]:,}</span>
          <span class="stat-label">Jobs Lost</span>
        </div>
        <div class="stat">
          <span class="stat-value">{entry["impact_percent"]}%</span>
          <span class="stat-label">of Workforce</span>
        </div>
        <div class="stat">
          <span class="stat-value">{entry["confidence_score"]}/100</span>
          <span class="stat-label">Confidence</span>
        </div>
      </div>
    </div>
    <div class="entry-meta">
      <span>📅 {entry["date"]}</span>
      <span>📍 {entry["headquarters"]}</span>
      <span>🏭 {entry["industry"]}</span>
      <span>📊 {entry["public_trade_status"].title()}</span>
    </div>
    <div class="entry-body">
      <p class="summary">{entry["summary"]}</p>
      {f'<blockquote class="ceo-quote"><p>"{entry["ceo_quote"]}"</p><cite>— {entry["company"]} CEO</cite></blockquote>' if entry.get("ceo_quote") else ""}
      <div class="tags">{tags_html}</div>
      <h2>Evidence</h2>
      <ul class="evidence-list">{evidence_html}</ul>
      <h2>Sources</h2>
      <ul class="source-list">
        <li><a href="{entry["source"]["url"]}" target="_blank" rel="noopener">{entry["source"]["title"]} <span class="source-pub">({entry["source"]["publisher"]})</span></a></li>
        {archive_html}
        {secondary_html}
      </ul>
      <h2>Departments Affected</h2>
      <ul><li>{"</li><li>".join(entry.get("departments_affected", ["Not specified"]))}</li></ul>
    </div>
  </article>
  <div class="share-section">
    <button onclick="shareEntry('{entry["company"]}', {entry["jobs_lost"]}, '{entry["classification"]}')" class="btn-share">📤 Share This Entry</button>
  </div>
</main>
<footer class="site-footer">
  <div class="container">
    <p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p>
    <p><a href="/methodology.html">Methodology</a> · <a href="/api/entries.json">JSON API</a> · <a href="/api/entries.csv">Download CSV</a></p>
  </div>
</footer>
<script src="/assets/js/share.js" defer></script>
</body>
</html>'''
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

def generate_entry_pages(data):
    """Generate individual entry pages at /entry/{id}/index.html."""
    entry_dir = PUBLIC_DIR / "entry"
    entries = data["entries"]

    # Build lookup maps
    by_company = {}
    by_industry = {}
    for e in entries:
        company = e["company"]
        if company not in by_company:
            by_company[company] = []
        by_company[company].append(e)
        ind = e["industry"]
        if ind not in by_industry:
            by_industry[ind] = []
        by_industry[ind].append(e)

    for entry in entries:
        eid = entry["id"]
        page_dir = entry_dir / eid
        os.makedirs(page_dir, exist_ok=True)

        class_info = data["classifications"].get(entry["classification"], {})

        # Evidence list
        evidence_html = ""
        for ev in entry.get("evidence", []):
            evidence_html += f'<li class="evidence-item"><strong>{ev["type"].replace("_", " ").title()}:</strong> {ev["description"]}</li>'

        # CEO quote
        ceo_html = ""
        if entry.get("ceo_quote"):
            ceo_html = f'<blockquote class="ceo-quote"><p>"{entry["ceo_quote"]}"</p><cite>— {entry["company"]} CEO</cite></blockquote>'

        # Source links
        source_obj = entry.get("source", {})
        source_html = f'<li><a href="{source_obj.get("url", "#")}" target="_blank" rel="noopener">{source_obj.get("title", "Source")} <span class="source-pub">({source_obj.get("publisher", "Unknown")})</span></a></li>'
        archive_html = ""
        if source_obj.get("archive_url"):
            archive_html = f'<li>📦 <a href="{source_obj["archive_url"]}" target="_blank" rel="noopener">Archived Source <span class="source-pub">(archive.org)</span></a></li>'

        # Timeline: Other entries from same company
        company_entries = sorted(by_company.get(entry["company"], []), key=lambda x: x["date"], reverse=True)
        company_timeline = ""
        for ce in company_entries:
            if ce["id"] != eid:
                company_timeline += f'<li><a href="/entry/{ce["id"]}/">{ce["date"]} — {ce["jobs_lost"]:,} jobs</a></li>'
        company_timeline_html = f'<ul class="timeline-list">{company_timeline}</ul>' if company_timeline else "<p>No other entries for this company.</p>"

        # Timeline: Other entries from same industry
        industry_entries = sorted(by_industry.get(entry["industry"], []), key=lambda x: x["date"], reverse=True)
        industry_timeline = ""
        for ie in industry_entries:
            if ie["id"] != eid:
                industry_timeline += f'<li><a href="/entry/{ie["id"]}/">{ie["date"]} — {ie["company"]}: {ie["jobs_lost"]:,} jobs</a></li>'
        industry_timeline_html = f'<ul class="timeline-list">{industry_timeline}</ul>' if industry_timeline else "<p>No other entries for this industry.</p>"

        # Confidence dot color
        conf = entry["confidence_score"]
        if conf >= 80:
            conf_color = "#44ff44"
        elif conf >= 60:
            conf_color = "#ffcc44"
        else:
            conf_color = "#ff4444"

        # JSON-LD Dataset schema
        jsonld = {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": f"{entry['company']}: {entry['jobs_lost']:,} Jobs Impacted by AI",
            "description": entry["summary"],
            "url": f"https://ailayofftracker.com/entry/{eid}/",
            "datePublished": entry["date"],
            "temporalCoverage": entry["date"],
            "spatialCoverage": {"@type": "Country", "name": entry["country"]},
            "creator": {"@type": "Organization", "name": "AI Layoff Tracker"},
            "keywords": [entry["classification"], entry["industry"], entry["company"], entry["country"]],
        }

        desc = entry["summary"][:200]

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{entry["company"]}: {entry["jobs_lost"]:,} Jobs Impacted | AI Layoff Tracker</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{entry["company"]}: {entry["jobs_lost"]:,} Jobs Impacted by AI">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://ailayofftracker.com/entry/{eid}/">
<link rel="canonical" href="https://ailayofftracker.com/entry/{eid}/">
<link rel="stylesheet" href="/assets/css/main.css">
<link rel="stylesheet" href="/assets/css/timeline.css">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False)}
</script>
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="container">
    <a href="/" class="logo">AI<span class="logo-accent">LAYOFF</span>TRACKER</a>
    <nav role="navigation" aria-label="Main navigation"><a href="/methodology.html">Methodology</a><a href="/api/stats.json">API</a></nav>
  </div>
</header>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">← Back to tracker</a> · <a href="/company/{entry["slug"]}/">← {entry["company"]} page</a></nav>
  <article class="entry-detail">
    <div class="entry-header">
      <div class="entry-classification" style="background:{class_info.get("color", "#ff4444")}">
        {class_info.get("label", entry["classification"])}
      </div>
      <h1>{entry["company"]}: {entry["jobs_lost"]:,} Jobs Impacted</h1>
      <div class="entry-stats">
        <div class="stat">
          <span class="stat-value">{entry["jobs_lost"]:,}</span>
          <span class="stat-label">Jobs Lost</span>
        </div>
        <div class="stat">
          <span class="stat-value">{entry["impact_percent"]}%</span>
          <span class="stat-label">of Workforce</span>
        </div>
        <div class="stat">
          <span class="stat-value"><span class="confidence-dot" style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{conf_color};margin-right:6px;"></span>{conf}/100</span>
          <span class="stat-label">Confidence</span>
        </div>
      </div>
    </div>
    <div class="entry-meta">
      <span>📅 {entry["date"]}</span>
      <span>📍 {entry["country"]}</span>
      <span>🏭 {entry["industry"]}</span>
    </div>
    <div class="entry-body">
      <p class="summary">{entry["summary"]}</p>
      {ceo_html}
      <h2>Evidence</h2>
      <ul class="evidence-list">{evidence_html}</ul>
      <h2>Sources</h2>
      <ul class="source-list">
        {source_html}
        {archive_html}
      </ul>
    </div>
  </article>
  <section class="related-links" aria-label="Related entries">
    <h2>Other entries from {entry["company"]}</h2>
    {company_timeline_html}
    <h2>Other entries from {entry["industry"]}</h2>
    {industry_timeline_html}
  </section>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="container">
    <p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p>
    <p><a href="/methodology.html">Methodology</a> · <a href="/api/entries.json">JSON API</a> · <a href="/api/entries.csv">Download CSV</a></p>
  </div>
</footer>
</body>
</html>'''
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

def generate_industry_pages(data):
    """Generate industry pages at /industry/{slug}/index.html."""
    industry_dir = PUBLIC_DIR / "industry"
    entries = data["entries"]

    # Group by industry
    by_industry = {}
    for e in entries:
        ind = e["industry"]
        ind_slug = ind.lower().replace(" ", "-").replace("&", "and")
        if ind_slug not in by_industry:
            by_industry[ind_slug] = {
                "industry": ind,
                "slug": ind_slug,
                "entries": [],
                "total_jobs": 0,
                "companies": {}
            }
        by_industry[ind_slug]["entries"].append(e)
        by_industry[ind_slug]["total_jobs"] += e["jobs_lost"]
        comp = e["company"]
        if comp not in by_industry[ind_slug]["companies"]:
            by_industry[ind_slug]["companies"][comp] = 0
        by_industry[ind_slug]["companies"][comp] += e["jobs_lost"]

    for ind_slug, ind_data in by_industry.items():
        page_dir = industry_dir / ind_slug
        os.makedirs(page_dir, exist_ok=True)

        # Companies list
        companies_html = ""
        for comp_name in sorted(ind_data["companies"].keys()):
            comp_jobs = ind_data["companies"][comp_name]
            companies_html += f'<li><a href="/company/{comp_name.lower().replace(" ", "-").replace("&", "and")}/">{comp_name}</a> — {comp_jobs:,} jobs</li>'

        # Mini timeline (entries sorted by date)
        timeline_html = ""
        for e in sorted(ind_data["entries"], key=lambda x: x["date"], reverse=True):
            timeline_html += f'<li><a href="/entry/{e["id"]}/">{e["date"]} — {e["company"]}: {e["jobs_lost"]:,} jobs</a></li>'

        desc = f"AI workforce reductions in the {ind_data['industry']} industry: {ind_data['total_jobs']:,} jobs impacted across {len(ind_data['companies'])} companies."

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ind_data["industry"]} — AI Workforce Reductions | AI Layoff Tracker</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{ind_data["industry"]} — AI Workforce Reductions">
<meta property="og:description" content="{desc[:200]}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://ailayofftracker.com/industry/{ind_slug}/">
<link rel="canonical" href="https://ailayofftracker.com/industry/{ind_slug}/">
<link rel="stylesheet" href="/assets/css/main.css">
<link rel="stylesheet" href="/assets/css/timeline.css">
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="container">
    <a href="/" class="logo">AI<span class="logo-accent">LAYOFF</span>TRACKER</a>
    <nav role="navigation" aria-label="Main navigation"><a href="/methodology.html">Methodology</a><a href="/api/stats.json">API</a></nav>
  </div>
</header>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">← Back to tracker</a></nav>
  <h1>{ind_data["industry"]} — AI Workforce Reductions</h1>
  <div class="entry-stats">
    <div class="stat">
      <span class="stat-value">{ind_data["total_jobs"]:,}</span>
      <span class="stat-label">Total Jobs Lost</span>
    </div>
    <div class="stat">
      <span class="stat-value">{len(ind_data["companies"])}</span>
      <span class="stat-label">Companies</span>
    </div>
    <div class="stat">
      <span class="stat-value">{len(ind_data["entries"])}</span>
      <span class="stat-label">Entries</span>
    </div>
  </div>
  <section aria-label="Companies in this industry">
    <h2>Companies</h2>
    <ul class="company-list">{companies_html}</ul>
  </section>
  <section aria-label="Timeline of entries">
    <h2>Timeline</h2>
    <ul class="timeline-list">{timeline_html}</ul>
  </section>
  <section aria-label="API access">
    <h2>API</h2>
    <p><a href="/api/industry/{ind_slug}.json">/api/industry/{ind_slug}.json</a></p>
  </section>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="container">
    <p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p>
    <p><a href="/methodology.html">Methodology</a> · <a href="/api/entries.json">JSON API</a> · <a href="/api/entries.csv">Download CSV</a></p>
  </div>
</footer>
</body>
</html>'''
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

def generate_country_pages(data):
    """Generate country pages at /country/{slug}/index.html."""
    country_dir = PUBLIC_DIR / "country"
    entries = data["entries"]

    # Group by country
    by_country = {}
    for e in entries:
        country = e["country"]
        c_slug = country.lower().replace(" ", "-")
        if c_slug not in by_country:
            by_country[c_slug] = {
                "country": country,
                "slug": c_slug,
                "entries": [],
                "total_jobs": 0,
                "companies": {},
                "industries": {}
            }
        by_country[c_slug]["entries"].append(e)
        by_country[c_slug]["total_jobs"] += e["jobs_lost"]
        comp = e["company"]
        if comp not in by_country[c_slug]["companies"]:
            by_country[c_slug]["companies"][comp] = 0
        by_country[c_slug]["companies"][comp] += e["jobs_lost"]
        ind = e["industry"]
        if ind not in by_country[c_slug]["industries"]:
            by_country[c_slug]["industries"][ind] = {"jobs": 0, "entries": 0}
        by_country[c_slug]["industries"][ind]["jobs"] += e["jobs_lost"]
        by_country[c_slug]["industries"][ind]["entries"] += 1

    for c_slug, c_data in by_country.items():
        page_dir = country_dir / c_slug
        os.makedirs(page_dir, exist_ok=True)

        # Industry breakdown
        industries_html = ""
        for ind_name in sorted(c_data["industries"].keys()):
            ind_stats = c_data["industries"][ind_name]
            industries_html += f'<li>{ind_name} — {ind_stats["jobs"]:,} jobs ({ind_stats["entries"]} entries)</li>'

        # Companies list
        companies_html = ""
        for comp_name in sorted(c_data["companies"].keys()):
            comp_jobs = c_data["companies"][comp_name]
            slug = e["slug"] if (e := next((x for x in c_data["entries"] if x["company"] == comp_name), None)) else comp_name.lower().replace(" ", "-")
            # Find actual slug from entries
            matching = [x for x in c_data["entries"] if x["company"] == comp_name]
            comp_slug = matching[0]["slug"] if matching else comp_name.lower().replace(" ", "-")
            companies_html += f'<li><a href="/company/{comp_slug}/">{comp_name}</a> — {comp_jobs:,} jobs</li>'

        desc = f"AI workforce reductions in {c_data['country']}: {c_data['total_jobs']:,} jobs impacted across {len(c_data['companies'])} companies."

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{c_data["country"]} — AI Workforce Reductions | AI Layoff Tracker</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{c_data["country"]} — AI Workforce Reductions">
<meta property="og:description" content="{desc[:200]}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://ailayofftracker.com/country/{c_slug}/">
<link rel="canonical" href="https://ailayofftracker.com/country/{c_slug}/">
<link rel="stylesheet" href="/assets/css/main.css">
<link rel="stylesheet" href="/assets/css/timeline.css">
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="container">
    <a href="/" class="logo">AI<span class="logo-accent">LAYOFF</span>TRACKER</a>
    <nav role="navigation" aria-label="Main navigation"><a href="/methodology.html">Methodology</a><a href="/api/stats.json">API</a></nav>
  </div>
</header>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">← Back to tracker</a></nav>
  <h1>{c_data["country"]} — AI Workforce Reductions</h1>
  <div class="entry-stats">
    <div class="stat">
      <span class="stat-value">{c_data["total_jobs"]:,}</span>
      <span class="stat-label">Total Jobs Lost</span>
    </div>
    <div class="stat">
      <span class="stat-value">{len(c_data["companies"])}</span>
      <span class="stat-label">Companies</span>
    </div>
    <div class="stat">
      <span class="stat-value">{len(c_data["entries"])}</span>
      <span class="stat-label">Entries</span>
    </div>
  </div>
  <section aria-label="Industry breakdown">
    <h2>Industry Breakdown</h2>
    <ul class="industry-list">{industries_html}</ul>
  </section>
  <section aria-label="Companies in this country">
    <h2>Companies</h2>
    <ul class="company-list">{companies_html}</ul>
  </section>
  <section aria-label="API access">
    <h2>API</h2>
    <p><a href="/api/country/{c_slug}.json">/api/country/{c_slug}.json</a></p>
  </section>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="container">
    <p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p>
    <p><a href="/methodology.html">Methodology</a> · <a href="/api/entries.json">JSON API</a> · <a href="/api/entries.csv">Download CSV</a></p>
  </div>
</footer>
</body>
</html>'''
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

def generate_rss(data, stats):
    """Generate RSS feed."""
    entries = data["entries"][:30]
    items = []
    for e in entries:
        slug = e["slug"]
        items.append(f'''    <item>
      <title>{e["company"]}: {e["jobs_lost"]:,} Jobs Impacted</title>
      <link>https://ailayofftracker.com/company/{slug}/</link>
      <description>{e["summary"]}</description>
      <pubDate>{e["date"]}T00:00:00Z</pubDate>
      <guid isPermaLink="true">https://ailayofftracker.com/company/{slug}/</guid>
      <category>{e["classification"]}</category>
    </item>''')
    
    feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>AI Layoff Tracker</title>
  <link>https://ailayofftracker.com</link>
  <description>Tracking documented workforce reductions linked to artificial intelligence and automation.</description>
  <language>en-us</language>
  <lastBuildDate>{stats["last_updated"]}</lastBuildDate>
  <atom:link href="https://ailayofftracker.com/api/feed.xml" rel="self" type="application/rss+xml"/>
{"".join(items)}
</channel>
</rss>'''
    with open(PUBLIC_DIR / "api" / "feed.xml", "w") as f:
        f.write(feed)

def generate_sitemap(data):
    """Generate sitemap.xml."""
    urls = [
        "https://ailayofftracker.com/",
        "https://ailayofftracker.com/methodology.html",
    ]
    for e in data["entries"]:
        urls.append(f'https://ailayofftracker.com/company/{e["slug"]}/')
        urls.append(f'https://ailayofftracker.com/entry/{e["id"]}/')

    # Industry pages
    seen_industries = set()
    for e in data["entries"]:
        ind_slug = e["industry"].lower().replace(" ", "-").replace("&", "and")
        if ind_slug not in seen_industries:
            seen_industries.add(ind_slug)
            urls.append(f"https://ailayofftracker.com/industry/{ind_slug}/")

    # Country pages
    seen_countries = set()
    for e in data["entries"]:
        c_slug = e["country"].lower().replace(" ", "-")
        if c_slug not in seen_countries:
            seen_countries.add(c_slug)
            urls.append(f"https://ailayofftracker.com/country/{c_slug}/")
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f"  <url><loc>{url}</loc></url>\n"
    xml += "</urlset>"
    
    with open(PUBLIC_DIR / "sitemap.xml", "w") as f:
        f.write(xml)

def main():
    print("🔨 AI Layoff Tracker — Static Site Generator v2.0")
    print(f"   Root: {ROOT}")
    
    # Load data
    data = load_data()
    entries = data["entries"]
    print(f"   Loaded {len(entries)} entries")
    
    # Compute stats
    stats = compute_stats(data)
    print(f"   Total jobs lost: {stats['total_jobs_lost']:,}")
    print(f"   Companies: {stats['companies']} | Countries: {stats['countries']} | Industries: {stats['industries']}")
    
    # Generate API
    generate_api(data, stats)
    print("   ✅ API files generated")
    
    # Generate company pages
    generate_company_pages(data)
    print(f"   ✅ {len(entries)} company pages generated")

    # Generate individual entry pages
    generate_entry_pages(data)
    print(f"   ✅ {len(entries)} entry pages generated")

    # Generate industry pages
    generate_industry_pages(data)
    industry_count = len(set(e["industry"].lower().replace(" ", "-").replace("&", "and") for e in entries))
    print(f"   ✅ {industry_count} industry pages generated")

    # Generate country pages
    generate_country_pages(data)
    country_count = len(set(e["country"].lower().replace(" ", "-") for e in entries))
    print(f"   ✅ {country_count} country pages generated")
    
    # Generate RSS
    generate_rss(data, stats)
    print("   ✅ RSS feed generated")
    
    # Generate sitemap
    generate_sitemap(data)
    print("   ✅ Sitemap generated")
    
    # Update last_updated in data file
    data["meta"]["last_updated"] = stats["last_updated"]
    with open(DATA_DIR / "entries.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✨ Build complete! → {PUBLIC_DIR}")
    print(f"   Run: cd {PUBLIC_DIR} && python3 -m http.server 8080")

if __name__ == "__main__":
    main()
