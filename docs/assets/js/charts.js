(function () {
  'use strict';

  /* ── constants ─────────────────────────────────────────────────── */
  const BG        = '#141414';
  const TEXT      = '#888';
  const ACCENT    = '#e53935';

  const TIER_COLORS = {
    tier1: '#43a047',   /* green — softer */
    tier2: '#f9a825',   /* amber */
    tier3: '#ef6c00',   /* orange */
    tier4: '#1e88e5'    /* blue */
  };

  const INDUSTRY_PALETTE = [
    '#e53935','#ff7043','#fb8c00','#fdd835',
    '#7cb342','#43a047','#00acc1','#039be5',
    '#1e88e5','#3949ab','#8e24aa','#d81b60',
    '#c0ca33','#ffb300','#ef6c00'
  ];

  const prefersReducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* track if we've already drawn (avoid double-draw on resize) */
  var drawn = {};

  /* ── helpers ──────────────────────────────────────────────────── */
  function isMobile() { return window.innerWidth <= 768; }
  function isSmall()  { return window.innerWidth <= 480; }

  function getCanvas(id) {
    var c = document.getElementById(id);
    if (!c) return null;
    var containerW = c.parentElement ? c.parentElement.clientWidth : 300;
    var ratio = isMobile() ? 0.45 : 0.58;
    var w = containerW - (isMobile() ? 0 : 0);  /* use full container width */
    var h = Math.round(w * ratio);
    /* clamp max height */
    if (isMobile() && h > 220) h = 220;
    c.style.width  = w + 'px';
    c.style.height = h + 'px';
    c.width  = Math.round(w * (window.devicePixelRatio || 1));
    c.height = Math.round(h * (window.devicePixelRatio || 1));
    return c;
  }

  function ctxSetup(canvas) {
    var ctx = canvas.getContext('2d');
    ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    return ctx;
  }

  function clearCanvas(ctx, w, h) {
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, w, h);
  }

  function drawNoData(ctx, w, h) {
    clearCanvas(ctx, w, h);
    ctx.fillStyle = TEXT;
    ctx.font = '13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
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
    if (drawn['industry']) return;  /* no double-draw */
    var canvas = getCanvas('chart-industry');
    if (!canvas) return;
    var w = parseInt(canvas.style.width);
    var h = parseInt(canvas.style.height);
    var ctx = ctxSetup(canvas);

    if (!entries || !entries.length) { drawNoData(ctx, w, h); drawn['industry'] = true; return; }

    var map = {};
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      var ind = e.industry || 'Unknown';
      map[ind] = (map[ind] || 0) + (Number(e.jobs_lost) || 0);
    }
    var data = Object.keys(map).map(function (k) {
      return { label: k, value: map[k] };
    }).sort(function (a, b) { return b.value - a.value; });

    var maxVal = data[0].value;
    var fontSize = isSmall() ? 10 : (isMobile() ? 11 : 12);
    var pad = { top: 10, right: isMobile() ? 8 : 20, bottom: 10, left: isSmall() ? 90 : (isMobile() ? 100 : 130) };
    var chartW = w - pad.left - pad.right;
    var barH  = Math.min(24, (h - pad.top - pad.bottom) / data.length - 4);
    var totalH = data.length * (barH + 4) + pad.top + pad.bottom;
    var startY = Math.max(pad.top, (h - totalH) / 2);

    animate(function (t) {
      clearCanvas(ctx, w, h);
      for (var j = 0; j < data.length; j++) {
        var x = pad.left;
        var y = startY + j * (barH + 4);
        var bw = (data[j].value / maxVal) * chartW * t;
        var color = INDUSTRY_PALETTE[j % INDUSTRY_PALETTE.length];

        /* label */
        ctx.fillStyle = TEXT;
        ctx.font = fontSize + 'px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        var label = truncate(data[j].label, isMobile() ? 10 : 16);
        ctx.fillText(label, pad.left - 8, y + barH / 2);

        /* bar */
        ctx.fillStyle = color + 'cc';  /* 80% opacity for softer look */
        roundRect(ctx, x, y, Math.max(bw, 2), barH, 3);
        ctx.fill();

        /* value inside bar */
        if (bw > 50) {
          ctx.fillStyle = '#fff';
          ctx.font = (fontSize - 1) + 'px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
          ctx.textAlign = 'right';
          ctx.fillText(fmtNum(data[j].value), x + bw - 6, y + barH / 2);
        }
      }
    }, 600);

    drawn['industry'] = true;
  }

  /* ── 2.  classification donut chart ───────────────────────────── */
  function drawClassificationChart(entries) {
    if (drawn['classification']) return;
    var canvas = getCanvas('chart-classification');
    if (!canvas) return;
    var w = parseInt(canvas.style.width);
    var h = parseInt(canvas.style.height);
    var ctx = ctxSetup(canvas);

    if (!entries || !entries.length) { drawNoData(ctx, w, h); drawn['classification'] = true; return; }

    var map = {};
    for (var i = 0; i < entries.length; i++) {
      var cls = entries[i].classification || 'Unknown';
      map[cls] = (map[cls] || 0) + 1;
    }
    var labels = Object.keys(map);
    var values = labels.map(function (k) { return map[k]; });
    var total  = values.reduce(function (a, b) { return a + b; }, 0);

    var cx = w / 2;
    var cy = h / 2 - (isMobile() ? 8 : 0);
    var outerR = Math.min(cx, cy) - 20;
    var innerR = outerR * 0.55;

    animate(function (t) {
      clearCanvas(ctx, w, h);
      var angle = -Math.PI / 2;
      for (var j = 0; j < values.length; j++) {
        var sliceAngle = (values[j] / total) * Math.PI * 2 * t;
        var color = TIER_COLORS[labels[j]] || '#555';
        ctx.beginPath();
        ctx.arc(cx, cy, outerR, angle, angle + sliceAngle);
        ctx.arc(cx, cy, innerR, angle + sliceAngle, angle, true);
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = BG;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        angle += sliceAngle;
      }

      /* centre text */
      ctx.fillStyle = '#fff';
      ctx.font = (isSmall() ? 'bold 18px' : 'bold 22px') + ' -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(fmtNum(total), cx, cy - 6);
      ctx.fillStyle = TEXT;
      ctx.font = (isSmall() ? '10px' : '12px') + ' -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillText('total entries', cx, cy + 14);

      /* legend */
      drawLegend(ctx, labels, values, total, w, h, isSmall() ? 10 : 11);
    }, 700);

    drawn['classification'] = true;
  }

  function drawLegend(ctx, labels, values, total, w, h, fontSize) {
    var x = isMobile() ? 8 : 16;
    var itemH = fontSize + 6;
    var y = h - 10 - labels.length * itemH;
    for (var i = 0; i < labels.length; i++) {
      var color = TIER_COLORS[labels[i]] || '#555';
      var pct = total ? Math.round(values[i] / total * 100) : 0;
      ctx.fillStyle = color;
      ctx.fillRect(x, y + i * itemH, 8, 8);
      ctx.fillStyle = TEXT;
      ctx.font = fontSize + 'px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(labels[i] + '  ' + values[i] + ' (' + pct + '%)', x + 14, y + i * itemH + 4);
    }
  }

  /* ── 3.  timeline line chart ──────────────────────────────────── */
  function drawTimelineChart(entries) {
    if (drawn['timeline']) return;
    var canvas = getCanvas('chart-timeline');
    if (!canvas) return;
    var w = parseInt(canvas.style.width);
    var h = parseInt(canvas.style.height);
    var ctx = ctxSetup(canvas);

    if (!entries || !entries.length) { drawNoData(ctx, w, h); drawn['timeline'] = true; return; }

    var map = {};
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      var d = parseDate(e.date || e.date_announced || e.announced);
      var key = d ? formatYM(d) : null;
      if (key) map[key] = (map[key] || 0) + (Number(e.jobs_lost) || 0);
    }
    var keys = Object.keys(map).sort();
    if (!keys.length) { drawNoData(ctx, w, h); drawn['timeline'] = true; return; }

    var pts = keys.map(function (k) { return { label: k, value: map[k] }; });
    var maxV = Math.max.apply(null, pts.map(function (p) { return p.value; }));
    if (maxV === 0) maxV = 1;

    var pad  = { top: 10, right: 10, bottom: isMobile() ? 28 : 35, left: isMobile() ? 40 : 48 };
    var plotW = w - pad.left - pad.right;
    var plotH = h - pad.top - pad.bottom;
    var xScale = pts.length > 1 ? plotW / (pts.length - 1) : plotW;
    var yScale = plotH / (maxV * 1.2);

    function x(i) { return pad.left + i * xScale; }
    function y(v) { return pad.top + plotH - v * yScale; }

    var labelStep = Math.max(1, Math.floor(pts.length / (isMobile() ? 4 : 7)));

    /* draw once — no animation on mobile, too slow */
    var drawStatic = function () {
      clearCanvas(ctx, w, h);

      /* y-axis gridlines */
      var ySteps = 3;
      for (var j = 0; j <= ySteps; j++) {
        var yy = pad.top + (plotH * j / ySteps);
        ctx.beginPath();
        ctx.moveTo(pad.left, yy);
        ctx.lineTo(pad.left + plotW, yy);
        ctx.strokeStyle = '#1e1e1e';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      /* y labels */
      ctx.fillStyle = TEXT;
      ctx.font = '9px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      for (var k = 0; k <= ySteps; k++) {
        var val = Math.round(maxV * 1.2 * k / ySteps);
        var yl = pad.top + plotH - (plotH * k / ySteps);
        ctx.fillText(fmtNum(val), pad.left - 6, yl);
      }

      /* filled area */
      ctx.beginPath();
      ctx.moveTo(x(0), pad.top + plotH);
      for (var m = 0; m < pts.length; m++) {
        if (m === 0) ctx.lineTo(x(m), y(pts[m].value));
        else {
          var cp = x(m - 1) + (x(m) - x(m - 1)) * 0.5;
          ctx.bezierCurveTo(cp, y(pts[m - 1].value), cp, y(pts[m].value), x(m), y(pts[m].value));
        }
      }
      ctx.lineTo(x(pts.length - 1), pad.top + plotH);
      ctx.closePath();
      var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
      grad.addColorStop(0, 'rgba(229,57,53,0.25)');
      grad.addColorStop(1, 'rgba(229,57,53,0.01)');
      ctx.fillStyle = grad;
      ctx.fill();

      /* line */
      ctx.beginPath();
      for (var n = 0; n < pts.length; n++) {
        if (n === 0) ctx.moveTo(x(n), y(pts[n].value));
        else {
          var cp2 = x(n - 1) + (x(n) - x(n - 1)) * 0.5;
          ctx.bezierCurveTo(cp2, y(pts[n - 1].value), cp2, y(pts[n].value), x(n), y(pts[n].value));
        }
      }
      ctx.strokeStyle = ACCENT;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      ctx.stroke();

      /* dots + x labels */
      for (var p = 0; p < pts.length; p++) {
        ctx.beginPath();
        ctx.arc(x(p), y(pts[p].value), 3, 0, Math.PI * 2);
        ctx.fillStyle = ACCENT;
        ctx.fill();
        ctx.strokeStyle = BG;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        if (p % labelStep === 0 || p === pts.length - 1) {
          ctx.fillStyle = TEXT;
          ctx.font = '9px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          /* rotate labels if narrow */
          if (pts.length > 12) {
            ctx.save();
            ctx.translate(x(p), pad.top + plotH + 8);
            ctx.rotate(-0.5);
            ctx.fillText(pts[p].label, 0, 0);
            ctx.restore();
          } else {
            ctx.fillText(pts[p].label, x(p), pad.top + plotH + 8);
          }
        }
      }
    };

    if (isMobile() || prefersReducedMotion) {
      drawStatic();
    } else {
      /* smooth reveal animation, then static frame */
      animate(function (t) {
        clearCanvas(ctx, w, h);
        var count = Math.ceil(pts.length * t);

        /* filled area */
        ctx.beginPath();
        ctx.moveTo(x(0), pad.top + plotH);
        for (var q = 0; q < count; q++) {
          if (q === 0) ctx.lineTo(x(q), y(pts[q].value));
          else {
            var cpA = x(q - 1) + (x(q) - x(q - 1)) * 0.5;
            ctx.bezierCurveTo(cpA, y(pts[q - 1].value), cpA, y(pts[q].value), x(q), y(pts[q].value));
          }
        }
        ctx.lineTo(x(count - 1), pad.top + plotH);
        ctx.closePath();
        var gradA = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
        gradA.addColorStop(0, 'rgba(229,57,53,0.25)');
        gradA.addColorStop(1, 'rgba(229,57,53,0.01)');
        ctx.fillStyle = gradA;
        ctx.fill();

        /* line */
        ctx.beginPath();
        for (var r = 0; r < count; r++) {
          if (r === 0) ctx.moveTo(x(r), y(pts[r].value));
          else {
            var cpB = x(r - 1) + (x(r) - x(r - 1)) * 0.5;
            ctx.bezierCurveTo(cpB, y(pts[r - 1].value), cpB, y(pts[r].value), x(r), y(pts[r].value));
          }
        }
        ctx.strokeStyle = ACCENT;
        ctx.lineWidth = 2;
        ctx.lineJoin = 'round';
        ctx.stroke();

        /* dots on last frame */
        if (t >= 0.99) {
          for (var s = 0; s < pts.length; s++) {
            ctx.beginPath();
            ctx.arc(x(s), y(pts[s].value), 3, 0, Math.PI * 2);
            ctx.fillStyle = ACCENT;
            ctx.fill();
            ctx.strokeStyle = BG;
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        }
      }, 800);

      setTimeout(drawStatic, 820);
    }

    drawn['timeline'] = true;
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
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  }

  /* ── exports ──────────────────────────────────────────────────── */
  window.drawIndustryChart      = drawIndustryChart;
  window.drawClassificationChart = drawClassificationChart;
  window.drawTimelineChart      = drawTimelineChart;
})();
