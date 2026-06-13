/* ==========================================================================
   AI Layoff Tracker — Filters v1.0
   Pure utility functions for filtering and sorting entry data.
   No side effects. No DOM access. Composable, testable.
   Exports: window.Filters
   ========================================================================== */

(function () {
  'use strict';

  // --- getUniqueValues ---------------------------------------------------
  // Returns a sorted array of unique, truthy values for a given key across
  // all entries. Useful for populating dropdown/select filter options.

  /**
   * @param {Object[]} entries - Array of entry objects
   * @param {string} key - Property key to extract values from
   * @returns {string[]} Sorted, deduplicated array of values
   */
  function getUniqueValues(entries, key) {
    if (!Array.isArray(entries) || entries.length === 0) return [];
    const seen = new Set();
    for (let i = 0; i < entries.length; i++) {
      const val = entries[i][key];
      if (val != null && val !== '') {
        seen.add(val);
      }
    }
    return [...seen].sort();
  }

  // --- filterByClassification ---------------------------------------------
  // Filters entries whose classification property matches any value in the
  // provided classifications array. If the array is empty, returns all entries.

  /**
   * @param {Object[]} entries
   * @param {string[]} classificationsArr - Accepted classification values
   * @returns {Object[]} Filtered entries
   */
  function filterByClassification(entries, classificationsArr) {
    if (!Array.isArray(entries)) return [];
    if (!classificationsArr || classificationsArr.length === 0) return entries;
    const classSet = new Set(classificationsArr);
    return entries.filter(function (e) {
      return classSet.has(e.classification);
    });
  }

  // --- filterByCountry ----------------------------------------------------
  // Returns entries matching a specific country. An empty string or falsy
  // value acts as a pass-through (returns all entries without filtering).

  /**
   * @param {Object[]} entries
   * @param {string} country - Country value to match (empty = pass all)
   * @returns {Object[]} Filtered entries
   */
  function filterByCountry(entries, country) {
    if (!Array.isArray(entries)) return [];
    if (!country) return entries;
    return entries.filter(function (e) {
      return e.country === country;
    });
  }

  // --- filterByIndustry ---------------------------------------------------
  // Same pattern as filterByCountry: empty string passes all.

  /**
   * @param {Object[]} entries
   * @param {string} industry - Industry value to match (empty = pass all)
   * @returns {Object[]} Filtered entries
   */
  function filterByIndustry(entries, industry) {
    if (!Array.isArray(entries)) return [];
    if (!industry) return entries;
    return entries.filter(function (e) {
      return e.industry === industry;
    });
  }

  // --- filterByDateRange --------------------------------------------------
  // Filters entries where date falls within an inclusive range.
  // Both `from` and `to` are optional — omitting either removes that bound.
  // Dates are compared as strings (assumes ISO 8601 or YYYY-MM-DD format).

  /**
   * @param {Object[]} entries
   * @param {string} from - Start date string (inclusive), optional
   * @param {string} to   - End date string (inclusive), optional
   * @returns {Object[]} Filtered entries
   */
  function filterByDateRange(entries, from, to) {
    if (!Array.isArray(entries)) return [];
    if (!from && !to) return entries;
    return entries.filter(function (e) {
      var date = e.date;
      if (!date) return false;
      if (from && date < from) return false;
      if (to && date > to) return false;
      return true;
    });
  }

  // --- filterByMinJobs ----------------------------------------------------
  // Returns entries whose jobs_lost is >= the given minimum.
  // If min is falsy or NaN coerce, returns all entries.

  /**
   * @param {Object[]} entries
   * @param {number|string} min - Minimum jobs_lost threshold
   * @returns {Object[]} Filtered entries
   */
  function filterByMinJobs(entries, min) {
    if (!Array.isArray(entries)) return [];
    var threshold = parseInt(min, 10);
    if (isNaN(threshold)) return entries;
    return entries.filter(function (e) {
      return (e.jobs_lost || 0) >= threshold;
    });
  }

  // --- sortEntries --------------------------------------------------------
  // Returns a new sorted array (non-mutating) based on the sort criterion.
  //
  //   'newest'   — date descending
  //   'oldest'   — date ascending
  //   'largest'  — jobs_lost descending
  //   'impact'   — impact_percent descending
  //   (default)  — newest (date descending)

  /**
   * @param {Object[]} entries
   * @param {string} sortBy - 'newest' | 'oldest' | 'largest' | 'impact'
   * @returns {Object[]} New sorted array (original unchanged)
   */
  function sortEntries(entries, sortBy) {
    if (!Array.isArray(entries)) return [];
    var sorted = entries.slice(); // shallow copy — no mutation

    switch (sortBy) {
      case 'oldest':
        sorted.sort(function (a, b) {
          return (a.date || '').localeCompare(b.date || '');
        });
        break;
      case 'largest':
        sorted.sort(function (a, b) {
          return (b.jobs_lost || 0) - (a.jobs_lost || 0);
        });
        break;
      case 'impact':
        sorted.sort(function (a, b) {
          return (b.impact_percent || 0) - (a.impact_percent || 0);
        });
        break;
      case 'newest':
      default:
        sorted.sort(function (a, b) {
          return (b.date || '').localeCompare(a.date || '');
        });
        break;
    }

    return sorted;
  }

  // --- Public API ---------------------------------------------------------
  window.Filters = {
    getUniqueValues: getUniqueValues,
    filterByClassification: filterByClassification,
    filterByCountry: filterByCountry,
    filterByIndustry: filterByIndustry,
    filterByDateRange: filterByDateRange,
    filterByMinJobs: filterByMinJobs,
    sortEntries: sortEntries
  };

})();
