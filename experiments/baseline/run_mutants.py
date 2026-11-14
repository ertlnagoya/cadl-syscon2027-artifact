"""Apply baseline.py to the MC1-MC4 mutants and their subjects.

    python -I run_mutants.py ../mutation/results.csv out.csv

A mutant is flagged by a check when that check has an unsat item that the
unmutated subject does not have.
"""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from baseline import analyse

MUT = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])))


def failing(d):
    f = {'ct': set(), 'fit': set(), 'vac': set()}
    for s in d['single']:
        if 'unsat' in (s['ct_consistency'], s['ct_compatibility']): f['ct'].add(('s', s['contract']))
        if s['F2'] == 'unsat': f['fit'].add(('s', s['contract']))
    for p in d['pairs']:
        k = ('p',) + tuple(p['pair'])
        if 'unsat' in (p['ct_consistency'], p['ct_compatibility']): f['ct'].add(k)
        if p['F3'] == 'unsat': f['fit'].add(k)
        if p['vacuous_c1'] or p['vacuous_c2']: f['vac'].add(k)
    return f


rows = [r for r in csv.DictReader(open(sys.argv[1])) if r['operator'] in ('MC1', 'MC2', 'MC3', 'MC4')]
base = {}
out = []
for r in rows:
    subj = os.path.join(MUT, 'subjects', r['file'])
    if subj not in base:
        base[subj] = failing(analyse(subj))
    m = failing(analyse(os.path.join(MUT, r['mutant_path'])))
    b = base[subj]
    out.append({'file': r['file'], 'operator': r['operator'], 'instance': r['instance'], 'cadl_outcome': r['outcome'],
                'ct_new': int(bool(m['ct'] - b['ct'])), 'fit_new': int(bool(m['fit'] - b['fit'])),
                'vacuity_new': int(bool(m['vac'] - b['vac']))})
with open(sys.argv[2], 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import defaultdict
agg = defaultdict(lambda: [0, 0, 0, 0, 0])
for o in out:
    a = agg[o['operator']]; a[0] += 1; a[1] += o['ct_new']; a[2] += o['fit_new']; a[3] += o['vacuity_new']; a[4] += o['cadl_outcome'] == 'MASKED'
for k in sorted(agg): print(k, 'n=%d contract_theory=%d fit=%d vacuity=%d masked=%d' % tuple(agg[k]))
