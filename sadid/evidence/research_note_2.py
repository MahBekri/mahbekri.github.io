"""Sadid Risk Analytics: calculations behind the technical note
"When does normal-model VaR understate tail risk? A reproducible check on synthetic returns"

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
# This is an i.i.d. percentile bootstrap.  Resampling creates ties, so the threshold rule "at or below the
# quantile" can average more than five observations; a fixed five-worst average is reported as a sensitivity.
bv, be, b5, cnt = [], [], [], []
for _ in range(5000):
    y = rng.choice(x, n, replace=True); q = np.percentile(y, 1)
    bv.append(-q); be.append(-y[y <= q].mean()); b5.append(-np.sort(y)[:5].mean()); cnt.append(int((y <= q).sum()))
out['bootstrap_99'] = dict(method='i.i.d. percentile bootstrap', seed=1, resamples=5000,
                           hist_var_interval=[float(np.percentile(bv, 2.5)), float(np.percentile(bv, 97.5))],
                           hist_tail_avg_interval=[float(np.percentile(be, 2.5)), float(np.percentile(be, 97.5))],
                           five_worst_average_interval=[float(np.percentile(b5, 2.5)), float(np.percentile(b5, 97.5))],
                           share_of_resamples_averaging_more_than_five=float(np.mean(np.array(cnt) > 5)))

# out of sample: fit on the first 250 returns, count exceedances in the last 250
fit, test = x[:250], x[250:]
oos = {}
for conf in (0.95, 0.975, 0.99):
    mo = models(fit, conf); p = 1 - conf
    row = {'expected': len(test) * p}
    for name in ('normal_var', 't_var', 'hist_var'):
        k = int((test < -mo[name]).sum()); lr, pv = kupiec(len(test), k, p)
        exact = float(stats.binomtest(k, len(test), p).pvalue)          # exact two-sided binomial test
        row[name] = dict(var=float(mo[name]), exceedances=k, kupiec_p=pv, exact_binomial_p=exact)
    oos[str(conf)] = row
out['out_of_sample'] = dict(fit_observations=250, test_observations=250, df_on_fit_window=models(fit, 0.99)['df'], results=oos)

# tail picture: the 25 largest losses against the two fitted models
m, s = x.mean(), x.std(ddof=1); v = out['table']['0.99']['portfolio']['df']; sc = s * np.sqrt((v - 2) / v)
worst = np.sort(-x)[::-1][:25]; p = (np.arange(1, 26) - 0.5) / n
out['tail_plot'] = dict(empirical=worst.tolist(), normal=(-(m + s * stats.norm.ppf(p))).tolist(), student_t=(-(m + sc * stats.t.ppf(p, v))).tolist())
S_, K_ = stats.skew(x, bias=False), stats.kurtosis(x, bias=False); jb = n / 6 * (S_**2 + K_**2 / 4)
out['jarque_bera'] = dict(statistic=float(jb), p_value=float(1 - stats.chi2.cdf(jb, 2)), note='computed from bias-corrected sample skewness and excess kurtosis, as in the workbook')
q99 = out['table']['0.99']['portfolio']
out['gaps_99'] = dict(hist_var_over_normal_var=q99['hist_var'] / q99['normal_var'] - 1, hist_tail_avg_over_normal_es=q99['hist_tail_avg'] / q99['normal_es'] - 1)
out['sample'] = dict(n=n, mean=float(m), volatility=float(s), skewness=float(stats.skew(x, bias=False)), excess_kurtosis=float(stats.kurtosis(x, bias=False)),
                     losses_beyond_3_vol=int((x < m - 3 * s).sum()), expected_beyond_3_vol_normal=float(n * stats.norm.cdf(-3)))
# ---------------------------------------------------------------- rolling backtest
# Refit each model every day on the previous 250 returns and forecast the next day, so 250 one-day forecasts.
def christoffersen(hits):
    """Independence test (Markov) and conditional coverage; returns LR_ind, p_ind."""
    h = np.asarray(hits, int); n00 = n01 = n10 = n11 = 0
    for a_, b_ in zip(h[:-1], h[1:]):
        if a_ == 0 and b_ == 0: n00 += 1
        elif a_ == 0: n01 += 1
        elif b_ == 0: n10 += 1
        else: n11 += 1
    pi01 = n01 / max(1, n00 + n01); pi11 = n11 / max(1, n10 + n11); pi = (n01 + n11) / max(1, n00 + n01 + n10 + n11)
    def ll(n_stay, n_move, pr): return (n_stay * np.log(1 - pr) if pr < 1 else 0.0) + (n_move * np.log(pr) if pr > 0 else 0.0)
    lr = -2 * (ll(n00 + n10, n01 + n11, pi) - ll(n00, n01, pi01) - ll(n10, n11, pi11))
    return float(lr), float(1 - stats.chi2.cdf(lr, 1)), n11

W = 250; T = n - W; rng2 = np.random.default_rng(7); SIMS = 5000
roll = {}
for conf in (0.95, 0.975, 0.99):
    a = 1 - conf; z = stats.norm.ppf(a); row = {'expected': T * a}
    for model in ('normal', 'student_t'):
        hits = []; var_f = []; es_f = []; sim = np.empty((SIMS, T))
        for i in range(T):
            w = x[i:i + W]; m, s = w.mean(), w.std(ddof=1)
            if model == 'normal':
                v_ = -(m + s * z); e_ = -m + s * stats.norm.pdf(z) / a; sim[:, i] = rng2.normal(m, s, SIMS)
            else:
                K = stats.kurtosis(w, bias=False); df = int(min(30, max(5, round(4 + 6 / K)))) if K > 0 else 30
                sc = s * np.sqrt((df - 2) / df); t = stats.t.ppf(a, df)
                v_ = -(m + sc * t); e_ = -m + sc * stats.t.pdf(t, df) / a * (df + t * t) / (df - 1); sim[:, i] = m + sc * rng2.standard_t(df, SIMS)
            var_f.append(v_); es_f.append(e_); hits.append(int(x[i + W] < -v_))
        var_f, es_f, hits = np.array(var_f), np.array(es_f), np.array(hits); r = x[W:]
        k = int(hits.sum()); lr_uc, p_uc = kupiec(T, k, a); lr_ind, p_ind, n11 = christoffersen(hits)
        # Acerbi-Szekely second test: Z2 = sum(r * hit) / (T a ES) + 1, zero in expectation if the model is right,
        # negative if realised tail losses are larger than forecast.  p-value by simulating from each day's fitted model.
        z2 = float((r * hits / es_f).sum() / (T * a) + 1)
        z2_sim = ((sim * (sim < -var_f)) / es_f).sum(axis=1) / (T * a) + 1
        row[model] = dict(exceedances=k, kupiec_p=p_uc, exact_binomial_p=float(stats.binomtest(k, T, a).pvalue),
                          consecutive_exceedances=int(n11), independence_p=p_ind, es_z2=z2, es_z2_p=float((z2_sim <= z2).mean()),
                          mean_var_forecast=float(var_f.mean()), mean_es_forecast=float(es_f.mean()))
    roll[str(conf)] = row
out['rolling'] = dict(window=W, forecasts=T, simulations=SIMS, seed=7, results=roll)

json.dump(out, open(os.path.join(HERE, 'research_note_2_results.json'), 'w'), indent=1)

pct = lambda u: '%.2f%%' % (100 * u)
for conf, r in out['table'].items():
    for k in ('portfolio', 'comparison'):
        q = r[k]; print(conf, k, 'VaR n/t/h', pct(q['normal_var']), pct(q['t_var']), pct(q['hist_var']), '| ES n/t/h', pct(q['normal_es']), pct(q['t_es']), pct(q['hist_tail_avg']), 'obs', q['tail_obs'], 'df', q['df'])
print('bootstrap 99%:', [pct(u) for u in out['bootstrap_99']['hist_var_interval']], [pct(u) for u in out['bootstrap_99']['hist_tail_avg_interval']])
for conf, r in oos.items():
    print('oos', conf, 'expected %.2f' % r['expected'], {k: (pct(r[k]['var']), r[k]['exceedances'], round(r[k]['kupiec_p'], 3), round(r[k]['exact_binomial_p'], 3)) for k in ('normal_var', 't_var', 'hist_var')})
print('five-worst interval', [pct(u) for u in out['bootstrap_99']['five_worst_average_interval']], 'share >5', out['bootstrap_99']['share_of_resamples_averaging_more_than_five'])
print('JB', out['jarque_bera'], 'gaps', out['gaps_99'])
print(out['sample'], 'df fit', out['out_of_sample']['df_on_fit_window'])
for conf, r in roll.items():
    print('rolling', conf, 'expected %.2f' % r['expected'], {m: (r[m]['exceedances'], 'kupiec %.3f' % r[m]['kupiec_p'], 'exact %.3f' % r[m]['exact_binomial_p'], 'consec %d' % r[m]['consecutive_exceedances'], 'ind %.3f' % r[m]['independence_p'], 'Z2 %.3f p %.3f' % (r[m]['es_z2'], r[m]['es_z2_p'])) for m in ('normal', 'student_t')})
