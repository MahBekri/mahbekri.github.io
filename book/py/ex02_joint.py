# Exercise 02 (chapter 3)  Joint distribution
# IBM and INTC daily prices, 1 Jan 2010 to 31 Dec 2018.
from bookkit import *

dates, P = load_prices(["INTC", "IBM"], "2010-01-01", "2018-12-31")
price = P
logret = price2ret(price)

# Mean and covariance of the two log-return series
mu = logret.mean(axis=0)
Sig = np.cov(logret, rowvar=False)
mat("mu", mu, "{:12.6f}", cols=["INTC", "IBM"])
mat("Sig", Sig, "{:12.3e}", rows=["INTC", "IBM"], cols=["INTC", "IBM"])

# Bivariate normal density of the log returns ...
g = np.linspace(-0.1, 0.1, 25)
X1, X2 = np.meshgrid(g, g)
p_logret = stats.multivariate_normal(mu, Sig).pdf(np.dstack([X1, X2]))
# ... and of the standardised log returns
n_logret = (logret - mu) / logret.std(axis=0, ddof=1)
n_sig = np.cov(n_logret, rowvar=False)
g2 = np.linspace(-4, 4, 25)
N1, N2 = np.meshgrid(g2, g2)
n_pdf = stats.multivariate_normal(n_logret.mean(axis=0), n_sig).pdf(np.dstack([N1, N2]))

fig = plt.figure(figsize=(8.5, 7))
ax = fig.add_subplot(221, projection="3d"); ax.plot_surface(X1, X2, p_logret, cmap="Blues"); ax.set_title("log returns")
ax = fig.add_subplot(222); ax.contour(X1, X2, p_logret, cmap="Blues_r"); ax.set_title("log returns, contours")
ax = fig.add_subplot(223, projection="3d"); ax.plot_surface(N1, N2, n_pdf, cmap="Blues"); ax.set_title("standardised")
ax = fig.add_subplot(224); ax.contour(N1, N2, n_pdf, cmap="Blues_r"); ax.set_title("standardised, contours")
fig.tight_layout()

# Portfolio with weights 1/3 (INTC) and 2/3 (IBM)
w = np.array([1 / 3, 2 / 3])
Var_P = w @ Sig @ w
Std_P = np.sqrt(Var_P)
print(f"\nVar_P = {Var_P:.4e}\nStd_P = {Std_P:.6f}")

# Correlations of log returns and of prices
mat("Corr_Logret", np.corrcoef(logret, rowvar=False), "{:10.4f}", rows=["INTC", "IBM"], cols=["INTC", "IBM"])
mat("Corr_Price", np.corrcoef(price, rowvar=False), "{:10.4f}", rows=["INTC", "IBM"], cols=["INTC", "IBM"])
rl = np.corrcoef(logret, rowvar=False)[0, 1]; rp_ = np.corrcoef(price, rowvar=False)[0, 1]
print(f"\nCorrelation, INTC vs IBM: log returns {rl:.4f}   prices {rp_:.4f}")
print(f"Covariance of log returns: {Sig[0, 1]:.3e} (in squared daily log-return units, so not comparable with a correlation)")
print("\nPrices are non-stationary, so their correlation mostly reflects common"
      "\ntrends; the log-return correlation is the meaningful dependence measure.")
plt.show()
