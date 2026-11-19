"""Sadid Risk Analytics: reference checks for the four prototype workbooks.

Each function recomputes a model's reference example from its published
synthetic inputs, using the method written on the product page, and compares
the result with the values read from the workbook (expected_outputs.json).

Run:  python3 reference_checks.py      (needs numpy and scipy)
All data is synthetic. No real institution, portfolio or market is represented.
"""
import json, os, sys
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
load = lambda name: json.load(open(os.path.join(HERE, name)))
EXPECTED = load('expected_outputs.json')
TOL = 1e-6          # absolute tolerance on every compared value
results = []

def compare(model, label, got, want):
    ok = abs(got - want) <= TOL
    results.append(ok)
    print('%-4s %-22s %-58s %16.6f %16.6f' % ('PASS' if ok else 'FAIL', model, label, got, want))

# ------------------------------------------------------------------ ALM Stress Tester v0.3
def alm():
    d = load('alm_stress_tester_inputs.json')
    I, O, par, mid = np.array(d['inflows'], float), np.array(d['outflows'], float), d['scenario_rates'], d['bucket_midpoints_years']
    delay_keys = ['d_ret', 'd_corp', 'd_pub', 'd_ij']
    for s, name in enumerate(d['scenarios']):
        p = {k: v[s] for k, v in par.items()}
        inflow = np.zeros(8); delayed = np.zeros(8)
        for i in range(6):
            if i < 4:                                   # financing classes: non-payment, then delay by one bucket
                keep = I[i] * (1 - p['loss']); dl = p[delay_keys[i]]
                for b in range(8):
                    inflow[b] += keep[b] * ((1 - dl) if b < 7 else 1.0)   # nothing is delayed out of the last bucket
                    if b > 0: inflow[b] += keep[b - 1] * dl
                    if b < 7: delayed[b] += keep[b] * dl
            else:
                inflow += I[i]
        outflow = np.zeros(8)
        for i, k in enumerate(['r_cur', 'r_psia', 'r_term']):          # accelerated withdrawal
            o = O[i] * (1 - p[k]); o[0] = O[i][0] + p[k] * O[i][1:].sum(); outflow += o
        outflow += O[3] * (1 - p['roll']) + O[4] + O[5]                 # wholesale net of rollover, sukuk issued, other
        outflow[0] += d['undrawn_commitments'] * p['draw']
        buffer = d['cash'] + d['liquid_sukuk'] * (1 - p['hc'])
        pos = buffer + np.cumsum(inflow - outflow)
        neg = np.where(pos < 0)[0]
        survived = 8 if len(neg) == 0 else int(neg[0])
        h = d['policy_horizon_bucket']
        cost = sum(delayed[b] * d['funding_cost'] * min(d['delay_cap_years'], mid[b + 1] - mid[b]) for b in range(7))
        e = EXPECTED['alm_stress_tester'][name]
        for label, got in [('buffer after haircut', buffer), ('lowest position', pos.min()), ('position at policy horizon', pos[h - 1]),
                           ('buckets survived', survived), ('extra buffer needed', max(0.0, -pos[:h].min())),
                           ('inflows delayed', delayed.sum()), ('cost of delay', cost)]:
            compare('ALM', name + ': ' + label, got, e[label])

# ------------------------------------------------------------------ Hedge Sizer v0.3
def hedge():
    d = load('hedge_sizer_inputs.json')
    G, Z, W, MID, UP = (np.array(d[k], float) for k in ['gap_usd_m', 'zero_rate', 'weight', 'midpoint_years', 'upper_bound_years'])
    g = -G * 1e6 * MID * np.exp(-Z * MID) * 1e-4                        # signed gap DV01 in USD
    A = np.zeros((len(G), len(d['swap_tenors_years'])))
    par = []
    for j, T in enumerate(d['swap_tenors_years']):
        t = np.arange(1, T + 1); df = np.exp(-np.interp(t, MID, Z) * t)
        c = (1 - df[-1]) / df.sum(); par.append(c)                      # par rate, annual fixed payments
        for k, tt in enumerate(t):
            cf = c + (1.0 if tt == T else 0.0)
            A[np.searchsorted(UP, tt, side='left'), j] += -cf * tt * df[k] * 1e-4 * 1e6   # per USD 1m notional
    Wm = np.diag(W)
    N = -np.linalg.solve(A.T @ Wm @ A + d['size_penalty'] * np.eye(A.shape[1]), A.T @ Wm @ g)
    e = EXPECTED['hedge_sizer']
    for j, T in enumerate(d['swap_tenors_years']):
        compare('Hedge', '%dY par rate' % T, par[j], e['par_rate'][j])
        compare('Hedge', '%dY exact notional (USD m)' % T, N[j], e['exact_notional'][j])
    for b in range(len(G)):
        compare('Hedge', 'gap DV01 bucket %d (USD)' % (b + 1), g[b], e['gap_dv01'][b])
    Nr = np.round(N / d['rounding_lot']) * d['rounding_lot']
    obj = lambda n: float(W @ (g + A @ n) ** 2)
    compare('Hedge', 'reduction in weighted squared DV01, exact', 1 - obj(N) / obj(0 * N), e['reduction_exact'])
    compare('Hedge', 'reduction in weighted squared DV01, rounded', 1 - obj(Nr) / obj(0 * N), e['reduction_rounded'])

# ------------------------------------------------------------------ Tail-Risk Screen v0.3
def tail():
    d = load('tail_risk_screen_inputs.json')
    a = 1 - d['confidence']
    for key in ['portfolio', 'comparison']:
        x = np.array(d[key]); m, s = x.mean(), x.std(ddof=1); z = stats.norm.ppf(a)
        S, K = stats.skew(x, bias=False), stats.kurtosis(x, bias=False)
        v = int(min(30, max(5, round(4 + 6 / K)))) if K > 0 else 30
        sc = s * np.sqrt((v - 2) / v); t = stats.t.ppf(a, v)
        q = np.percentile(x, 100 * a)                                    # linear interpolation, as Excel PERCENTILE
        zcf = z + (z**2 - 1) * S / 6 + (z**3 - 3 * z) * K / 24 - (2 * z**3 - 5 * z) * S**2 / 36
        losses = np.sort(-x)[::-1]; k = d['hill_k']
        hill = 1 / np.mean(np.log(losses[:k] / losses[k]))
        e = EXPECTED['tail_risk_screen'][key]
        for label, got in [('skewness', S), ('excess kurtosis', K), ('normal VaR', -(m + s * z)), ('normal ES', -m + s * stats.norm.pdf(z) / a),
                           ('Cornish-Fisher VaR', -(m + s * zcf)), ('degrees of freedom', v), ('Student-t VaR', -(m + sc * t)),
                           ('Student-t ES', -m + sc * stats.t.pdf(t, v) / a * (v + t * t) / (v - 1)),
                           ('historical VaR', -q), ('historical tail average', -x[x <= q].mean()),
                           ('tail observations', int((x <= q).sum())), ('Hill tail index', hill)]:
            compare('Tail', key + ': ' + label, got, e[label])

# ------------------------------------------------------------------ Equity Mandate Monitor v0.5
def equity():
    d = load('equity_mandate_monitor_inputs.json')
    b = np.array(d['benchmark_returns']); a = 1 - d['confidence']
    for key in ['A', 'B', 'C']:
        r = np.array(d['manager_returns'][key]); act = r - b
        te = act.std(ddof=1) * np.sqrt(12)
        idx = np.cumprod(1 + r); peak = np.maximum.accumulate(np.concatenate([[1.0], idx]))[1:]
        q = np.percentile(r, 100 * a)
        nes = -r.mean() + r.std(ddof=1) * stats.norm.pdf(stats.norm.ppf(a)) / a
        w = np.array([h[2] for h in d['holdings'][key]])
        e = EXPECTED['equity_mandate_monitor'][key]
        for label, got in [('annualised return', idx[-1] ** (12 / len(r)) - 1), ('tracking error', te),
                           ('information ratio', act.mean() * 12 / te), ('maximum drawdown', (idx / np.maximum(peak, 1.0) - 1).min()),
                           ('historical VaR', -q), ('historical tail average', -r[r <= q].mean()), ('normal ES', nes),
                           ('largest single weight', w.max()), ('effective number of names', 1 / (w**2).sum())]:
            compare('Equity', 'Manager ' + key + ': ' + label, got, e[label])

if __name__ == '__main__':
    print('%-4s %-22s %-58s %16s %16s' % ('', 'model', 'output', 'recomputed', 'workbook'))
    alm(); hedge(); tail(); equity()
    print('\n%d of %d comparisons within %g' % (sum(results), len(results), TOL))
    sys.exit(0 if all(results) else 1)
