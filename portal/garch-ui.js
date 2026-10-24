/* ARMA-GARCH section of the portal: runs the backtest in worker.js (or on the page if workers are
   unavailable) and renders parameters, the next-period forecast, the conditional VaR chart and the tests. */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var t = function (k) { return window.__t ? window.__t(k) : k; };
  var LEVELS = [0.95, 0.975, 0.99], MODELS = ['un', 'us', 'gn', 'gs'];
  var worker = null, job = 0, G = null, base = null, cur = null;
  function done(msg) {
    if (msg.id !== job) return;
    if (msg.progress) { status(t('gxProg').replace('{i}', msg.progress[0]).replace('{n}', msg.progress[1])); return; }
    if (msg.error) { status(t('gxErr'), true); return; }
    G = msg.result; G.opts = cur; render();
  }

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pc(v, k) { return isFinite(v) ? (100 * v).toFixed(k == null ? 2 : k) + '%' : '∞'; }
  function f(v, k) { return isFinite(v) ? v.toFixed(k) : '∞'; }
  function pv(p) { return p < 1e-4 ? '&lt; 0.0001' : p.toFixed(4); }
  function status(msg, err) { var s = $('gx-status'); s.innerHTML = msg; s.classList.toggle('pt-err', !!err); }
  function lvLabel(p) { return '<bdi dir="ltr">' + (100 * p).toFixed(1).replace('.0', '') + '%</bdi>'; }

  function start() {
    var res = window.__portal && window.__portal.res;
    if (!res) return;
    var CAP = 10000; // the model is re-estimated window by window; keep long series tractable in a browser
    base = res.pts.length > CAP ? { pts: res.pts.slice(-CAP), col: res.col, capped: res.pts.length } : res;
    G = null; $('gx-out').hidden = true;
    var n0 = base.pts.length, opts = { mode: $('gx-mode').value, init: 500, step: Math.max(250, Math.ceil((n0 - 500) / 20)) };
    if (opts.mode === 'oos' && res.pts.length < opts.init + 100) { opts.mode = 'is'; }
    var pts = base.pts.map(function (p) { return { r: p.r }; }), id = ++job;
    status(t('gxBusy'));
    cur = opts;
    try {
      if (!worker) { worker = new Worker('worker.js?v=3'); worker.onmessage = function (e) { done(e.data); }; worker.onerror = function () { worker = null; fallback(); }; }
      worker.postMessage({ id: id, pts: pts, levels: LEVELS, opts: opts });
    } catch (e) { worker = null; fallback(); }
    function fallback() {
      setTimeout(function () {
        try {
          var R = window.Garch.run(pts, LEVELS, opts);
          done({ id: id, result: { oos: R.oos, start: R.start, V: R.V, tests: R.tests, forecast: R.forecast, vol: R.vol, volOos: R.volOos, nBlocks: R.blocks.length, full: R.full } });
        } catch (err) { done({ id: id, error: String(err) }); }
      }, 30);
    }
  }

  function kv(rows) { return rows.map(function (r) { return '<tr><th scope="row">' + r[0] + '</th><td dir="ltr">' + r[1] + '</td></tr>'; }).join(''); }
  function render() {
    if (!G || !base) return;
    var fp = G.full, z = fp.z, n = base.pts.length, nEval = n - G.start;
    var from = base.pts[G.start].d, to = base.pts[n - 1].d;
    status(G.oos && !from ? t('gxDoneOosN').replace('{k}', G.nBlocks).replace('{n}', nEval) : G.oos ? t('gxDoneOos').replace('{k}', G.nBlocks).replace('{n}', nEval).replace('{from}', '<bdi dir="ltr">' + esc(from || '') + '</bdi>')
      : t('gxDoneIs').replace('{n}', nEval)) ;
    if (base.capped) $('gx-status').innerHTML += ' ' + t('gxCap').replace('{n}', base.capped);
    if (G.opts && G.opts.step > 250) $('gx-status').innerHTML += ' ' + t('gxStep').replace('{s}', G.opts.step);
    var cancel = Math.abs(fp.phi + fp.theta) < 0.05 && Math.abs(fp.phi) > 0.3;
    $('gx-parn').textContent = cancel ? t('gxCancel') : '';
    $('gx-par').innerHTML = kv([
      ['c', f(fp.c, 4) + '%'], ['φ · AR(1)', f(fp.phi, 4)], ['θ · MA(1)', f(fp.theta, 4)], ['ω', f(fp.omega, 4) + ' (%²)'],
      ['α₁ · ARCH', f(fp.a, 4)], ['β₁ · GARCH', f(fp.b, 4)], [t('gxPers') + ' α₁ + β₁', f(fp.a + fp.b, 4)], [t('gxLL'), f(fp.ll, 1)]]);
    $('gx-z').innerHTML = kv([['α · ' + t('alpha'), f(z.alpha, 3)], ['β · ' + t('beta'), f(z.beta, 3)], ['σ · ' + t('sigma'), f(z.sigma, 3)], ['μ · ' + t('mu'), f(z.mu, 3)],
      [t('gxMc'), 'α ' + f(fp.zMc.alpha, 2) + ', β ' + f(fp.zMc.beta, 2)]]);
    var fc = '<thead><tr><th scope="col">' + t('measure2') + '</th><th scope="col">' + t('mGN') + '</th><th scope="col">' + t('mGS') + '</th></tr></thead><tbody>';
    G.forecast.forEach(function (r) {
      fc += '<tr><th scope="row">' + t('var') + ' ' + lvLabel(r.p) + '</th><td dir="ltr">' + pc(r.varN) + '</td><td dir="ltr">' + pc(r.varS) + '</td></tr>';
      fc += '<tr><th scope="row">' + t('es') + ' ' + lvLabel(r.p) + '</th><td dir="ltr">' + pc(r.esN) + '</td><td dir="ltr">' + pc(r.esS) + '</td></tr>';
    });
    $('gx-fc').innerHTML = fc + '</tbody>';
    $('gx-out').hidden = false;
    tests(); draw();
  }

  function tests() {
    var j = +$('gx-lv').value, lv = LEVELS[j], pb = 1 - lv, T = G.tests;
    var p3 = function (p) { return p < 0.001 ? '&lt;0.001' : p.toFixed(3); };
    var expN = (T.un[j].n * pb).toFixed(1);
    var rows = MODELS.map(function (m) {
      var o = T[m][j], bad = o.cc < 0.05;
      return '<tr><th scope="row">' + t('m' + m.toUpperCase()) + ' <span class="' + (bad ? 'pt-bad' : 'pt-good') + '">' + (bad ? '✗' : '✓') + '</span></th><td dir="ltr">' + pc(o.avg) + '</td><td dir="ltr">' + o.k + '</td><td dir="ltr">' + p3(o.kup) + '</td><td dir="ltr">' + p3(o.ind) + '</td><td dir="ltr" class="' + (bad ? 'pt-bad' : 'pt-good') + '">' + p3(o.cc) + '</td></tr>';
    }).join('');
    $('gx-bt').innerHTML = '<thead><tr><th scope="col">' + t('gxModel') + '</th><th scope="col">' + t('gxHAvg') + ' ' + lvLabel(lv) + '</th><th scope="col">' + t('gxHHits') + '<br><span class="pt-muted">' + t('gxExpS') + ' ' + expN + '</span></th><th scope="col">' + t('gxHKup') + '</th><th scope="col">' + t('gxHInd') + '</th><th scope="col">' + t('gxHCc') + '</th></tr></thead><tbody>' + rows + '</tbody>';
    // year by year
    var pts = base.pts, start = G.start;
    if (!isFinite(pts[0].tm)) { $('gx-yr').innerHTML = ''; $('gx-yrn').textContent = t('yrNoDates'); return; }
    var ys = {}, order = [];
    for (var i = start; i < pts.length; i++) {
      var y = new Date(pts[i].tm).getUTCFullYear();
      if (!ys[y]) { ys[y] = { n: 0, k: [0, 0, 0, 0] }; order.push(y); }
      ys[y].n++; MODELS.forEach(function (m, q) { if (T[m][j].hits[i - start]) ys[y].k[q]++; });
    }
    var cell = function (k, nn) {
      if (window.Garch.kupiec(k, nn, pb).p >= 0.05) return '<td dir="ltr">' + k + '</td>';
      var many = k > nn * pb; return '<td dir="ltr" class="' + (many ? 'pt-bad' : 'pt-few') + '">' + k + ' ' + (many ? '▲' : '▼') + '</td>';
    };
    var body = order.map(function (y) { var e = ys[y]; return '<tr><th scope="row">' + y + '</th><td dir="ltr">' + (e.n * pb).toFixed(1) + '</td>' + e.k.map(function (k) { return cell(k, e.n); }).join('') + '</tr>'; }).join('');
    var tot = MODELS.map(function (m) { return cell(T[m][j].k, T[m][j].n); }).join('');
    $('gx-yr').innerHTML = '<thead><tr><th scope="col">' + t('yrYear') + '</th><th scope="col">' + t('btExp') + '</th>' + MODELS.map(function (m) { return '<th scope="col">' + t('m' + m.toUpperCase()) + '</th>'; }).join('') + '</tr></thead><tbody>' + body +
      '</tbody><tfoot><tr><th scope="row">' + t('yrAll') + '</th><td dir="ltr">' + (T.un[j].n * pb).toFixed(1) + '</td>' + tot + '</tr></tfoot>';
    $('gx-yrn').innerHTML = t('gxYrNote').replace('{lv}', lvLabel(lv));
  }

  function css(name, fb) { var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); return v || fb; }
  function niceStep(span, k) { var r = span / k, p = Math.pow(10, Math.floor(Math.log10(r))), m = r / p; return (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * p; }
  function draw() {
    if (!G || $('gx-out').hidden) return;
    var cv = $('gx-ts'), c = cv.getContext('2d'), dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.fillStyle = css('--card', '#fff'); c.fillRect(0, 0, W, H); c.font = '12px "JetBrains Mono", ui-monospace, monospace';
    var j = +$('gx-lv').value, s0 = G.start, pts = base.pts, n = pts.length - s0, L = 52, R = 12, Tp = 10, B = 26, pw = W - L - R, ph = H - Tp - B;
    var gn = G.V.gn[j], gs = G.V.gs[j], lo = 0, hi = 0, i;
    for (i = 0; i < n; i++) { var r = pts[s0 + i].r; lo = Math.min(lo, r, -gs[i] / 100); hi = Math.max(hi, r); }
    lo *= 1.05; hi *= 1.05;
    var X = function (k) { return L + k / Math.max(1, n - 1) * pw; }, Y = function (v) { return Tp + (hi - v) / (hi - lo) * ph; };
    var st = niceStep(hi - lo, 5); c.strokeStyle = css('--rule', '#d9dfe8'); c.fillStyle = css('--axis', '#465166'); c.lineWidth = 1; c.textAlign = 'right'; c.textBaseline = 'middle';
    for (var v = Math.ceil(lo / st) * st; v <= hi; v += st) { var yy = Y(v); c.beginPath(); c.moveTo(L, yy); c.lineTo(W - R, yy); c.stroke(); c.fillText((100 * v).toFixed(st < 0.01 ? 1 : 0) + '%', L - 6, yy); }
    c.textAlign = 'center'; c.textBaseline = 'top';
    if (isFinite(pts[s0].tm)) {
      var y0 = new Date(pts[s0].tm).getUTCFullYear(), y1 = new Date(pts[pts.length - 1].tm).getUTCFullYear(), step = Math.max(1, Math.ceil((y1 - y0 + 1) / 6)), last = -1;
      for (i = 0; i < n; i++) { var yr = new Date(pts[s0 + i].tm).getUTCFullYear(); if (yr !== last) { last = yr; if ((yr - y0) % step === 0 && i > 0) { var px = X(i); c.beginPath(); c.moveTo(px, Tp); c.lineTo(px, Tp + ph); c.stroke(); c.fillText(String(yr), px, Tp + ph + 6); } } }
    }
    c.save(); c.beginPath(); c.rect(L, Tp, pw, ph); c.clip();
    c.strokeStyle = css('--accent', '#1f3a6e'); c.lineWidth = 0.8; c.beginPath();
    for (i = 0; i < n; i++) { if (i === 0) c.moveTo(X(i), Y(pts[s0 + i].r)); else c.lineTo(X(i), Y(pts[s0 + i].r)); } c.stroke();
    function line(a, col, w) { c.strokeStyle = col; c.lineWidth = w; c.beginPath(); for (var k = 0; k < n; k++) { var yv = Y(-a[k] / 100); if (k === 0) c.moveTo(X(k), yv); else c.lineTo(X(k), yv); } c.stroke(); }
    line(gn, css('--muted', '#586378'), 1.1); line(gs, css('--err', '#a8322a'), 1.3);
    c.fillStyle = css('--err', '#a8322a');
    for (i = 0; i < n; i++) if (pts[s0 + i].r < -gs[i] / 100) { c.beginPath(); c.arc(X(i), Y(pts[s0 + i].r), 2.3, 0, 2 * Math.PI); c.fill(); }
    c.restore();
    cv.setAttribute('aria-label', t('gxFig').replace(/<[^>]+>/g, '') + ', ' + (100 * LEVELS[j]).toFixed(1).replace('.0', '') + '%');
  }

  function download() {
    if (!G) return;
    var lines = ['date,return,' + LEVELS.map(function (lv) { return 'VaR_arma_garch_normal_' + lv + ',VaR_arma_garch_stable_' + lv; }).join(',') + ',volatility'];
    for (var i = G.start; i < base.pts.length; i++) {
      var k = i - G.start, row = [base.pts[i].d, base.pts[i].r.toPrecision(10)];
      LEVELS.forEach(function (lv, j) { row.push((G.V.gn[j][k] / 100).toPrecision(8), (G.V.gs[j][k] / 100).toPrecision(8)); });
      row.push(G.volOos[k].toPrecision(8)); lines.push(row.join(','));
    }
    var b = new Blob(['﻿' + lines.join('\n') + '\n'], { type: 'text/csv;charset=utf-8' }), a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = String(base.col).replace(/[^\w.-]+/g, '_') + '_arma_garch_var.csv'; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  document.addEventListener('portal:result', start);
  $('gx-mode').addEventListener('change', start);
  $('gx-lv').addEventListener('change', function () { tests(); draw(); });
  $('gx-dl').addEventListener('click', download);
  document.addEventListener('langchange', function () { if (G) render(); });
  var tm = null; window.addEventListener('resize', function () { clearTimeout(tm); tm = setTimeout(draw, 120); });
  window.__garch = { get G() { return G; } };
})();
