/* ARMA(1,1)-GARCH(1,1) with normal and stable innovations, and VaR backtests for the portal.
   Mean:      r_t = c + phi r_{t-1} + theta e_{t-1} + e_t,   e_t = s_t z_t
   Variance:  s_t^2 = omega + a e_{t-1}^2 + b s_{t-1}^2
   Estimation is two-step: Gaussian quasi-maximum likelihood for the ARMA-GARCH parameters, then
   McCulloch's quantile fit of a stable law to the standardised residuals z_t (stable innovations).
   Requires stable.js and analysis.js. Returns are scaled to per cent internally. */
(function (root) {
  var P = root.Portal, ST = root.Stable;
  var LN2PI = Math.log(2 * Math.PI);

  // ---------- parameter transforms (keep the model stationary and the variance positive) ----------
  function unpack(u) {
    var e1 = Math.exp(u[4]), e2 = Math.exp(u[5]), d = 1 + e1 + e2;
    return { c: u[0], phi: 0.99 * Math.tanh(u[1]), theta: 0.99 * Math.tanh(u[2]), omega: Math.exp(u[3]), a: 0.999 * e1 / d, b: 0.999 * e2 / d };
  }
  function pack(p) {
    var s = 1 - (p.a + p.b) / 0.999;
    return [p.c, Math.atanh(p.phi / 0.99), Math.atanh(p.theta / 0.99), Math.log(p.omega), Math.log(p.a / 0.999 / s), Math.log(p.b / 0.999 / s)];
  }

  // ---------- filter: one-step-ahead conditional mean and variance ----------
  // s0: starting variance (sample variance of the estimation window); m0: starting return (its mean)
  function filter(x, p, from, to, s0, m0) {
    var n = to - from, mu = new Float64Array(n + 1), s2 = new Float64Array(n + 1), e = new Float64Array(n);
    var rPrev = m0, ePrev = 0, sPrev = s0;
    for (var i = 0; i <= n; i++) {
      mu[i] = p.c + p.phi * rPrev + p.theta * ePrev;
      s2[i] = i === 0 ? s0 : p.omega + p.a * ePrev * ePrev + p.b * sPrev;
      if (i === n) break;
      var r = x[from + i]; e[i] = r - mu[i];
      rPrev = r; ePrev = e[i]; sPrev = s2[i];
    }
    return { mu: mu, s2: s2, e: e }; // mu[n], s2[n] are the forecast for the next period
  }
  function negLL(x, from, to, s0, m0) {
    return function (u) {
      var p = unpack(u), rPrev = m0, ePrev = 0, sPrev = s0, ll = 0;
      for (var t = from; t < to; t++) {
        var mu = p.c + p.phi * rPrev + p.theta * ePrev, s2 = t === from ? s0 : p.omega + p.a * ePrev * ePrev + p.b * sPrev;
        if (!(s2 > 0) || !isFinite(s2)) return 1e300;
        var e = x[t] - mu; ll += LN2PI + Math.log(s2) + e * e / s2;
        rPrev = x[t]; ePrev = e; sPrev = s2;
      }
      return 0.5 * ll;
    };
  }

  // ---------- Nelder-Mead ----------
  function nelderMead(f, x0, step, maxIt, tol) {
    tol = tol || 1e-10;
    var n = x0.length, S = [x0.slice()], F = [f(x0)], i, j;
    for (i = 0; i < n; i++) { var v = x0.slice(); v[i] += step[i]; S.push(v); F.push(f(v)); }
    for (var it = 0; it < maxIt; it++) {
      var idx = F.map(function (_, k) { return k; }).sort(function (a, b) { return F[a] - F[b]; });
      S = idx.map(function (k) { return S[k]; }); F = idx.map(function (k) { return F[k]; });
      if (Math.abs(F[n] - F[0]) <= tol * (Math.abs(F[0]) + 1e-10)) break;
      var cen = new Array(n).fill(0);
      for (i = 0; i < n; i++) for (j = 0; j < n; j++) cen[j] += S[i][j] / n;
      var pt = function (t) { return cen.map(function (c, k) { return c + t * (S[n][k] - c); }); };
      var xr = pt(-1), fr = f(xr);
      if (fr < F[0]) { var xe = pt(-2), fe = f(xe); if (fe < fr) { S[n] = xe; F[n] = fe; } else { S[n] = xr; F[n] = fr; } }
      else if (fr < F[n - 1]) { S[n] = xr; F[n] = fr; }
      else {
        var xc = fr < F[n] ? pt(-0.5) : pt(0.5), fc = f(xc);
        if (fc < Math.min(fr, F[n])) { S[n] = xc; F[n] = fc; }
        else for (i = 1; i <= n; i++) { S[i] = S[i].map(function (v, k) { return S[0][k] + 0.5 * (v - S[0][k]); }); F[i] = f(S[i]); }
      }
    }
    var b = 0; for (i = 1; i <= n; i++) if (F[i] < F[b]) b = i;
    return { x: S[b], f: F[b] };
  }


  // ---------- maximum likelihood for the stable innovations (profile likelihood) ----------
  // For given (alpha, beta) the standard density is tabulated once on a sinh-spaced grid; scale and
  // location are then optimised on the interpolated log density, so each outer step costs ~150 densities.
  function stableTable(al, be) {
    var N = 150, U = 60, g = [], lf = [];
    for (var i = 0; i < N; i++) { var u = Math.sinh(-Math.asinh(U) + 2 * Math.asinh(U) * i / (N - 1)); g.push(u); lf.push(Math.log(Math.max(1e-300, ST.pdf(u, al, be, 1, 0)))); }
    return { g: g, lf: lf, al: al, be: be, U: U, N: N };
  }
  function tabLogPdf(T, u) {
    if (u <= -T.U || u >= T.U) { // power-law tail beyond the grid
      var side = u < 0 ? 0 : T.N - 1, u0 = T.g[side];
      return T.lf[side] - (T.al + 1) * Math.log(Math.abs(u) / Math.abs(u0));
    }
    var s = (Math.asinh(u) + Math.asinh(T.U)) / (2 * Math.asinh(T.U)) * (T.N - 1), i = Math.min(T.N - 2, Math.floor(s)), w = s - i;
    return T.lf[i] + w * (T.lf[i + 1] - T.lf[i]);
  }
  function profile(z, T, sm) { // best (sigma, mu) for this table; returns negative log-likelihood
    var n = z.length, f = function (v) {
      var sg = Math.exp(v[0]), m = v[1], ll = 0;
      for (var i = 0; i < n; i++) ll += tabLogPdf(T, (z[i] - m) / sg);
      return -(ll - n * Math.log(sg));
    };
    var r = nelderMead(f, [Math.log(sm[0]), sm[1]], [0.04, 0.02], 150, 1e-8);
    return { f: r.f, sigma: Math.exp(r.x[0]), mu: r.x[1] };
  }
  function stableMLE(z, start, maxOuter) {
    var best = null, last = [start.sigma, start.mu];
    var f = function (v) {
      var al = 1.05 + 0.95 / (1 + Math.exp(-v[0])), be = Math.tanh(v[1]);
      var pr = profile(z, stableTable(al, be), last);
      if (!best || pr.f < best.f) { best = { f: pr.f, alpha: al, beta: be, sigma: pr.sigma, mu: pr.mu }; last = [pr.sigma, pr.mu]; }
      return pr.f;
    };
    var a0 = Math.min(1.99, Math.max(1.06, start.alpha)), b0 = Math.max(-0.99, Math.min(0.99, start.beta));
    nelderMead(f, [-Math.log(0.95 / (a0 - 1.05) - 1), Math.atanh(b0)], maxOuter && maxOuter < 30 ? [0.15, 0.1] : [0.4, 0.3], maxOuter || 60, 1e-7);
    var al = best.alpha, be = best.beta;
    var mu0 = Math.abs(al - 1) < 1e-9 ? best.mu : best.mu + best.sigma * be * Math.tan(Math.PI * al / 2); // S0 location, used to bracket quantiles
    return { alpha: al, beta: be, sigma: best.sigma, mu: best.mu, mu0: mu0, nll: best.f };
  }

  // ---------- estimation on x[from, to) ----------
  function meanVar(x, from, to) {
    var m = 0, v = 0, t; for (t = from; t < to; t++) m += x[t]; m /= (to - from);
    for (t = from; t < to; t++) v += (x[t] - m) * (x[t] - m); return [m, v / (to - from)];
  }
  function fit(x, from, to, warm, warmZ) {
    var mv = meanVar(x, from, to), m0 = mv[0], s0 = mv[1], f = negLL(x, from, to, s0, m0);
    var start = warm || pack({ c: m0, phi: 0.05, theta: -0.05, omega: 0.05 * s0, a: 0.08, b: 0.9 });
    var best = null;
    // three restarts of Nelder-Mead from the best point so far; robust for this small problem
    for (var k = 0; k < 3; k++) {
      var r = nelderMead(f, best ? best.x : start, [0.05, 0.2, 0.2, 0.5, 0.5, 0.5], 4000);
      if (!best || r.f < best.f - 1e-9) best = r; else break;
    }
    var p = unpack(best.x), fl = filter(x, p, from, to, s0, m0), z = [];
    for (var i = 0; i < to - from; i++) z.push(fl.e[i] / Math.sqrt(fl.s2[i]));
    var zs = z.slice().sort(function (a, b) { return a - b; });
    p.ll = -best.f - 0; p.s0 = s0; p.m0 = m0; p.u = best.x;
    var mc = P.fitStable(zs) || { alpha: 2, beta: 0, sigma: Math.SQRT1_2, mu: 0, mu0: 0 };
    p.zMc = mc;
    p.z = stableMLE(z, warmZ || mc, warmZ ? 14 : 60);
    p.zsorted = zs;
    return p;
  }

  // innovation quantiles for each level: normal and stable
  function zQuant(p, levels) {
    return levels.map(function (lv) { return { n: P.normInv(1 - lv), s: P.stQuantile(1 - lv, p.z) }; });
  }

  // ---------- backtest tests ----------
  function kupiec(k, n, pb) {
    var lr;
    if (k === 0) lr = -2 * n * Math.log(1 - pb);
    else if (k === n) lr = -2 * n * Math.log(pb);
    else { var q = k / n; lr = -2 * ((n - k) * Math.log(1 - pb) + k * Math.log(pb) - (n - k) * Math.log(1 - q) - k * Math.log(q)); }
    lr = Math.max(0, lr);
    return { lr: lr, p: 1 - ST.erf(Math.sqrt(lr / 2)) };
  }
  function xlogy(x, y) { return x === 0 ? 0 : x * Math.log(y); }
  function christoffersen(hits, pb) { // independence and conditional coverage (Christoffersen, 1998)
    var n00 = 0, n01 = 0, n10 = 0, n11 = 0;
    for (var i = 1; i < hits.length; i++) {
      var a = hits[i - 1], b = hits[i];
      if (!a && !b) n00++; else if (!a && b) n01++; else if (a && !b) n10++; else n11++;
    }
    var p01 = n01 / Math.max(1, n00 + n01), p11 = n11 / Math.max(1, n10 + n11), pi = (n01 + n11) / Math.max(1, n00 + n01 + n10 + n11);
    var l0 = xlogy(n00 + n10, 1 - pi) + xlogy(n01 + n11, pi);
    var l1 = xlogy(n00, 1 - p01) + xlogy(n01, p01) + xlogy(n10, 1 - p11) + xlogy(n11, p11);
    var lrInd = Math.max(0, -2 * (l0 - l1));
    var k = 0; hits.forEach(function (h) { if (h) k++; });
    var lrCc = kupiec(k, hits.length, pb).lr + lrInd;
    return { ind: 1 - ST.erf(Math.sqrt(lrInd / 2)), cc: Math.exp(-lrCc / 2), n11: n11 };
  }

  // ---------- full analysis ----------
  // pts: [{r, tm}], levels: [0.95, 0.975, 0.99]; opts.mode: 'oos' (expanding window, refitted every opts.step) or 'is'
  function run(pts, levels, opts, progress) {
    var x = pts.map(function (p) { return 100 * p.r; }), n = x.length;
    var oos = opts.mode === 'oos' && n >= opts.init + 100;
    var start = oos ? opts.init : 0, cuts = [];
    if (oos) for (var c = start; c < n; c += opts.step) cuts.push(c); else cuts.push(0);
    var models = ['un', 'us', 'gn', 'gs'];
    var V = {}; models.forEach(function (m) { V[m] = levels.map(function () { return new Float64Array(n - start); }); });
    var warm = null, warmZ = null, blocks = [];
    cuts.forEach(function (c0, bi) {
      var c1 = oos ? Math.min(n, c0 + opts.step) : n, fitTo = oos ? c0 : n;
      var p = fit(x, 0, fitTo, warm, warmZ); warm = p.u; warmZ = p.z;
      var zq = zQuant(p, levels);
      var d = P.describe(x.slice(0, fitTo)), fu = P.fitStable(d.sorted);
      var uq = levels.map(function (lv) { return { n: d.mean + d.sd * P.normInv(1 - lv), s: P.stQuantile(1 - lv, fu) }; });
      var fl = filter(x, p, 0, n, p.s0, p.m0); // causal: value at t uses data up to t-1 only
      for (var t = c0; t < c1; t++) {
        var s = Math.sqrt(fl.s2[t]);
        levels.forEach(function (lv, j) {
          V.un[j][t - start] = -uq[j].n; V.us[j][t - start] = -uq[j].s;
          V.gn[j][t - start] = -(fl.mu[t] + s * zq[j].n); V.gs[j][t - start] = -(fl.mu[t] + s * zq[j].s);
        });
      }
      blocks.push({ from: c0, to: c1, p: p });
      if (progress) progress(bi + 1, cuts.length);
    });
    // tests per model and level
    var tests = {};
    models.forEach(function (m) {
      tests[m] = levels.map(function (lv, j) {
        var hits = [], k = 0, avg = 0;
        for (var t = start; t < n; t++) { var h = x[t] < -V[m][j][t - start]; hits.push(h); if (h) k++; avg += V[m][j][t - start]; }
        var ku = kupiec(k, hits.length, 1 - lv), ch = christoffersen(hits, 1 - lv);
        return { k: k, n: hits.length, avg: avg / hits.length / 100, kup: ku.p, ind: ch.ind, cc: ch.cc, hits: hits };
      });
    });
    // full-sample fit and next-period forecast
    var pf = fit(x, 0, n, warm, warmZ), ff = filter(x, pf, 0, n, pf.s0, pf.m0), sN = Math.sqrt(ff.s2[n]), mN = ff.mu[n];
    var fc = levels.map(function (lv) {
      var qn = P.normInv(1 - lv), qs = P.stQuantile(1 - lv, pf.z);
      var esN = -mN + sN * Math.exp(-0.5 * qn * qn) / Math.sqrt(2 * Math.PI) / (1 - lv);
      var esZ = pf.z.alpha > 1 ? P.stES(lv, pf.z, qs) : -Infinity;
      return { p: lv, varN: -(mN + sN * qn) / 100, esN: esN / 100, varS: -(mN + sN * qs) / 100, esS: isFinite(esZ) ? -(mN + sN * esZ) / 100 : Infinity };
    });
    var vol = []; for (var t = 0; t < n; t++) vol.push(Math.sqrt(ff.s2[t]) / 100);
    return { oos: oos, start: start, V: V, tests: tests, blocks: blocks, full: pf, forecast: fc, vol: vol, persistence: pf.a + pf.b };
  }

  root.Garch = { stableMLE: stableMLE, fit: fit, filter: filter, run: run, kupiec: kupiec, christoffersen: christoffersen, unpack: unpack };
})(typeof window !== 'undefined' ? window : globalThis);
