# Exercise 07 (chapter 7)  alpha-stable Value at Risk
# DJIA daily log returns, 1 Jan 2008 to 31 Dec 2018.
from bookkit import *

dates, data = load_prices("DJI", "2008-01-01", "2018-12-31")
logret = np.log(data[1:] / data[:-1])
sortedlogret = np.sort(logret)
n = len(logret)

xmin, xmax = logret.min(), logret.max()
dx = (xmax - xmin) / 100
xdata = np.arange(xmin, xmax + dx / 2, dx)
ydata, _ = np.histogram(logret, bins=np.append(xdata - dx / 2, xdata[-1] + dx / 2))
ydata = ydata / n

m, sig_nor = logret.mean(), logret.std(ddof=1)
print(f"mean = {m:.6f}  std = {sig_nor:.6f}  skewness = {skewness(logret):.3f}  kurtosis = {kurtosis(logret):.3f}")
pdfNormal = stats.norm.pdf(xdata, m, sig_nor)
H, p, ks, cv = kstest_normal((logret - m) / sig_nor)
print(f"KS test, normal: stat = {ks:.4f}  p = {p:.3g}  -> {'reject' if H else 'accept'}")

# Fit the stable law by maximum likelihood (MATLAB: fitdist(logret,'stable'))
pdStable = fit_stable(logret)
print(pdStable)
pdfStable = pdStable.fast_pdf(xdata)
H, p, ks, cv = kstest_cdf(logret, pdStable.fast_cdf)
print(f"KS test, stable: stat = {ks:.4f}  p = {p:.3g}  -> {'reject' if H else 'accept'}")

# VaR at 95% and 99%: normal, stable and empirical
norVaR95, norVaR99 = -stats.norm.ppf([0.05, 0.01], m, sig_nor)
stableVaR95 = -pdStable.icdf(0.05)
stableVaR99 = -pdStable.icdf(0.01)
# NOTE: MATLAB indexes from 1, so sortedlogret(floor(0.05*n)) is element floor(0.05*n)-1 here.
empVaR95 = -sortedlogret[int(np.floor(0.05 * n)) - 1]
empVaR99 = -sortedlogret[int(np.floor(0.01 * n)) - 1]
print("\n            VaR 95%    VaR 99%")
print(f"  normal    {norVaR95:8.4%}   {norVaR99:8.4%}")
print(f"  stable    {stableVaR95:8.4%}   {stableVaR99:8.4%}")
print(f"  empirical {empVaR95:8.4%}   {empVaR99:8.4%}")
for lvl, nv, sv, ev in [("95%", norVaR95, stableVaR95, empVaR95), ("99%", norVaR99, stableVaR99, empVaR99)]:
    print(f"  {lvl}: normal is {'below' if nv < ev else 'above'} the empirical VaR, "
          f"stable is {'below' if sv < ev else 'above'} it")

pp = (np.arange(1, n + 1) - 0.5) / n
fig, ax = plt.subplots(2, 2, figsize=(9, 6.6))
ax[0, 0].plot(xdata, ydata, "o", ms=3, mfc="none", color=GREY)
ax[0, 0].plot(xdata, pdfNormal / pdfNormal.sum(), "-"); ax[0, 0].set_title("normal fit")
# NOTE: the book's qqplot(sortedlogret, norminv(sortedlogret, ...)) passes returns
# where probabilities are expected; the QQ plots below use plotting positions.
qqplot(ax[0, 1], logret, stats.norm(m, sig_nor), "QQ plot: normal")
ax[1, 0].plot(xdata, ydata, "o", ms=3, mfc="none", color=GREY)
ax[1, 0].plot(xdata, pdfStable / pdfStable.sum(), "-", color=COLORS[1]); ax[1, 0].set_title("stable fit")
qqplot(ax[1, 1], logret, pdStable.fast_icdf, "QQ plot: stable")
for a in (ax[0, 0], ax[1, 0]):
    a.set_yscale("log"); a.set_ylim(1e-4, 0.2)
fig.tight_layout(); plt.show()
