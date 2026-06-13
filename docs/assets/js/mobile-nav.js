/* =====================================================================
   AI Layoff Tracker — Mobile Navigation
   Hamburger toggle, slide-out drawer, backdrop dismiss, Escape key.
   ===================================================================== */
(function(){
  'use strict';

  function init() {
    const hamburger = document.querySelector('.hamburger');
    const mobileNav = document.querySelector('.mobile-nav');
    const backdrop = document.querySelector('.mobile-nav-backdrop');
    if (!hamburger || !mobileNav) return;

    function open() {
      hamburger.classList.add('active');
      hamburger.setAttribute('aria-expanded', 'true');
      mobileNav.classList.add('open');
      document.body.style.overflow = 'hidden';
      // Focus first link
      const firstLink = mobileNav.querySelector('a');
      if (firstLink) setTimeout(() => firstLink.focus(), 400);
    }

    function close() {
      hamburger.classList.remove('active');
      hamburger.setAttribute('aria-expanded', 'false');
      mobileNav.classList.remove('open');
      document.body.style.overflow = '';
      hamburger.focus();
    }

    hamburger.addEventListener('click', function() {
      if (mobileNav.classList.contains('open')) {
        close();
      } else {
        open();
      }
    });

    if (backdrop) {
      backdrop.addEventListener('click', close);
    }

    // Close on Escape
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && mobileNav.classList.contains('open')) {
        close();
      }
    });

    // Close on nav link click
    mobileNav.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        setTimeout(close, 150);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
