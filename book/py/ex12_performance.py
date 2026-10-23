# Exercise 12 (chapter 10)  Performance measures
# Benchmark: DJIA. Portfolio: equally weighted INTC, IBM, AAPL, MSFT, MMM, CSCO.
# 1 Oct 2008 to 30 Sep 2018. Sharpe, STARR (alpha = 0.01), Rachev ratio (0.05, 0.01).
from bookkit import *

dates, P = load_prices(["DJI", "INTC", "IBM", "AAPL", "MSFT", "MMM", "CSCO"], "2008-10-01", "2018-09-30")
rb = tick2ret(P[:, 0])
Ret_p = tick2ret(P[:, 1:])          # NOTE: net returns, consistent with tick2ret for rb
# NOTE: the book's loop `rp = Ret_p(:,i)*w` overwrites rp, keeping only CSCO/6.
rp = Ret_p @ np.full(6, 1 / 6)

def sharpe(rp, rb):
    """MATLAB sharpe(Asset, Cash): mean excess return over the std of the asset."""
    return np.mean(rp - rb) / np.std(rp, ddof=1)
# NOTE: the book calls sharpe(Asset, Cash) with the DJIA in place of cash. Since the
# DJIA is a risky benchmark, this is neither the classic Sharpe ratio (excess return
# over a risk-free rate) nor the information ratio (active return over tracking error).
# It is kept to match the book and labelled as such; the information ratio is added
# below. A classic Sharpe ratio would need a risk-free series, which the data file
# does not contain.

def information_ratio(rp, rb):
    """Mean active return over the std of active returns (tracking error)."""
    a = rp - rb
    return np.mean(a) / np.std(a, ddof=1)

def etl(r, alpha):
    """Expected tail loss: -(1/alpha) * mean of the lowest alpha share of r."""
    r = np.sort(r); n = len(r); ub = int(np.ceil(n * alpha)) - 1; x = int(np.ceil(n * alpha))
    return -1 / alpha * (r[:ub].sum() / n + (alpha - ub / n) * r[x - 1])

def STARR_ratio(rp, rb, alpha):
    return np.mean(rp - rb) / etl(rp - rb, alpha)

def rachev_ratio(rp, alpha_num, alpha_den):
    # expected tail gain at alpha_num divided by expected tail loss at alpha_den
    # NOTE: the book uses g(ub) for the boundary term; the ETL formula needs g(x), x = ceil(n*alpha).
    return etl(-rp, alpha_num) / etl(rp, alpha_den)

Sharpe = sharpe(rp, rb)
IR = information_ratio(rp, rb)
STARR = STARR_ratio(rp, rb, 0.01)
RR = rachev_ratio(rp, 0.05, 0.01)
print("Daily ratios, benchmark DJIA:")
print(f"  book's Sharpe (DJIA as cash) = {Sharpe:.4f}   mean(rp - rb) / std(rp)")
print(f"  information ratio            = {IR:.4f}   mean(rp - rb) / std(rp - rb)")
print(f"  STARR(1%)                    = {STARR:.4f}   mean(rp - rb) / ETL_1%(rp - rb)")
print(f"  Rachev ratio                 = {RR:.4f}   ETG_5%(rp) / ETL_1%(rp)")
print(f"  information ratio, annualised = {IR*np.sqrt(252):.4f}   (x sqrt(252))")
print(f"\nAnnualised arithmetic mean returns (daily mean x 252): portfolio {rp.mean()*252:.2%}, DJIA {rb.mean()*252:.2%}")
print("Constant 1/6 weights on daily returns imply daily rebalancing to equal weights.")

fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.8))
ax[0].plot(dates[1:], np.cumprod(1 + rp), label="equal-weight portfolio")
ax[0].plot(dates[1:], np.cumprod(1 + rb), label="DJIA"); ax[0].set_title("Growth of 1"); ax[0].legend()
ax[1].hist(rp - rb, bins=80, color=GREY); ax[1].set_title("Daily active return vs DJIA")
q = np.quantile(rp - rb, 0.01); ax[1].axvline(q, color=COLORS[1], ls="--"); ax[1].text(q, ax[1].get_ylim()[1]*0.8, " 1% quantile", color=COLORS[1], fontsize=8)
fig.tight_layout(); plt.show()
