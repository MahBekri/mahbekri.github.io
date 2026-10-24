/* Stable laws S(alpha, beta, sigma, mu), S1 parameterisation (as in the book and MATLAB).
   Density and distribution function from Nolan's (1997) integral representation with
   Gauss-Legendre quadrature; shared by the portal. Validated against SciPy. */
(function (root) {
  var GX = [], GW = [];
  (function legendre(n) {
    for (var i = 1; i <= n; i++) {
      var z = Math.cos(Math.PI * (i - 0.25) / (n + 0.5)), z1, pp;
      do {
        var p1 = 1, p2 = 0;
        for (var j = 1; j <= n; j++) { var p3 = p2; p2 = p1; p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j; }
        pp = n * (z * p1 - p2) / (z * z - 1);
        z1 = z; z = z1 - p1 / pp;
      } while (Math.abs(z - z1) > 1e-14);
      GX.push(z); GW.push(2 / ((1 - z * z) * pp * pp));
    }
  })(20);
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
    for (var s = 0; s < pts.length - 1; s++) {
      var a = pts[s], b = pts[s + 1];
      if (b - a <= 0) continue;
      var c = 0.5 * (b + a), h = 0.5 * (b - a);
      for (var q = 0; q < GX.length; q++) tot += h * GW[q] * fun(c + h * GX[q]);
    }
    return tot;
  }
  function root1(g, lo, hi) {
    var a = lo + 1e-12, b = hi - 1e-12, ga = g(a), gb = g(b);
    if (!isFinite(ga)) ga = 1e300;
    if (!isFinite(gb)) gb = 1e300;
    var inc = gb > ga;
    for (var i = 0; i < 80; i++) {
      var m = 0.5 * (a + b), v = g(m);
      if (!isFinite(v)) v = 1e300;
      if ((v < 1) === inc) a = m; else b = m;
    }
    return 0.5 * (a + b);
  }
  function kpdf(G) { if (!isFinite(G) || G <= 0) return 0; var r = G * Math.exp(-G); return isFinite(r) ? r : 0; }
  function kcdf(G) { if (G !== G) return 0; if (G === Infinity) return 0; var r = Math.exp(-G); return isFinite(r) ? r : 0; }
  function gammaFn(z) {
    var p = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
      -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
    if (z < 0.5) return Math.PI / (Math.sin(Math.PI * z) * gammaFn(1 - z));
    z -= 1; var x = p[0];
    for (var i = 1; i < 9; i++) x += p[i] / (z + i);
    var t = z + 7.5;
    return Math.sqrt(2 * Math.PI) * Math.pow(t, z + 0.5) * Math.exp(-t) * x;
  }
  function erf(x) { // Abramowitz-Stegun 7.1.26 refined by series for small |x|
    var s = x < 0 ? -1 : 1; x = Math.abs(x);
    var t = 1 / (1 + 0.3275911 * x);
    var y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
    return s * y;
  }
  function nolanSetup(a, b) {
    var th0 = Math.atan(b * Math.tan(Math.PI * a / 2)) / a, e = a / (a - 1), lc0 = Math.log(Math.cos(a * th0)) / (a - 1);
    return { th0: th0, e: e, lc0: lc0, zeta: -b * Math.tan(Math.PI * a / 2) };
  }
  function nolanG(S, a, k) {
    // evaluated in logs: near alpha = 1 the factors under- and overflow separately (e = alpha/(alpha-1) is large)
    var lk = Math.log(k);
    return function (th) { return Math.exp(lk + S.lc0 + S.e * Math.log(Math.cos(th) / Math.sin(a * (S.th0 + th))) + Math.log(Math.cos(a * S.th0 + (a - 1) * th) / Math.cos(th))); };
  }
  function nPdf(x, a, b) {
    var S = nolanSetup(a, b);
    if (x < S.zeta) return nPdf(-x, a, -b);
    if (Math.abs(x - S.zeta) < 1e-10) return gammaFn(1 + 1 / a) * Math.cos(S.th0) / (Math.PI * Math.pow(1 + S.zeta * S.zeta, 1 / (2 * a)));
    var g = nolanG(S, a, Math.pow(x - S.zeta, S.e)), lo = -S.th0, hi = Math.PI / 2, mid = root1(g, lo, hi);
    return a / (Math.PI * Math.abs(a - 1) * (x - S.zeta)) * quad(function (th) { return kpdf(g(th)); }, lo, hi, mid);
  }
  function nCdf(x, a, b) {
    var S = nolanSetup(a, b);
    if (x < S.zeta) return 1 - nCdf(-x, a, -b);
    var c1 = a < 1 ? (Math.PI / 2 - S.th0) / Math.PI : 1;
    if (Math.abs(x - S.zeta) < 1e-10) return (Math.PI / 2 - S.th0) / Math.PI;
    var g = nolanG(S, a, Math.pow(x - S.zeta, S.e)), lo = -S.th0, hi = Math.PI / 2, mid = root1(g, lo, hi);
    return c1 + (a < 1 ? 1 : -1) / Math.PI * quad(function (th) { return kcdf(g(th)); }, lo, hi, mid);
  }
  function g1(x, b) {
    var c = Math.exp(-Math.PI * x / (2 * b));
    return function (th) { return c * (2 / Math.PI) * ((Math.PI / 2 + b * th) / Math.cos(th)) * Math.exp((1 / b) * (Math.PI / 2 + b * th) * Math.tan(th)); };
  }
  var LO1 = -Math.PI / 2 + 1e-12, HI1 = Math.PI / 2 - 1e-12;
  function pdf1(x, b) {
    if (Math.abs(b) < 1e-12) return 1 / (Math.PI * (1 + x * x));
    if (b < 0) return pdf1(-x, -b);
    var g = g1(x, b); return quad(function (th) { return kpdf(g(th)); }, LO1, HI1, root1(g, LO1, HI1)) / (2 * b);
  }
  function cdf1(x, b) {
    if (Math.abs(b) < 1e-12) return 0.5 + Math.atan(x) / Math.PI;
    if (b < 0) return 1 - cdf1(-x, -b);
    var g = g1(x, b); return quad(function (th) { return kcdf(g(th)); }, LO1, HI1, root1(g, LO1, HI1)) / Math.PI;
  }
  function shiftLoc(a, b, s, m) { return Math.abs(a - 1) < 1e-9 ? m + (2 / Math.PI) * b * s * Math.log(s) : m; }
  function pdf(x, a, b, s, m) {
    m = shiftLoc(a, b, s, m); var z = (x - m) / s, v;
    if (a >= 2) v = Math.exp(-z * z / 4) / Math.sqrt(4 * Math.PI);
    else if (Math.abs(a - 1) < 1e-2) v = pdf1(Math.abs(a - 1) < 1e-9 ? z : z - b * Math.tan(Math.PI * a / 2), b); // near 1: S0 law at alpha = 1, error O(|alpha - 1|)
    else v = nPdf(z - b * Math.tan(Math.PI * a / 2), a, b);
    v = v / s; return isFinite(v) && v > 0 ? v : 0;
  }
  function cdf(x, a, b, s, m) {
    m = shiftLoc(a, b, s, m); var z = (x - m) / s, v;
    if (a >= 2) v = 0.5 * (1 + erf(z / 2));
    else if (Math.abs(a - 1) < 1e-2) v = cdf1(Math.abs(a - 1) < 1e-9 ? z : z - b * Math.tan(Math.PI * a / 2), b);
    else v = nCdf(z - b * Math.tan(Math.PI * a / 2), a, b);
    return isFinite(v) ? Math.min(1, Math.max(0, v)) : 0;
  }
  root.Stable = { pdf: pdf, cdf: cdf, erf: erf, gamma: gammaFn };
})(typeof window !== 'undefined' ? window : globalThis);
