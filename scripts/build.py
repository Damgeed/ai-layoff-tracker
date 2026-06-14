#!/usr/bin/env python3
"""
AI Layoff Tracker — Static Site Generator v3.0
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

def generate_company_pages(data, stats):
    """Generate company hub pages at /company/{slug}/index.html for SEO. NOT linked in nav."""
    entries = data["entries"]
    company_dir = PUBLIC_DIR / "company"
    os.makedirs(company_dir, exist_ok=True)

    # Group by company slug
    by_company = {}
    for e in entries:
        slug = e["slug"]
        if slug not in by_company:
            by_company[slug] = {"company": e["company"], "entries": [], "total_jobs": 0,
                                "countries": set(), "industries": set(),
                                "classifications": set(), "oldest_date": e["date"], "newest_date": e["date"]}
        c = by_company[slug]
        c["entries"].append(e)
        c["total_jobs"] += e["jobs_lost"]
        c["countries"].add(e["country"])
        c["industries"].add(e["industry"])
        c["classifications"].add(e["classification"])
        if e["date"] < c["oldest_date"]:
            c["oldest_date"] = e["date"]
        if e["date"] > c["newest_date"]:
            c["newest_date"] = e["date"]

    for slug, cdata in by_company.items():
        page_dir = company_dir / slug
        os.makedirs(page_dir, exist_ok=True)
        sorted_entries = sorted(cdata["entries"], key=lambda x: x["date"], reverse=True)

        # Timeline HTML
        timeline_items = ""
        for e in sorted_entries:
            classification_label = data["classifications"].get(e["classification"], {}).get("label", e["classification"])
            timeline_items += f'''<li><a href="entry/{e['id']}/"><strong>{e['date']}</strong> — {e['jobs_lost']:,} jobs</a> <span class="badge">{classification_label}</span></li>\n'''

        # Evidence summary
        evidence_sources = set()
        for e in sorted_entries:
            for ev in e.get("evidence", []):
                evidence_sources.add(ev["description"][:120])
        evidence_html = "".join(f"<li>{src}</li>" for src in list(evidence_sources)[:5])

        # Schema.org JSON-LD
        jsonld = {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": f"AI Layoff Data: {cdata['company']}",
            "description": f"Documented workforce reductions at {cdata['company']} linked to AI. {cdata['total_jobs']:,} jobs across {len(sorted_entries)} events.",
            "url": f"https://ailayofftracker.com/company/{slug}/",
            "temporalCoverage": f"{cdata['oldest_date']}/{cdata['newest_date']}",
            "creator": {"@type": "Organization", "name": "AI Layoff Tracker"},
            "keywords": [cdata["company"]] + list(cdata["industries"]) + list(cdata["classifications"]),
        }

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
  <base href="/ai-layoff-tracker/">
  <script>
    (function(){{var t=localStorage.getItem('ai-layoff-tracker-theme');document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');}})();
  </script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{cdata["company"]}: {cdata["total_jobs"]:,} Jobs Impacted by AI | AI Layoff Tracker</title>
<meta name="description" content="AI-related workforce reductions at {cdata["company"]}. {cdata["total_jobs"]:,} jobs documented across {len(sorted_entries)} events. Industries: {", ".join(sorted(cdata["industries"]))}.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://ailayofftracker.com/company/{slug}/">
<meta property="og:title" content="{cdata["company"]}: {cdata["total_jobs"]:,} Jobs Impacted by AI">
<meta property="og:description" content="AI-related workforce reductions at {cdata["company"]}. {cdata["total_jobs"]:,} jobs across {len(sorted_entries)} events.">
<meta property="og:type" content="article">
<meta property="og:url" content="https://ailayofftracker.com/company/{slug}/">
<meta property="og:site_name" content="AI Layoff Tracker">
<link rel="stylesheet" href="assets/css/main.css">
<link rel="stylesheet" href="assets/css/timeline.css">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False)}
</script>
</head>
<body>
<div class="bg-mesh" aria-hidden="true"></div>
<div class="bg-grid" aria-hidden="true"></div>
<div class="particles" aria-hidden="true">
  <div class="particle"></div><div class="particle"></div>
  <div class="particle"></div><div class="particle"></div><div class="particle"></div>
</div>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="container">
    <a href="./" class="logo" aria-label="AI Layoff Tracker home"><span class="logo-dot"></span>AI Layoff Tracker</a>
    <nav aria-label="Main navigation">
      <a href="methodology.html">Methodology</a>
      <a href="data-dictionary.html">Data Dictionary</a>
      <a href="changelog.html">Changelog</a>
      <a href="corrections.html">Corrections</a>
      <a href="evidence/">Evidence</a>
      <a href="api/">API</a>
    </nav>
    <div class="header-actions">
      <button class="theme-toggle" aria-label="Toggle dark/light theme" title="Toggle theme">
        <span class="icon-sun">☀️</span><span class="icon-moon">🌙</span>
      </button>
      <button class="hamburger" aria-label="Open navigation menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>
<div class="mobile-nav" role="dialog" aria-label="Navigation menu" aria-hidden="true">
  <div class="mobile-nav-backdrop"></div>
  <div class="mobile-nav-panel">
    <nav class="mobile-nav-links">
      <a href="methodology.html">Methodology</a>
      <a href="data-dictionary.html">Data Dictionary</a>
      <a href="changelog.html">Changelog</a>
      <a href="corrections.html">Corrections</a>
      <a href="evidence/">Evidence</a>
      <a href="api/">API</a>
    </nav>
  </div>
</div>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="./">← Back to tracker</a></nav>
  <article>
    <header>
      <h1>{cdata["company"]}</h1>
      <p class="lead">AI-related workforce reductions: <strong>{cdata["total_jobs"]:,} jobs</strong> documented across <strong>{len(sorted_entries)} events</strong>.</p>
    </header>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-value">{cdata["total_jobs"]:,}</div><div class="stat-label">Total Jobs Lost</div></div>
      <div class="stat-card"><div class="stat-value">{len(sorted_entries)}</div><div class="stat-label">Events</div></div>
      <div class="stat-card"><div class="stat-value">{cdata["oldest_date"]}</div><div class="stat-label">First Event</div></div>
      <div class="stat-card"><div class="stat-value">{cdata["newest_date"]}</div><div class="stat-label">Latest Event</div></div>
    </div>
    <div class="entry-meta">
      <span>🏭 {", ".join(sorted(cdata["industries"]))}</span>
      <span>📍 {", ".join(sorted(cdata["countries"]))}</span>
    </div>
    <h2>Layoff Timeline</h2>
    <ul class="timeline-list">{timeline_items}</ul>
    <h2>Evidence Summary</h2>
    <ul>{evidence_html}</ul>
    <p><a href="api/company/{slug}.json">📡 View raw JSON API endpoint</a></p>
  </article>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="container">
    <div class="footer-info">
      <p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p>
    </div>
    <div class="footer-links">
      <div class="footer-col">
        <h4>Data</h4>
        <a href="methodology.html">Methodology</a>
        <a href="api/">JSON API</a>
        <a href="api/entries.csv">Download CSV</a>
        <a href="api/feed.xml">RSS Feed</a>
      </div>
      <div class="footer-col">
        <h4>Resources</h4>
        <a href="press/">Press Kit</a>
        <a href="research/">Research</a>
        <a href="citation-guide/">Citation Guide</a>
        <a href="versions/">Versions</a>
        <a href="history/">Entry History</a>
      </div>
    </div>
  </div>
  <div class="footer-bottom">
    <div class="container">
      <small>Dataset last updated: <span id="footer-updated">—</span>. This project is a public research resource. All data is sourced from public statements, earnings reports, and verified media coverage.</small>
    </div>
  </div>
</footer>
<script src="assets/js/theme.js" defer></script>
<script src="assets/js/mobile-nav.js" defer></script>
</body>
</html>'''
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

    print(f"   ✅ {len(by_company)} company pages generated")

def generate_report_pages(data, stats):
    """Generate programmatic research pages for SEO: /reports/2024/, /reports/fintech/, etc."""
    entries = data["entries"]
    reports_dir = PUBLIC_DIR / "reports"
    os.makedirs(reports_dir, exist_ok=True)

    # Index page
    report_index_html = _make_report_index(stats)
    with open(reports_dir / "index.html", "w") as f:
        f.write(report_index_html)

    # Year reports
    by_year = {}
    for e in entries:
        year = e["date"][:4]
        if year not in by_year:
            by_year[year] = {"entries": [], "total_jobs": 0, "companies": set(), "industries": set(), "countries": set()}
        by_year[year]["entries"].append(e)
        by_year[year]["total_jobs"] += e["jobs_lost"]
        by_year[year]["companies"].add(e["company"])
        by_year[year]["industries"].add(e["industry"])
        by_year[year]["countries"].add(e["country"])

    for year, ydata in by_year.items():
        page_dir = reports_dir / year
        os.makedirs(page_dir, exist_ok=True)
        html = _make_report_page(f"AI Job Displacement in {year}", year, ydata, data, stats,
                                  f"{ydata['total_jobs']:,} jobs documented across {len(ydata['companies'])} companies")
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

    # Industry reports
    by_industry = {}
    for e in entries:
        ind = e["industry"]
        if ind not in by_industry:
            by_industry[ind] = {"entries": [], "total_jobs": 0, "companies": set(), "countries": set()}
        by_industry[ind]["entries"].append(e)
        by_industry[ind]["total_jobs"] += e["jobs_lost"]
        by_industry[ind]["companies"].add(e["company"])
        by_industry[ind]["countries"].add(e["country"])

    for ind, idata in by_industry.items():
        slug = ind.lower().replace(" ", "-").replace("&", "and")
        page_dir = reports_dir / slug
        os.makedirs(page_dir, exist_ok=True)
        html = _make_report_page(f"AI Job Displacement in {ind}", ind, idata, data, stats,
                                  f"{idata['total_jobs']:,} jobs documented across {len(idata['companies'])} companies")
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

    # Country reports
    by_country = {}
    for e in entries:
        c = e["country"]
        if c not in by_country:
            by_country[c] = {"entries": [], "total_jobs": 0, "companies": set(), "industries": set()}
        by_country[c]["entries"].append(e)
        by_country[c]["total_jobs"] += e["jobs_lost"]
        by_country[c]["companies"].add(e["company"])
        by_country[c]["industries"].add(e["industry"])

    for country, cdata in by_country.items():
        slug = country.lower().replace(" ", "-")
        page_dir = reports_dir / slug
        os.makedirs(page_dir, exist_ok=True)
        html = _make_report_page(f"AI Job Displacement in {country}", country, cdata, data, stats,
                                  f"{cdata['total_jobs']:,} jobs documented across {len(cdata['companies'])} companies")
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

    # Classification reports
    for cls_key, cls_info in data["classifications"].items():
        slug = cls_key.lower().replace("_", "-")
        cls_entries = [e for e in entries if e["classification"] == cls_key]
        if not cls_entries:
            continue
        page_dir = reports_dir / slug
        os.makedirs(page_dir, exist_ok=True)
        cdata = {"entries": cls_entries, "total_jobs": sum(e["jobs_lost"] for e in cls_entries),
                 "companies": set(e["company"] for e in cls_entries),
                 "industries": set(e["industry"] for e in cls_entries),
                 "countries": set(e["country"] for e in cls_entries)}
        html = _make_report_page(cls_info["label"], cls_key, cdata, data, stats,
                                  f"{cdata['total_jobs']:,} jobs classified as {cls_info['label']}")
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

    print(f"   ✅ {len(by_year) + len(by_industry) + len(by_country) + len(data['classifications']) + 1} report pages generated")

def _make_report_index(stats):
    """Generate /reports/index.html."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
  <base href="/ai-layoff-tracker/">
  <script>(function(){{var t=localStorage.getItem('ai-layoff-tracker-theme');document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');}})();</script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Research Reports — AI Layoff Tracker</title>
<meta name="description" content="Research reports and analysis on AI-related workforce reductions. Automated reports by year, industry, country, and classification tier.">
<link rel="canonical" href="https://ailayofftracker.com/reports/">
<link rel="stylesheet" href="assets/css/main.css">
<link rel="stylesheet" href="assets/css/timeline.css">
</head>
<body>
<div class="bg-mesh" aria-hidden="true"></div><div class="bg-grid" aria-hidden="true"></div>
<div class="particles" aria-hidden="true"><div class="particle"></div><div class="particle"></div><div class="particle"></div><div class="particle"></div><div class="particle"></div></div>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="container">
    <a href="./" class="logo" aria-label="AI Layoff Tracker home"><span class="logo-dot"></span>AI Layoff Tracker</a>
    <nav aria-label="Main navigation">
      <a href="methodology.html">Methodology</a>
      <a href="data-dictionary.html">Data Dictionary</a>
      <a href="changelog.html">Changelog</a>
      <a href="corrections.html">Corrections</a>
      <a href="evidence/">Evidence</a>
      <a href="api/">API</a>
    </nav>
    <div class="header-actions">
      <button class="theme-toggle" aria-label="Toggle dark/light theme"><span class="icon-sun">☀️</span><span class="icon-moon">🌙</span></button>
      <button class="hamburger" aria-label="Open navigation menu" aria-expanded="false"><span></span><span></span><span></span></button>
    </div>
  </div>
</header>
<div class="mobile-nav" role="dialog" aria-label="Navigation menu" aria-hidden="true">
  <div class="mobile-nav-backdrop"></div><div class="mobile-nav-panel"><nav class="mobile-nav-links"><a href="methodology.html">Methodology</a><a href="data-dictionary.html">Data Dictionary</a><a href="changelog.html">Changelog</a><a href="corrections.html">Corrections</a><a href="evidence/">Evidence</a><a href="api/">API</a></nav></div>
</div>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="./">← Back to tracker</a></nav>
  <h1>Research Reports</h1>
  <p class="lead">Automated research reports generated from the AI Layoff Tracker dataset. These are programmatic pages built from the live data — updated with every rebuild.</p>
  <h2>By Year</h2>
  <ul><li><a href="reports/2023/">2023 Report</a></li><li><a href="reports/2024/">2024 Report</a></li></ul>
  <h2>By Industry</h2>
  <ul id="industry-reports"><li>Loading…</li></ul>
  <h2>By Country</h2>
  <ul id="country-reports"><li>Loading…</li></ul>
  <h2>By Classification</h2>
  <ul id="classification-reports"><li>Loading…</li></ul>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="container"><div class="footer-info"><p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p></div><div class="footer-links"><div class="footer-col"><h4>Data</h4><a href="methodology.html">Methodology</a><a href="api/">JSON API</a><a href="api/entries.csv">Download CSV</a><a href="api/feed.xml">RSS Feed</a></div><div class="footer-col"><h4>Resources</h4><a href="press/">Press Kit</a><a href="research/">Research</a><a href="citation-guide/">Citation Guide</a><a href="versions/">Versions</a><a href="history/">Entry History</a></div></div></div>
  <div class="footer-bottom"><div class="container"><small>Dataset last updated: <span id="footer-updated">—</span>. This project is a public research resource.</small></div></div>
</footer>
<script src="assets/js/theme.js" defer></script>
<script src="assets/js/mobile-nav.js" defer></script>
<script>
fetch('api/stats.json').then(r=>r.json()).then(s=>{{
  document.getElementById('industry-reports').innerHTML=Object.keys(s.by_industry).map(i=>'<li><a href="reports/'+i.toLowerCase().replace(/ /g,'-').replace(/&/g,'and')+'/">'+i+' ('+s.by_industry[i].entries.toLocaleString()+' entries)</a></li>').join('');
  document.getElementById('country-reports').innerHTML=Object.keys(s.by_country).map(c=>'<li><a href="reports/'+c.toLowerCase().replace(/ /g,'-')+'/">'+c+' ('+s.by_country[c].entries.toLocaleString()+' entries)</a></li>').join('');
  fetch('api/entries.json').then(r=>r.json()).then(d=>{{
    var cls={{}}; d.entries.forEach(e=>{{cls[e.classification]=(cls[e.classification]||0)+1;}});
    var labels={{}}; Object.keys(d.classifications||{{}}).forEach(k=>{{labels[k]=d.classifications[k].label;}});
    document.getElementById('classification-reports').innerHTML=Object.keys(cls).map(k=>'<li><a href="reports/'+k.toLowerCase().replace(/_/g,'-')+'/">'+(labels[k]||k)+' ('+cls[k]+' entries)</a></li>').join('');
  }});
}});
</script>
</body>
</html>'''

def _make_report_page(title, key, rdata, data, stats, description):
    """Generate a single report page."""
    entries_sorted = sorted(rdata["entries"], key=lambda x: x["date"], reverse=True)
    timeline = "".join(f'<li><strong>{e["date"]}</strong> — {e["company"]}: {e["jobs_lost"]:,} jobs</li>' for e in entries_sorted[:50])

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": title,
        "description": description,
        "url": f"https://ailayofftracker.com/reports/{key.lower().replace(' ','-').replace('_','-').replace('&','and')}/",
        "creator": {"@type": "Organization", "name": "AI Layoff Tracker"},
    }

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
  <base href="/ai-layoff-tracker/">
  <script>(function(){{var t=localStorage.getItem('ai-layoff-tracker-theme');document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');}})();</script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | AI Layoff Tracker</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://ailayofftracker.com/reports/{key.lower().replace(' ','-').replace('_','-').replace('&','and')}/">
<link rel="stylesheet" href="assets/css/main.css">
<link rel="stylesheet" href="assets/css/timeline.css">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<div class="bg-mesh" aria-hidden="true"></div><div class="bg-grid" aria-hidden="true"></div>
<div class="particles" aria-hidden="true"><div class="particle"></div><div class="particle"></div><div class="particle"></div><div class="particle"></div><div class="particle"></div></div>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="container">
    <a href="./" class="logo" aria-label="AI Layoff Tracker home"><span class="logo-dot"></span>AI Layoff Tracker</a>
    <nav aria-label="Main navigation">
      <a href="methodology.html">Methodology</a><a href="data-dictionary.html">Data Dictionary</a><a href="changelog.html">Changelog</a><a href="corrections.html">Corrections</a><a href="evidence/">Evidence</a><a href="api/">API</a>
    </nav>
    <div class="header-actions">
      <button class="theme-toggle" aria-label="Toggle dark/light theme"><span class="icon-sun">☀️</span><span class="icon-moon">🌙</span></button>
      <button class="hamburger" aria-label="Open navigation menu" aria-expanded="false"><span></span><span></span><span></span></button>
    </div>
  </div>
</header>
<div class="mobile-nav" role="dialog" aria-label="Navigation menu" aria-hidden="true">
  <div class="mobile-nav-backdrop"></div><div class="mobile-nav-panel"><nav class="mobile-nav-links"><a href="methodology.html">Methodology</a><a href="data-dictionary.html">Data Dictionary</a><a href="changelog.html">Changelog</a><a href="corrections.html">Corrections</a><a href="evidence/">Evidence</a><a href="api/">API</a></nav></div>
</div>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="reports/">← All Reports</a> · <a href="./">← Tracker Home</a></nav>
  <h1>{title}</h1>
  <p class="lead">{description}</p>
  <div class="stats-grid">
    <div class="stat-card"><div class="stat-value">{rdata["total_jobs"]:,}</div><div class="stat-label">Total Jobs</div></div>
    <div class="stat-card"><div class="stat-value">{len(rdata["entries"])}</div><div class="stat-label">Events</div></div>
    <div class="stat-card"><div class="stat-value">{len(rdata["companies"])}</div><div class="stat-label">Companies</div></div>
    <div class="stat-card"><div class="stat-value">{len(rdata.get("industries", rdata.get("countries", [])))}</div><div class="stat-label">{("Industries" if "industries" in rdata else "Countries") if "countries" in rdata else "Sectors"}</div></div>
  </div>
  <h2>Timeline</h2>
  <ul class="timeline-list">{timeline}</ul>
  <p><a href="api/entries.csv">📥 Download full dataset (CSV)</a> · <a href="api/entries.json">📡 View JSON API</a></p>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="container"><div class="footer-info"><p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p></div><div class="footer-links"><div class="footer-col"><h4>Data</h4><a href="methodology.html">Methodology</a><a href="api/">JSON API</a><a href="api/entries.csv">Download CSV</a><a href="api/feed.xml">RSS Feed</a></div><div class="footer-col"><h4>Resources</h4><a href="press/">Press Kit</a><a href="research/">Research</a><a href="citation-guide/">Citation Guide</a><a href="versions/">Versions</a><a href="history/">Entry History</a></div></div></div>
  <div class="footer-bottom"><div class="container"><small>Dataset last updated: <span id="footer-updated">—</span>. This project is a public research resource.</small></div></div>
</footer>
<script src="assets/js/theme.js" defer></script>
<script src="assets/js/mobile-nav.js" defer></script>
</body>
</html>'''

def generate_entry_pages(data):
    """Generate individual entry pages at /entry/{id}/index.html using v3.0 CSS."""
    entry_dir = PUBLIC_DIR / "entry"
    entries = data["entries"]

    # Classification → v3.0 tier mapping
    CLASSIFICATION_TIER = {
        "DIRECT_AI_REPLACEMENT": "tier1",
        "AI_DRIVEN_RESTRUCTURING": "tier2",
        "AI_REALLOCATION": "tier3",
        "MARKET_DISRUPTION": "tier4",
    }
    TIER_LABELS = {
        "tier1": "Direct AI Replacement",
        "tier2": "AI-Driven Restructuring",
        "tier3": "AI Reallocation",
        "tier4": "Market Disruption",
    }

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
        tier = CLASSIFICATION_TIER.get(entry["classification"], "tier4")
        tier_label = class_info.get("label", TIER_LABELS.get(tier, entry["classification"]))

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
        source_html = f'<li><a href="{source_obj.get("url", "#")}" target="_blank" rel="noopener" class="entry-source">{source_obj.get("title", "Source")} <small>({source_obj.get("publisher", "Unknown")})</small></a></li>'
        archive_html = ""
        if source_obj.get("archive_url"):
            archive_html = f'<li>📦 <a href="{source_obj["archive_url"]}" target="_blank" rel="noopener" class="entry-source">Archived Source <small>(archive.org)</small></a></li>'

        # Timeline: Other entries from same company
        company_entries = sorted(by_company.get(entry["company"], []), key=lambda x: x["date"], reverse=True)
        company_timeline = ""
        for ce in company_entries:
            if ce["id"] != eid:
                company_timeline += f'<li><a href="entry/{ce["id"]}/">{ce["date"]} — {ce["jobs_lost"]:,} jobs</a></li>'
        company_timeline_html = f'<ul class="timeline-list">{company_timeline}</ul>' if company_timeline else "<p>No other entries for this company.</p>"

        # Timeline: Other entries from same industry
        industry_entries = sorted(by_industry.get(entry["industry"], []), key=lambda x: x["date"], reverse=True)
        industry_timeline = ""
        for ie in industry_entries:
            if ie["id"] != eid:
                industry_timeline += f'<li><a href="entry/{ie["id"]}/">{ie["date"]} — {ie["company"]}: {ie["jobs_lost"]:,} jobs</a></li>'
        industry_timeline_html = f'<ul class="timeline-list">{industry_timeline}</ul>' if industry_timeline else "<p>No other entries for this industry.</p>"

        # Confidence dot class
        conf = entry["confidence_score"]
        if conf >= 80:
            conf_class = "high"
        elif conf >= 60:
            conf_class = "medium"
        else:
            conf_class = "low"

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
  <base href="/ai-layoff-tracker/">
  <!-- Inline theme script BEFORE CSS to prevent flash of wrong theme -->
  <script>
    (function(){{
      var t=localStorage.getItem('ai-layoff-tracker-theme');
      document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');
    }})();
  </script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{entry["company"]}: {entry["jobs_lost"]:,} Jobs Impacted | AI Layoff Tracker</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{entry["company"]}: {entry["jobs_lost"]:,} Jobs Impacted by AI">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://ailayofftracker.com/entry/{eid}/">
<meta property="og:site_name" content="AI Layoff Tracker">
<link rel="canonical" href="https://ailayofftracker.com/entry/{eid}/">
<link rel="stylesheet" href="assets/css/main.css">
<link rel="stylesheet" href="assets/css/timeline.css">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False)}
</script>
</head>
<body>

<!-- Animated Background -->
<div class="bg-mesh" aria-hidden="true"></div>
<div class="bg-grid" aria-hidden="true"></div>
<div class="particles" aria-hidden="true">
  <div class="particle"></div><div class="particle"></div>
  <div class="particle"></div><div class="particle"></div><div class="particle"></div>
</div>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="container">
    <a href="./" class="logo" aria-label="AI Layoff Tracker home"><span class="logo-dot"></span>AI Layoff Tracker</a>
    <nav aria-label="Main navigation">
      <a href="methodology.html">Methodology</a>
      <a href="data-dictionary.html">Data Dictionary</a>
      <a href="changelog.html">Changelog</a>
      <a href="corrections.html">Corrections</a>
      <a href="evidence/">Evidence</a>
      <a href="api/">API</a>
    </nav>
    <div class="header-actions">
      <button class="theme-toggle" aria-label="Toggle dark/light theme" title="Toggle theme">
        <span class="icon-sun">☀️</span>
        <span class="icon-moon">🌙</span>
      </button>
      <button class="hamburger" aria-label="Open navigation menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>
<!-- Mobile Navigation Drawer -->
<div class="mobile-nav" role="dialog" aria-label="Navigation menu" aria-hidden="true">
  <div class="mobile-nav-backdrop"></div>
  <div class="mobile-nav-panel">
    <nav class="mobile-nav-links">
      <a href="methodology.html">Methodology</a>
      <a href="data-dictionary.html">Data Dictionary</a>
      <a href="changelog.html">Changelog</a>
      <a href="corrections.html">Corrections</a>
      <a href="evidence/">Evidence</a>
      <a href="api/">API</a>
    </nav>
  </div>
</div>
<main class="container" id="main-content" role="main">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="./">← Back to tracker</a> · <a href="company/{entry["slug"]}/">← {entry["company"]} page</a></nav>
  <article class="entry-detail">
    <header class="entry-header">
      <span class="class-badge {tier}"><span class="badge-dot {tier}"></span>{tier_label}</span>
      <h1>{entry["company"]}: {entry["jobs_lost"]:,} Jobs Impacted</h1>
    </header>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{entry["jobs_lost"]:,}</div>
        <div class="stat-label">Jobs Lost</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{entry["impact_percent"]}%</div>
        <div class="stat-label">of Workforce</div>
      </div>
      <div class="stat-card">
        <div class="stat-value"><span class="confidence-dot {conf_class}"></span>{conf}/100</div>
        <div class="stat-label">Confidence</div>
      </div>
    </div>
    <div class="entry-meta">
      <span>📅 {entry["date"]}</span>
      <span>📍 {entry["country"]}</span>
      <span>🏭 {entry["industry"]}</span>
    </div>
    <div class="entry-body">
      <p class="entry-summary">{entry["summary"]}</p>
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
    <div class="footer-info">
      <p>AI Layoff Tracker — Tracking documented workforce reductions linked to AI and automation.</p>
    </div>
    <div class="footer-links">
      <div class="footer-col">
        <h4>Data</h4>
        <a href="methodology.html">Methodology</a>
        <a href="api/">JSON API</a>
        <a href="api/entries.csv">Download CSV</a>
        <a href="api/feed.xml">RSS Feed</a>
      </div>
      <div class="footer-col">
        <h4>Resources</h4>
        <a href="press/">Press Kit</a>
        <a href="research/">Research</a>
        <a href="citation-guide/">Citation Guide</a>
        <a href="versions/">Versions</a>
        <a href="history/">Entry History</a>
      </div>
    </div>
  </div>
  <div class="footer-bottom">
    <div class="container">
      <small>Dataset last updated: <span id="footer-updated">—</span>. This project is a public research resource. All data is sourced from public statements, earnings reports, and verified media coverage.</small>
    </div>
  </div>
</footer>
<script src="assets/js/theme.js" defer></script>
<script src="assets/js/mobile-nav.js" defer></script>
</body>
</html>'''
        with open(page_dir / "index.html", "w") as f:
            f.write(html)

def generate_rss(data, stats):
    """Generate RSS feed with ALL entries, full metadata."""
    entries = sorted(data["entries"], key=lambda x: x["date"], reverse=True)
    items = []
    for e in entries:
        eid = e["id"]
        slug = e["slug"]
        classification_label = data["classifications"].get(e["classification"], {}).get("label", e["classification"])
        evidence_summary = "; ".join(ev.get("description", "")[:80] for ev in e.get("evidence", [])[:2])
        source_url = e.get("source", {}).get("url", "")
        items.append(f'''    <item>
      <title>{e["company"]}: {e["jobs_lost"]:,} Jobs Impacted ({classification_label})</title>
      <link>https://ailayofftracker.com/entry/{eid}/</link>
      <description>&lt;![CDATA[
        &lt;p&gt;{e["summary"][:300]}&lt;/p&gt;
        &lt;ul&gt;
          &lt;li&gt;&lt;strong&gt;Jobs Lost:&lt;/strong&gt; {e["jobs_lost"]:,}&lt;/li&gt;
          &lt;li&gt;&lt;strong&gt;Impact:&lt;/strong&gt; {e["impact_percent"]}% of workforce&lt;/li&gt;
          &lt;li&gt;&lt;strong&gt;Classification:&lt;/strong&gt; {classification_label}&lt;/li&gt;
          &lt;li&gt;&lt;strong&gt;Confidence:&lt;/strong&gt; {e["confidence_score"]}/100&lt;/li&gt;
          &lt;li&gt;&lt;strong&gt;Country:&lt;/strong&gt; {e["country"]}&lt;/li&gt;
          &lt;li&gt;&lt;strong&gt;Industry:&lt;/strong&gt; {e["industry"]}&lt;/li&gt;
          &lt;li&gt;&lt;strong&gt;Evidence:&lt;/strong&gt; {evidence_summary}&lt;/li&gt;
        &lt;/ul&gt;
        {'&lt;p&gt;&lt;a href="' + source_url + '"&gt;Original Source&lt;/a&gt;&lt;/p&gt;' if source_url else ''}
      ]]></description>
      <pubDate>{e["date"]}T00:00:00Z</pubDate>
      <guid isPermaLink="true">https://ailayofftracker.com/entry/{eid}/</guid>
      <category>{classification_label}</category>
      <category>{e["country"]}</category>
      <category>{e["industry"]}</category>
      <source url="https://ailayofftracker.com/api/feed.xml">AI Layoff Tracker</source>
    </item>''')
    
    feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
  <title>AI Layoff Tracker</title>
  <link>https://ailayofftracker.com</link>
  <description>Tracking documented workforce reductions linked to artificial intelligence and automation. {stats["total_jobs_lost"]:,} jobs across {stats["companies"]} companies. Updated with every new verified entry.</description>
  <language>en-us</language>
  <lastBuildDate>{stats["last_updated"]}</lastBuildDate>
  <atom:link href="https://ailayofftracker.com/api/feed.xml" rel="self" type="application/rss+xml"/>
  <docs>https://ailayofftracker.com/api/</docs>
  <webMaster>ailayofftracker.com (AI Layoff Tracker)</webMaster>
  <ttl>1440</ttl>
{"".join(items)}
</channel>
</rss>'''
    with open(PUBLIC_DIR / "api" / "feed.xml", "w") as f:
        f.write(feed)

def generate_sitemap(data, stats):
    """Generate sitemap.xml with all pages including company and report URLs."""
    urls = [
        "https://ailayofftracker.com/",
        "https://ailayofftracker.com/methodology.html",
        "https://ailayofftracker.com/data-dictionary.html",
        "https://ailayofftracker.com/changelog.html",
        "https://ailayofftracker.com/corrections.html",
        "https://ailayofftracker.com/api/",
        "https://ailayofftracker.com/evidence/",
        "https://ailayofftracker.com/citation-guide/",
        "https://ailayofftracker.com/disputed/",
        "https://ailayofftracker.com/history/",
        "https://ailayofftracker.com/pending-review/",
        "https://ailayofftracker.com/press/",
        "https://ailayofftracker.com/research/",
        "https://ailayofftracker.com/versions/",
        "https://ailayofftracker.com/reports/",
    ]
    
    # Entry pages
    for e in data["entries"]:
        urls.append(f'https://ailayofftracker.com/entry/{e["id"]}/')
    
    # Company pages (for SEO)
    company_slugs = sorted(set(e["slug"] for e in data["entries"]))
    for slug in company_slugs:
        urls.append(f'https://ailayofftracker.com/company/{slug}/')
    
    # Report pages
    reports_dir = PUBLIC_DIR / "reports"
    if reports_dir.exists():
        for d in reports_dir.iterdir():
            if d.is_dir():
                urls.append(f'https://ailayofftracker.com/reports/{d.name}/')
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in sorted(set(urls)):
        xml += f"  <url><loc>{url}</loc></url>\n"
    xml += "</urlset>"
    
    with open(PUBLIC_DIR / "sitemap.xml", "w") as f:
        f.write(xml)

def main():
    print("🔨 AI Layoff Tracker — Static Site Generator v3.1")
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
    
    # Generate company pages (SEO, not nav-linked)
    generate_company_pages(data, stats)
    
    # Generate report pages (programmatic SEO)
    generate_report_pages(data, stats)
    
    # Generate individual entry pages
    generate_entry_pages(data)
    print(f"   ✅ {len(entries)} entry pages generated")
    
    # Generate RSS
    generate_rss(data, stats)
    print("   ✅ RSS feed generated")
    
    # Generate sitemap
    generate_sitemap(data, stats)
    print("   ✅ Sitemap generated")
    
    # Update last_updated in data file
    data["meta"]["last_updated"] = stats["last_updated"]
    data["meta"]["version"] = "3.1.0"
    with open(DATA_DIR / "entries.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✨ Build complete! → {PUBLIC_DIR}")
    print(f"   Run: cd {PUBLIC_DIR} && python3 -m http.server 8080")

if __name__ == "__main__":
    main()
