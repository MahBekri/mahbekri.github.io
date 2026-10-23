# Exercise 09 (chapter 7)  VaR and AVaR
# INTC, IBM, AAPL, MSFT, MMM, 1 Oct 2008 to 30 Sep 2018; equally weighted portfolio.
# VaR and AVaR for confidence levels 90%, 91%, ..., 99%.
from bookkit import *

StockTicker = ["INTC", "IBM", "AAPL", "MSFT", "MMM"]
dates, data = load_prices(StockTicker, "2008-10-01", "2018-09-30")
# NOTE: the book uses data(t)/data(t-1), a gross return close to 1, so the
# "losses" -stockReturn sit near -1. Net returns are used here.
stockReturn = data[1:] / data[:-1] - 1

def empVaR(eps, lossdata):
    """VaR+ = sup{x: P(L<=x)<=eps}, VaR- = inf{x: P(L<=x)>=eps}."""
    s = np.sort(lossdata); n = len(s); cce = int(np.ceil(n * eps))
    return s[cce - 1], s[cce - 2]          # (vp, vm), MATLAB indices cce and cce-1

def empAVaR(eps, lossdata):
    """Empirical AVaR (Acerbi-Tasche): mean of the worst (1-eps) share of losses,
    with the boundary observation weighted fractionally. (Not listed in the book.)"""
    s = np.sort(lossdata)[::-1]; n = len(s); k = (1 - eps) * n; kf = int(np.floor(k))
    return (s[:kf].sum() + (k - kf) * (s[kf] if kf < n else 0)) / k

def normalAVaR(eps, lossdata):
    mu, sigma = lossdata.mean(), lossdata.std(ddof=1)
    var = stats.norm.ppf(eps, mu, sigma)
    avar = sigma * np.exp(-(var - mu) ** 2 / (2 * sigma ** 2)) / ((1 - eps) * np.sqrt(2 * np.pi)) + mu
    return avar, var

beta = np.round(np.arange(0.90, 0.995, 0.01), 2)
k = len(StockTicker)
VaR = np.zeros((len(beta), k)); AVaR = np.zeros_like(VaR); nVaR = np.zeros_like(VaR); nAVaR = np.zeros_like(VaR)
for j, b in enumerate(beta):
    for i in range(k):
        L = -stockReturn[:, i]
        VaR[j, i] = empVaR(b, L)[0]
        AVaR[j, i] = empAVaR(b, L)
        nAVaR[j, i], nVaR[j, i] = normalAVaR(b, L)

w = np.full(k, 0.2)
portReturn = stockReturn @ w
P = np.array([[empVaR(b, -portReturn)[0], empAVaR(b, -portReturn), *normalAVaR(b, -portReturn)[::-1]] for b in beta])

rows = [f"{b:.2f}" for b in beta]
mat("valueAtRisk (empirical)", VaR * 100, "{:9.3f}", rows, StockTicker)
mat("averageValueAtRisk (empirical)", AVaR * 100, "{:9.3f}", rows, StockTicker)
mat("normalValueAtRisk", nVaR * 100, "{:9.3f}", rows, StockTicker)
mat("normalAverageValueAtRisk", nAVaR * 100, "{:9.3f}", rows, StockTicker)
mat("portfolio, % of value", P * 100, "{:9.3f}", rows, ["VaR emp", "AVaR emp", "VaR nor", "AVaR nor"])
print("\nConventions: empirical VaR at level b is the ceil(n*b)-th smallest loss; empirical AVaR"
      "\naverages the worst (1-b)*n losses, counting the boundary loss with its fractional weight."
      "\nConstant 20% weights on daily returns imply daily rebalancing.")
print("\nAll figures are daily losses in percent. Diversification: the portfolio AVaR is"
      "\nbelow the average of the stocks' AVaRs (subadditivity of a coherent measure).")
print(f"  99%: portfolio AVaR {P[-1,1]:.3%} vs mean stock AVaR {AVaR[-1].mean():.3%}")

fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.8))
for i, t in enumerate(StockTicker):
    ax[0].plot(beta, AVaR[:, i] * 100, "-o", ms=3, label=t)
ax[0].set_title("Empirical AVaR by stock (%)"); ax[0].legend(); ax[0].set_xlabel("confidence level")
ax[1].plot(beta, P[:, 0] * 100, "-o", ms=3, label="VaR empirical")
ax[1].plot(beta, P[:, 1] * 100, "-o", ms=3, label="AVaR empirical")
ax[1].plot(beta, P[:, 2] * 100, "--", label="VaR normal")
ax[1].plot(beta, P[:, 3] * 100, "--", label="AVaR normal")
ax[1].set_title("Equally weighted portfolio (%)"); ax[1].legend(); ax[1].set_xlabel("confidence level")
fig.tight_layout(); plt.show()
