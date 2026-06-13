/* =====================================================================
   AI Layoff Tracker — Theme Toggle
   Persists to localStorage. Runs before paint to prevent flash.
   ===================================================================== */
(function(){
  'use strict';

  const KEY = 'ai-layoff-tracker-theme';

  // Apply saved theme immediately to prevent FOUC
  const saved = localStorage.getItem(KEY);
  if (saved === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    // Default: dark. Explicitly set for CSS selector consistency
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  // Toggle on DOM ready
  function init() {
    const btn = document.querySelector('.theme-toggle');
    if (!btn) return;

    btn.addEventListener('click', function() {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem(KEY, next);
    });

    // Keyboard: press Enter/Space to toggle
    btn.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        btn.click();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
