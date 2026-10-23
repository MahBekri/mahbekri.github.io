# Exercise 11 (chapter 9)  Mean-CVaR portfolio optimisation
# INTC, IBM, AAPL, MSFT, MMM, CSCO, 1 Oct 2008 to 30 Sep 2018.
# Scenarios from kernel-smoothed margins joined by a fitted t copula;
# long-only, fully invested frontier at CVaR 95%; compared with mean-variance.
from bookkit import *
rng = np.random.default_rng(0)

symbol = ["INTC", "IBM", "AAPL", "MSFT", "MMM", "CSCO"]
dates, data = load_prices(symbol, "2008-10-01", "2018-09-30")
# NOTE: net returns; the book's data(t)/data(t-1) gives gross returns.
Return = data[1:] / data[:-1] - 1
nAsset = len(symbol)
nScen = 5000

def sim_empirical(Return, nScen):
    nSample, nAsset = Return.shape
    u = np.column_stack([ksdensity_cdf(Return[:, i], Return[:, i]) for i in range(nAsset)])
    rho, dof = copulafit_t(u)
    print(f"t copula fitted: degrees of freedom = {dof:.2f}")
    r = copularnd("t", rho, dof, nScen, rng=rng)
    return np.column_stack([ksdensity_icdf(Return[:, i], r[:, i]) for i in range(nAsset)])

AssetScen = sim_empirical(Return, nScen)

fig, ax = plt.subplots(2, 3, figsize=(9, 5))
for i, a in enumerate(ax.ravel()):
    a.hist(AssetScen[:, i], bins=60, color=COLORS[0]); a.set_title(symbol[i])
fig.suptitle("Simulated asset return scenarios"); fig.tight_layout()

# CVaR frontier (Rockafellar-Uryasev linear programme), probability level 0.95
w1 = cvar_frontier(AssetScen, 0.95, 10)
# Mean-variance frontier on the historical moments
w2 = mv_frontier(Return, 10)

mu = AssetScen.mean(axis=0)
pReturn1 = mu @ w1; pRisk1 = np.array([port_var_cvar(AssetScen, w1[:, j], 0.95)[1] for j in range(10)])
pReturn2 = mu @ w2; pRisk2 = np.array([port_var_cvar(AssetScen, w2[:, j], 0.95)[1] for j in range(10)])

mat("CVaR portfolio weights (%), ports 1..10", (w1 * 100).T, "{:8.1f}", [str(j + 1) for j in range(10)], symbol)
mat("Mean-variance weights (%), ports 1..10", (w2 * 100).T, "{:8.1f}", [str(j + 1) for j in range(10)], symbol)

best = symbol[int(np.argmax(mu))]
print(f"\nPortfolio 10 is the maximum-return end of each frontier. With long-only weights and no"
      f"\nposition limits, it holds 100% of the single asset with the highest mean return ({best})."
      "\nThis corner solution is a known property of unconstrained optimisation, not a recommendation:"
      "\nreal mandates add concentration limits (for example at most 30% per stock), and these"
      "\nfrontiers are in-sample, so their weights would need an out-of-sample test.")

plt.figure(figsize=(6.4, 4))
plt.plot(pRisk1, pReturn1, "-o", ms=3, color=COLORS[1], label="CVaR")
plt.plot(pRisk2, pReturn2, "--o", ms=3, color=COLORS[0], label="Mean-variance")
plt.title("Efficient frontiers (CVaR vs mean-variance)"); plt.xlabel("CVaR 95% of portfolio (daily)")
plt.ylabel("Mean of portfolio returns"); plt.legend(loc="lower right")

def area(ax, W, title):
    ax.stackplot(np.arange(1, W.shape[1] + 1), W * 100, labels=symbol, colors=COLORS)
    ax.set_title(title); ax.set_xlabel("Port"); ax.set_ylabel("Portfolio weights (%)"); ax.set_ylim(0, 100); ax.set_xlim(1, 10)
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
area(ax[0], w1, "CVaR"); area(ax[1], w2, "Mean-Variance"); ax[1].legend(loc="center left", bbox_to_anchor=(1, 0.5))
fig.tight_layout()

# Histogram of portfolio returns for port 6, tail beyond VaR highlighted
port = 6
pr = Return @ w1[:, port - 1]
VaR, CVaR = port_var_cvar(AssetScen, w1[:, port - 1], 0.95)
plt.figure(figsize=(6.4, 3.8))
cnt, edges, patches = plt.hist(pr, bins=50, color=GREY)
for p_, e in zip(patches, edges[:-1]):
    if e < -VaR:
        p_.set_facecolor(COLORS[1])
plt.axvline(-CVaR, ls="--", color=COLORS[1])
plt.text(-CVaR, cnt.max() * 0.85, f"CVaR = {CVaR:.4f}  ", ha="right", color=COLORS[1])
plt.title(f"Histogram of returns, CVaR portfolio {port}"); plt.xlabel("Returns"); plt.ylabel("Frequency")
plt.show()
