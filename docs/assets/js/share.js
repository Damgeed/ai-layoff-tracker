(function () {
  'use strict';

  /**
   * Generate a social card PNG for the AI Layoff Tracker.
   *
   * @param {string}  company      - Company name
   * @param {number|string} jobsLost - Number of jobs lost
   * @param {string}  classification - One of DIRECT_AI_REPLACEMENT,
   *                                    AI_DRIVEN_RESTRUCTURING,
   *                                    AI_REALLOCATION,
   *                                    MARKET_DISRUPTION
   * @param {string}  date         - Date string (e.g. "June 2026")
   * @returns {string} PNG data URL
   */
  function generateShareCard(company, jobsLost, classification, date) {
    var WIDTH = 1200;
    var HEIGHT = 630;

    var canvas = document.createElement('canvas');
    canvas.width = WIDTH;
    canvas.height = HEIGHT;
    var ctx = canvas.getContext('2d');

    // --- Background ---
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    // --- Top label: "AI LAYOFF TRACKER" ---
    var topLabelY = 90;
    ctx.fillStyle = '#a0a0a0';
    ctx.font = '20px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('AI LAYOFF TRACKER', WIDTH / 2, topLabelY);

    // --- Company name ---
    var companyY = 200;
    ctx.fillStyle = '#f5f5f5';
    ctx.font = 'bold 72px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Truncate if too wide (leave 80px padding on each side)
    var maxCompanyWidth = WIDTH - 160;
    var companyText = truncateText(ctx, company, maxCompanyWidth);
    ctx.fillText(companyText, WIDTH / 2, companyY);

    // --- Jobs impacted ---
    var jobsY = 300;
    ctx.fillStyle = '#ff4444';
    ctx.font = '48px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    var jobsText = formatNumber(jobsLost) + ' JOBS IMPACTED';
    ctx.fillText(jobsText, WIDTH / 2, jobsY);

    // --- Classification badge ---
    var badgeLabel = getBadgeLabel(classification);
    var badgeColor = getBadgeColor(classification);
    var badgeY = 390;
    var badgePaddingX = 28;
    var badgePaddingY = 14;
    var badgeRadius = 10;

    ctx.font = 'bold 22px sans-serif';
    var badgeTextWidth = ctx.measureText(badgeLabel).width;
    var badgeWidth = badgeTextWidth + badgePaddingX * 2;
    var badgeHeight = 30 + badgePaddingY * 2;
    var badgeX = (WIDTH - badgeWidth) / 2;
    var badgeTextY = badgeY + badgeHeight / 2;

    // Draw rounded rectangle badge
    ctx.fillStyle = badgeColor;
    roundRect(ctx, badgeX, badgeY, badgeWidth, badgeHeight, badgeRadius);

    // Badge label
    ctx.fillStyle = '#ffffff';
    ctx.textBaseline = 'middle';
    ctx.fillText(badgeLabel, WIDTH / 2, badgeTextY);

    // --- Date ---
    var dateY = 475;
    ctx.fillStyle = '#a0a0a0';
    ctx.font = '22px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(date, WIDTH / 2, dateY);

    // --- Bottom domain ---
    var bottomY = 580;
    ctx.fillStyle = '#666666';
    ctx.font = '18px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText('AILAYOFFTRACKER.COM', WIDTH / 2, bottomY);

    // --- Return data URL ---
    return canvas.toDataURL('image/png');
  }

  /**
   * Truncate text with ellipsis if it exceeds maxWidth.
   */
  function truncateText(ctx, text, maxWidth) {
    if (ctx.measureText(text).width <= maxWidth) {
      return text;
    }
    var ellipsis = '\u2026';
    var trimmed = text;
    while (trimmed.length > 1 && ctx.measureText(trimmed + ellipsis).width > maxWidth) {
      trimmed = trimmed.slice(0, -1);
    }
    return trimmed + ellipsis;
  }

  /**
   * Format a number with locale-aware separators and no decimal places.
   */
  function formatNumber(value) {
    var num = typeof value === 'string' ? parseInt(value, 10) : value;
    if (isNaN(num)) { return String(value); }
    return num.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }

  /**
   * Map classification code to human-readable badge label.
   */
  function getBadgeLabel(classification) {
    switch (classification) {
      case 'DIRECT_AI_REPLACEMENT':    return 'Direct AI Replacement';
      case 'AI_DRIVEN_RESTRUCTURING':  return 'AI-Driven Restructuring';
      case 'AI_REALLOCATION':          return 'AI Reallocation';
      case 'MARKET_DISRUPTION':        return 'Market Disruption';
      default:                         return classification || 'Unknown';
    }
  }

  /**
   * Map classification code to badge background color.
   */
  function getBadgeColor(classification) {
    switch (classification) {
      case 'DIRECT_AI_REPLACEMENT':    return '#00c853';
      case 'AI_DRIVEN_RESTRUCTURING':  return '#ffc107';
      case 'AI_REALLOCATION':          return '#ff9800';
      case 'MARKET_DISRUPTION':        return '#2196f3';
      default:                         return '#757575';
    }
  }

  /**
   * Draw a filled rounded rectangle.
   */
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.arcTo(x + w, y, x + w, y + r, r);
    ctx.lineTo(x + w, y + h - r);
    ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
    ctx.lineTo(x + r, y + h);
    ctx.arcTo(x, y + h, x, y + h - r, r);
    ctx.lineTo(x, y + r);
    ctx.arcTo(x, y, x + r, y, r);
    ctx.closePath();
    ctx.fill();
  }

  // --- Export ---
  window.generateShareCard = generateShareCard;
})();
