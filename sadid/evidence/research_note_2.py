"""Sadid Risk Analytics: calculations behind the technical note
"When does VaR under a normal distribution understate risk?"

Reads the synthetic return series published as tail_risk_screen_inputs.json and
recomputes every figure quoted in the note.  Run:  python3 research_note_2.py
(needs numpy and scipy).  All data is synthetic.
"""
import json, os
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'tail_risk_screen_inputs.json')))

def models(x, conf):
    """Normal, Student-t (moment heuristic) and historical figures, losses as positive numbers."""
    a = 1 - conf; m, s = x.mean(), x.std(ddof=1); z = stats.norm.ppf(a)
    K = stats.kurtosis(x, bias=False)
    v = int(min(30, max(5, round(4 + 6 / K)))) if K > 0 else 30
    sc = s * np.sqrt((v - 2) / v); t = stats.t.ppf(a, v)
    q = np.percentile(x, 100 * a)
    return dict(df=v, normal_var=-(m + s * z), normal_es=-m + s * stats.norm.pdf(z) / a,
                t_var=-(m + sc * t), t_es=-m + sc * stats.t.pdf(t, v) / a * (v + t * t) / (v - 1),
                hist_var=-q, hist_tail_avg=-x[x <= q].mean(), tail_obs=int((x <= q).sum()))

def kupiec(n, x, p):
    """Kupiec proportion-of-failures test: likelihood ratio and p-value for x exceedances in n days at rate p."""
    if x == 0: lr = -2 * n * np.log(1 - p)
    else:
        ph = x / n
        lr = -2 * ((n - x) * np.log(1 - p) + x * np.log(p) - (n - x) * np.log(1 - ph) - x * np.log(ph))
    return float(lr), float(1 - stats.chi2.cdf(lr, 1))

out = {}
x = np.array(d['portfolio']); c = np.array(d['comparison']); n = len(x)
out['table'] = {str(conf): {'portfolio': models(x, conf), 'comparison': models(c, conf)} for conf in (0.95, 0.975, 0.99)}

# sampling uncertainty of the historical figures at 99%: percentile bootstrap, 5,000 resamples
rng = np.random.default_rng(1)
bv, be = [], []
for _ in range(5000):
    y = rng.choice(x, n, replace=True); q = np.percentile(y, 1)
    bv.append(-q); be.append(-y[y <= q].mean())
out['bootstrap_99'] = dict(resamples=5000, hist_var_interval=[float(np.percentile(bv, 2.5)), float(np.percentile(bv, 97.5))],
                           hist_tail_avg_interval=[float(np.percentile(be, 2.5)), float(np.percentile(be, 97.5))])

# out of sample: fit on the first 250 returns, count exceedances in the last 250
fit, test = x[:250], x[250:]
oos = {}
for conf in (0.95, 0.975, 0.99):
    mo = models(fit, conf); p = 1 - conf
    row = {'expected': len(test) * p}
    for name in ('normal_var', 't_var', 'hist_var'):
        k = int((test < -mo[name]).sum()); lr, pv = kupiec(len(test), k, p)
        row[name] = dict(var=float(mo[name]), exceedances=k, kupiec_p=pv)
    oos[str(conf)] = row
out['out_of_sample'] = dict(fit_observations=250, test_observations=250, df_on_fit_window=models(fit, 0.99)['df'], results=oos)

# tail picture: the 25 largest losses against the two fitted models
m, s = x.mean(), x.std(ddof=1); v = out['table']['0.99']['portfolio']['df']; sc = s * np.sqrt((v - 2) / v)
worst = np.sort(-x)[::-1][:25]; p = (np.arange(1, 26) - 0.5) / n
out['tail_plot'] = dict(empirical=worst.tolist(), normal=(-(m + s * stats.norm.ppf(p))).tolist(), student_t=(-(m + sc * stats.t.ppf(p, v))).tolist())
out['sample'] = dict(n=n, mean=float(m), volatility=float(s), skewness=float(stats.skew(x, bias=False)), excess_kurtosis=float(stats.kurtosis(x, bias=False)),
                     losses_beyond_3_vol=int((x < m - 3 * s).sum()), expected_beyond_3_vol_normal=float(n * stats.norm.cdf(-3)))
json.dump(out, open(os.path.join(HERE, 'research_note_2_results.json'), 'w'), indent=1)

pct = lambda u: '%.2f%%' % (100 * u)
for conf, r in out['table'].items():
    for k in ('portfolio', 'comparison'):
        q = r[k]; print(conf, k, 'VaR n/t/h', pct(q['normal_var']), pct(q['t_var']), pct(q['hist_var']), '| ES n/t/h', pct(q['normal_es']), pct(q['t_es']), pct(q['hist_tail_avg']), 'obs', q['tail_obs'], 'df', q['df'])
print('bootstrap 99%:', [pct(u) for u in out['bootstrap_99']['hist_var_interval']], [pct(u) for u in out['bootstrap_99']['hist_tail_avg_interval']])
for conf, r in oos.items():
    print('oos', conf, 'expected %.2f' % r['expected'], {k: (pct(r[k]['var']), r[k]['exceedances'], round(r[k]['kupiec_p'], 3)) for k in ('normal_var', 't_var', 'hist_var')})
print(out['sample'], 'df fit', out['out_of_sample']['df_on_fit_window'])
