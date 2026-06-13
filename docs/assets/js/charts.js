(function () {
  'use strict';

  /* ── constants ─────────────────────────────────────────────────── */
  const BG        = '#141414';
  const TEXT      = '#a0a0a0';
  const ACCENT    = '#ff4444';
  const DPR       = window.devicePixelRatio || 1;

  const TIER_COLORS = {
    tier1: '#00c853',
    tier2: '#ffc107',
    tier3: '#ff9800',
    tier4: '#2196f3'
  };

  const INDUSTRY_PALETTE = [
    '#ff4444', '#ff6d3a', '#ff9100', '#ffab00',
    '#ffd600', '#aeea00', '#00e676', '#00bfa5',
    '#00b8d4', '#0091ea', '#2979ff', '#651fff',
    '#aa00ff', '#c51162', '#ff1744', '#ff7043'
  ];

  const prefersReducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── helpers ──────────────────────────────────────────────────── */
  function getCanvas(id) {
    var c = document.getElementById(id);
    if (!c) return null;
    var w = c.parentElement ? c.parentElement.clientWidth : 300;
    var h = Math.round(w * 0.6);   /* 5:3 aspect – tweak per chart */
    c.style.width  = w + 'px';
    c.style.height = h + 'px';
    c.width  = Math.round(w * DPR);
    c.height = Math.round(h * DPR);
    return c;
  }

  function ctxSetup(canvas) {
    var ctx = canvas.getContext('2d');
    ctx.scale(DPR, DPR);
    return ctx;
  }

  function clearCanvas(ctx, w, h) {
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, w, h);
  }

  function drawNoData(ctx, w, h) {
    clearCanvas(ctx, w, h);
    ctx.fillStyle = TEXT;
    ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('No data', w / 2, h / 2);
  }

  function easing(t) { return 1 - Math.pow(1 - t, 3); }

  function animate(drawFn, duration) {
    if (prefersReducedMotion || !duration) {
      drawFn(1);
      return;
    }
    var start = performance.now();
    function frame(now) {
      var t = Math.min((now - start) / duration, 1);
      drawFn(easing(t));
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  /* ── 1.  industry horizontal bar chart ────────────────────────── */
  function drawIndustryChart(entries) {
    var canvas = getCanvas('chart-industry');
    if (!canvas) return;
    var w = canvas.parentElement.clientWidth;
    var h = Math.round(w * 0.6);
    var ctx = ctxSetup(canvas);

    if (!entries || !entries.length) { drawNoData(ctx, w, h); return; }

    /* aggregate */
    var map = {};
    var i, e;
    for (i = 0; i < entries.length; i++) {
      e = entries[i];
      var ind = e.industry || 'Unknown';
      map[ind] = (map[ind] || 0) + (Number(e.jobs_lost) || 0);
    }

    var data = Object.keys(map).map(function (k) {
      return { label: k, value: map[k] };
    }).sort(function (a, b) { return b.value - a.value; });

    var maxVal = data[0].value;
    var pad = { top: 16, right: 24, bottom: 24, left: 120 };
    var chartW = w - pad.left - pad.right;
    var barH  = Math.min(28, (h - pad.top - pad.bottom) / data.length - 6);
    var totalH = data.length * (barH + 6) + pad.top + pad.bottom;
    var startY = pad.top;

    animate(function (t) {
      clearCanvas(ctx, w, h);

      /* bars */
      for (i = 0; i < data.length; i++) {
        var x = pad.left;
        var y = startY + i * (barH + 6);
        var bw = (data[i].value / maxVal) * chartW * t;
        var color = INDUSTRY_PALETTE[i % INDUSTRY_PALETTE.length];

        /* label */
        ctx.fillStyle = TEXT;
        ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(truncate(data[i].label, 14), pad.left - 8, y + barH / 2);

        /* bar */
        var grad = ctx.createLinearGradient(x, 0, x + bw, 0);
        grad.addColorStop(0, color);
        grad.addColorStop(1, lighten(color, 0.3));
        ctx.fillStyle = grad;
        roundRect(ctx, x, y, Math.max(bw, 2), barH, 4);
        ctx.fill();

        /* value label */
        if (bw > 40) {
          ctx.fillStyle = '#fff';
          ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
          ctx.textAlign = 'right';
          ctx.fillText(fmtNum(data[i].value), x + bw - 6, y + barH / 2);
        }
      }
    }, 600);
  }

  /* ── 2.  classification donut chart ───────────────────────────── */
  function drawClassificationChart(entries) {
    var canvas = getCanvas('chart-classification');
    if (!canvas) return;
    var w = canvas.parentElement.clientWidth;
    var h = Math.round(w * 0.6);
    var ctx = ctxSetup(canvas);

    if (!entries || !entries.length) { drawNoData(ctx, w, h); return; }

    /* count by classification */
    var map = {};
    var i, e;
    for (i = 0; i < entries.length; i++) {
      e = entries[i];
      var cls = e.classification || 'Unknown';
      map[cls] = (map[cls] || 0) + 1;
    }

    var labels = Object.keys(map);
    var values = labels.map(function (k) { return map[k]; });
    var total  = values.reduce(function (a, b) { return a + b; }, 0);

    var cx = w / 2;
    var cy = h / 2;
    var outerR = Math.min(cx, cy) - 16;
    var innerR = outerR * 0.55;

    animate(function (t) {
      clearCanvas(ctx, w, h);

      var angle = -Math.PI / 2;

      for (i = 0; i < values.length; i++) {
        var sliceAngle = (values[i] / total) * Math.PI * 2 * t;
        var color = TIER_COLORS[labels[i]] || '#555';

        ctx.beginPath();
        ctx.arc(cx, cy, outerR, angle, angle + sliceAngle);
        ctx.arc(cx, cy, innerR, angle + sliceAngle, angle, true);
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();

        /* subtle separator */
        ctx.strokeStyle = BG;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        angle += sliceAngle;
      }

      /* centre text */
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 22px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(fmtNum(total), cx, cy - 6);

      ctx.fillStyle = TEXT;
      ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillText('total entries', cx, cy + 14);

      /* legend */
      drawLegend(ctx, labels, values, total, w, h);
    }, 700);
  }

  function drawLegend(ctx, labels, values, total, w, h) {
    var x = 16, y = h - 14 - labels.length * 18;
    var i;
    for (i = 0; i < labels.length; i++) {
      var color = TIER_COLORS[labels[i]] || '#555';
      var pct = total ? Math.round(values[i] / total * 100) : 0;

      ctx.fillStyle = color;
      ctx.fillRect(x, y + i * 18, 10, 10);

      ctx.fillStyle = TEXT;
      ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(labels[i] + '  ' + values[i] + ' (' + pct + '%)', x + 16, y + i * 18 + 5);
    }
  }

  /* ── 3.  timeline line chart ──────────────────────────────────── */
  function drawTimelineChart(entries) {
    var canvas = getCanvas('chart-timeline');
    if (!canvas) return;
    var w = canvas.parentElement.clientWidth;
    var h = Math.round(w * 0.55);
    var ctx = ctxSetup(canvas);

    if (!entries || !entries.length) { drawNoData(ctx, w, h); return; }

    /* group by YYYY-MM */
    var map = {};
    var i, e;
    for (i = 0; i < entries.length; i++) {
      e = entries[i];
      var d = parseDate(e.date || e.date_announced || e.announced);
      var key = d ? formatYM(d) : null;
      if (key) map[key] = (map[key] || 0) + (Number(e.jobs_lost) || 0);
    }

    var keys = Object.keys(map).sort();
    if (!keys.length) { drawNoData(ctx, w, h); return; }

    var pts = keys.map(function (k) { return { label: k, value: map[k] }; });
    var maxV = Math.max.apply(null, pts.map(function (p) { return p.value; }));
    if (maxV === 0) maxV = 1;

    var pad  = { top: 20, right: 20, bottom: 40, left: 50 };
    var plotW = w - pad.left - pad.right;
    var plotH = h - pad.top - pad.bottom;

    var xScale = pts.length > 1 ? plotW / (pts.length - 1) : plotW;
    var yScale = plotH / (maxV * 1.15);  /* 15 % headroom */

    function x(i) { return pad.left + i * xScale; }
    function y(v) { return pad.top + plotH - v * yScale; }

    animate(function (t) {
      clearCanvas(ctx, w, h);

      var count = Math.ceil(pts.length * t);

      /* filled area */
      ctx.beginPath();
      ctx.moveTo(x(0), pad.top + plotH);
      for (i = 0; i < count; i++) {
        if (i === 0) ctx.lineTo(x(i), y(pts[i].value));
        else {
          var prevX = x(i - 1);
          var prevY = y(pts[i - 1].value);
          var curX  = x(i);
          var curY  = y(pts[i].value);
          var cp1x  = prevX + (curX - prevX) * 0.5;
          ctx.bezierCurveTo(cp1x, prevY, cp1x, curY, curX, curY);
        }
      }
      ctx.lineTo(x(count - 1), pad.top + plotH);
      ctx.closePath();
      var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
      grad.addColorStop(0, 'rgba(255,68,68,0.35)');
      grad.addColorStop(1, 'rgba(255,68,68,0.02)');
      ctx.fillStyle = grad;
      ctx.fill();

      /* line */
      ctx.beginPath();
      for (i = 0; i < count; i++) {
        if (i === 0) ctx.moveTo(x(i), y(pts[i].value));
        else {
          var pX = x(i - 1), pY = y(pts[i - 1].value);
          var cX = x(i),     cY = y(pts[i].value);
          var cpX = pX + (cX - pX) * 0.5;
          ctx.bezierCurveTo(cpX, pY, cpX, cY, cX, cY);
        }
      }
      ctx.strokeStyle = ACCENT;
      ctx.lineWidth = 2.5;
      ctx.lineJoin = 'round';
      ctx.stroke();

      /* dots & labels on last frame */
      if (t >= 0.99) {
        for (i = 0; i < pts.length; i++) {
          /* dot */
          ctx.beginPath();
          ctx.arc(x(i), y(pts[i].value), 3.5, 0, Math.PI * 2);
          ctx.fillStyle = ACCENT;
          ctx.fill();
          ctx.strokeStyle = BG;
          ctx.lineWidth = 1.5;
          ctx.stroke();

          /* x-axis label - show every N to avoid crowding */
          var step = Math.max(1, Math.floor(pts.length / 8));
          if (i % step === 0 || i === pts.length - 1) {
            ctx.fillStyle = TEXT;
            ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText(pts[i].label, x(i), pad.top + plotH + 8);
          }
        }
      }
    }, 800);

    /* After animation completes, draw the full static chart with axes/legends */
    var finalize = function () {
      drawTimelineStatic(ctx, pts, w, h, pad, plotW, plotH, x, y, maxV);
    };
    if (!prefersReducedMotion) {
      setTimeout(finalize, 820);
    } else {
      finalize();
    }
  }

  function drawTimelineStatic(ctx, pts, w, h, pad, plotW, plotH, xFn, yFn, maxV) {
    clearCanvas(ctx, w, h);

    var i;
    /* filled area */
    ctx.beginPath();
    ctx.moveTo(xFn(0), pad.top + plotH);
    for (i = 0; i < pts.length; i++) {
      if (i === 0) ctx.lineTo(xFn(i), yFn(pts[i].value));
      else {
        var prevX = xFn(i - 1), prevY = yFn(pts[i - 1].value);
        var curX  = xFn(i),     curY  = yFn(pts[i].value);
        var cpX   = prevX + (curX - prevX) * 0.5;
        ctx.bezierCurveTo(cpX, prevY, cpX, curY, curX, curY);
      }
    }
    ctx.lineTo(xFn(pts.length - 1), pad.top + plotH);
    ctx.closePath();
    var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
    grad.addColorStop(0, 'rgba(255,68,68,0.35)');
    grad.addColorStop(1, 'rgba(255,68,68,0.02)');
    ctx.fillStyle = grad;
    ctx.fill();

    /* line */
    ctx.beginPath();
    for (i = 0; i < pts.length; i++) {
      if (i === 0) ctx.moveTo(xFn(i), yFn(pts[i].value));
      else {
        var pX = xFn(i - 1), pY = yFn(pts[i - 1].value);
        var cX = xFn(i),     cY = yFn(pts[i].value);
        var cpX2 = pX + (cX - pX) * 0.5;
        ctx.bezierCurveTo(cpX2, pY, cpX2, cY, cX, cY);
      }
    }
    ctx.strokeStyle = ACCENT;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.stroke();

    /* dots */
    for (i = 0; i < pts.length; i++) {
      ctx.beginPath();
      ctx.arc(xFn(i), yFn(pts[i].value), 3.5, 0, Math.PI * 2);
      ctx.fillStyle = ACCENT;
      ctx.fill();
      ctx.strokeStyle = BG;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    /* x labels */
    var step = Math.max(1, Math.floor(pts.length / 8));
    ctx.fillStyle = TEXT;
    ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    for (i = 0; i < pts.length; i++) {
      if (i % step === 0 || i === pts.length - 1) {
        ctx.fillText(pts[i].label, xFn(i), pad.top + plotH + 8);
      }
    }

    /* y-axis */
    ctx.fillStyle = '#3a3a3a';
    var ySteps = 4;
    for (i = 0; i <= ySteps; i++) {
      var yy = pad.top + plotH - (plotH * i / ySteps);
      ctx.beginPath();
      ctx.moveTo(pad.left, yy);
      ctx.lineTo(pad.left + plotW, yy);
      ctx.strokeStyle = '#222';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    /* y labels */
    ctx.fillStyle = TEXT;
    ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (i = 0; i <= ySteps; i++) {
      var val = Math.round(maxV * 1.15 * i / ySteps);
      var yy2 = pad.top + plotH - (plotH * i / ySteps);
      ctx.fillText(fmtNum(val), pad.left - 8, yy2);
    }
  }

  /* ── tiny helpers ─────────────────────────────────────────────── */
  function truncate(str, max) {
    return str.length > max ? str.slice(0, max - 1) + '…' : str;
  }

  function fmtNum(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(Math.round(n));
  }

  function lighten(hex, amount) {
    var r = parseInt(hex.slice(1, 3), 16);
    var g = parseInt(hex.slice(3, 5), 16);
    var b = parseInt(hex.slice(5, 7), 16);
    r = Math.min(255, Math.round(r + (255 - r) * amount));
    g = Math.min(255, Math.round(g + (255 - g) * amount));
    b = Math.min(255, Math.round(b + (255 - b) * amount));
    return '#' + [r, g, b].map(function (c) {
      return c.toString(16).padStart(2, '0');
    }).join('');
  }

  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
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
  }

  function parseDate(val) {
    if (!val) return null;
    var d = new Date(val);
    return isNaN(d.getTime()) ? null : d;
  }

  function formatYM(d) {
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    return y + '-' + m;
  }

  /* ── exports ──────────────────────────────────────────────────── */
  window.drawIndustryChart      = drawIndustryChart;
  window.drawClassificationChart = drawClassificationChart;
  window.drawTimelineChart      = drawTimelineChart;
})();
