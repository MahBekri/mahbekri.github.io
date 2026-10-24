/* Risk analysis of a return series: descriptive statistics, normal and stable fits, value at risk and
   expected shortfall (historical, normal, stable), and Kupiec's unconditional coverage test.
   Runs in a Web Worker (worker.js) or, as a fallback, on the page. Needs assets/stable.js. */
(function (root) {
  'use strict';
  var S = root.Stable;
  var LEVELS = [0.95, 0.975, 0.99];
  function kupiec(x, n, p) {
    var lr;
    if (x === 0) lr = -2 * n * Math.log(1 - p);
    else if (x === n) lr = -2 * n * Math.log(p);
    else { var ph = x / n; lr = -2 * ((n - x) * Math.log(1 - p) + x * Math.log(p) - (n - x) * Math.log(1 - ph) - x * Math.log(ph)); }
    lr = Math.max(0, lr);
    return { lr: lr, p: S.erfc(Math.sqrt(lr / 2)) };
  }
  function analyse(x) {
    var n = x.length, i, mean = 0;
    for (i = 0; i < n; i++) mean += x[i];
    mean /= n;
    var m2 = 0, m3 = 0, m4 = 0;
    for (i = 0; i < n; i++) { var d = x[i] - mean, d2 = d * d; m2 += d2; m3 += d2 * d; m4 += d2 * d2; }
    m2 /= n; m3 /= n; m4 /= n;
    var sd = Math.sqrt(m2 * n / (n - 1)), skew = m3 / Math.pow(m2, 1.5), kurt = m4 / (m2 * m2) - 3;
    var jb = n / 6 * (skew * skew + kurt * kurt / 4);
    var xs = x.slice().sort(function (a, b) { return a - b; });
    var stats = { n: n, mean: mean, sd: sd, skew: skew, kurt: kurt, min: xs[0], max: xs[n - 1], jb: jb, jbP: Math.exp(-jb / 2) };

    var quick = S.fit(x), st = quick, method = 'ecf';
    if (n >= 100) { try { st = S.mle(x, quick); method = 'mle'; } catch (e) { st = quick; } }

    var risk = LEVELS.map(function (c) {
      var p = 1 - c, q = S.quantSorted(xs, p), tail = 0, k = 0;
      for (i = 0; i < n && xs[i] <= q; i++) { tail += xs[i]; k++; }
      var z = S.normInv(p), ve = S.varEs(p, st.alpha, st.beta, st.sigma, st.mu);
      return {
        level: c,
        hist: { VaR: -q, ES: -tail / k },
        normal: { VaR: -(mean + sd * z), ES: -mean + sd * S.normPdf(z) / p },
        stable: { VaR: ve.VaR, ES: ve.ES }
      };
    });
    var backtest = risk.filter(function (r) { return r.level !== 0.975; }).map(function (r) {
      var p = 1 - r.level, out = { level: r.level, expected: n * p };
      ['hist', 'normal', 'stable'].forEach(function (m) {
        var v = -r[m].VaR, cnt = 0;
        for (var j = 0; j < n; j++) if (x[j] < v) cnt++;
        out[m] = { count: cnt, test: kupiec(cnt, n, p) };
      });
      return out;
    });

    // density curves for the histogram figure
    var lo = xs[Math.floor(0.001 * (n - 1))], hi = xs[Math.ceil(0.999 * (n - 1))], pad = 0.15 * (hi - lo);
    var r99 = risk[2], far = Math.max(r99.stable.VaR, r99.normal.VaR, r99.hist.VaR) * 1.15;
    var x0 = Math.min(lo - pad, -far + mean), x1 = hi + pad, gx = [], fs = [], fn = [];
    for (i = 0; i <= 240; i++) {
      var xx = x0 + (x1 - x0) * i / 240;
      gx.push(xx); fs.push(S.pdf(xx, st.alpha, st.beta, st.sigma, st.mu)); fn.push(S.normPdf((xx - mean) / sd) / sd);
    }
    return { stats: stats, normal: { mu: mean, sd: sd }, stable: { alpha: st.alpha, beta: st.beta, sigma: st.sigma, mu: st.mu, method: method },
      risk: risk, backtest: backtest, curve: { x: gx, stable: fs, normal: fn } };
  }
  root.analyse = analyse;
})(this);
