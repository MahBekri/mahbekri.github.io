/* Runs the analysis off the main thread so the page stays responsive during the maximum-likelihood fit. */
importScripts('../assets/stable.js?v=1', 'analysis.js?v=1');
self.onmessage = function (e) {
  try { self.postMessage({ id: e.data.id, result: self.analyse(e.data.x) }); }
  catch (err) { self.postMessage({ id: e.data.id, error: String(err && err.message || err) }); }
};
