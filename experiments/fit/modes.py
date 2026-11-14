"""CPU time of cadl fit when the destination has mutually exclusive operating
modes, so that the sets of contracts that can be in force together with the
rule must be enumerated (review of 2026-11-14).

    python -I modes.py FIT_SRC out.csv

A destination with n contracts and m modes: n-1 contracts spread evenly over
the modes (assume mode == k, a guarantee on s), one contract for all modes.
The rule applies in every mode. Variant 'fits': the rule guarantees an
unrelated attribute; 'misfit': it guarantees s <= m - 2, which the
contracts of the last mode contradict (a guarantee conflict in one mode).
Median process CPU time of five runs.
"""
import csv, os, statistics, sys, time
sys.path.insert(0, sys.argv[1])
from cadl.fit import fit_check


def sos(n, m, variant):
    cs = [{"id": "RULE", "parties": ["A"],
           "guarantee": ["u >= 0" if variant == "fits" else f"s <= {m - 2}"]}]
    for i in range(n - 1):
        k = i % m
        cs.append({"id": f"D{i:03d}", "parties": ["A"], "assume": [f"mode == {k}"],
                   "guarantee": [f"s >= {k}"]})
    cs.append({"id": "ALL", "parties": ["A"], "guarantee": ["t >= 0"]})
    return {"sos": {"name": "M", "type": "Collaborative", "version": "1.0.0",
                    "actors": [{"id": "A", "role": "r"}], "contracts": cs}}


rows = []
for n, m in ((10, 2), (20, 4), (50, 8), (100, 16), (200, 32)):
    for variant in ("fits", "misfit"):
        d = sos(n, m, variant)
        ts = []
        for _ in range(5):
            t = time.process_time(); r = fit_check(d, "RULE"); ts.append(time.process_time() - t)
        f3 = [f for f in r.findings if f.condition == "F3" and f.status == "failed"]
        rows.append({"contracts": n, "modes": m, "variant": variant,
                     "neighbourhood": len(r.neighbourhood), "verdict": r.verdict,
                     "conflicts": len(f3), "fit_cpu_s": round(statistics.median(ts), 3),
                     "loadavg1": round(os.getloadavg()[0], 1)})
        print(rows[-1], flush=True)
with open(sys.argv[2], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
