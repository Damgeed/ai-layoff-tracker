# AI Layoff Tracker — Complete File Tree Report

**Generated:** 2026-06-13T14:32:00+08:00  
**Project Root:** `/Users/openclaw_007/projects/ai-layoff-tracker`  
**Total docs/ size:** 424K

---

## Git History (Last 3 Commits)

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| `0434a75` | Sat Jun 13 10:04:49 2026 +0800 | 25 <bud@ailayofftracker.com> | v2.1: Rebuild frontend — index.html, methodology.html, CSS (dark theme), 5 JS modules (search, filters, charts, share, app) |
| `888683a` | Sat Jun 13 09:24:18 2026 +0800 | 25 <bud@ailayofftracker.com> | Switch output to docs/ for GitHub Pages, add per-company/industry/country API |
| `4a2e002` | Sat Jun 13 08:30:50 2026 +0800 | 25 <bud@ailayofftracker.com> | v2.0: AI Layoff Tracker — full static site with 4-tier classification, per-company/industry/country API |

---

## File Tree with Line Counts

### Root

| File | Lines | Description |
|------|-------|-------------|
| `.gitignore` | — | Git ignore rules |

---

### Python Scripts (`scripts/`)

| File | Lines | Description |
|------|-------|-------------|
| `scripts/build.py` | **333** | Static site build script — generates HTML pages, API JSON/CSV/XML from data/entries.json |
| `scripts/statistics.py` | **41** | Computes aggregate statistics (totals by company, industry, country, tier) |
| `scripts/validation.py` | **164** | Validates entries.json schema, checks field consistency and data integrity |

**Python subtotal:** 538 lines

---

### Frontend — HTML (`docs/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/index.html` | **287** | Main landing page — timeline view, filters, search, stats dashboard |
| `docs/methodology.html` | **219** | Methodology page — explains 4-tier classification system and data sources |

#### Per-Company Pages (`docs/company/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/company/amazon/index.html` | 77 | Amazon company detail page |
| `docs/company/chegg/index.html` | 77 | Chegg company detail page |
| `docs/company/cisco/index.html` | 77 | Cisco company detail page |
| `docs/company/cvshealth/index.html` | 77 | CVS Health company detail page |
| `docs/company/dropbox/index.html` | 77 | Dropbox company detail page |
| `docs/company/duolingo/index.html` | 77 | Duolingo company detail page |
| `docs/company/google/index.html` | 77 | Google company detail page |
| `docs/company/ibm/index.html` | 77 | IBM company detail page |
| `docs/company/klarna/index.html` | 77 | Klarna company detail page |
| `docs/company/linkedin/index.html` | 77 | LinkedIn company detail page |
| `docs/company/meta/index.html` | 77 | Meta company detail page |
| `docs/company/paypal/index.html` | 77 | PayPal company detail page |
| `docs/company/sap/index.html` | 77 | SAP company detail page |
| `docs/company/stackoverflow/index.html` | 77 | Stack Overflow company detail page |
| `docs/company/ups/index.html` | 77 | UPS company detail page |

**HTML subtotal:** 287 + 219 + (15 × 77) = **1,661 lines**

---

### Frontend — CSS (`docs/assets/css/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/assets/css/main.css` | **675** | Primary stylesheet — dark theme, layout, typography, card components, responsive |
| `docs/assets/css/timeline.css` | **202** | Timeline-specific styles — event cards, tier badges, connectors |

**CSS subtotal:** 877 lines

---

### Frontend — JavaScript (`docs/assets/js/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/assets/js/app.js` | **609** | Main application logic — data loading, rendering, state management, event wiring |
| `docs/assets/js/charts.js` | **486** | Chart visualizations — bar charts, pie charts, trend lines using a charting library |
| `docs/assets/js/filters.js` | **180** | Filtering logic — company, industry, country, tier, date range filters |
| `docs/assets/js/search.js` | **117** | Full-text search across entry titles, descriptions, and company names |
| `docs/assets/js/share.js` | **171** | Share functionality — URL permalink generation, social sharing |

**JavaScript subtotal:** 1,563 lines

---

### Data & Configuration

#### Source Data (`data/`)

| File | Lines | Description |
|------|-------|-------------|
| `data/entries.json` | — | Primary data file — all layoff entries with company, date, tier, source URLs |

#### API Endpoints — Companies (`docs/api/company/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/api/company/amazon.json` | — | Amazon layoff data (API) |
| `docs/api/company/chegg.json` | — | Chegg layoff data (API) |
| `docs/api/company/cisco.json` | — | Cisco layoff data (API) |
| `docs/api/company/cvshealth.json` | — | CVS Health layoff data (API) |
| `docs/api/company/dropbox.json` | — | Dropbox layoff data (API) |
| `docs/api/company/duolingo.json` | — | Duolingo layoff data (API) |
| `docs/api/company/google.json` | — | Google layoff data (API) |
| `docs/api/company/ibm.json` | — | IBM layoff data (API) |
| `docs/api/company/klarna.json` | — | Klarna layoff data (API) |
| `docs/api/company/linkedin.json` | — | LinkedIn layoff data (API) |
| `docs/api/company/meta.json` | — | Meta layoff data (API) |
| `docs/api/company/paypal.json` | — | PayPal layoff data (API) |
| `docs/api/company/sap.json` | — | SAP layoff data (API) |
| `docs/api/company/stackoverflow.json` | — | Stack Overflow layoff data (API) |
| `docs/api/company/ups.json` | — | UPS layoff data (API) |

#### API Endpoints — Countries (`docs/api/country/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/api/country/germany.json` | — | Germany layoff data (API) |
| `docs/api/country/sweden.json` | — | Sweden layoff data (API) |
| `docs/api/country/united-states.json` | — | United States layoff data (API) |

#### API Endpoints — Industries (`docs/api/industry/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/api/industry/education-technology.json` | — | EdTech layoff data (API) |
| `docs/api/industry/enterprise-software.json` | — | Enterprise software layoff data (API) |
| `docs/api/industry/fintech.json` | — | Fintech layoff data (API) |
| `docs/api/industry/healthcare.json` | — | Healthcare layoff data (API) |
| `docs/api/industry/logistics.json` | — | Logistics layoff data (API) |
| `docs/api/industry/technology.json` | — | Technology layoff data (API) |

#### API Endpoints — Top-Level (`docs/api/`)

| File | Lines | Description |
|------|-------|-------------|
| `docs/api/entries.json` | — | Full dataset as JSON API |
| `docs/api/entries.csv` | — | Full dataset as CSV export |
| `docs/api/feed.xml` | — | RSS/Atom feed of entries |
| `docs/api/stats.json` | — | Aggregate statistics API |
| `docs/sitemap.xml` | — | Sitemap for search engines |

---

## Summary

| Category | Files | Lines |
|----------|-------|-------|
| Python scripts | 3 | 538 |
| HTML pages | 17 | 1,661 |
| CSS stylesheets | 2 | 877 |
| JavaScript modules | 5 | 1,563 |
| JSON data (API) | 25 | — |
| CSV data | 1 | — |
| XML (feed + sitemap) | 2 | — |
| Config / other | 1 | — |
| **Total (tracked code)** | **30** | **4,639** |
| **Total (all tracked files)** | **56** | — |

### Language Breakdown

| Language | Lines | % of Code |
|----------|-------|-----------|
| HTML | 1,661 | 35.8% |
| JavaScript | 1,563 | 33.7% |
| CSS | 877 | 18.9% |
| Python | 538 | 11.6% |
| **Total** | **4,639** | **100%** |

### Directory Size

| Directory | Size |
|-----------|------|
| `docs/` (entire static site) | 424K |
