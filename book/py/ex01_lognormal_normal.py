# Exercise 01 (chapter 3)  Price distribution and log-return distribution
# INTC daily prices, 1 Jan 2010 to 31 Dec 2018.
#  - fit a lognormal distribution to the prices      (MATLAB: lognfit)
#  - fit a normal distribution to the log returns   (MATLAB: normfit)
from bookkit import *

dates, data = load_prices("INTC", "2010-01-01", "2018-12-31")

# ---- Exercise_LogNormalFit.m ---------------------------------------------
shape, loc, scale = stats.lognorm.fit(data, floc=0)
parmhat = [np.log(scale), shape]              # [mu, sigma] of log(price)
print(f"lognormal parameters: mu = {parmhat[0]:.4f}, sigma = {parmhat[1]:.4f}")

dx = 5
x = np.arange(data.min(), data.max() + dx, dx)
ydata, _ = np.histogram(data, bins=np.append(x - dx / 2, x[-1] + dx / 2))

fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
ax[0].bar(x, ydata / len(data), width=dx * 0.95, color=GREY)
ax[0].plot(x, dx * stats.lognorm.pdf(x, parmhat[1], scale=np.exp(parmhat[0])), color=COLORS[0])
ax[0].set_title("INTC prices: histogram and lognormal fit")

s = np.sort(data)
empcdf = np.arange(1, len(s) + 1) / len(s)
ax[1].step(s, empcdf, where="post", color=GREY, label="empirical")
ax[1].plot(s, stats.lognorm.cdf(s, parmhat[1], scale=np.exp(parmhat[0])), color=COLORS[0], label="lognormal")
ax[1].set_title("Empirical vs lognormal cdf"); ax[1].legend()

# ---- Exercise_NormalFit.m ------------------------------------------------
logret = price2ret(data)
mu, sig = logret.mean(), logret.std(ddof=1)
n = len(logret)
muci = mu + np.array([-1, 1]) * stats.t.ppf(0.975, n - 1) * sig / np.sqrt(n)
sigci = sig * np.sqrt((n - 1) / stats.chi2.ppf([0.975, 0.025], n - 1))
print(f"normal parameters:    mu = {mu:.6f}  95% CI [{muci[0]:.6f}, {muci[1]:.6f}]")
print(f"                     sig = {sig:.6f}  95% CI [{sigci[0]:.6f}, {sigci[1]:.6f}]")

dx = 0.001
x = np.arange(logret.min(), logret.max() + dx, dx)
ydata, _ = np.histogram(logret, bins=np.append(x - dx / 2, x[-1] + dx / 2))
plt.figure()
plt.bar(x, ydata / n, width=dx, color=GREY)
plt.plot(x, dx * stats.norm.pdf(x, mu, sig), color=COLORS[0])
plt.title("INTC log returns: histogram and normal fit")
plt.show()
