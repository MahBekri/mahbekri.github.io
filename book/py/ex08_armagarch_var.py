# Exercise 08 (chapter 7)  ARMA-GARCH Value at Risk
# DJIA daily log returns, 1 Jan 2008 to 31 Dec 2018.
# ARMA(1,1)-GARCH(1,1) with Student t (and normal) innovations,
# then 10,000 Monte Carlo paths for the 10-day VaR.
from bookkit import *
rng = np.random.default_rng(0)

dates, data = load_prices("DJI", "2008-01-01", "2018-12-31")
logret = np.log(data[1:] / data[:-1])

def armagarch(logret, distname):
    est = arima_estimate(logret, ar=1, ma=1, garch=True, dist=distname)
    return est

def path_armagarch(init_ret, init_res, init_sig, est, distname, num_days, num_path):
    """Simulate y_t = c + a*y_{t-1} + b*e_{t-1} + e_t, e_t = sig_t*z_t."""
    if distname == "t":
        nu = est.DoF
        # NOTE: MATLAB's arima uses a t rescaled to unit variance; the book's
        # trnd(DF) draws are not rescaled, which inflates the simulated risk.
        z = rng.standard_t(nu, (num_days, num_path)) * np.sqrt((nu - 2) / nu)
    else:
        z = rng.standard_normal((num_days, num_path))
    y = np.full(num_path, init_ret); e = np.full(num_path, init_res); s2 = np.full(num_path, init_sig ** 2)
    out = np.empty((num_days, num_path))
    for k in range(num_days):
        s2 = est.alpha0 + est.alpha1 * e ** 2 + est.beta1 * s2
        e_new = np.sqrt(s2) * z[k]
        y = est.c + est.a * y + est.b * e + e_new
        e = e_new
        out[k] = y
    return out

t = 10
num_path = 10000
m, sig_nor = logret.mean(), logret.std(ddof=1)
norVaR95 = -stats.norm.ppf(0.05, m * t, sig_nor * np.sqrt(t))
norVaR99 = -stats.norm.ppf(0.01, m * t, sig_nor * np.sqrt(t))

results = {}
for distname in ["t", "normal"]:
    est = armagarch(logret, distname)
    sp = path_armagarch(logret[-1], est.res[-1], est.sigma[-1], est, distname, t, num_path)
    # NOTE: the book takes sp(t+1,:), the return of day 10 alone. The 10-day
    # VaR needs the cumulative 10-day log return, i.e. the sum over the path.
    SimRet = sp.sum(axis=0)
    s = np.sort(SimRet)
    results[distname] = (-s[int(np.floor(0.05 * num_path)) - 1], -s[int(np.floor(0.01 * num_path)) - 1], est, SimRet)

print(f"\n10-day VaR, DJIA, starting {str(dates[-1])}:")
print("                          VaR 95%    VaR 99%")
print(f"  normal (i.i.d., sqrt t) {norVaR95:8.3%}   {norVaR99:8.3%}")
for d in ["normal", "t"]:
    v95, v99, _, _ = results[d]
    print(f"  ARMA-GARCH, {d:<6} MC  {v95:8.3%}   {v99:8.3%}")
print("\nThe GARCH VaR is conditional on today's volatility, so it differs from the"
      "\nunconditional normal VaR in either direction depending on the market state.")

est = results["t"][2]
fig, ax = plt.subplots(2, 2, figsize=(9, 6.4))
ax[0, 0].plot(dates, data, lw=0.8); ax[0, 0].set_title("DJIA")
ax[1, 0].plot(dates[1:], logret, lw=0.5); ax[1, 0].set_title("log returns")
ax[0, 1].plot(dates[2:], est.res, lw=0.5, color=COLORS[2]); ax[0, 1].set_title("residuals (t model)")
ax[1, 1].plot(dates[2:], est.sigma, lw=0.8, color=COLORS[1]); ax[1, 1].set_title("conditional volatility")
fig.tight_layout()
plt.figure(figsize=(6.4, 3.6))
plt.hist(results["t"][3], bins=80, color=GREY)
for v, ls in [(results["t"][0], "--"), (results["t"][1], "-")]:
    plt.axvline(-v, color=COLORS[1], ls=ls)
plt.title("Simulated 10-day log returns (t innovations) with −VaR95 and −VaR99")
plt.show()
