/* ==========================================================================
   AI Layoff Tracker — Relevance-Scored Search v1.0
   Client-side search module exposing window.searchEntries.
   No framework. No deps.
   ========================================================================== */

(function () {
  'use strict';

  /**
   * Search entries by query with relevance scoring.
   *
   * Searches across: company, industry, country, summary, ceo_quote, tags.
   *
   * Scoring:
   *   +100  Exact company name match
   *   +50   Company name starts with query
   *   +30   Query matches a whole word in company name
   *   +1    Per field containing the query
   *
   * Results are sorted by score descending. Original order is preserved
   * for entries with equal scores. An empty query returns entries unchanged.
   *
   * @param {Object[]} entries - Array of entry objects.
   * @param {string}   query   - Search string.
   * @returns {Object[]} Filtered and relevance-sorted entries.
   */
  function searchEntries(entries, query) {
    // Fast path: empty query => unchanged
    if (!query || !query.trim()) {
      return entries;
    }

    var q = query.trim().toLowerCase();
    var scored = [];

    for (var i = 0; i < entries.length; i++) {
      var entry = entries[i];
      var score = 0;

      // --- Company name scoring ------------------------------------------
      var company = (entry.company || '').toLowerCase();

      if (company === q) {
        score += 100;
      } else if (company.indexOf(q) === 0) {
        score += 50;
      } else {
        // Word-boundary match: split company into words, check any exact word match
        var words = company.split(/[\s,.-]+/);
        for (var w = 0; w < words.length; w++) {
          if (words[w] === q) {
            score += 30;
            break; // one word match is enough
          }
        }
      }

      // --- Per-field matches (+1 each) -----------------------------------
      // Score only once per field regardless of how many times the query appears.

      if (company.indexOf(q) !== -1) {
        score += 1;
      }

      if ((entry.industry || '').toLowerCase().indexOf(q) !== -1) {
        score += 1;
      }

      if ((entry.country || '').toLowerCase().indexOf(q) !== -1) {
        score += 1;
      }

      if ((entry.summary || '').toLowerCase().indexOf(q) !== -1) {
        score += 1;
      }

      if ((entry.ceo_quote || '').toLowerCase().indexOf(q) !== -1) {
        score += 1;
      }

      var tags = entry.tags;
      if (tags && tags.length) {
        for (var t = 0; t < tags.length; t++) {
          if ((tags[t] || '').toLowerCase().indexOf(q) !== -1) {
            score += 1;
            break; // one matching tag is enough
          }
        }
      }

      // --- Keep only entries with at least one match ----------------------
      if (score > 0) {
        scored.push({ entry: entry, score: score, idx: i });
      }
    }

    // --- Sort: score desc, then original index asc for stability -------
    scored.sort(function (a, b) {
      if (b.score !== a.score) {
        return b.score - a.score;
      }
      return a.idx - b.idx;
    });

    // --- Unwrap -----------------------------------------------------------
    var results = [];
    for (var s = 0; s < scored.length; s++) {
      results.push(scored[s].entry);
    }

    return results;
  }

  // --- Export -------------------------------------------------------------
  window.searchEntries = searchEntries;
})();
