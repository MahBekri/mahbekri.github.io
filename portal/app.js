/* Return analysis portal: reads a CSV of prices or returns, runs the analysis in analysis.js and
   renders tables, figures and downloads. Nothing is sent anywhere. */
(function () {
  var P = window.Portal, ST = window.Stable;
  var $ = function (id) { return document.getElementById(id); };
  var t = function (k) { return window.__t ? window.__t(k) : k; };
  var LEVELS = [0.95, 0.975, 0.99];
  var table = null;   // parsed file
  var res = null;     // last analysis

  // ---------- parsing ----------
  function cellNum(s) {
    if (s == null) return NaN;
    s = String(s).trim().replace(/^"|"$/g, '').replace(/−/g, '-').replace(/%$/, '').replace(/\s/g, '');
    if (s === '' || /^(na|n\/a|#n\/a|null|nan|-)$/i.test(s)) return NaN;
    if (!/^[-+]?[\d.,]+(e[-+]?\d+)?$/i.test(s)) return NaN;
    return parseFloat(s);
  }
  function parseDate(s, mf) { // mf: month first (US m/d/yyyy), decided per column
    s = String(s || '').trim().replace(/^"|"$/g, '');
    var TIME = '([ T]\\d{1,2}:\\d{2}(:\\d{2}(\\.\\d+)?)?\\s*(Z|[+-]\\d{2}:?\\d{2})?)?$'; // optional time; anything else is not a date
    var m = s.match(new RegExp('^(\\d{1,2})[./-](\\d{1,2})[./-](\\d{4})' + TIME));
    if (m) return mf ? Date.UTC(+m[3], +m[1] - 1, +m[2]) : Date.UTC(+m[3], +m[2] - 1, +m[1]);
    m = s.match(new RegExp('^(\\d{4})[./-](\\d{1,2})[./-](\\d{1,2})' + TIME));
    if (m) return Date.UTC(+m[1], +m[2] - 1, +m[3]);
    if (!/\d{4}/.test(s) || /[<>&"]/.test(s)) return NaN;
    var v = Date.parse(s); if (!isFinite(v)) return NaN;
    var dt = new Date(v); return Date.UTC(dt.getFullYear(), dt.getMonth(), dt.getDate()); // calendar date as written, whatever the time zone
  }
  function parse(text) {
    var lines = text.replace(/^﻿/, '').split(/\r\n|\n|\r/).filter(function (l) { return l.trim() !== ''; });
    if (lines.length < 3) throw new Error('errFew');
    var sample = lines.slice(0, Math.min(20, lines.length)), delim = null, best = 0;
    ['\t', ';', ',', '|'].forEach(function (d) {
      var c = sample.map(function (l) { return l.replace(/"[^"]*"/g, '').split(d).length - 1; });
      var ok = c.every(function (v) { return v === c[0]; }) && c[0] > 0;
      if (ok && c[0] >= best) { if (!(d === ',' && delim)) { delim = d; best = c[0]; } }
    });
    function split(l) { // quote-aware: "4,742.83" stays one cell
      if (!delim) return l.trim().split(/\s+/);
      var out = [], cur = '', q = false;
      for (var i = 0; i < l.length; i++) {
        var ch = l[i];
        if (ch === '"') { if (q && l[i + 1] === '"') { cur += '"'; i++; } else q = !q; }
        else if (ch === delim && !q) { out.push(cur); cur = ''; }
        else cur += ch;
      }
      out.push(cur); return out;
    }
    var rows = lines.map(function (l) { return split(l).map(function (c) { return c.trim(); }); });
    var decComma = delim !== ',' && rows.slice(1, 40).some(function (r) { return r.some(function (c) { return /^-?\d+,\d+$/.test(c); }); });
    if (decComma) rows = rows.map(function (r) { return r.map(function (c) { return /^[-+]?\d{1,3}(\.\d{3})*,\d+$|^[-+]?\d+,\d+$/.test(c) ? c.replace(/\./g, '').replace(',', '.') : c; }); });
    else rows = rows.map(function (r) { return r.map(function (c) { return /^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(c) ? c.replace(/,/g, '') : c; }); });
    var ncol = rows.reduce(function (m, r) { return Math.max(m, r.length); }, 0); // no apply: very long files exceed the argument limit
    var header = rows[0].some(function (c) { return c !== '' && isNaN(cellNum(c)) && isNaN(parseDate(c)); });
    var names = [], body = header ? rows.slice(1) : rows;
    for (var j = 0; j < ncol; j++) names.push(header && rows[0][j] ? rows[0][j] : (t('colN') + ' ' + (j + 1)));
    var numeric = [], dateCol = -1;
    for (j = 0; j < ncol; j++) {
      var nNum = 0, nDate = 0;
      body.forEach(function (r) { if (isFinite(cellNum(r[j]))) nNum++; if (isFinite(parseDate(r[j]))) nDate++; });
      if (dateCol < 0 && nDate >= 0.9 * body.length && !/^\d+(\.\d+)?$/.test(body[0][j] || '')) dateCol = j;
      else if (nNum >= 0.8 * body.length) numeric.push(j);
    }
    if (!numeric.length) throw new Error('errNoNum');
    var mf = false;
    if (dateCol >= 0) {
      var firstBig = false, secondBig = false, f1 = {}, f2 = {};
      body.forEach(function (r) { var m = String(r[dateCol]).match(/^(\d{1,2})[./-](\d{1,2})[./-]\d{4}/); if (m) { if (+m[1] > 12) firstBig = true; if (+m[2] > 12) secondBig = true; f1[+m[1]] = 1; f2[+m[2]] = 1; } });
      var n1 = Object.keys(f1).length, n2 = Object.keys(f2).length;
      // a field above 12 must be the day; if neither is, the field that never changes is the day (monthly data dated on the 1st)
      mf = secondBig && !firstBig || (!firstBig && !secondBig && n2 === 1 && n1 > 1);
    }
    return { names: names, rows: body, numeric: numeric, dateCol: dateCol, mf: mf };
  }

  // ---------- build the return series ----------
  function series(tb, col, kind, rtype) {
    var pts = [];
    tb.rows.forEach(function (r) {
      var v = cellNum(r[col]); if (!isFinite(v)) return;
      pts.push({ d: tb.dateCol >= 0 ? r[tb.dateCol] : '', tm: tb.dateCol >= 0 ? parseDate(r[tb.dateCol], tb.mf) : NaN, v: v });
    });
    if (pts.length > 1 && isFinite(pts[0].tm) && isFinite(pts[pts.length - 1].tm) && pts[0].tm > pts[pts.length - 1].tm) pts.reverse();
    var vals = pts.map(function (p) { return p.v; });
    if (kind === 'auto') {
      var min = vals.reduce(function (m, v) { return v < m ? v : m; }, Infinity);
      if (min > 0) kind = 'price';
      else { var a = vals.map(Math.abs).sort(function (x, y) { return x - y; }); kind = a[Math.floor(a.length / 2)] > 0.2 ? 'pct' : 'ret'; }
    }
    var out = [];
    if (kind === 'price') {
      for (var i = 1; i < pts.length; i++) {
        var p0 = pts[i - 1].v, p1 = pts[i].v;
        if (!(p0 > 0 && p1 > 0)) continue;
        out.push({ d: pts[i].d, tm: pts[i].tm, r: rtype === 'simple' ? p1 / p0 - 1 : Math.log(p1 / p0) });
      }
    } else pts.forEach(function (p) { out.push({ d: p.d, tm: p.tm, r: kind === 'pct' ? p.v / 100 : p.v }); });
    return { pts: out, kind: kind };
  }
  function frequency(pts, choice) {
    if (choice !== 'auto') return +choice;
    var gaps = [];
    for (var i = 1; i < pts.length; i++) if (isFinite(pts[i].tm) && isFinite(pts[i - 1].tm)) gaps.push((pts[i].tm - pts[i - 1].tm) / 864e5);
    if (gaps.length < 5) return 252;
    gaps.sort(function (a, b) { return a - b; });
    var g = gaps[Math.floor(gaps.length / 2)];
    return g <= 3 ? 252 : g <= 10 ? 52 : g <= 40 ? 12 : g <= 120 ? 4 : 1;
  }

  // ---------- run ----------
  function status(msg, err) { var s = $('pt-status'); s.innerHTML = msg; s.classList.toggle('pt-err', !!err); }
  function load(text, name, defaultCol) {
    try { table = parse(text); }
    catch (e) { table = null; res = null; $('pt-opts').hidden = true; $('results').hidden = true; status(t(e.message in (window.__T_en || {}) ? e.message : 'errRead'), true); return; }
    table.file = name;
    var sel = $('pt-col'); sel.innerHTML = '';
    table.numeric.forEach(function (j) { var o = document.createElement('option'); o.value = j; o.textContent = table.names[j]; sel.appendChild(o); });
    var pick = table.numeric[table.numeric.length - 1];
    if (/close|adj|price|last|value|ret/i.test(table.names.join(' '))) {
      for (var k = table.numeric.length - 1; k >= 0; k--) if (/adj/i.test(table.names[table.numeric[k]])) { pick = table.numeric[k]; break; }
      if (!/adj/i.test(table.names[pick])) for (k = table.numeric.length - 1; k >= 0; k--) if (/close|price|last|ret/i.test(table.names[table.numeric[k]])) { pick = table.numeric[k]; break; }
    }
    if (defaultCol != null) table.numeric.forEach(function (j) { if (table.names[j] === defaultCol) pick = j; });
    sel.value = pick;
    $('pt-opts').hidden = false;
    run();
  }
  function run() {
    if (!table) return;
    status(t('stBusy'));
    setTimeout(function () {
      var col = +$('pt-col').value, s = series(table, col, $('pt-kind').value, $('pt-rt').value);
      var x = s.pts.map(function (p) { return p.r; });
      $('pt-rt').closest('.pt-opt').hidden = s.kind !== 'price';
      if (x.length < 30) { $('results').hidden = true; res = null; status(t('errFew'), true); return; }
      var d = P.describe(x), fit = P.fitStable(d.sorted);
      if (!fit) { $('results').hidden = true; res = null; status(t('errFlat'), true); return; }
      res = { col: table.names[col], file: table.file, kind: s.kind, rtype: $('pt-rt').value, pts: s.pts, d: d, fit: fit,
        ann: frequency(s.pts, $('pt-freq').value), risk: P.risk(d, fit, LEVELS) };
      $('results').hidden = false;
      render();
      try { document.dispatchEvent(new CustomEvent('portal:result')); } catch (e) {}
    }, 30);
  }

  // ---------- rendering ----------
  function pc(v, k) { return isFinite(v) ? (100 * v).toFixed(k == null ? 2 : k) + '%' : '∞'; }
  function f(v, k) { return isFinite(v) ? v.toFixed(k) : '∞'; }
  function kv(id, rows) {
    $(id).innerHTML = rows.map(function (r) { var word = !/\d/.test(String(r[1]).replace(/<[^>]+>/g, '')); return '<tr><th scope="row">' + r[0] + '</th><td dir="ltr"' + (word ? ' class="pt-word"' : '') + '>' + r[1] + '</td></tr>'; }).join(''); // words in the body font, numbers in mono
  }
  function render() {
    if (!res) return;
    var d = res.d, fit = res.fit, p = res.pts;
    var kindTxt = { price: t(res.rtype === 'simple' ? 'kindPs' : 'kindPl'), ret: t('kindR'), pct: t('kindR') }[res.kind];
    status(t('stDone').replace('{n}', d.n).replace('{col}', '<bdi>' + esc(res.col) + '</bdi>').replace('{kind}', kindTxt));
    var period = p[0].d && p[p.length - 1].d ? '<bdi dir="ltr">' + esc(p[0].d) + ' –</bdi><wbr> <bdi dir="ltr">' + esc(p[p.length - 1].d) + '</bdi>' : '—';
    var fq = { 252: t('fD'), 52: t('fW'), 12: t('fM'), 4: t('fQ'), 1: t('fY') }[res.ann];
    kv('pt-sum', [[t('obs'), d.n], [t('period'), period], [t('freq'), fq], [t('mean'), pc(d.mean, 3)], [t('sd'), pc(d.sd, 3)],
      [t('annVol') + ' <bdi dir="ltr">(×√' + res.ann + ')</bdi>', pc(d.sd * Math.sqrt(res.ann))], [t('skew'), f(d.skew, 3)], [t('kurt'), f(d.kurt, 3)],
      [t('min'), pc(d.min)], [t('max'), pc(d.max)]]);
    kv('pt-jb', [[t('jb'), f(d.jb, 1)], [t('jbp'), d.jbP < 1e-4 ? '&lt; 0.0001' : f(d.jbP, 4)]]);
    $('pt-jbv').textContent = d.jbP < 0.05 ? t('jbRej') : t('jbNot');
    kv('pt-fit', [['α · ' + t('alpha'), f(fit.alpha, 3)], ['β · ' + t('beta'), f(fit.beta, 3)], ['σ · ' + t('sigma'), pc(fit.sigma, 3)], ['μ · ' + t('mu'), pc(fit.mu, 3)]]);
    $('pt-fitn').innerHTML = (fit.alpha >= 2 ? t('fitG') : fit.alpha <= 1 + 1e-9 ? t('fitHeavy') : t('fitOk')) + (fit.low ? ' ' + t('fitLow') : '') + (d.n < 250 ? ' ' + t('fewObs') : '');
    var rows = '<thead><tr><th scope="col">' + t('measure') + '</th><th scope="col">' + t('hist') + '</th><th scope="col">' + t('normal') + '</th><th scope="col">' + t('stable') + '</th></tr></thead><tbody>';
    res.risk.forEach(function (r) {
      var lv = '<bdi dir="ltr">' + (100 * r.p).toFixed(1).replace('.0', '') + '%</bdi>';
      rows += '<tr><th scope="row">' + t('var') + ' ' + lv + '</th><td>' + pc(r.hist.VaR) + '</td><td>' + pc(r.norm.VaR) + '</td><td>' + pc(r.stab.VaR) + '</td></tr>';
      rows += '<tr><th scope="row">' + t('es') + ' ' + lv + '</th><td>' + pc(r.hist.ES) + '</td><td>' + pc(r.norm.ES) + '</td><td>' + pc(r.stab.ES) + '</td></tr>';
    });
    $('pt-risk').innerHTML = rows + '</tbody>';
    var thin = res.risk[res.risk.length - 1].hist.n;
    $('pt-riskn').textContent = t('riskN').replace('{k}', thin);
    draw();
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // ---------- charts ----------
  function css(name, fb) { var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); return v || fb; }
  function frame(canvas) {
    var ctx = canvas.getContext('2d'), dpr = window.devicePixelRatio || 1, W = canvas.clientWidth, H = canvas.clientHeight;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.fillStyle = css('--card', '#ffffff'); ctx.fillRect(0, 0, W, H);
    ctx.font = '11px "JetBrains Mono", ui-monospace, monospace'; ctx.lineWidth = 1;
    return { ctx: ctx, W: W, H: H, L: 52, R: 12, T: 10, B: 26 };
  }
  function niceStep(span, n) { var r = span / n, p = Math.pow(10, Math.floor(Math.log10(r))), m = r / p; return (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * p; }
  function grid(F, X, Y, xt, yt) {
    var c = F.ctx, muted = css('--muted', '#586378'); c.strokeStyle = css('--rule', '#d9dfe8'); c.fillStyle = muted;
    c.textAlign = 'right'; c.textBaseline = 'middle';
    yt.forEach(function (v) { var y = Y(v[0]); c.beginPath(); c.moveTo(F.L, y); c.lineTo(F.W - F.R, y); c.stroke(); c.fillText(v[1], F.L - 6, y); });
    c.textAlign = 'center'; c.textBaseline = 'top';
    xt.forEach(function (v) { var x = X(v[0]); c.beginPath(); c.moveTo(x, F.T); c.lineTo(x, F.H - F.B); c.stroke(); c.fillText(v[1], x, F.H - F.B + 6); });
  }
  function drawTs() {
    var cv = $('pt-ts'), F = frame(cv), c = F.ctx, x = res.pts, n = x.length, d = res.d;
    var lim = Math.max(Math.abs(d.min), Math.abs(d.max)) * 1.05, pw = F.W - F.L - F.R, ph = F.H - F.T - F.B;
    var X = function (i) { return F.L + i / Math.max(1, n - 1) * pw; }, Y = function (v) { return F.T + (lim - v) / (2 * lim) * ph; };
    var st = niceStep(2 * lim, 4), yt = [];
    for (var v = -Math.floor(lim / st) * st; v <= lim + 1e-12; v += st) yt.push([v, (100 * v).toFixed(st < 0.01 ? 1 : 0) + '%']);
    var xt = [];
    if (isFinite(x[0].tm)) {
      var y0 = new Date(x[0].tm).getUTCFullYear(), y1 = new Date(x[n - 1].tm).getUTCFullYear(), step = Math.max(1, Math.ceil((y1 - y0 + 1) / 6)), last = -1;
      for (var i = 0; i < n; i++) { var yr = new Date(x[i].tm).getUTCFullYear(); if (yr !== last) { last = yr; if ((yr - y0) % step === 0 && (yr !== y0 || i < n * 0.02)) xt.push([i, String(yr)]); } }
    } else for (var k = 0; k <= 4; k++) { var ii = Math.round(k * (n - 1) / 4); xt.push([ii, String(ii + 1)]); }
    grid(F, X, Y, xt, yt);
    c.save(); c.beginPath(); c.rect(F.L, F.T, pw, ph); c.clip();
    c.strokeStyle = css('--accent', '#1f3a6e'); c.lineWidth = 1; c.beginPath();
    for (i = 0; i < n; i++) { if (i === 0) c.moveTo(X(i), Y(x[i].r)); else c.lineTo(X(i), Y(x[i].r)); }
    c.stroke();
    var lv = +$('pt-lv').value, rk = res.risk[lv], vs = -rk.stab.VaR, vn = -rk.norm.VaR;
    c.lineWidth = 1.4;
    c.strokeStyle = css('--muted', '#586378'); c.setLineDash([2, 3]); c.beginPath(); c.moveTo(F.L, Y(vn)); c.lineTo(F.W - F.R, Y(vn)); c.stroke();
    c.strokeStyle = css('--err', '#b3261e'); c.setLineDash([6, 4]); c.beginPath(); c.moveTo(F.L, Y(vs)); c.lineTo(F.W - F.R, Y(vs)); c.stroke();
    c.setLineDash([]); c.fillStyle = css('--err', '#b3261e');
    for (i = 0; i < n; i++) if (x[i].r < vs) { c.beginPath(); c.arc(X(i), Y(x[i].r), 2.2, 0, 2 * Math.PI); c.fill(); }
    c.restore();
    var lvs = (100 * rk.p).toFixed(1).replace('.0', '') + '%';
    cv.setAttribute('aria-label', t('figTs') + ', ' + lvs + ': ' + t('lgNVar').replace(/<[^>]+>/g, '') + ' ' + pc(-vn) + ', ' + t('lgSVar').replace(/<[^>]+>/g, '') + ' ' + pc(-vs));
    backtest(lv);
  }
  function kupiec(k, n, p) { // unconditional coverage; p = breach probability
    var lr;
    if (k === 0) lr = -2 * n * Math.log(1 - p);
    else if (k === n) lr = -2 * n * Math.log(p);
    else { var q = k / n; lr = -2 * ((n - k) * Math.log(1 - p) + k * Math.log(p) - (n - k) * Math.log(1 - q) - k * Math.log(q)); }
    lr = Math.max(0, lr);
    return 1 - ST.erf(Math.sqrt(lr / 2)); // chi-square(1) tail
  }
  function backtest(lv) {
    var rk = res.risk[lv], n = res.pts.length, pb = 1 - rk.p, lvs = '<bdi dir="ltr">' + (100 * rk.p).toFixed(1).replace('.0', '') + '%</bdi>';
    var cols = [rk.norm.VaR, rk.stab.VaR].map(function (v) {
      var k = 0; res.pts.forEach(function (p) { if (p.r < -v) k++; });
      return { v: v, k: k, p: kupiec(k, n, pb) };
    });
    var row = function (h, f) { return '<tr><th scope="row">' + h + '</th>' + cols.map(function (c) { return '<td dir="ltr">' + f(c) + '</td>'; }).join('') + '</tr>'; };
    $('pt-bt').innerHTML = '<thead><tr><th scope="col">' + t('measure2') + '</th><th scope="col">' + t('normal') + '</th><th scope="col">' + t('stable') + '</th></tr></thead><tbody>' +
      row(t('btVar') + ' ' + lvs, function (c) { return pc(c.v); }) +
      row(t('btHits'), function (c) { return c.k + ' <span class="pt-muted">(' + (100 * c.k / n).toFixed(2) + '%)</span>'; }) +
      row(t('btExp'), function () { return (pb * n).toFixed(1) + ' <span class="pt-muted">(' + (100 * pb).toFixed(1).replace('.0', '') + '%)</span>'; }) +
      row(t('btP'), function (c) { return c.p < 1e-4 ? '&lt; 0.0001' : c.p.toFixed(4); }) +
      row(t('btVerd'), function (c) { return '<span class="' + (c.p < 0.05 ? 'pt-bad' : 'pt-good') + '">' + t(c.p < 0.05 ? 'btRej' : 'btOk') + '</span>'; }) + '</tbody>';
    $('pt-btn').innerHTML = t('btNote').replace('{lv}', lvs).replace('{e}', (pb * n).toFixed(0)).replace('{n}', n);
    yearly(cols, pb, lvs);
  }
  function yearly(cols, pb, lvs) {
    var tb = $('pt-yr'), note = $('pt-yrn'), pts = res.pts;
    if (!isFinite(pts[0].tm)) { tb.innerHTML = ''; note.textContent = t('yrNoDates'); return; }
    var ys = {}, order = [];
    pts.forEach(function (p) {
      var y = new Date(p.tm).getUTCFullYear();
      if (!ys[y]) { ys[y] = { n: 0, k: [0, 0] }; order.push(y); }
      ys[y].n++; cols.forEach(function (c, j) { if (p.r < -c.v) ys[y].k[j]++; });
    });
    var cell = function (k, n) { // flag rejections: too many breaches (risk understated) or too few (overstated)
      if (kupiec(k, n, pb) >= 0.05) return '<td dir="ltr">' + k + '</td>';
      var many = k > n * pb;
      return '<td dir="ltr" class="' + (many ? 'pt-bad' : 'pt-few') + '">' + k + ' ' + (many ? '▲' : '▼') + '</td>';
    };
    var body = order.map(function (y) {
      var e = ys[y];
      return '<tr><th scope="row">' + y + '</th><td dir="ltr">' + e.n + '</td><td dir="ltr">' + (e.n * pb).toFixed(1) + '</td>' + cell(e.k[0], e.n) + cell(e.k[1], e.n) + '</tr>';
    }).join('');
    var n = pts.length;
    tb.innerHTML = '<thead><tr><th scope="col">' + t('yrYear') + '</th><th scope="col">' + t('yrN') + '</th><th scope="col">' + t('btExp') + '</th><th scope="col">' + t('normal') + '</th><th scope="col">' + t('stable') + '</th></tr></thead><tbody>' + body +
      '</tbody><tfoot><tr><th scope="row">' + t('yrAll') + '</th><td dir="ltr">' + n + '</td><td dir="ltr">' + (n * pb).toFixed(1) + '</td>' + cell(cols[0].k, n) + cell(cols[1].k, n) + '</tr></tfoot>';
    note.innerHTML = t('yrNote').replace('{lv}', lvs);
  }

  function drawHist() {
    var cv = $('pt-hist'), F = frame(cv), c = F.ctx, d = res.d, s = d.sorted, n = s.length, fit = res.fit, log = $('pt-log').checked;
    var lo = s[0], hi = s[n - 1], span = hi - lo; lo -= 0.03 * span; hi += 0.03 * span;
    var nb = Math.max(30, Math.min(120, Math.round(2 * Math.sqrt(n)))), w = (hi - lo) / nb, cnt = new Array(nb).fill(0);
    s.forEach(function (v) { cnt[Math.min(nb - 1, Math.floor((v - lo) / w))]++; });
    var dens = cnt.map(function (k) { return k / (n * w); });
    var NP = 240, xs = [], fn = [], fs = [];
    for (var i = 0; i < NP; i++) {
      var xv = lo + (hi - lo) * i / (NP - 1), z = (xv - d.mean) / d.sd; xs.push(xv);
      fn.push(Math.exp(-0.5 * z * z) / (d.sd * Math.sqrt(2 * Math.PI))); fs.push(ST.pdf(xv, fit.alpha, fit.beta, fit.sigma, fit.mu));
    }
    var top = Math.max(Math.max.apply(null, dens), Math.max.apply(null, fs), Math.max.apply(null, fn));
    var pw = F.W - F.L - F.R, ph = F.H - F.T - F.B, X = function (v) { return F.L + (v - lo) / (hi - lo) * pw; }, Y, yt = [];
    if (log) {
      var yhi = Math.pow(10, Math.ceil(Math.log10(top))), ylo = Math.max(yhi * 1e-5, 0.3 / (n * w));
      ylo = Math.pow(10, Math.floor(Math.log10(ylo)));
      Y = function (v) { return F.T + (Math.log10(yhi) - Math.log10(Math.max(v, ylo / 10))) / (Math.log10(yhi) - Math.log10(ylo)) * ph; };
      for (var e = Math.log10(yhi); e >= Math.log10(ylo) - 1e-9; e--) yt.push([Math.pow(10, e), '1e' + Math.round(e)]);
    } else {
      var tp = top * 1.08; Y = function (v) { return F.T + (tp - v) / tp * ph; };
      var st = niceStep(tp, 4); for (var v = 0; v <= tp; v += st) yt.push([v, v === 0 ? '0' : String(+v.toPrecision(3))]);
    }
    var xst = niceStep(hi - lo, 5), xt = [];
    for (v = Math.ceil(lo / xst) * xst; v <= hi; v += xst) xt.push([v, (100 * v).toFixed(xst < 0.01 ? 1 : 0) + '%']);
    grid(F, X, Y, xt, yt);
    c.save(); c.beginPath(); c.rect(F.L, F.T, pw, ph); c.clip();
    c.fillStyle = css('--bar', 'rgba(47, 99, 168, 0.22)');
    dens.forEach(function (v, i) { if (v <= 0) return; var x0 = X(lo + i * w), x1 = X(lo + (i + 1) * w), y = Y(v); c.fillRect(x0, y, Math.max(1, x1 - x0 - 0.5), F.H - F.B - y); });
    function line(ys, col, dash, wd) { c.strokeStyle = col; c.setLineDash(dash); c.lineWidth = wd; c.beginPath(); ys.forEach(function (y, i) { if (i === 0) c.moveTo(X(xs[i]), Y(y)); else c.lineTo(X(xs[i]), Y(y)); }); c.stroke(); }
    line(fn, css('--muted', '#586378'), [5, 4], 1.5); line(fs, css('--accent', '#1f3a6e'), [], 2.2); c.restore();
    cv.setAttribute('aria-label', t('figHist') + (log ? ', log' : '') + ': α ' + f(fit.alpha, 2) + ', β ' + f(fit.beta, 2));
  }
  function draw() { if (!res || $('results').hidden) return; drawTs(); drawHist(); }

  // ---------- downloads ----------
  function save(name, text, type) {
    var b = new Blob(['﻿' + text], { type: type || 'text/csv;charset=utf-8' }), a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function stem() { return String(res.col).replace(/[^\w.-]+/g, '_'); }
  $('pt-dlr').addEventListener('click', function () {
    if (!res) return;
    var head = (res.pts[0].d ? 'date,' : '') + (res.kind === 'price' ? (res.rtype === 'simple' ? 'simple_return' : 'log_return') : 'return');
    save(stem() + '_returns.csv', head + '\n' + res.pts.map(function (p) { return (p.d ? p.d + ',' : '') + p.r.toPrecision(10); }).join('\n') + '\n');
  });
  $('pt-dlx').addEventListener('click', function () {
    if (!res) return;
    var d = res.d, fit = res.fit, L = [['section', 'item', 'value']];
    L.push(['series', 'column', res.col], ['series', 'observations', d.n], ['series', 'first', res.pts[0].d], ['series', 'last', res.pts[res.pts.length - 1].d],
      ['series', 'periods_per_year', res.ann], ['statistics', 'mean', d.mean], ['statistics', 'std_dev', d.sd], ['statistics', 'annualised_volatility', d.sd * Math.sqrt(res.ann)],
      ['statistics', 'skewness', d.skew], ['statistics', 'excess_kurtosis', d.kurt], ['statistics', 'min', d.min], ['statistics', 'max', d.max],
      ['normality', 'jarque_bera', d.jb], ['normality', 'p_value', d.jbP],
      ['stable_fit_S1', 'alpha', fit.alpha], ['stable_fit_S1', 'beta', fit.beta], ['stable_fit_S1', 'sigma', fit.sigma], ['stable_fit_S1', 'mu', fit.mu]);
    res.risk.forEach(function (r) {
      ['hist', 'norm', 'stab'].forEach(function (m) {
        var nm = { hist: 'historical', norm: 'normal', stab: 'stable' }[m];
        L.push(['risk_' + nm, 'VaR_' + r.p, r[m].VaR], ['risk_' + nm, 'ES_' + r.p, r[m].ES]);
      });
    });
    save(stem() + '_results.csv', L.map(function (r) { return r.map(function (v) { return typeof v === 'number' ? (isFinite(v) ? +v.toPrecision(8) : 'inf') : '"' + String(v).replace(/"/g, '""') + '"'; }).join(','); }).join('\n') + '\n');
  });
  document.querySelectorAll('.pt-png').forEach(function (b) {
    b.addEventListener('click', function () {
      var cv = $(b.dataset.canvas); if (!cv.toBlob) return;
      cv.toBlob(function (bl) { var a = document.createElement('a'); a.href = URL.createObjectURL(bl); a.download = stem() + '_' + b.dataset.name; document.body.appendChild(a); a.click(); setTimeout(function () { a.remove(); }, 500); });
    });
  });

  // ---------- inputs ----------
  $('pt-file').addEventListener('change', function () {
    var fl = this.files && this.files[0]; if (!fl) return;
    if (fl.size > 30e6) { status(t('errBig'), true); return; }
    var rd = new FileReader();
    rd.onload = function () { load(String(rd.result), fl.name); };
    rd.onerror = function () { status(t('errRead'), true); };
    rd.readAsText(fl);
  });
  $('pt-go').addEventListener('click', function () { var v = $('pt-text').value; if (v.trim()) load(v, 'pasted'); });
  $('pt-sample').addEventListener('click', function () {
    status(t('stBusy'));
    fetch('../book/data/prices.csv').then(function (r) { if (!r.ok) throw 0; return r.text(); })
      .then(function (txt) { load(txt, 'prices.csv', 'DJI'); }).catch(function () { status(t('errRead'), true); });
  });
  ['pt-col', 'pt-kind', 'pt-rt', 'pt-freq'].forEach(function (id) { $(id).addEventListener('change', run); });
  $('pt-log').addEventListener('change', draw);
  $('pt-lv').addEventListener('change', drawTs);
  document.addEventListener('langchange', function () { if (res) render(); });
  var tmr = null;
  window.addEventListener('resize', function () { clearTimeout(tmr); tmr = setTimeout(draw, 120); });
  window.__portal = { load: load, get res() { return res; } };
})();
