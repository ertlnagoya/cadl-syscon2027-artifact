"""Labelled cases for the classification of cadl fit.

    python -I cases.py FIT_SRC out.csv

Each case is a contract RULE and destination contracts, with the expected
verdict and F3 class written before running the tool. Cases with two causes
expect the class that Definition 1 gives first (vacuous before disabling before exclusion
before guarantee conflict).
"""
import csv, sys
sys.path.insert(0, sys.argv[1])
from cadl.fit import fit_check


def sos(contracts):
    return {"sos": {"name": "T", "type": "Collaborative", "version": "1.0.0",
                    "actors": [{"id": "A", "role": "r"}, {"id": "B", "role": "r"}],
                    "contracts": contracts}}


def c(cid, parties=("A",), assume=(), guarantee=()):
    return {"id": cid, "parties": list(parties), "assume": list(assume), "guarantee": list(guarantee)}


CASES = [
    # (name, contracts, expected verdict, expected class, note)
    ("vacuous, one contract", [c("RULE", assume=["x <= 5"]), c("D", guarantee=["x >= 6"])], "misfit", "vacuous", ""),
    ("vacuous, two contracts jointly", [c("RULE", assume=["x + y <= 10"]), c("D1", guarantee=["x >= 6"]), c("D2", guarantee=["y >= 5"])], "misfit", "vacuous", ""),
    ("vacuous, shared attribute, no shared party", [c("RULE", assume=["x <= 5"]), c("D", parties=["B"], guarantee=["x >= 6"])], "misfit", "vacuous", ""),
    ("disabling (rule makes destination contract vacuous; relabelled from vacuous when the class was split, 2026-11-14)", [c("RULE", guarantee=["x >= 6"]), c("D", assume=["x <= 5"], guarantee=["z >= 0"])], "misfit", "disabling", ""),
    ("guarantee conflict", [c("RULE", guarantee=["y <= 0"]), c("D", guarantee=["y >= 1"])], "misfit", "guarantee", ""),
    ("guarantee conflict, two contracts jointly", [c("RULE", guarantee=["y <= 3"]), c("D1", guarantee=["y >= z"]), c("D2", guarantee=["z >= 4"])], "misfit", "guarantee", ""),
    ("exclusion, same mode variable", [c("RULE", assume=["mode == 1"], guarantee=["s <= 10"]), c("D", assume=["mode == 2"], guarantee=["t >= 0"])], "fits", "exclusion", ""),
    ("exclusion with conflicting guarantees (modes)", [c("RULE", assume=["mode == 1"], guarantee=["s <= 10"]), c("D", assume=["mode == 2"], guarantee=["s >= 30"])], "fits", "exclusion", ""),
    ("modes as two propositions, exclusivity stated", [c("RULE", assume=["emergency_mode", "NOT normal_mode"], guarantee=["s <= 10"]), c("D", assume=["normal_mode"], guarantee=["s >= 30"])], "fits", "exclusion", ""),
    ("modes as two propositions, exclusivity not stated", [c("RULE", assume=["emergency_mode"], guarantee=["s <= 10"]), c("D", assume=["normal_mode"], guarantee=["s >= 30"])], "fits", "exclusion", "the encoding cannot know that the modes exclude each other"),
    ("exclusion with D2, guarantee conflict with D1", [c("RULE", assume=["x >= 5"], guarantee=["y >= 5"]), c("D1", guarantee=["y <= 0"]), c("D2", assume=["x <= 0"])], "misfit", "guarantee", ""),
    ("two causes: vacuous and guarantee conflict", [c("RULE", assume=["x <= 5"], guarantee=["y <= 0"]), c("D", guarantee=["x >= 6", "y >= 1"])], "misfit", "vacuous", "first class by order"),
    ("other (no single cause)", [c("RULE", assume=["x >= 1"], guarantee=["y <= 0"]), c("D", assume=["y >= x"])], "misfit", "other", ""),
    ("fits", [c("RULE", assume=["x <= 5"], guarantee=["y >= 0"]), c("D", guarantee=["x >= 0", "y <= 10"])], "fits", "", ""),
    ("destination modes, rule unrelated", [c("RULE", assume=["x <= 5"], guarantee=["y >= 0"]), c("D1", assume=["mode == 1"], guarantee=["s <= 10"]), c("D2", assume=["mode == 2"], guarantee=["s >= 30"])], "fits", "exclusion", "two sets in force"),
    ("destination modes, conflict in one mode", [c("RULE", guarantee=["s <= 20"]), c("D1", assume=["mode == 1"], guarantee=["s <= 10"]), c("D2", assume=["mode == 2"], guarantee=["s >= 30"])], "misfit", "guarantee", ""),
    ("rule inconsistent by itself (F2)", [c("RULE", assume=["x >= 1"], guarantee=["x <= 0"]), c("D", guarantee=["z >= 0"])], "misfit", "*", "F2 fails; F3 then fails too"),
]

rows = []
for name, cs, exp_verdict, exp_class, note in CASES:
    r = fit_check(sos(cs), "RULE")
    f3 = [f for f in r.findings if f.condition == "F3"]
    got_class = f3[0].kind or "" if f3 else ""
    ok = r.verdict == exp_verdict and (exp_class == "*" or got_class == exp_class)
    rows.append({"case": name, "expected_verdict": exp_verdict, "verdict": r.verdict,
                 "expected_class": exp_class, "class": got_class,
                 "core": ";".join(f3[0].contracts) if f3 else "", "correct": int(ok), "note": note})
    print(("OK  " if ok else "MISS"), name, "->", r.verdict, got_class)
with open(sys.argv[2], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(sum(r["correct"] for r in rows), "of", len(rows), "correct")
