"""MN mutants with an attribute mapping: the transplanted contract's attribute x
is mapped to the destination's name x_v2 (as `cadl fit --map x=x_v2` does for a
contract taken from a source).

    python -I mapping.py FIT_SRC results.csv out.csv
"""
import csv, os, sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mutation'))
import yaml
import mutate as M
from cadl.fit import fit_check, _rename

rows = []
for r in csv.DictReader(open(sys.argv[2])):
    if r['operator'] != 'MN':
        continue
    path = os.path.join('mutants', f"{r['file'][:-5]}_MN_{r['contract']}.cadl")
    d = yaml.safe_load(open(path, encoding='utf-8'))
    tok = M.main_symbol_token(M.eligible(r['assumption'])[1])
    cs = d['sos']['contracts']
    for i, c in enumerate(cs):
        if c.get('id') == r['contract']:
            cs[i] = _rename(c, {tok: tok + '_v2'})
    rep = fit_check(d, r['contract'])
    base = fit_check(yaml.safe_load(open(os.path.join('..', 'mutation', 'subjects', r['file']), encoding='utf-8')), r['contract'])
    new = {(f.condition, f.kind) for f in rep.findings if f.status == 'failed'} - {(f.condition, f.kind) for f in base.findings if f.status == 'failed'}
    rows.append({'file': r['file'], 'contract': r['contract'], 'attribute': tok, 'fit_unmapped': r['fit'],
                 'fit_mapped': int(bool(new)), 'kind': ';'.join(sorted(k or '' for _, k in new))})
with open(sys.argv[3], 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), 'MN mutants; flagged without mapping', sum(int(x['fit_unmapped']) for x in rows), '; with mapping', sum(x['fit_mapped'] for x in rows))
for x in rows:
    if not x['fit_mapped']: print('not flagged:', x)
