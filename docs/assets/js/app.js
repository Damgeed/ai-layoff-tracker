/* ==========================================================================
   AI Layoff Tracker — Core App v2.1
   Fetches /api/entries.json + /api/stats.json, orchestrates all modules.
   No framework. No deps. Progressive enhancement.
   ========================================================================== */

(function () {
  'use strict';

  // --- State ------------------------------------------------------------
  const state = {
    entries: [],
    stats: null,
    filtered: [],
    filters: {
      classification: [],
      country: '',
      industry: '',
      dateFrom: '',
      dateTo: '',
      minJobs: '',
      search: ''
    },
    sort: 'newest',
    loading: true
  };

  // --- DOM refs (lazy) ---------------------------------------------------
  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  // --- Init --------------------------------------------------------------
  async function init() {
    showSkeletons();
    try {
      const [entriesRes, statsRes] = await Promise.all([
        fetch('/api/entries.json'),
        fetch('/api/stats.json')
      ]);
      if (!entriesRes.ok || !statsRes.ok) throw new Error('API fetch failed');
      const entriesData = await entriesRes.json();
      state.entries = entriesData.entries || entriesData;
      state.stats = await statsRes.json();
      state.filtered = [...state.entries];
      hideSkeletons();
      renderAll();
      initEventListeners();
      initKeyboardShortcuts();
    } catch (err) {
      console.error('Failed to load data:', err);
      hideSkeletons();
      showError('Unable to load data. Please try again later.');
    }
    state.loading = false;
  }

  // --- Skeleton Loading --------------------------------------------------
  function showSkeletons() {
    const timeline = $('.timeline');
    if (timeline) {
      for (let i = 0; i < 5; i++) {
        const sk = document.createElement('div');
        sk.className = 'skeleton skeleton-card';
        timeline.appendChild(sk);
      }
    }
  }
  function hideSkeletons() {
    $$('.skeleton').forEach(el => el.remove());
  }
  function showError(msg) {
    const timeline = $('.timeline');
    if (timeline) timeline.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${msg}</p></div>`;
  }

  // --- Render All --------------------------------------------------------
  function renderAll() {
    renderCounter();
    renderStats();
    renderTimeline();
    renderCharts();
    populateFilters();
    updateResultsCount();
  }

  // --- Counter Animation -------------------------------------------------
  function renderCounter() {
    const el = $('.counter-value');
    if (!el || !state.stats) return;
    const target = state.stats.total_jobs_lost || 0;
    const duration = 1200;
    const start = performance.now();

    function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Cubic ease-out
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * target);
      el.textContent = current.toLocaleString();
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = target.toLocaleString();
      }
    }
    requestAnimationFrame(tick);

    // Update meta
    const metaEl = $('.counter-meta');
    if (metaEl && state.stats) {
      metaEl.innerHTML = `
        <span>${state.stats.companies.toLocaleString()} Companies</span>
        <span>${state.stats.countries.toLocaleString()} Countries</span>
        <span>${state.stats.industries.toLocaleString()} Industries</span>
        <span>Updated ${formatDate(state.stats.last_updated)}</span>
      `;
    }

    // Populate browse-by counts
    const bCompany = $('#browse-companies');
    const bCountry = $('#browse-countries');
    const bIndustry = $('#browse-industries');
    if (bCompany) bCompany.textContent = state.stats.companies.toLocaleString();
    if (bCountry) bCountry.textContent = state.stats.countries.toLocaleString();
    if (bIndustry) bIndustry.textContent = state.stats.industries.toLocaleString();
  }

  // --- Stats Dashboard ---------------------------------------------------
  function renderStats() {
    if (!state.stats) return;
    const grid = $('.stats-grid');
    if (!grid) return;
    grid.innerHTML = `
      <div class="stat-card">
        <div class="stat-value">${state.stats.total_jobs_lost.toLocaleString()}</div>
        <div class="stat-label">Total Jobs Impacted</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${state.stats.companies.toLocaleString()}</div>
        <div class="stat-label">Companies</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${state.stats.countries.toLocaleString()}</div>
        <div class="stat-label">Countries</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${state.stats.industries.toLocaleString()}</div>
        <div class="stat-label">Industries</div>
      </div>
    `;
  }

  // --- Timeline Rendering ------------------------------------------------
  function renderTimeline() {
    const timeline = $('.timeline');
    if (!timeline) return;
    const entries = state.filtered;

    if (entries.length === 0) {
      timeline.innerHTML = `<div class="empty-state"><h3>No results</h3><p>Try adjusting your filters or search terms.</p></div>`;
      return;
    }

    let html = '';
    entries.forEach((entry, i) => {
      const tierClass = getTierClass(entry.classification);
      const classLabel = getClassLabel(entry.classification);
      const confClass = entry.confidence_score >= 80 ? 'high' : entry.confidence_score >= 60 ? 'medium' : 'low';
      const sourceUrl = entry.source?.url || '#';
      const sourceName = entry.source?.title || 'Source';
      const slug = entry.slug || '';

      html += `
        <article class="entry-card animate-in" data-index="${i % 10}" data-classification="${entry.classification}" data-country="${entry.country}" data-industry="${entry.industry}">
          <div class="entry-card-header">
            <div>
              <h3 class="entry-card-company">${escHtml(entry.company)}</h3>
              <div class="entry-card-meta">
                <span>📅 ${entry.date || '—'}</span>
                <span>📍 ${escHtml(entry.country || '—')}</span>
                <span>🏭 ${escHtml(entry.industry || '—')}</span>
                <span class="class-badge ${tierClass}">${classLabel}</span>
              </div>
            </div>
            <div class="entry-card-jobs">
              ${(entry.jobs_lost || 0).toLocaleString()}
              <span class="entry-card-jobs-label">Jobs impacted</span>
            </div>
          </div>
          <p class="entry-card-summary">${escHtml(truncate(entry.summary || '', 200))}</p>
          <div class="impact-bar">
            <div class="impact-bar-fill ${tierClass}" style="width:${Math.min(entry.impact_percent || 0, 100)}%"></div>
          </div>
          <div class="entry-card-footer">
            <span class="confidence-dot ${confClass}" title="Confidence: ${entry.confidence_score}/100"></span>
            <span>${entry.confidence_score}/100</span>
            <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer">📄 ${escHtml(sourceName)}</a>
            <a href="/company/${slug}/">📋 Full report</a>
            <button class="btn btn-secondary" onclick="trackerShare('${escAttr(entry.company)}', ${entry.jobs_lost}, '${escAttr(entry.classification)}', '${escAttr(entry.date || '')}')" aria-label="Share ${escAttr(entry.company)}">📤 Share</button>
          </div>
        </article>`;
    });

    timeline.innerHTML = html;

    // Observe for animation
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.classList.add('visible');
            observer.unobserve(e.target);
          }
        });
      }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
      $$('.entry-card.animate-in').forEach(card => observer.observe(card));
    } else {
      // Fallback: show all immediately
      $$('.entry-card.animate-in').forEach(card => card.classList.add('visible'));
    }
  }

  // --- Charts (delegated) ------------------------------------------------
  function renderCharts() {
    if (typeof drawIndustryChart === 'function') drawIndustryChart(state.filtered);
    if (typeof drawClassificationChart === 'function') drawClassificationChart(state.filtered);
    if (typeof drawTimelineChart === 'function') drawTimelineChart(state.filtered);
  }

  // --- Filters -----------------------------------------------------------
  function populateFilters() {
    const unique = (arr, key) => [...new Set(arr.map(e => e[key]).filter(Boolean))].sort();

    const countries = unique(state.entries, 'country');
    const industries = unique(state.entries, 'industry');

    const countrySel = $('#filter-country');
    const industrySel = $('#filter-industry');
    if (countrySel) {
      countrySel.innerHTML = '<option value="">All Countries</option>' + countries.map(c => `<option value="${escAttr(c)}">${escHtml(c)}</option>`).join('');
    }
    if (industrySel) {
      industrySel.innerHTML = '<option value="">All Industries</option>' + industries.map(i => `<option value="${escAttr(i)}">${escHtml(i)}</option>`).join('');
    }
  }

  function applyFilters() {
    let entries = [...state.entries];

    // Search
    if (state.filters.search) {
      const q = state.filters.search.toLowerCase();
      entries = entries.filter(e => {
        return (e.company || '').toLowerCase().includes(q) ||
               (e.industry || '').toLowerCase().includes(q) ||
               (e.country || '').toLowerCase().includes(q) ||
               (e.summary || '').toLowerCase().includes(q) ||
               (e.ceo_quote || '').toLowerCase().includes(q) ||
               (e.tags || []).some(t => t.toLowerCase().includes(q));
      });
    }

    // Classification
    if (state.filters.classification.length > 0) {
      entries = entries.filter(e => state.filters.classification.includes(e.classification));
    }

    // Country
    if (state.filters.country) {
      entries = entries.filter(e => e.country === state.filters.country);
    }

    // Industry
    if (state.filters.industry) {
      entries = entries.filter(e => e.industry === state.filters.industry);
    }

    // Date range
    if (state.filters.dateFrom) {
      entries = entries.filter(e => e.date >= state.filters.dateFrom);
    }
    if (state.filters.dateTo) {
      entries = entries.filter(e => e.date <= state.filters.dateTo);
    }

    // Min jobs
    if (state.filters.minJobs) {
      const min = parseInt(state.filters.minJobs, 10);
      if (!isNaN(min)) entries = entries.filter(e => (e.jobs_lost || 0) >= min);
    }

    // Sort
    switch (state.sort) {
      case 'oldest':
        entries.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
        break;
      case 'largest':
        entries.sort((a, b) => (b.jobs_lost || 0) - (a.jobs_lost || 0));
        break;
      case 'impact':
        entries.sort((a, b) => (b.impact_percent || 0) - (a.impact_percent || 0));
        break;
      case 'newest':
      default:
        entries.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        break;
    }

    state.filtered = entries;
    renderTimeline();
    renderCharts();
    updateResultsCount();
    updateURL();
  }

  function updateResultsCount() {
    const el = $('.results-count');
    if (el) {
      el.textContent = `Showing ${state.filtered.length} of ${state.entries.length} entries`;
    }
  }

  function clearFilters() {
    state.filters = { classification: [], country: '', industry: '', dateFrom: '', dateTo: '', minJobs: '', search: '' };
    state.sort = 'newest';
    // Reset UI
    const search = $('#search-input');
    const country = $('#filter-country');
    const industry = $('#filter-industry');
    const dateFrom = $('#filter-date-from');
    const dateTo = $('#filter-date-to');
    const minJobs = $('#filter-min-jobs');
    const sort = $('#filter-sort');

    if (search) search.value = '';
    if (country) country.value = '';
    if (industry) industry.value = '';
    if (dateFrom) dateFrom.value = '';
    if (dateTo) dateTo.value = '';
    if (minJobs) minJobs.value = '';
    if (sort) sort.value = 'newest';

    $$('.filter-chip').forEach(chip => chip.classList.remove('active'));
    applyFilters();
  }

  function updateURL() {
    if (!history.replaceState) return;
    const params = new URLSearchParams();
    if (state.filters.classification.length) params.set('class', state.filters.classification.join(','));
    if (state.filters.country) params.set('country', state.filters.country);
    if (state.filters.industry) params.set('industry', state.filters.industry);
    if (state.filters.search) params.set('q', state.filters.search);
    if (state.sort !== 'newest') params.set('sort', state.sort);
    const qs = params.toString();
    const url = window.location.pathname + (qs ? '?' + qs : '');
    history.replaceState(null, '', url);
  }

  function loadFromURL() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('class')) {
      state.filters.classification = params.get('class').split(',');
      state.filters.classification.forEach(c => {
        const chip = $(`.filter-chip[data-classification="${c}"]`);
        if (chip) chip.classList.add('active');
      });
    }
    if (params.has('country')) state.filters.country = params.get('country');
    if (params.has('industry')) state.filters.industry = params.get('industry');
    if (params.has('q')) state.filters.search = params.get('q');
    if (params.has('sort')) state.sort = params.get('sort');
  }

  // --- Event Listeners ---------------------------------------------------
  function initEventListeners() {
    // Search
    const searchInput = $('#search-input');
    if (searchInput) {
      let debounceTimer;
      searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          state.filters.search = searchInput.value.trim();
          applyFilters();
        }, 200);
      });
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          searchInput.value = '';
          state.filters.search = '';
          applyFilters();
          searchInput.blur();
        }
      });
    }

    // Classification chips
    $$('.filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const c = chip.dataset.classification;
        chip.classList.toggle('active');
        if (chip.classList.contains('active')) {
          state.filters.classification.push(c);
        } else {
          state.filters.classification = state.filters.classification.filter(v => v !== c);
        }
        applyFilters();
      });
    });

    // Select filters
    ['#filter-country', '#filter-industry', '#filter-sort'].forEach(sel => {
      const el = $(sel);
      if (!el) return;
      el.addEventListener('change', () => {
        if (sel === '#filter-country') state.filters.country = el.value;
        if (sel === '#filter-industry') state.filters.industry = el.value;
        if (sel === '#filter-sort') state.sort = el.value;
        applyFilters();
      });
    });

    // Date range
    const dateFrom = $('#filter-date-from');
    const dateTo = $('#filter-date-to');
    if (dateFrom) dateFrom.addEventListener('change', () => { state.filters.dateFrom = dateFrom.value; applyFilters(); });
    if (dateTo) dateTo.addEventListener('change', () => { state.filters.dateTo = dateTo.value; applyFilters(); });

    // Min jobs
    const minJobsEl = $('#filter-min-jobs');
    if (minJobsEl) {
      minJobsEl.addEventListener('input', () => {
        state.filters.minJobs = minJobsEl.value;
        applyFilters();
      });
    }

    // Clear
    const clearBtn = $('#btn-clear-filters');
    if (clearBtn) clearBtn.addEventListener('click', clearFilters);

    // Mobile filter toggle
    const filterToggle = $('.filter-toggle');
    if (filterToggle) {
      filterToggle.addEventListener('click', () => {
        const filtersBar = $('.filters-bar');
        const expanded = filtersBar.classList.toggle('open');
        filterToggle.setAttribute('aria-expanded', expanded.toString());
      });
    }

    // Copy API URL buttons
    $$('.btn-copy-api').forEach(btn => {
      btn.addEventListener('click', () => {
        const url = btn.dataset.apiUrl;
        if (url && navigator.clipboard) {
          navigator.clipboard.writeText(window.location.origin + url).then(() => {
            showToast('Copied to clipboard');
          });
        }
      });
    });
  }

  function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        const search = $('#search-input');
        if (search) search.focus();
      }
      if (e.key === 'Escape') {
        clearFilters();
      }
    });
  }

  // --- Utilities ---------------------------------------------------------
  function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
  function escAttr(str) {
    return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function truncate(str, len) {
    return str.length <= len ? str : str.substring(0, len).replace(/\s+\S*$/, '') + '…';
  }
  function formatDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch { return iso; }
  }
  function getTierClass(c) {
    switch (c) {
      case 'DIRECT_AI_REPLACEMENT': return 'tier-1';
      case 'AI_DRIVEN_RESTRUCTURING': return 'tier-2';
      case 'AI_REALLOCATION': return 'tier-3';
      case 'MARKET_DISRUPTION': return 'tier-4';
      default: return 'tier-2';
    }
  }
  function getClassLabel(c) {
    switch (c) {
      case 'DIRECT_AI_REPLACEMENT': return 'Direct AI Replacement';
      case 'AI_DRIVEN_RESTRUCTURING': return 'AI Restructuring';
      case 'AI_REALLOCATION': return 'AI Reallocation';
      case 'MARKET_DISRUPTION': return 'Market Disruption';
      default: return c || 'Unknown';
    }
  }

  // --- Toast -------------------------------------------------------------
  function showToast(msg) {
    let toast = $('.toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('visible');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('visible'), 2000);
  }

  // --- Share (called from inline buttons) --------------------------------
  window.trackerShare = function (company, jobs, classification, date) {
    const overlay = $('.share-overlay');
    if (!overlay) return;
    const img = $('#share-image');
    if (img && typeof generateShareCard === 'function') {
      const dataUrl = generateShareCard(company, jobs, classification, date);
      img.src = dataUrl;
    }
    overlay.classList.add('open');
  };

  // Share overlay close
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('share-overlay')) {
      e.target.classList.remove('open');
    }
  });
  const closeShare = $('#close-share');
  if (closeShare) {
    closeShare.addEventListener('click', () => {
      const overlay = $('.share-overlay');
      if (overlay) overlay.classList.remove('open');
    });
  }

  // Copy share image
  const copyImgBtn = $('#copy-share-image');
  if (copyImgBtn) {
    copyImgBtn.addEventListener('click', async () => {
      const img = $('#share-image');
      if (!img || !img.src) return;
      try {
        const blob = await (await fetch(img.src)).blob();
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        showToast('Copied image to clipboard');
      } catch {
        showToast('Copy failed — right-click the image to save');
      }
    });
  }

  // Download share image
  const downloadBtn = $('#download-share-image');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const img = $('#share-image');
      if (!img || !img.src) return;
      const a = document.createElement('a');
      a.href = img.src;
      a.download = 'ai-layoff-tracker-share.png';
      a.click();
    });
  }

  // Copy link
  const copyLinkBtn = $('#copy-share-link');
  if (copyLinkBtn) {
    copyLinkBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(window.location.href).then(() => showToast('Link copied'));
    });
  }

  // --- CSV Export (filtered) ---------------------------------------------
  window.exportFilteredCSV = function () {
    const entries = state.filtered;
    if (!entries.length) return;
    const headers = ['Company', 'Date', 'Country', 'Industry', 'Jobs Lost', 'Impact %', 'Classification', 'Confidence', 'Summary', 'Source URL'];
    const rows = entries.map(e => [
      e.company, e.date, e.country, e.industry, e.jobs_lost,
      e.impact_percent + '%', getClassLabel(e.classification),
      e.confidence_score, `"${(e.summary || '').replace(/"/g, '""')}"`,
      e.source?.url || ''
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ai-layoff-tracker-filtered.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  // --- Boot --------------------------------------------------------------
  loadFromURL();
  document.addEventListener('DOMContentLoaded', init);
})();
