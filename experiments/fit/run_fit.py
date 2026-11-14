"""Run the fit check (cadl fit, branch feature/fit-check) on every mutant.

    python -I run_fit.py CADL_SRC ../mutation/results.csv out.csv

For each mutant, every contract is fit-checked in the mutant and in its
subject; a mutant counts as flagged by a condition when that condition has a
failed (or, for `review`, warning) finding in the mutant that the subject
does not have.
"""
import csv, os, sys
from collections import defaultdict
sys.path.insert(0, sys.argv[1])
import yaml
from cadl.fit import fit_check

MUT = os.path.dirname(os.path.abspath(sys.argv[2]))


def findings(path):
    d = yaml.safe_load(open(path, encoding='utf-8'))
    out = set()
    for c in (d.get('sos') or {}).get('contracts') or []:
        if not isinstance(c, dict) or 'id' not in c:
            continue
        try:
            r = fit_check(d, c['id'])
        except Exception as e:
            out.add(('error', c['id'], type(e).__name__))
            continue
        for f in r.findings:
            if f.status in ('failed', 'unknown') or (f.condition == 'review' and f.status == 'warning'):
                out.add((f.condition, f.status, f.kind, f.message))
    return out


rows = list(csv.DictReader(open(sys.argv[2])))
base = {}
out = []
for r in rows:
    subj = os.path.join(MUT, 'subjects', r['file'])
    if subj not in base:
        base[subj] = findings(subj)
    new = findings(os.path.join(MUT, r['mutant_path'])) - base[subj]
    conds = sorted({x[0] for x in new})
    out.append({'file': r['file'], 'operator': r['operator'], 'instance': r['instance'],
                'cadl_outcome': r['outcome'], 'fit_new': ';'.join(conds),
                'fit_f3_kind': ';'.join(sorted({str(x[2]) for x in new if x[0] == 'F3'}))})
with open(sys.argv[3], 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
agg = defaultdict(lambda: defaultdict(int))
for o in out:
    a = agg[o['operator']]; a['n'] += 1
    a['flagged'] += bool(o['fit_new'])
    a['verify_detected'] += o['cadl_outcome'].startswith('DETECTED')
    for c in o['fit_new'].split(';'):
        if c: a[c] += 1
for k in sorted(agg):
    print(k, dict(agg[k]))
