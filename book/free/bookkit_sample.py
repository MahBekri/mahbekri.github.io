"""
bookkit (free sample): the stable-law part of the helpers for the exercises of
M. Bekri, *Heavy Tails and Coherent Risk Measures in Islamic Finance* (IsDBI, 2021).

The book's code is MATLAB (Statistics, Econometrics, Financial and Risk
Management toolboxes). This module supplies Python stand-ins for the toolbox
functions it calls (fitdist 'stable', arima/garch estimate, copula*, varbacktest,
PortfolioCVaR, ...) using only numpy, scipy and matplotlib, so every exercise
can run in a web browser through Pyodide.

Conventions
-----------
* Prices are adjusted daily closes from Yahoo Finance, 2 Jan 2008 to 31 Dec 2018.
* Stable laws use the S1 parameterisation, as MATLAB's makedist('Stable') does:
  E[exp(iuX)] = exp(i*delta*u - |gam*u|^alpha * (1 - i*beta*sign(u)*tan(pi*alpha/2))).
"""
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
import math
import numpy as np
from scipy import stats, optimize, signal, special

# --------------------------------------------------------------------------
# Plot style (navy palette of the website)
# --------------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = ["#1f3a6e", "#c0392b", "#2f8f6b", "#c98a12", "#7a4fa3", "#3a8fb7"]
GREY = "#98a1b0"
plt.rcParams.update({
    "figure.figsize": (7.2, 4.4),
    "figure.dpi": 100,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#c4ccd8",
    "axes.labelcolor": "#16233b",
    "axes.titlesize": 10.5,
    "axes.titleweight": "normal",
    "axes.labelsize": 9.5,
    "axes.grid": True,
    "grid.color": "#e6eaf0",
    "grid.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.prop_cycle": matplotlib.cycler(color=COLORS),
    "xtick.color": "#586378",
    "ytick.color": "#586378",
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.5,
    "legend.frameon": False,
    "lines.linewidth": 1.6,
    "font.family": "DejaVu Sans",
})

# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
DATA_FILE = "prices.csv"
TICKERS = ["DJI", "INTC", "IBM", "AAPL", "MSFT", "MMM", "CSCO"]


# --------------------------------------------------------------------------
# Stable laws (S1), as used by exercise 5
# --------------------------------------------------------------------------
class Stable:
    """Stable law S(alpha, beta, gam, delta) in S1, with the pdf, cdf and icdf
    methods of a MATLAB distribution object. pdf/cdf/icdf use scipy's
    levy_stable (Nolan's integral representation); fast grid versions
    (FFT of the characteristic function) are used when many points are needed."""

    def __init__(self, alpha, beta, gam, delta):
        self.alpha, self.beta, self.gam, self.delta = float(alpha), float(beta), float(gam), float(delta)
        self._grid = None

    def __repr__(self):
        return (f"StableDistribution\n  alpha = {self.alpha:.6g}\n  beta  = {self.beta:.6g}\n"
                f"  gam   = {self.gam:.6g}\n  delta = {self.delta:.6g}")

    @property
    def _scipy(self):
        st = stats.levy_stable
        st.parameterization = "S1"
        return st(self.alpha, self.beta, loc=self.delta, scale=self.gam)

    def pdf(self, x):
        return self._scipy.pdf(np.asarray(x, float))

    def cdf(self, x):
        return self._scipy.cdf(np.asarray(x, float))

    def icdf(self, p):
        p = np.atleast_1d(np.asarray(p, float))
        out = np.empty_like(p)
        for i, pi in enumerate(p):
            # bracket from the fast grid, then refine on scipy's cdf
            x0 = float(self.fast_icdf(pi))
            f = lambda x: float(self.cdf(x)) - pi
            a, b = x0 - 0.5 * self.gam, x0 + 0.5 * self.gam
            k = 0
            while f(a) > 0 and k < 60:
                a -= self.gam * 2 ** k; k += 1
            k = 0
            while f(b) < 0 and k < 60:
                b += self.gam * 2 ** k; k += 1
            out[i] = optimize.brentq(f, a, b, xtol=1e-12 * max(1.0, abs(x0)))
        return out if out.size > 1 else float(out[0])

    def random(self, size, rng=None):
        return stable_rnd(self.alpha, self.beta, self.gam, self.delta, size, rng)

    # fast, grid-based versions
    def _ensure_grid(self):
        if self._grid is None:
            z, f, F = _std_stable_grid(self.alpha, self.beta)
            self._grid = (z, f, F)
        return self._grid

    def fast_pdf(self, x):
        z, f, _ = self._ensure_grid()
        u = (np.asarray(x, float) - self.delta) / self.gam
        return _grid_eval_pdf(u, z, f, self.alpha, self.beta) / self.gam

    def fast_cdf(self, x):
        z, _, F = self._ensure_grid()
        u = (np.asarray(x, float) - self.delta) / self.gam
        return np.interp(u, z, F)

    def fast_icdf(self, p):
        z, _, F = self._ensure_grid()
        return self.delta + self.gam * np.interp(p, F, z)


def _tail_const(alpha):
    return math.sin(math.pi * alpha / 2) * math.gamma(alpha) / math.pi


def _std_stable_grid(alpha, beta, N=2 ** 14, L=60.0):
    """Density and cdf of S(alpha, beta, 1, 0) on a regular grid by FFT
    inversion of the characteristic function (alpha != 1)."""
    h = 2 * L / N
    z0 = -L
    du = 2 * math.pi / (N * h)
    u0 = -math.pi / h
    j = np.arange(N)
    u = u0 + j * du
    au = np.abs(u)
    if abs(alpha - 1) > 1e-6:
        logphi = -au ** alpha * (1 - 1j * beta * np.sign(u) * math.tan(math.pi * alpha / 2))
    else:
        with np.errstate(divide="ignore", invalid="ignore"):
            lg = np.where(au > 0, np.log(au), 0.0)
        logphi = -au * (1 + 1j * beta * (2 / math.pi) * np.sign(u) * lg)
    phi = np.exp(logphi)
    k = np.arange(N)
    z = z0 + k * h
    f = (du / (2 * math.pi)) * np.exp(-1j * u0 * z0) * np.exp(-1j * u0 * k * h) * np.fft.fft(phi * np.exp(-1j * j * du * z0))
    f = np.maximum(f.real, 1e-300)
    c = _tail_const(alpha)
    lo = c * (1 - beta) * L ** (-alpha) if alpha < 2 else 0.0
    hi = c * (1 + beta) * L ** (-alpha) if alpha < 2 else 0.0
    F = lo + np.concatenate([[0.0], np.cumsum(0.5 * (f[1:] + f[:-1]) * h)])
    F = lo + (F - lo) * ((1 - lo - hi) / max(F[-1] - lo, 1e-300))
    return z, f, np.clip(F, 0, 1)


def _grid_eval_pdf(u, z, f, alpha, beta):
    out = np.interp(u, z, f)
    if alpha < 2:
        c = _tail_const(alpha)
        L = z[-1]
        big = u > L
        small = u < z[0]
        out = np.where(big, alpha * c * (1 + beta) * np.abs(u) ** (-alpha - 1), out)
        out = np.where(small, alpha * c * (1 - beta) * np.abs(u) ** (-alpha - 1), out)
    return np.maximum(out, 1e-300)


def stable_rnd(alpha, beta, gam, delta, size, rng=None):
    """Chambers-Mallows-Stuck sampler, S1 parameterisation."""
    rng = np.random.default_rng() if rng is None else rng
    V = rng.uniform(-math.pi / 2, math.pi / 2, size)
    W = rng.exponential(1.0, size)
    if abs(alpha - 1) > 1e-9:
        B = math.atan(beta * math.tan(math.pi * alpha / 2)) / alpha
        S = (1 + beta ** 2 * math.tan(math.pi * alpha / 2) ** 2) ** (1 / (2 * alpha))
        X = S * np.sin(alpha * (V + B)) / np.cos(V) ** (1 / alpha) * \
            (np.cos(V - alpha * (V + B)) / W) ** ((1 - alpha) / alpha)
        return gam * X + delta
    X = (2 / math.pi) * ((math.pi / 2 + beta * V) * np.tan(V) -
                         beta * np.log((math.pi / 2 * W * np.cos(V)) / (math.pi / 2 + beta * V)))
    return gam * X + (2 / math.pi) * beta * gam * math.log(gam) + delta


