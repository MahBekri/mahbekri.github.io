/* Stable-law numerics for the website, S1 parameterisation (Samorodnitsky-Taqqu, as in MATLAB and the book).
   pdf/cdf: Nolan (1997) integral representation with Gauss-Legendre quadrature clustered at the peak.
   fit: Koutrouvelis (1980) regression on the empirical characteristic function, iterated.
   rnd: Chambers-Mallows-Stuck (1976) with Weron's (1996) correction. All validated against SciPy. */
(function (root) {
  'use strict';
  var PI = Math.PI;
  var GX = [], GW = [];
  (function legendre(n) {
    for (var i = 1; i <= n; i++) {
      var z = Math.cos(PI * (i - 0.25) / (n + 0.5)), z1, pp;
      do {
        var p1 = 1, p2 = 0;
        for (var j = 1; j <= n; j++) { var p3 = p2; p2 = p1; p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j; }
        pp = n * (z * p1 - p2) / (z * z - 1);
        z1 = z; z = z1 - p1 / pp;
      } while (Math.abs(z - z1) > 1e-14);
      GX.push(z); GW.push(2 / ((1 - z * z) * pp * pp));
    }
  })(20);
  function gl(fun, a, b) { var c = 0.5 * (a + b), h = 0.5 * (b - a), t = 0; for (var q = 0; q < 20; q++) t += GW[q] * fun(c + h * GX[q]); return h * t; }
  function quad(fun, lo, hi, mid) {
    var pts = [lo, hi];
    if (mid > lo && mid < hi) pts.push(mid);
    for (var k = 0; k < 10; k++) {
      var d = (hi - lo) * Math.pow(10, -0.6 * k);
      if (mid - d > lo && mid - d < hi) pts.push(mid - d);
      if (mid + d > lo && mid + d < hi) pts.push(mid + d);
    }
    pts.sort(function (a, b) { return a - b; });
    var tot = 0;
    for (var s = 0; s < pts.length - 1; s++) if (pts[s + 1] > pts[s]) tot += gl(fun, pts[s], pts[s + 1]);
    return tot;
  }
  function root1(g, lo, hi) {
    var a = lo + 1e-12, b = hi - 1e-12, ga = g(a), gb = g(b);
    if (!isFinite(ga)) ga = 1e300;
    if (!isFinite(gb)) gb = 1e300;
    var inc = gb > ga;
    for (var i = 0; i < 80; i++) { var m = 0.5 * (a + b), v = g(m); if (!isFinite(v)) v = 1e300; if ((v < 1) === inc) a = m; else b = m; }
    return 0.5 * (a + b);
  }
  function kpdf(G) { if (!isFinite(G) || G <= 0) return 0; var r = G * Math.exp(-G); return isFinite(r) ? r : 0; }
  function kcdf(G) { if (G !== G || G === Infinity) return 0; var r = Math.exp(-G); return isFinite(r) ? r : 0; }
  function gammaFn(z) {
    var p = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
      -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
    if (z < 0.5) return PI / (Math.sin(PI * z) * gammaFn(1 - z));
    z -= 1; var x = p[0];
    for (var i = 1; i < 9; i++) x += p[i] / (z + i);
    var t = z + 7.5;
    return Math.sqrt(2 * PI) * Math.pow(t, z + 0.5) * Math.exp(-t) * x;
  }
  // erfc with relative accuracy ~1e-7 everywhere (Numerical Recipes erfcc), so small p-values stay meaningful
  function erfc(x) {
    var z = Math.abs(x), t = 1 / (1 + 0.5 * z);
    var r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
    return x >= 0 ? r : 2 - r;
  }
  function normCdf(z) { return 0.5 * erfc(-z / Math.SQRT2); }
  function normPdf(z) { return Math.exp(-0.5 * z * z) / Math.sqrt(2 * PI); }
  function normInv(p) { // Acklam, refined by one Halley step
    var a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239],
      b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572],
      c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783],
      d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416], q, r, x;
    if (p < 0.02425) { q = Math.sqrt(-2 * Math.log(p)); x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    else if (p > 1 - 0.02425) { q = Math.sqrt(-2 * Math.log(1 - p)); x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    else { q = p - 0.5; r = q * q; x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1); }
    var e = normCdf(x) - p, u = e * Math.sqrt(2 * PI) * Math.exp(x * x / 2);
    return x - u / (1 + x * u / 2);
  }

  function nolanSetup(a, b) {
    var th0 = Math.atan(b * Math.tan(PI * a / 2)) / a;
    return { th0: th0, e: a / (a - 1), c0: Math.pow(Math.cos(a * th0), 1 / (a - 1)), zeta: -b * Math.tan(PI * a / 2) };
  }
  function nolanG(S, a, k) {
    return function (th) { return k * S.c0 * Math.pow(Math.cos(th) / Math.sin(a * (S.th0 + th)), S.e) * Math.cos(a * S.th0 + (a - 1) * th) / Math.cos(th); };
  }
  function nPdf(x, a, b) {
    var S = nolanSetup(a, b);
    if (x < S.zeta) return nPdf(-x, a, -b);
    if (Math.abs(x - S.zeta) < 1e-10) return gammaFn(1 + 1 / a) * Math.cos(S.th0) / (PI * Math.pow(1 + S.zeta * S.zeta, 1 / (2 * a)));
    var g = nolanG(S, a, Math.pow(x - S.zeta, S.e)), lo = -S.th0, hi = PI / 2, mid = root1(g, lo, hi);
    return a / (PI * Math.abs(a - 1) * (x - S.zeta)) * quad(function (th) { return kpdf(g(th)); }, lo, hi, mid);
  }
  // upper tail P(X > x) for x >= zeta; computing the tail directly avoids cancellation far out
  function nSurv(x, a, b) {
    var S = nolanSetup(a, b);
    if (Math.abs(x - S.zeta) < 1e-10) return 1 - (PI / 2 - S.th0) / PI;
    var g = nolanG(S, a, Math.pow(x - S.zeta, S.e)), lo = -S.th0, hi = PI / 2, mid = root1(g, lo, hi);
    var I = quad(function (th) { return kcdf(g(th)); }, lo, hi, mid) / PI;
    return a < 1 ? 1 - (PI / 2 - S.th0) / PI - I : I;
  }
  function nCdf(x, a, b) {
    var S = nolanSetup(a, b);
    if (x < S.zeta) return nSurv(-x, a, -b);
    return 1 - nSurv(x, a, b);
  }
  function g1(x, b) {
    var lc = -PI * x / (2 * b) + Math.log(2 / PI); // log space: exp(-pi x / 2b) overflows far in the left tail
    return function (th) { var v = PI / 2 + b * th; return Math.exp(lc + Math.log(v / Math.cos(th)) + (v / b) * Math.tan(th)); };
  }
  var LO1 = -PI / 2 + 1e-12, HI1 = PI / 2 - 1e-12;
  function pdf1(x, b) {
    if (Math.abs(b) < 1e-12) return 1 / (PI * (1 + x * x));
    if (b < 0) return pdf1(-x, -b);
    var g = g1(x, b); return quad(function (th) { return kpdf(g(th)); }, LO1, HI1, root1(g, LO1, HI1)) / (2 * b);
  }
  function cdf1(x, b) { // P(X <= x), computed on the side that is small
    if (Math.abs(b) < 1e-12) return x < 0 ? Math.atan(-1 / x) / PI : 0.5 + Math.atan(x) / PI;
    if (b < 0) return 1 - cdf1(-x, -b);
    var g = g1(x, b); return quad(function (th) { return kcdf(g(th)); }, LO1, HI1, root1(g, LO1, HI1)) / PI;
  }
  function shiftLoc(a, b, s, m) { return Math.abs(a - 1) < 1e-9 ? m + (2 / PI) * b * s * Math.log(s) : m; }
  function pdf(x, a, b, s, m) {
    m = shiftLoc(a, b, s, m); var z = (x - m) / s, v;
    if (a >= 2) v = Math.exp(-z * z / 4) / Math.sqrt(4 * PI);
    else if (Math.abs(a - 1) < 1e-9) v = pdf1(z, b);
    else v = nPdf(z - b * Math.tan(PI * a / 2), a, b);
    v = v / s; return isFinite(v) && v > 0 ? v : 0;
  }
  function cdf(x, a, b, s, m) {
    m = shiftLoc(a, b, s, m); var z = (x - m) / s, v;
    if (a >= 2) v = normCdf(z / Math.SQRT2);
    else if (Math.abs(a - 1) < 1e-9) v = cdf1(z, b);
    else v = nCdf(z - b * Math.tan(PI * a / 2), a, b);
    return isFinite(v) ? Math.min(1, Math.max(0, v)) : 0;
  }
  // p-quantile by bracketing then bisection on the cdf
  function quantile(p, a, b, s, m) {
    if (a >= 2) return m + s * Math.SQRT2 * normInv(p);
    var lo = m - s, hi = m + s, k = 0;
    while (cdf(lo, a, b, s, m) > p && k++ < 200) lo = m - (m - lo) * 2;
    k = 0; while (cdf(hi, a, b, s, m) < p && k++ < 200) hi = m + (hi - m) * 2;
    for (var i = 0; i < 100 && hi - lo > 1e-12 * Math.max(1, Math.abs(lo)); i++) { var c = 0.5 * (lo + hi); if (cdf(c, a, b, s, m) < p) lo = c; else hi = c; }
    return 0.5 * (lo + hi);
  }
  // Value at risk and expected shortfall of the loss -X at tail probability p (e.g. 0.01 for 99%), both as positive numbers.
  // ES = -q + (1/p) * integral_{-inf}^{q} F(x) dx, with the far tail closed by F(x) ~ c |x|^-alpha.
  function varEs(p, a, b, s, m) {
    var q = quantile(p, a, b, s, m);
    if (a >= 2) { var z = normInv(p), sd = s * Math.SQRT2; return { VaR: -q, ES: -m + sd * normPdf(z) / p }; }
    if (a <= 1) return { VaR: -q, ES: Infinity };
    var F = function (t) { return cdf(q - t, a, b, s, m); }, tot = 0, t0 = 0, t1 = 0.25 * s, T = 1e5 * s;
    while (t1 < T) { tot += gl(F, t0, t1); t0 = t1; t1 *= 2; }
    var xT = q - t0, FT = cdf(xT, a, b, s, m), ref = Math.abs(xT - m);
    tot += FT * ref / (a - 1);
    return { VaR: -q, ES: -q + tot / p };
  }

  // ---------- random numbers ----------
  function rng(seed) { // mulberry32
    var t = seed >>> 0;
    return function () { t = (t + 0x6D2B79F5) >>> 0; var r = Math.imul(t ^ (t >>> 15), 1 | t); r ^= r + Math.imul(r ^ (r >>> 7), 61 | r); return ((r ^ (r >>> 14)) >>> 0) / 4294967296; };
  }
  function rnd(n, a, b, s, m, seed) {
    var u = rng(seed == null ? 1 : seed), out = new Array(n), i;
    for (i = 0; i < n; i++) {
      var V = PI * (u() - 0.5), W = -Math.log(1 - u()), X;
      if (Math.abs(a - 1) < 1e-9) {
        X = (2 / PI) * ((PI / 2 + b * V) * Math.tan(V) - b * Math.log((PI / 2) * W * Math.cos(V) / (PI / 2 + b * V)));
        out[i] = s * X + (2 / PI) * b * s * Math.log(s) + m;
      } else {
        var t = b * Math.tan(PI * a / 2), B = Math.atan(t) / a, S = Math.pow(1 + t * t, 1 / (2 * a));
        X = S * Math.sin(a * (V + B)) / Math.pow(Math.cos(V), 1 / a) * Math.pow(Math.cos(V - a * (V + B)) / W, (1 - a) / a);
        out[i] = s * X + m;
      }
    }
    return out;
  }

  // ---------- estimation ----------
  function sorted(x) { return x.slice().sort(function (p, q) { return p - q; }); }
  function quantSorted(xs, p) { // linear interpolation (type 7, as NumPy's default)
    var h = (xs.length - 1) * p, lo = Math.floor(h), hi = Math.ceil(h);
    return xs[lo] + (h - lo) * (xs[hi] - xs[lo]);
  }
  function ols(X, y) { // least squares with columns X[j][i]
    var k = X.length, n = y.length, A = [], r = [], i, j, l;
    for (j = 0; j < k; j++) { A.push([]); for (l = 0; l < k; l++) { var s = 0; for (i = 0; i < n; i++) s += X[j][i] * X[l][i]; A[j].push(s); } var t = 0; for (i = 0; i < n; i++) t += X[j][i] * y[i]; r.push(t); }
    for (j = 0; j < k; j++) { // Gaussian elimination
      var piv = A[j][j]; if (Math.abs(piv) < 1e-300) return null;
      for (l = j + 1; l < k; l++) { var f = A[l][j] / piv; for (var c = j; c < k; c++) A[l][c] -= f * A[j][c]; r[l] -= f * r[j]; }
    }
    var x = new Array(k);
    for (j = k - 1; j >= 0; j--) { var s2 = r[j]; for (l = j + 1; l < k; l++) s2 -= A[j][l] * x[l]; x[j] = s2 / A[j][j]; }
    return x;
  }
  function ecf(z, u) { var re = 0, im = 0, n = z.length; for (var i = 0; i < n; i++) { re += Math.cos(u * z[i]); im += Math.sin(u * z[i]); } return [re / n, im / n]; }
  function interp(tab, a) { // tab: [[alpha, value], ...] with alpha decreasing
    if (a >= tab[0][0]) return tab[0][1];
    for (var i = 1; i < tab.length; i++) if (a >= tab[i][0]) { var w = (a - tab[i][0]) / (tab[i - 1][0] - tab[i][0]); return tab[i][1] + w * (tab[i - 1][1] - tab[i][1]); }
    return tab[tab.length - 1][1];
  }
  // Number of ECF points, after Koutrouvelis (1980), Tables I and II, for samples of about 1,000 to 2,000
  var KTAB = [[1.9, 9], [1.5, 11], [1.3, 22], [1.1, 24], [0.9, 28], [0.7, 30], [0.5, 86], [0.3, 134]];
  var LTAB = [[1.9, 10], [1.5, 14], [1.3, 16], [1.1, 18], [0.9, 14], [0.7, 16], [0.5, 42], [0.3, 46]];
  function fit(x) {
    var n = x.length, xs = sorted(x);
    var mu = quantSorted(xs, 0.5), sig = (quantSorted(xs, 0.75) - quantSorted(xs, 0.25)) / 1.9;
    if (!(sig > 0)) { var mm = 0, v = 0, i; for (i = 0; i < n; i++) mm += x[i]; mm /= n; for (i = 0; i < n; i++) v += (x[i] - mm) * (x[i] - mm); sig = Math.sqrt(v / n) || 1; }
    var a = 1.7, b = 0, floor = Math.max(0.05, 3 / Math.sqrt(n));
    for (var it = 0; it < 12; it++) {
      var z = x.map(function (v) { return (v - mu) / sig; });
      var K = Math.round(interp(KTAB, a)), w = [], y = [];
      for (var k = 1; k <= K; k++) {
        var t = PI * k / 25, c = ecf(z, t), mod = Math.hypot(c[0], c[1]);
        if (mod > floor && mod < 1 - 1e-9) { w.push(Math.log(t)); y.push(Math.log(-2 * Math.log(mod))); }
      }
      if (w.length < 3) break;
      var r1 = ols([w.map(function () { return 1; }), w], y);
      if (!r1) break;
      var aN = Math.min(2, Math.max(0.1, r1[1])), s1 = Math.pow(Math.exp(r1[0]) / 2, 1 / aN);
      // second regression: unwrapped argument of the ECF on standardised data
      var L = Math.round(interp(LTAB, aN)), U = [], G = [], prev = 0, off = 0;
      for (var l = 1; l <= L; l++) {
        var uu = PI * l / 50, cc = ecf(z, uu);
        if (Math.hypot(cc[0], cc[1]) <= floor) break;
        var g = Math.atan2(cc[1], cc[0]);
        if (g - prev > PI) off -= 2 * PI; else if (g - prev < -PI) off += 2 * PI;
        prev = g; U.push(uu); G.push(g + off);
      }
      var bN = b, m1 = 0;
      if (U.length >= 2) {
        if (Math.abs(aN - 1) < 0.02) {
          var r2 = ols([U, U.map(function (u) { return u * Math.log(u); })], G);
          if (r2) { bN = -r2[1] / (s1 * 2 / PI); m1 = r2[0] + s1 * bN * (2 / PI) * Math.log(s1); }
        } else if (aN < 2) {
          var r3 = ols([U, U.map(function (u) { return Math.pow(u, aN); })], G);
          if (r3) { bN = r3[1] / (Math.pow(s1, aN) * Math.tan(PI * aN / 2)); m1 = r3[0]; }
        } else { var r4 = ols([U], G); if (r4) m1 = r4[0]; bN = 0; }
      }
      bN = Math.min(1, Math.max(-1, isFinite(bN) ? bN : 0));
      var muN = mu + sig * m1, sigN = sig * s1;
      if (Math.abs(aN - 1) < 0.02) muN -= (2 / PI) * bN * sigN * Math.log(sig);
      var done = Math.abs(aN - a) < 1e-4 && Math.abs(s1 - 1) < 1e-4 && Math.abs(m1) < 1e-4;
      a = aN; b = bN; mu = muN; sig = sigN;
      if (done) break;
    }
    if (a >= 2) b = 0;
    return { alpha: a, beta: b, sigma: sig, mu: mu };
  }

  // ---------- maximum likelihood ----------
  function nelderMead(f, x0, step, maxIt, tol) {
    var n = x0.length, P = [x0.slice()], F = [f(x0)], i, j;
    for (i = 0; i < n; i++) { var v = x0.slice(); v[i] += step[i]; P.push(v); F.push(f(v)); }
    for (var it = 0; it < maxIt; it++) {
      var idx = P.map(function (_, k) { return k; }).sort(function (p, q) { return F[p] - F[q]; });
      P = idx.map(function (k) { return P[k]; }); F = idx.map(function (k) { return F[k]; });
      if (Math.abs(F[n] - F[0]) < tol * (Math.abs(F[0]) + 1e-12)) break;
      var c = new Array(n).fill(0);
      for (i = 0; i < n; i++) for (j = 0; j < n; j++) c[j] += P[i][j] / n;
      var pt = function (t) { return c.map(function (cj, k) { return cj + t * (P[n][k] - cj); }); };
      var xr = pt(-1), fr = f(xr);
      if (fr < F[0]) { var xe = pt(-2), fe = f(xe); if (fe < fr) { P[n] = xe; F[n] = fe; } else { P[n] = xr; F[n] = fr; } }
      else if (fr < F[n - 1]) { P[n] = xr; F[n] = fr; }
      else {
        var xc = fr < F[n] ? pt(-0.5) : pt(0.5), fc = f(xc);
        if (fc < Math.min(fr, F[n])) { P[n] = xc; F[n] = fc; }
        else for (i = 1; i <= n; i++) { P[i] = P[i].map(function (v, k) { return P[0][k] + 0.5 * (v - P[0][k]); }); F[i] = f(P[i]); }
      }
    }
    var b = 0; for (i = 1; i <= n; i++) if (F[i] < F[b]) b = i;
    return { x: P[b], f: F[b] };
  }
  // Log-density of the standard law S(a, b, 1, 0) tabulated on an asinh grid, interpolated with Catmull-Rom splines.
  function logPdfTable(a, b, zmax) {
    var N = 241, umax = Math.log(zmax + Math.sqrt(zmax * zmax + 1)), du = 2 * umax / (N - 1), L = new Array(N);
    for (var i = 0; i < N; i++) { var z = Math.sinh(-umax + i * du), v = pdf(z, a, b, 1, 0); L[i] = Math.log(Math.max(v, 1e-300)); }
    return function (z) {
      var u = Math.log(z + Math.sqrt(z * z + 1)), h = (u + umax) / du, k = Math.floor(h);
      if (k < 1 || k > N - 3) return Math.log(Math.max(pdf(z, a, b, 1, 0), 1e-300));
      var t = h - k, p0 = L[k - 1], p1 = L[k], p2 = L[k + 1], p3 = L[k + 2];
      return p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)));
    };
  }
  // Maximum likelihood: outer search over (alpha, beta), inner search over (mu, log sigma) on a tabulated density.
  function mle(x, start) {
    var n = x.length, st = start || fit(x);
    var spread = 0; for (var i = 0; i < n; i++) spread = Math.max(spread, Math.abs(x[i] - st.mu));
    var zmax = Math.max(50, 4 * spread / st.sigma);
    var toAB = function (v) { return [0.4 + 1.6 / (1 + Math.exp(-v[0])), Math.tanh(v[1])]; };
    var fromA = function (a) { var t = Math.min(0.9999, Math.max(1e-4, (a - 0.4) / 1.6)); return Math.log(t / (1 - t)); };
    var fromB = function (b) { b = Math.min(0.999, Math.max(-0.999, b)); return 0.5 * Math.log((1 + b) / (1 - b)); };
    var best = null, ms = [st.mu, Math.log(st.sigma)];
    var outer = function (v) {
      var ab = toAB(v), a = ab[0], b = ab[1];
      if (Math.abs(a - 1) < 1e-6) a = 1 + 1e-6;
      var lp = logPdfTable(a, b, zmax);
      var nll = function (w) {
        var s = Math.exp(w[1]), m = w[0], tot = n * Math.log(s);
        var mm = Math.abs(a - 1) < 1e-9 ? m + (2 / PI) * b * s * Math.log(s) : m;
        for (var i = 0; i < n; i++) tot -= lp((x[i] - mm) / s);
        return tot;
      };
      var r = nelderMead(nll, ms, [0.1 * Math.exp(ms[1]), 0.1], 200, 1e-10);
      if (!best || r.f < best.f) { best = { f: r.f, a: a, b: b, m: r.x[0], s: Math.exp(r.x[1]) }; ms = r.x.slice(); }
      return r.f;
    };
    nelderMead(outer, [fromA(st.alpha), fromB(st.beta)], [0.3, 0.3], 80, 1e-9);
    return { alpha: best.a, beta: best.b, sigma: best.s, mu: best.m, logLik: -best.f };
  }

  var api = { pdf: pdf, cdf: cdf, quantile: quantile, varEs: varEs, rnd: rnd, fit: fit, mle: mle, normCdf: normCdf, normPdf: normPdf, normInv: normInv, erfc: erfc, quantSorted: quantSorted };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.Stable = api;
})(this);
