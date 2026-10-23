# Exercise 03 (chapter 4)  Time series modelling
# DJIA daily log returns, 1 Oct 2008 to 30 Sep 2018.
# Gaussian innovations; conditional maximum likelihood (MATLAB: arima + estimate).
from bookkit import *

dates, data = load_prices("DJI", "2008-10-01", "2018-09-30")
y = np.log(data[1:] / data[:-1])

# 1. AR(1):        y_t = c + a*y_{t-1} + sigma*eps_t
m1 = arima_estimate(y, ar=1)
# 2. MA(1):        y_t = c + b*sigma*eps_{t-1} + sigma*eps_t
m2 = arima_estimate(y, ma=1)
# 3. ARMA(1,1):    y_t = c + a*y_{t-1} + b*sigma*eps_{t-1} + sigma*eps_t
m3 = arima_estimate(y, ar=1, ma=1)
# 4. GARCH(1,1):   y_t = c + sigma_t*eps_t,
#                  sigma_t^2 = alpha0 + alpha1*sigma_{t-1}^2*eps_{t-1}^2 + beta1*sigma_{t-1}^2
m4 = arima_estimate(y, garch=True)

print("\nModel comparison (lower is better):")
for nm, m in [("AR(1)", m1), ("MA(1)", m2), ("ARMA(1,1)", m3), ("GARCH(1,1)", m4)]:
    print(f"  {nm:<11} AIC = {m.AIC:10.1f}   BIC = {m.BIC:10.1f}")

# Residual diagnostics before reading the AIC ranking: Ljung-Box Q(10) on the standardised
# residuals (left-over autocorrelation) and on their squares (left-over volatility clustering).
def ljung_box(z, lags=10):
    z = np.asarray(z) - np.mean(z); n = len(z); d = np.sum(z ** 2)
    rho = np.array([np.sum(z[k:] * z[:-k]) / d for k in range(1, lags + 1)])
    Q = n * (n + 2) * np.sum(rho ** 2 / (n - np.arange(1, lags + 1)))
    return Q, stats.chi2.sf(Q, lags)
print("\nLjung-Box Q(10) on standardised residuals")
print(f"  {'':<11}  {'residuals':<20}  {'squared residuals':<20}")
for nm, m in [("AR(1)", m1), ("MA(1)", m2), ("ARMA(1,1)", m3), ("GARCH(1,1)", m4)]:
    zs = m.res / m.sigma if np.ndim(m.sigma) else m.res / np.std(m.res)
    q1, p1 = ljung_box(zs); q2, p2 = ljung_box(zs ** 2)
    print(f"  {nm:<11}  Q = {q1:7.1f}  p = {p1:.3f}  Q = {q2:7.1f}  p = {p2:.3f}")
print("A small p-value on the squared residuals means volatility clustering is not modelled:"
      "\nonly the GARCH model should remove it.")

fig, ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
ax[0].plot(dates[1:], y, lw=0.6, color=COLORS[0]); ax[0].set_title("DJIA daily log returns")
ax[1].plot(dates[2:], m4.sigma, lw=0.9, color=COLORS[1]); ax[1].set_title("GARCH(1,1) conditional volatility")
fig.tight_layout(); plt.show()
