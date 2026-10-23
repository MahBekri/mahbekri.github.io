/* Runs the book's Python exercises in a Web Worker with Pyodide,
   so long computations never freeze the page. */
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const VERSION = "4";
importScripts(PYODIDE + "pyodide.js");

let py = null;
let ready = null;
let current = null;   // id of the run whose output is being streamed
let queue = Promise.resolve();

function post(msg) { self.postMessage(msg); }

async function init() {
  post({ type: "status", key: "stLoadPy" });
  py = await loadPyodide({ indexURL: PYODIDE });
  py.setStdout({ batched: (s) => post({ type: "out", id: current, text: s + "\n" }) });
  py.setStderr({ batched: (s) => post({ type: "err", id: current, text: s + "\n" }) });
  post({ type: "status", key: "stLoadPkg" });
  const [kit, csv] = await Promise.all([
    fetch("py/bookkit.py?v=" + VERSION).then((r) => { if (!r.ok) throw new Error("bookkit.py " + r.status); return r.text(); }),
    fetch("data/prices.csv?v=" + VERSION).then((r) => { if (!r.ok) throw new Error("prices.csv " + r.status); return r.text(); }),
    py.loadPackage(["numpy", "scipy", "matplotlib"]),
  ]);
  py.FS.writeFile("/home/pyodide/bookkit.py", kit);
  py.FS.writeFile("/home/pyodide/prices.csv", csv);
  await py.runPythonAsync(`
import os, sys, io, base64, warnings
os.environ["MPLBACKEND"] = "Agg"
os.chdir("/home/pyodide")
if "/home/pyodide" not in sys.path:
    sys.path.insert(0, "/home/pyodide")
warnings.filterwarnings("ignore", message=".*non-interactive.*")
warnings.filterwarnings("ignore", message=".*FigureCanvasAgg.*")
import bookkit
import matplotlib.pyplot as plt

def _bk_figs():
    out = []
    for n in plt.get_fignums():
        f = plt.figure(n)
        b = io.BytesIO()
        f.savefig(b, format="png", dpi=144, bbox_inches="tight", facecolor="white")
        titles = []
        if f._suptitle is not None and f._suptitle.get_text():
            titles.append(f._suptitle.get_text())
        for ax in f.axes:
            t = ax.get_title()
            if t:
                titles.append(t)
        out.append([base64.b64encode(b.getvalue()).decode("ascii"), "; ".join(titles)])
    plt.close("all")
    return out
`);
  post({ type: "status", key: "stReady" });
}

async function run(id, code) {
  if (!ready) ready = init();
  try {
    await ready;
  } catch (e) {
    ready = null;
    post({ type: "status", key: "stFail" });
    post({ type: "done", id, ok: false, error: String(e && e.message || e), figs: [], ms: 0 });
    return;
  }
  current = id;
  post({ type: "started", id });
  const t0 = performance.now();
  let ok = true, error = null, figs = [];
  try {
    py.runPython("plt.close('all')");
    const ns = py.globals.get("dict")();
    await py.runPythonAsync(code, { globals: ns, filename: "<exercise>" });
    ns.destroy();
  } catch (e) {
    ok = false;
    error = String(e && e.message || e);
    // keep only the part of the traceback that concerns the exercise code
    const i = error.indexOf('File "<exercise>"');
    if (i > 0) error = "Traceback (most recent call last):\n  " + error.slice(i);
  }
  try {
    const p = py.globals.get("_bk_figs")();
    figs = p.toJs();
    p.destroy();
  } catch (e) { /* no figures */ }
  post({ type: "done", id, ok, error, figs, ms: performance.now() - t0 });
  current = null;
}

self.onmessage = (e) => {
  const m = e.data;
  if (m.type === "init") { queue = queue.then(() => { if (!ready) ready = init(); return ready.catch(() => { ready = null; post({ type: "status", key: "stFail" }); }); }); }
  if (m.type === "run") { queue = queue.then(() => run(m.id, m.code)); }
};
