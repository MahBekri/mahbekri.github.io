# Exercise 04 (chapter 5)  Goodness of fit
# DJIA daily log returns, 1 Jan 2010 to 31 Dec 2018. Are they normal?
from bookkit import *

dates, data = load_prices("DJI", "2010-01-01", "2018-12-31")
logret = price2ret(data)

print(f"min = {logret.min():.5f}   max = {logret.max():.5f}")

# Empirical mean, variance, skewness and kurtosis vs the normal values
mu, sig = logret.mean(), logret.std(ddof=1)
s, k = skewness(logret), kurtosis(logret)
print(f"mean     = {mu:.6f}")
print(f"variance = {sig**2:.4e}")
print(f"skewness = {s:.4f}   (normal: 0)")
print(f"kurtosis = {k:.4f}   (normal: 3)")

# Histogram against the fitted normal density
dx = (logret.max() - logret.min()) / 200
xdata = np.arange(logret.min(), logret.max() + dx / 2, dx)
ydata, _ = np.histogram(logret, bins=np.append(xdata - dx / 2, xdata[-1] + dx / 2))
ydata = ydata / len(logret)
# NOTE: the book divides by sqrt(2*pi*sig); the normal density uses sig*sqrt(2*pi).
pdfNorm = np.exp(-(xdata - mu) ** 2 / (2 * sig ** 2)) / (sig * np.sqrt(2 * np.pi))

fig, ax = plt.subplots(2, 2, figsize=(9, 6.4))
ax[0, 0].plot(dates, data, lw=0.8); ax[0, 0].set_title("DJIA")
ax[1, 0].plot(dates[1:], logret, lw=0.5); ax[1, 0].set_title("log returns")
ax[0, 1].plot(xdata, ydata, ".-", ms=3, lw=0.6, label="empirical")
ax[0, 1].plot(xdata, pdfNorm / pdfNorm.sum(), "k-", label="normal"); ax[0, 1].legend()
ax[0, 1].set_title("density")
x = (logret - mu) / sig
qqplot(ax[1, 1], x)
fig.tight_layout()

# KS, AD and JB statistics on the standardised returns
print("\n           H      p-value      stat    5% crit.")
for nm, f in [("KS", kstest_normal), ("AD", adtest_normal), ("JB", jbtest)]:
    H, p, st, cv = f(x)
    print(f"  {nm}:  {H:5d}  {p:11.3g}  {st:8.4f}  {cv:8.4f}")
# NOTE: the mean and variance used to standardise x are estimated from the same data.
# The table KS p-value assumes known parameters; AD above applies the estimated-parameter
# correction and JB is asymptotic. The Lilliefors version of KS, simulated here, gives the
# KS p-value with estimated parameters.
rng = np.random.default_rng(2021)
B = 999
Dsim = np.array([stats.kstest((z - z.mean()) / z.std(ddof=1), "norm").statistic
                 for z in rng.standard_normal((B, len(x)))])
D_obs = kstest_normal(x)[2]
print(f"  KS with estimated mean and variance (Lilliefors, {B} simulations): p = {(1 + np.sum(Dsim >= D_obs)) / (B + 1):.3g}")
print("\nH = 1 rejects normality at the 5% level: the log returns are not normal")
print("(excess kurtosis and heavy tails, visible in the QQ plot).")
plt.show()
