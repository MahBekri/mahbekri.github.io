"""Sadid Risk Analytics: how the synthetic return series in tail_risk_screen_inputs.json were generated.

Both series are 500 draws built from Student-t random numbers scaled to unit variance, so their
tails are heavier than normal by construction.  The portfolio series mixes a common factor
(5 degrees of freedom) with a specific factor (5 degrees of freedom); the comparison series uses
a specific factor with 9 degrees of freedom.  Values are rounded to five decimals.

Run:  python3 generate_tail_series.py     (needs numpy; prints whether the result equals the published file)
"""
import json, os
import numpy as np

rng = np.random.default_rng(2026); N = 500
def tn(df, n): return rng.standard_t(df, n) / np.sqrt(df / (df - 2))     # unit-variance Student-t
common = tn(5, N)
portfolio = np.round(0.0004 + 0.011 * (0.85 * common + np.sqrt(1 - 0.85**2) * tn(5, N)), 5)
comparison = np.round(0.0004 + 0.010 * (0.85 * common + np.sqrt(1 - 0.85**2) * tn(9, N)), 5)

if __name__ == '__main__':
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tail_risk_screen_inputs.json')))
    same = np.allclose(portfolio, d['portfolio'], atol=1e-12) and np.allclose(comparison, d['comparison'], atol=1e-12)
    print('regenerated series equal the published file:', bool(same))
