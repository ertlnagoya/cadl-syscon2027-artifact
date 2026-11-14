"""CPU time of cadl fit on the synthetic descriptions of ../scale (5 runs), and of
the parsing and type checking it does first (measured separately).

    python -I timing.py FIT_SRC out.csv
"""
import csv, os, statistics, sys, time
sys.path.insert(0, sys.argv[1]); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scale'))
import yaml, scale
from cadl.fit import fit_check
from cadl.parser import parse
from cadl.type_checker import type_check
rows = []
for topo in ('star', 'chain'):
    for k in (10, 25, 50, 100, 200):
        d = yaml.safe_load(scale.gen(k, topo, 0))
        ts, pre = [], []
        for _ in range(5):
            t = time.process_time(); r = fit_check(d, 'C0'); ts.append(time.process_time() - t)
            t = time.process_time(); type_check(parse(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))); pre.append(time.process_time() - t)
        rows.append({'topology': topo, 'contracts': k, 'neighbourhood': len(r.neighbourhood),
                     'verdict': r.verdict, 'fit_cpu_s': statistics.median(ts),
                     'parse_typecheck_cpu_s': statistics.median(pre), 'loadavg1': os.getloadavg()[0]})
        print(rows[-1], flush=True)
with open(sys.argv[2], 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
