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

fig, ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
ax[0].plot(dates[1:], y, lw=0.6, color=COLORS[0]); ax[0].set_title("DJIA daily log returns")
ax[1].plot(dates[2:], m4.sigma, lw=0.9, color=COLORS[1]); ax[1].set_title("GARCH(1,1) conditional volatility")
fig.tight_layout(); plt.show()
