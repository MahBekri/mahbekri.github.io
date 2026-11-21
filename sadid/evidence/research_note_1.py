"""Sadid Risk Analytics: calculations behind the technical note
"What a small Islamic bank needs from a liquidity stress test".

Reads alm_stress_tester_inputs.json and recomputes the scenario table and the
one-assumption-at-a-time driver table quoted in the note.  Run:  python3 research_note_1.py
(needs numpy).  All data is synthetic, in USD million.
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'alm_stress_tester_inputs.json')))
I, O, par = np.array(d['inflows'], float), np.array(d['outflows'], float), d['scenario_rates']
DELAY = ['d_ret', 'd_corp', 'd_pub', 'd_ij']

def run(p):
    """Cumulative position by bucket, delayed amount by originating bucket, and the funding-cost proxy."""
    inflow = np.zeros(8); delayed = np.zeros(8)
    for i in range(6):
        if i < 4:
            keep = I[i] * (1 - p['loss']); dl = p[DELAY[i]]
            for b in range(8):
                inflow[b] += keep[b] * ((1 - dl) if b < 7 else 1.0)      # nothing is delayed out of the last bucket
                if b > 0: inflow[b] += keep[b - 1] * dl
                if b < 7: delayed[b] += keep[b] * dl
        else:
            inflow += I[i]
    outflow = np.zeros(8)
    for i, k in enumerate(['r_cur', 'r_psia', 'r_term']):
        o = O[i] * (1 - p[k]); o[0] = O[i][0] + p[k] * O[i][1:].sum(); outflow += o
    outflow += O[3] * (1 - p['roll']) + O[4] + O[5]
    outflow[0] += d['undrawn_commitments'] * p['draw']
    pos = d['cash'] + d['liquid_sukuk'] * (1 - p['hc']) + np.cumsum(inflow - outflow)
    mid = d['bucket_midpoints_years']
    cost = sum(delayed[b] * d['funding_cost'] * min(d['delay_cap_years'], mid[b + 1] - mid[b]) for b in range(7))
    return pos, delayed, cost

out = {'scenarios': {}}
h = d['policy_horizon_bucket']
for s, name in enumerate(d['scenarios'][:5]):
    pos, delayed, cost = run({k: v[s] for k, v in par.items()})
    neg = np.where(pos < 0)[0]
    out['scenarios'][name] = dict(position_by_bucket=pos.tolist(), full_buckets_completed=8 if len(neg) == 0 else int(neg[0]),
                                  extra_buffer_needed=float(max(0.0, -pos[:h].min())), inflows_delayed=float(delayed.sum()),
                                  inflows_delayed_first_three_buckets=float(delayed[:3].sum()), funding_cost_proxy=float(cost))

# driver table: move each run-off assumption from its base value on its own, read the 1-3M position
base = {k: v[0] for k, v in par.items()}; runoff = {k: v[2] for k, v in par.items()}
groups = [('Early withdrawal, profit-sharing investment accounts', ['r_psia']), ('Lower rollover of wholesale funding', ['roll']),
          ('Early withdrawal, term and Wakala deposits', ['r_term']), ('Early withdrawal, current accounts', ['r_cur']),
          ('Drawdown of commitments', ['draw']), ('Haircut on liquid Sukuk', ['hc']), ('Higher payment delays', DELAY)]
b0 = run(base)[0][1]; drivers = []
for label, keys in groups:
    p = dict(base); p.update({k: runoff[k] for k in keys}); drivers.append((label, float(run(p)[0][1] - b0)))
out['drivers_1_3M'] = dict(base=float(b0), effects=drivers, runoff=float(run(runoff)[0][1]), sum_of_effects=float(sum(e for _, e in drivers)))
json.dump(out, open(os.path.join(HERE, 'research_note_1_results.json'), 'w'), indent=1)

for name, r in out['scenarios'].items():
    print('%-16s' % name, ' '.join('%9.2f' % v for v in r['position_by_bucket'][:5]), '| completed', r['full_buckets_completed'],
          '| extra %.2f | delayed %.3f (first three buckets %.3f) | cost %.4f' % (r['extra_buffer_needed'], r['inflows_delayed'], r['inflows_delayed_first_three_buckets'], r['funding_cost_proxy']))
print('base 1-3M %.2f' % b0)
for label, e in drivers: print('  %-55s %8.2f' % (label, e))
print('run-off 1-3M %.2f, base plus effects %.2f' % (out['drivers_1_3M']['runoff'], b0 + out['drivers_1_3M']['sum_of_effects']))
