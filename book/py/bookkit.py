"""
bookkit: helpers for the exercises of
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


def load_prices(tickers, start="2008-01-01", end="2018-12-31", path=DATA_FILE):
    """Adjusted daily closes for `tickers` between `start` and `end` (inclusive).

    Returns (dates, prices): dates is a numpy datetime64[D] vector, prices is a
    vector for one ticker or an (n x k) matrix for several, oldest first
    (no flipud needed, unlike the Yahoo CSV files used in the book)."""
    single = isinstance(tickers, str)
    if single:
        tickers = [tickers]
    with open(path) as f:
        header = f.readline().strip().split(",")
        rows = [line.strip().split(",") for line in f if line.strip()]
    dates = np.array([r[0] for r in rows], dtype="datetime64[D]")
    cols = [header.index(t) for t in tickers]
    px = np.array([[float(r[c]) for c in cols] for r in rows])
    keep = (dates >= np.datetime64(start)) & (dates <= np.datetime64(end))
    dates, px = dates[keep], px[keep]
    return dates, (px[:, 0] if single else px)


def price2ret(p):
    """Continuously compounded (log) returns, like MATLAB price2ret."""
    p = np.asarray(p, float)
    return np.diff(np.log(p), axis=0)


def tick2ret(p):
    """Simple returns, like MATLAB tick2ret."""
    p = np.asarray(p, float)
    return p[1:] / p[:-1] - 1.0


def year(d):
    return d.astype("datetime64[Y]").astype(int) + 1970


# --------------------------------------------------------------------------
# Descriptive statistics and normality tests
# --------------------------------------------------------------------------
def skewness(x):
    return float(stats.skew(x))


def kurtosis(x):
    """Pearson kurtosis (normal = 3), as in MATLAB."""
    return float(stats.kurtosis(x, fisher=False))


def kstest_normal(z):
    """One-sample Kolmogorov-Smirnov test of z against N(0,1)."""
    r = stats.kstest(z, "norm")
    n = len(z)
    cv = 1.358 / math.sqrt(n)  # asymptotic 5% critical value
    return int(r.pvalue < 0.05), float(r.pvalue), float(r.statistic), cv


def kstest_cdf(x, cdf):
    """KS test of x against an arbitrary continuous cdf (callable)."""
    x = np.sort(np.asarray(x))
    n = len(x)
    F = cdf(x)
    d = max(np.max(np.arange(1, n + 1) / n - F), np.max(F - np.arange(0, n) / n))
    p = float(stats.kstwo.sf(d, n))
    return int(p < 0.05), p, float(d), 1.358 / math.sqrt(n)


def adtest_normal(z):
    """Anderson-Darling test for normality (mean and variance estimated)."""
    r = stats.anderson(z, "norm")
    stat = float(r.statistic)
    n = len(z)
    a = stat * (1 + 0.75 / n + 2.25 / n ** 2)  # D'Agostino & Stephens adjustment
    if a >= 0.6:
        p = math.exp(1.2937 - 5.709 * a + 0.0186 * a * a)
    elif a >= 0.34:
        p = math.exp(0.9177 - 4.279 * a - 1.38 * a * a)
    elif a >= 0.2:
        p = 1 - math.exp(-8.318 + 42.796 * a - 59.938 * a * a)
    else:
        p = 1 - math.exp(-13.436 + 101.14 * a - 223.73 * a * a)
    cv = float(r.critical_values[list(r.significance_level).index(5.0)])
    return int(p < 0.05), max(min(p, 1.0), 0.0), stat, cv


def jbtest(z):
    r = stats.jarque_bera(z)
    return int(r.pvalue < 0.05), float(r.pvalue), float(r.statistic), float(stats.chi2.ppf(0.95, 2))


def qqplot(ax, x, dist=stats.norm, title="QQ plot of sample data versus standard normal"):
    """MATLAB-style qqplot: sorted sample against theoretical quantiles."""
    x = np.sort(np.asarray(x))
    n = len(x)
    pp = (np.arange(1, n + 1) - 0.5) / n
    q = dist.ppf(pp) if hasattr(dist, "ppf") else dist(pp)
    ax.plot(q, x, "+", ms=3.5, color=COLORS[0], alpha=0.8)
    q1, q3 = np.percentile(x, [25, 75])
    t1, t3 = (dist.ppf([0.25, 0.75]) if hasattr(dist, "ppf") else dist(np.array([0.25, 0.75])))
    slope = (q3 - q1) / (t3 - t1)
    xx = np.array([q.min(), q.max()])
    ax.plot(xx, q1 + slope * (xx - t1), "--", color=COLORS[1], lw=1.2)
    ax.set_title(title)
    ax.set_xlabel("Theoretical quantiles")
    ax.set_ylabel("Sample quantiles")


# --------------------------------------------------------------------------
# alpha-stable distribution (S1)
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


def fit_stable(x, verbose=False):
    """Maximum-likelihood fit of an S1 stable law, like fitdist(x,'stable').
    Starts from McCulloch's quantile estimator and maximises the likelihood
    evaluated on an FFT density grid (alpha restricted to [1.01, 2])."""
    x = np.asarray(x, float)
    st = stats.levy_stable
    st.parameterization = "S1"
    a0, b0, d0, g0 = st._fitstart(x)
    a0 = min(max(a0, 1.05), 1.99)
    s = g0  # work in units of the starting scale

    def nll(th):
        a, b, lg, d = th
        if not (1.01 <= a <= 2.0 and -1 <= b <= 1):
            return 1e12
        g = math.exp(lg)
        z, f, _ = _std_stable_grid(a, b, N=2 ** 13, L=60.0)
        u = (x / s - d) / g
        return -np.sum(np.log(_grid_eval_pdf(u, z, f, a, b))) + len(x) * math.log(g)

    th0 = np.array([a0, b0, 0.0, d0 / s])
    res = optimize.minimize(nll, th0, method="Nelder-Mead",
                            options={"xatol": 1e-5, "fatol": 1e-4, "maxiter": 1500, "maxfev": 3000})
    a, b, lg, d = res.x
    if verbose:
        print(res.message)
    return Stable(min(a, 2.0), max(min(b, 1.0), -1.0), math.exp(lg) * s, d * s)


# --------------------------------------------------------------------------
# ARMA(p<=1, q<=1) with constant or GARCH(1,1) variance, Gaussian or t
# innovations, estimated by conditional maximum likelihood (MATLAB arima/estimate)
# --------------------------------------------------------------------------
class ArimaFit:
    pass


def _std_t_logpdf(z, nu):
    # log density of a Student t rescaled to unit variance
    c = special.gammaln((nu + 1) / 2) - special.gammaln(nu / 2) - 0.5 * math.log(math.pi * (nu - 2))
    return c - (nu + 1) / 2 * np.log1p(z * z / (nu - 2))


def _arma_garch_filter(theta, y, spec):
    ar, ma, garch, tdist, const = spec
    k = 0
    c = 0.0
    if const:
        c = theta[k]; k += 1
    a = theta[k] if ar else 0.0; k += int(ar)
    b = theta[k] if ma else 0.0; k += int(ma)
    # residuals: e_t = y_t - c - a*y_{t-1} - b*e_{t-1}, conditioned on y_0, e_0 = 0
    rhs = y[1:] - c - a * y[:-1]
    e = signal.lfilter([1.0], [1.0, b], rhs)
    if garch:
        w, al, be = theta[k], theta[k + 1], theta[k + 2]; k += 3
        s0 = np.var(e)
        x = np.empty_like(e)
        x[0] = s0
        x[1:] = w + al * e[:-1] ** 2
        # s2_t = x_t + be*s2_{t-1}; with s2_0 = s0 (presample) -> correct the first term
        s2 = signal.lfilter([1.0], [1.0, -be], x)
    else:
        v = theta[k]; k += 1
        s2 = np.full_like(e, v)
    nu = theta[k] if tdist else None
    return e, s2, nu


def _arma_garch_nll(theta, y, spec):
    e, s2, nu = _arma_garch_filter(theta, y, spec)
    if np.any(s2 <= 0) or not np.all(np.isfinite(s2)):
        return 1e12
    z = e / np.sqrt(s2)
    if spec[3]:
        ll = _std_t_logpdf(z, nu) - 0.5 * np.log(s2)
    else:
        ll = -0.5 * (math.log(2 * math.pi) + np.log(s2) + z * z)
    v = -np.sum(ll)
    return v if np.isfinite(v) else 1e12


def _num_hessian(f, x, rel=1e-4):
    n = len(x)
    H = np.zeros((n, n))
    h = rel * np.maximum(np.abs(x), 1e-2)
    for i in range(n):
        for j in range(i, n):
            ei = np.zeros(n); ei[i] = h[i]
            ej = np.zeros(n); ej[j] = h[j]
            fpp = f(x + ei + ej); fpm = f(x + ei - ej)
            fmp = f(x - ei + ej); fmm = f(x - ei - ej)
            H[i, j] = H[j, i] = (fpp - fpm - fmp + fmm) / (4 * h[i] * h[j])
    return H


def arima_estimate(y, ar=0, ma=0, garch=False, dist="gaussian", constant=True, display=True):
    """Estimate y_t = c + a*y_{t-1} + e_t + b*e_{t-1},
    e_t = sigma_t*z_t, sigma_t^2 = w + alpha1*e_{t-1}^2 + beta1*sigma_{t-1}^2 (if garch)
    z_t ~ N(0,1) or unit-variance t(nu). Prints a MATLAB-style table."""
    y = np.asarray(y, float)
    S = 100.0  # estimate on percent returns for numerical conditioning
    ys = y * S
    tdist = dist.lower() in ("t", "student", "students t")
    spec = (bool(ar), bool(ma), bool(garch), tdist, bool(constant))
    names, th0, lb, ub = [], [], [], []
    if constant:
        names.append("Constant"); th0.append(ys.mean()); lb.append(-5); ub.append(5)
    if ar:
        names.append("AR{1}"); th0.append(0.05); lb.append(-0.995); ub.append(0.995)
    if ma:
        names.append("MA{1}"); th0.append(-0.05); lb.append(-0.995); ub.append(0.995)
    v = ys.var()
    if garch:
        names += ["GARCH Constant", "ARCH{1}", "GARCH{1}"]
        th0 += [0.05 * v, 0.08, 0.88]; lb += [1e-8, 0.0, 0.0]; ub += [10 * v, 0.999, 0.999]
    else:
        names.append("Variance"); th0.append(v); lb.append(1e-8); ub.append(100 * v)
    if tdist:
        names.append("DoF"); th0.append(8.0); lb.append(2.05); ub.append(200.0)
    th0, lb, ub = map(np.array, (th0, lb, ub))

    def f(th):
        if garch:
            i = names.index("ARCH{1}")
            if th[i] + th[i + 1] >= 0.9999:
                return 1e12
        return _arma_garch_nll(th, ys, spec)

    best = None
    starts = [th0]
    if ar and ma:  # ARMA(1,1) likelihoods are bimodal; try a second start
        alt = th0.copy(); alt[names.index("AR{1}")] = 0.5; alt[names.index("MA{1}")] = -0.5
        starts.append(alt)
    for s in starts:
        r = optimize.minimize(f, s, method="L-BFGS-B", bounds=list(zip(lb, ub)))
        r2 = optimize.minimize(f, r.x, method="Nelder-Mead",
                               options={"xatol": 1e-8, "fatol": 1e-9, "maxiter": 4000, "maxfev": 8000})
        cand = r2 if r2.fun < r.fun else r
        if best is None or cand.fun < best.fun:
            best = cand
    th = best.x
    try:
        # Hessian of the unconstrained likelihood (the stationarity penalty in f
        # would corrupt finite differences when alpha1 + beta1 is close to 1)
        H = _num_hessian(lambda z: _arma_garch_nll(z, ys, spec), th)
        cov = np.linalg.inv(H)
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        se = np.full_like(th, np.nan)

    # back to the original (decimal) scale
    scale = []
    for nm in names:
        if nm == "Constant":
            scale.append(1 / S)
        elif nm in ("Variance", "GARCH Constant"):
            scale.append(1 / S ** 2)
        else:
            scale.append(1.0)
    scale = np.array(scale)
    est, se = th * scale, se * scale
    e, s2, nu = _arma_garch_filter(th, ys, spec)

    out = ArimaFit()
    out.names, out.params, out.se = names, est, se
    out.tstat = est / se
    out.pvalue = 2 * stats.norm.sf(np.abs(out.tstat))
    out.logL = -best.fun - len(e) * math.log(S)  # log-likelihood of the unscaled data
    out.res = e / S
    out.sigma = np.sqrt(s2) / S
    out.nparams = len(th)
    out.n = len(e)
    out.AIC = -2 * out.logL + 2 * out.nparams
    out.BIC = -2 * out.logL + out.nparams * math.log(out.n)
    d = dict(zip(names, est))
    out.c = d.get("Constant", 0.0); out.a = d.get("AR{1}", 0.0); out.b = d.get("MA{1}", 0.0)
    out.alpha0 = d.get("GARCH Constant"); out.alpha1 = d.get("ARCH{1}"); out.beta1 = d.get("GARCH{1}")
    out.variance = d.get("Variance"); out.DoF = d.get("DoF")
    if display:
        p, q = int(bool(ar)), int(bool(ma))
        title = f"ARIMA({p},0,{q})"
        if garch:
            title += " with GARCH(1,1) variance"
        title += " Model (" + ("t" if tdist else "Gaussian") + " Distribution):"
        print("\n    " + title + "\n")
        print(f"    {'':16s}{'Value':>13s}{'StandardError':>15s}{'TStatistic':>12s}{'PValue':>13s}")
        print(f"    {'':16s}{'_'*11:>13s}{'_'*13:>15s}{'_'*10:>12s}{'_'*11:>13s}")
        for nm, v_, s_, t_, p_ in zip(names, est, se, out.tstat, out.pvalue):
            print(f"    {nm:16s}{v_:13.5g}{s_:15.5g}{t_:12.5g}{p_:13.5g}")
        print(f"\n    log-likelihood = {out.logL:.2f}   AIC = {out.AIC:.2f}   BIC = {out.BIC:.2f}")
    return out


# --------------------------------------------------------------------------
# Copulas (bivariate unless stated): cdf, pdf, random numbers
# --------------------------------------------------------------------------
def copulacdf(name, U, *param):
    name = name.lower()
    u, v = np.clip(U[:, 0], 1e-12, 1), np.clip(U[:, 1], 1e-12, 1)
    if name == "gaussian":
        rho = param[0]
        x, y = stats.norm.ppf(np.minimum(u, 1 - 1e-12)), stats.norm.ppf(np.minimum(v, 1 - 1e-12))
        mvn = stats.multivariate_normal(mean=[0, 0], cov=[[1, rho], [rho, 1]])
        return np.array([mvn.cdf([a, b]) for a, b in zip(x, y)])
    if name == "t":
        rho, nu = param
        x, y = stats.t.ppf(np.minimum(u, 1 - 1e-12), nu), stats.t.ppf(np.minimum(v, 1 - 1e-12), nu)
        mvt = stats.multivariate_t(loc=[0, 0], shape=[[1, rho], [rho, 1]], df=nu)
        return np.array([mvt.cdf([a, b]) for a, b in zip(x, y)])
    th = param[0]
    if name == "clayton":
        return np.maximum(u ** -th + v ** -th - 1, 0) ** (-1 / th)
    if name == "gumbel":
        return np.exp(-((-np.log(u)) ** th + (-np.log(v)) ** th) ** (1 / th))
    if name == "frank":
        return -np.log1p(np.expm1(-th * u) * np.expm1(-th * v) / np.expm1(-th)) / th
    raise ValueError(name)


def copulapdf(name, U, *param):
    name = name.lower()
    u, v = np.clip(U[:, 0], 1e-9, 1 - 1e-9), np.clip(U[:, 1], 1e-9, 1 - 1e-9)
    if name == "gaussian":
        r = param[0]
        x, y = stats.norm.ppf(u), stats.norm.ppf(v)
        return np.exp(-(r * r * (x * x + y * y) - 2 * r * x * y) / (2 * (1 - r * r))) / math.sqrt(1 - r * r)
    if name == "t":
        r, nu = param
        x, y = stats.t.ppf(u, nu), stats.t.ppf(v, nu)
        q = (x * x - 2 * r * x * y + y * y) / (1 - r * r)
        lj = (special.gammaln((nu + 2) / 2) + special.gammaln(nu / 2) - 2 * special.gammaln((nu + 1) / 2)
              - 0.5 * math.log(1 - r * r) - (nu + 2) / 2 * np.log1p(q / nu))
        lm = -(nu + 1) / 2 * (np.log1p(x * x / nu) + np.log1p(y * y / nu))
        return np.exp(lj - lm)
    th = param[0]
    if name == "clayton":
        return (1 + th) * (u * v) ** (-1 - th) * (u ** -th + v ** -th - 1) ** (-2 - 1 / th)
    if name == "gumbel":
        a, b = -np.log(u), -np.log(v)
        A = (a ** th + b ** th) ** (1 / th)
        return np.exp(-A) * (a * b) ** (th - 1) / (u * v) * A ** (1 - 2 * th) * (A + th - 1)
    if name == "frank":
        num = th * (1 - math.exp(-th)) * np.exp(-th * (u + v))
        den = ((1 - math.exp(-th)) - (1 - np.exp(-th * u)) * (1 - np.exp(-th * v))) ** 2
        return num / den
    raise ValueError(name)


def copularnd(name, *args, rng=None):
    """copularnd('Gaussian', rho, n), copularnd('t', Rho, nu, n),
    copularnd('Clayton'|'Gumbel'|'Frank', theta, n). rho/Rho may be a scalar
    (bivariate) or a correlation matrix."""
    rng = np.random.default_rng() if rng is None else rng
    name = name.lower()
    if name in ("gaussian", "t"):
        R = np.atleast_2d(args[0])
        if R.size == 1:
            r = float(R[0, 0]); R = np.array([[1, r], [r, 1]])
        n = int(args[-1])
        L = np.linalg.cholesky(R)
        Z = rng.standard_normal((n, R.shape[0])) @ L.T
        if name == "gaussian":
            return stats.norm.cdf(Z)
        nu = args[1]
        W = rng.chisquare(nu, (n, 1)) / nu
        return stats.t.cdf(Z / np.sqrt(W), nu)
    th, n = args[0], int(args[1])
    E = rng.exponential(1.0, (n, 2))
    if name == "clayton":  # gamma frailty (Marshall-Olkin)
        V = rng.gamma(1 / th, 1.0, (n, 1))
        return (1 + E / V) ** (-1 / th)
    if name == "gumbel":  # positive stable frailty
        a = 1 / th
        if a == 1:
            V = np.ones((n, 1))
        else:
            V = stable_rnd(a, 1.0, math.cos(math.pi * a / 2) ** (1 / a), 0.0, (n, 1), rng)
        return np.exp(-(E / V) ** a)
    if name == "frank":  # conditional inversion
        u = rng.uniform(size=n); w = rng.uniform(size=n)
        v = -np.log1p(w * np.expm1(-th) / (w + (1 - w) * np.exp(-th * u))) / th
        return np.column_stack([u, v])
    raise ValueError(name)


def copulafit_t(U):
    """Fit a t copula to pseudo-observations U (n x d): correlation matrix from
    Kendall's tau (sin(pi*tau/2)), degrees of freedom by profile likelihood."""
    n, d = U.shape
    R = np.eye(d)
    for i in range(d):
        for j in range(i + 1, d):
            tau = stats.kendalltau(U[:, i], U[:, j])[0]
            R[i, j] = R[j, i] = math.sin(math.pi * tau / 2)
    w, V = np.linalg.eigh(R)  # make sure it is positive definite
    if w.min() < 1e-6:
        R = V @ np.diag(np.maximum(w, 1e-6)) @ V.T
        dd = np.sqrt(np.diag(R)); R = R / np.outer(dd, dd)
    Ri = np.linalg.inv(R)
    ld = np.linalg.slogdet(R)[1]
    Uc = np.clip(U, 1e-9, 1 - 1e-9)

    def nll(nu):
        X = stats.t.ppf(Uc, nu)
        q = np.einsum("ij,jk,ik->i", X, Ri, X)
        lj = (special.gammaln((nu + d) / 2) + (d - 1) * special.gammaln(nu / 2) - d * special.gammaln((nu + 1) / 2)
              - 0.5 * ld - (nu + d) / 2 * np.log1p(q / nu))
        lm = -(nu + 1) / 2 * np.sum(np.log1p(X * X / nu), axis=1)
        return -np.sum(lj - lm)

    r = optimize.minimize_scalar(nll, bounds=(2.1, 100), method="bounded", options={"xatol": 1e-3})
    return R, float(r.x)


# --------------------------------------------------------------------------
# Kernel density cdf and inverse cdf (ksdensity 'function','cdf'/'icdf')
# --------------------------------------------------------------------------
def _bandwidth(x):
    x = np.asarray(x)
    sig = np.median(np.abs(x - np.median(x))) / 0.6745
    if sig == 0:
        sig = np.std(x)
    return sig * (4 / (3 * len(x))) ** 0.2  # MATLAB's normal-reference rule


def ksdensity_cdf(x, pts):
    h = _bandwidth(x)
    pts = np.asarray(pts)
    out = np.empty(len(pts))
    for k in range(0, len(pts), 500):
        out[k:k + 500] = special.ndtr((pts[k:k + 500, None] - x[None, :]) / h).mean(axis=1)
    return out


def ksdensity_icdf(x, p, ngrid=2000):
    h = _bandwidth(x)
    g = np.linspace(x.min() - 4 * h, x.max() + 4 * h, ngrid)
    F = ksdensity_cdf(x, g)
    F, idx = np.unique(F, return_index=True)
    return np.interp(p, F, g[idx])


# --------------------------------------------------------------------------
# VaR backtesting (varbacktest): TL, Bin, POF, TUFF, CC, CCI, TBFI
# --------------------------------------------------------------------------
def _lr_pof(N, x, p):
    if x == 0:
        return -2 * N * math.log(1 - p)
    if x == N:
        return -2 * N * math.log(p)
    ph = x / N
    return -2 * ((N - x) * math.log((1 - p) / (1 - ph)) + x * math.log(p / ph))


def _lr_cci(I):
    I = np.asarray(I, int)
    a, b = I[:-1], I[1:]
    n00 = int(np.sum((a == 0) & (b == 0))); n01 = int(np.sum((a == 0) & (b == 1)))
    n10 = int(np.sum((a == 1) & (b == 0))); n11 = int(np.sum((a == 1) & (b == 1)))
    pi0 = n01 / max(n00 + n01, 1); pi1 = n11 / max(n10 + n11, 1); pi = (n01 + n11) / max(len(a), 1)

    def xlog(k, q):
        return k * math.log(q) if k > 0 else 0.0
    l0 = xlog(n00 + n10, 1 - pi) + xlog(n01 + n11, pi)
    l1 = xlog(n00, 1 - pi0) + xlog(n01, pi0) + xlog(n10, 1 - pi1) + xlog(n11, pi1)
    return -2 * (l0 - l1), (n00, n01, n10, n11)


def _lr_tuff(I, p):
    idx = np.flatnonzero(I)
    if len(idx) == 0:
        return float("nan"), None
    n = int(idx[0]) + 1
    if n == 1:
        return -2 * math.log(p), n
    return -2 * (math.log(p) + (n - 1) * math.log(1 - p) - (-math.log(n) + (n - 1) * math.log(1 - 1 / n))), n


def _lr_tbfi(I, p):
    idx = np.flatnonzero(I)
    if len(idx) == 0:
        return float("nan"), 0
    gaps = np.diff(np.concatenate([[-1], idx]))  # time until first failure, then between failures
    lr = 0.0
    for n in gaps:
        n = int(n)
        if n == 1:
            lr += -2 * math.log(p)
        else:
            lr += -2 * (math.log(p) + (n - 1) * math.log(1 - p) - (-math.log(n) + (n - 1) * math.log(1 - 1 / n)))
    return lr, len(gaps)


def varbacktest(returns, VaR, var_level, var_id, portfolio="Portfolio", test_level=0.95, show=True):
    """Run the standard VaR backtests on one or more VaR series (columns).
    VaR values are positive numbers; a failure is a return below -VaR."""
    returns = np.asarray(returns, float)
    VaR = np.atleast_2d(np.asarray(VaR, float))
    if VaR.shape[0] == 1 and VaR.shape[1] == len(returns):
        VaR = VaR.T
    if np.isscalar(var_level):
        var_level = [var_level] * VaR.shape[1]
    rows = []
    for j in range(VaR.shape[1]):
        I = (returns < -VaR[:, j]).astype(int)
        N, x, p = len(I), int(I.sum()), 1 - var_level[j]
        # traffic light (Basel), scaled to the sample size
        cp = stats.binom.cdf(x, N, p)
        tl = "green" if cp < 0.95 else ("yellow" if cp < 0.9999 else "red")
        zb = (x - N * p) / math.sqrt(N * p * (1 - p))
        pb = 2 * stats.norm.sf(abs(zb))
        lpof = _lr_pof(N, x, p); ppof = stats.chi2.sf(lpof, 1)
        lcci, _ = _lr_cci(I); pcci = stats.chi2.sf(lcci, 1)
        lcc = lpof + lcci; pcc = stats.chi2.sf(lcc, 2)
        ltu, _n1 = _lr_tuff(I, p); ptu = stats.chi2.sf(ltu, 1) if np.isfinite(ltu) else float("nan")
        ltb, nf = _lr_tbfi(I, p); ptb = stats.chi2.sf(ltb, max(nf, 1)) if np.isfinite(ltb) else float("nan")
        rej = lambda pv: "reject" if (np.isfinite(pv) and pv < 1 - test_level) else "accept"
        rows.append(dict(VaRID=var_id[j], VaRLevel=var_level[j], Observed=N, Failures=x,
                         Expected=N * p, Ratio=x / (N * p), TL=tl, Bin=rej(pb), POF=rej(ppof),
                         TUFF=rej(ptu), CC=rej(pcc), CCI=rej(pcci), TBFI=rej(ptb),
                         p=dict(Bin=pb, POF=ppof, TUFF=ptu, CC=pcc, CCI=pcci, TBFI=ptb),
                         LR=dict(POF=lpof, CCI=lcci, CC=lcc, TUFF=ltu, TBFI=ltb)))
    if show:
        print(f"\n  runtests: {portfolio}")
        print(f"  {'VaRID':<13}{'Level':>6}{'Obs':>6}{'Fail':>6}{'Expect':>8}  {'TL':<7}{'Bin':<8}{'POF':<8}{'TUFF':<8}{'CC':<8}{'CCI':<8}{'TBFI':<8}")
        for r in rows:
            print(f"  {r['VaRID']:<13}{r['VaRLevel']:>6.2f}{r['Observed']:>6d}{r['Failures']:>6d}{r['Expected']:>8.1f}  "
                  f"{r['TL']:<7}{r['Bin']:<8}{r['POF']:<8}{r['TUFF']:<8}{r['CC']:<8}{r['CCI']:<8}{r['TBFI']:<8}")
    return rows


# --------------------------------------------------------------------------
# Portfolio optimisation: mean-CVaR (Rockafellar-Uryasev LP) and mean-variance
# --------------------------------------------------------------------------
def _cvar_lp(S, beta, target=None):
    """min CVaR_beta of loss -S@w s.t. sum w = 1, w >= 0 (and mean >= target)."""
    nS, nA = S.shape
    # variables: w (nA), zeta (1), z (nS)
    c = np.concatenate([np.zeros(nA), [1.0], np.full(nS, 1 / ((1 - beta) * nS))])
    from scipy import sparse
    A = sparse.hstack([sparse.csr_matrix(-S), sparse.csr_matrix(-np.ones((nS, 1))), -sparse.identity(nS, format="csr")], format="csr")
    b = np.zeros(nS)
    mu = S.mean(axis=0)
    if target is not None:
        A = sparse.vstack([A, sparse.csr_matrix(np.concatenate([-mu, [0.0], np.zeros(nS)])[None, :])], format="csr")
        b = np.concatenate([b, [-target]])
    Aeq = np.concatenate([np.ones(nA), [0.0], np.zeros(nS)])[None, :]
    bounds = [(0, 1)] * nA + [(None, None)] + [(0, None)] * nS
    r = optimize.linprog(c, A_ub=A, b_ub=b, A_eq=Aeq, b_eq=[1.0], bounds=bounds, method="highs")
    return r.x[:nA], r.x[nA], r.fun


def port_var_cvar(S, w, beta):
    """Scenario VaR and CVaR (positive numbers = losses) of portfolio w."""
    loss = -S @ w
    q = np.quantile(loss, beta)
    cv = q + np.mean(np.maximum(loss - q, 0)) / (1 - beta)
    return q, cv


def cvar_frontier(S, beta=0.95, n=10):
    mu = S.mean(axis=0)
    w_min, _, _ = _cvar_lp(S, beta)
    r_lo, r_hi = float(mu @ w_min), float(mu.max())
    W = []
    for tr in np.linspace(r_lo, r_hi, n):
        w, _, _ = _cvar_lp(S, beta, target=tr)
        W.append(np.clip(w, 0, 1))
    W = np.array(W).T
    return W / W.sum(axis=0)


def mv_frontier(R, n=10):
    mu = R.mean(axis=0)
    C = np.cov(R, rowvar=False)
    nA = len(mu)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bnds = [(0, 1)] * nA
    w0 = np.full(nA, 1 / nA)
    r = optimize.minimize(lambda w: w @ C @ w, w0, jac=lambda w: 2 * C @ w,
                          bounds=bnds, constraints=cons, method="SLSQP", options={"ftol": 1e-14, "maxiter": 500})
    r_lo, r_hi = float(mu @ r.x), float(mu.max())
    W = []
    for tr in np.linspace(r_lo, r_hi, n):
        cc = cons + [{"type": "ineq", "fun": lambda w, tr=tr: mu @ w - tr}]
        rr = optimize.minimize(lambda w: w @ C @ w, r.x, jac=lambda w: 2 * C @ w,
                               bounds=bnds, constraints=cc, method="SLSQP", options={"ftol": 1e-14, "maxiter": 500})
        W.append(np.clip(rr.x, 0, 1))
    W = np.array(W).T
    return W / W.sum(axis=0)


def mat(name, M, fmt="{:10.5f}", rows=None, cols=None):
    """Print a vector or matrix the way MATLAB echoes a variable."""
    M = np.atleast_2d(np.asarray(M, float))
    print(f"\n{name} =\n")
    if cols:
        w = len(fmt.format(0.0))
        print(" " * (10 if rows else 0) + "".join(f"{c:>{w}s}" for c in cols))
    for i, row in enumerate(M):
        lead = f"{rows[i]:>10s}" if rows else ""
        print(lead + "".join(fmt.format(v) for v in row))
