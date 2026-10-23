# Exercise 10 (chapter 8)  VaR backtesting
# DJIA daily returns, 1 Oct 2008 to 30 Sep 2018. Rolling 250-day estimation window,
# test window from the first trading day of 2011. Normal, historical and EWMA VaR.
from bookkit import *

dates, DJI_price = load_prices("DJI", "2008-10-01", "2018-09-30")
Returns = tick2ret(DJI_price)
DateReturns = dates[1:]
SampleSize = len(Returns)
TestWindowStart = int(np.argmax(year(DateReturns) == 2011))
TestWindow = np.arange(TestWindowStart, SampleSize)
W = 250
pVaR = np.array([0.05, 0.01])
Zscore = stats.norm.ppf(pVaR)

Normal95 = np.zeros(len(TestWindow)); Normal99 = np.zeros(len(TestWindow))
Historical95 = np.zeros(len(TestWindow)); Historical99 = np.zeros(len(TestWindow))
for i, t in enumerate(TestWindow):
    X = Returns[t - W:t]
    Sigma = X.std(ddof=1)
    Normal95[i], Normal99[i] = -Zscore * Sigma
    Historical95[i], Historical99[i] = -np.quantile(X, pVaR, method="hazen")  # MATLAB quantile rule

Lambda = 0.94
Sigma2 = np.zeros(SampleSize)
Sigma2[0] = Returns[0] ** 2
for i in range(1, TestWindowStart):
    Sigma2[i] = (1 - Lambda) * Returns[i - 1] ** 2 + Lambda * Sigma2[i - 1]
EWMA95 = np.zeros(len(TestWindow)); EWMA99 = np.zeros(len(TestWindow))
for k, t in enumerate(TestWindow):
    Sigma2[t] = (1 - Lambda) * Returns[t - 1] ** 2 + Lambda * Sigma2[t - 1]
    EWMA95[k], EWMA99[k] = -Zscore * np.sqrt(Sigma2[t])

D = DateReturns[TestWindow]
fig, ax = plt.subplots(3, 1, figsize=(8, 7.5), sharex=True)
for a, (v95, v99, nm) in zip(ax, [(Normal95, Normal99, "Gaussian"), (Historical95, Historical99, "historical simulation"), (EWMA95, EWMA99, "EWMA")]):
    a.plot(D, v95, label="95%"); a.plot(D, v99, label="99%"); a.set_title(f"VaR estimation using the {nm} method"); a.legend(loc="upper right")
fig.tight_layout()

ReturnsTest = Returns[TestWindow]
plt.figure(figsize=(8, 3.8))
plt.plot(D, ReturnsTest, color=GREY, lw=0.6, label="Returns")
plt.plot(D, -Normal95, label="Normal"); plt.plot(D, -Historical95, label="Historical"); plt.plot(D, -EWMA95, label="EWMA")
plt.title("Comparison of returns and VaR at 95% for different models"); plt.legend(ncol=4, loc="lower left")

# Zoom on Q3 2011
Z = (D >= np.datetime64("2011-07-03")) & (D <= np.datetime64("2011-09-30"))
d, R = D[Z], ReturnsTest[Z]
plt.figure(figsize=(8, 4))
plt.bar(d, R, width=0.6, color="#c9ced8", label="Returns")
for v, ls, nm, c in [(Normal95, "-", "Normal", COLORS[0]), (Historical95, "--", "Historical", COLORS[1]), (EWMA95, "-.", "EWMA", COLORS[2])]:
    plt.step(d, -v[Z], ls, where="mid", color=c, label=nm)
    hit = R < -v[Z]
    plt.plot(d[hit], -v[Z][hit], "o", mfc="none", ms=8, mew=1.5, color=c)
plt.title("95% VaR violations for different models, Q3 2011"); plt.legend(loc="lower left", ncol=4)

# Backtests (MATLAB: varbacktest + runtests)
varbacktest(ReturnsTest, np.column_stack([Normal95, Normal99]), [0.95, 0.99], ["Normal95", "Normal99"], "DJI")
print("""
  How to read the table
  TL (traffic light), MATLAB varbacktest convention applied to the whole test window,
  not the Basel 250-day window: with N observations and x failures,
  green if P(X <= x) < 95%, yellow if < 99.99%, red otherwise, where X ~ Binomial(N, 1 - VaR level).
  Coverage tests (Bin, POF, TUFF) ask whether there are too many or too few failures.
  Independence tests (CCI, TBFI) ask whether failures cluster in time; CC combines POF and CCI.
  "accept" means not rejected at the 95% test level.""")
varbacktest(ReturnsTest, np.column_stack([Normal95, Historical95, EWMA95, Normal99, Historical99, EWMA99]),
            [0.95, 0.95, 0.95, 0.99, 0.99, 0.99],
            ["Normal95", "Historical95", "EWMA95", "Normal99", "Historical99", "EWMA99"], "DJI")
for yr in (2015, 2017):
    I = year(D) == yr
    r = varbacktest(ReturnsTest[I], np.column_stack([Normal95[I], Historical95[I], EWMA95[I]]), 0.95,
                    ["Normal", "Historical", "EWMA"], f"DJI, {yr}")
print("\nConditional coverage independence (CCI) and time between failures (TBFI), 2017:")
for x in r:
    print(f"  {x['VaRID']:<11} LR_CCI = {x['LR']['CCI']:7.3f}  p = {x['p']['CCI']:.3f}   "
          f"LR_TBFI = {x['LR']['TBFI']:7.3f}  p = {x['p']['TBFI']:.3f}")
plt.show()
