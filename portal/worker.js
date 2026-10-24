/* Runs the ARMA-GARCH backtest off the main thread so the page stays responsive. */
importScripts('stable.js?v=2', 'analysis.js?v=2', 'garch.js?v=2');
self.onmessage = function (e) {
  var d = e.data;
  try {
    var R = self.Garch.run(d.pts, d.levels, d.opts, function (i, n) { self.postMessage({ id: d.id, progress: [i, n] }); });
    var tests = {};
    Object.keys(R.tests).forEach(function (m) { tests[m] = R.tests[m].map(function (o) { return { k: o.k, n: o.n, avg: o.avg, kup: o.kup, ind: o.ind, cc: o.cc, hits: o.hits }; }); });
    var V = {}; Object.keys(R.V).forEach(function (m) { V[m] = R.V[m].map(function (a) { return Array.prototype.slice.call(a); }); });
    var f = R.full;
    self.postMessage({ id: d.id, result: { oos: R.oos, start: R.start, V: V, tests: tests, forecast: R.forecast, vol: R.vol, nBlocks: R.blocks.length,
      full: { c: f.c, phi: f.phi, theta: f.theta, omega: f.omega, a: f.a, b: f.b, ll: f.ll, z: f.z, zMc: f.zMc } } });
  } catch (err) { self.postMessage({ id: d.id, error: String(err && err.message || err) }); }
};
