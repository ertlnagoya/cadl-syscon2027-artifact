#!/usr/bin/env python
"""Driver for the CADL mutation analysis.

    python run.py control      # step 1: YAML round-trip control
    python run.py generate     # step 2: write mutants/ (calls mutate.py)
    python run.py run          # step 3: run cadl check / verify on every mutant
    python run.py summarize    # step 4: results.csv -> summary.csv / summary_table.md
    python run.py supplement   # optional: MA2/MA3 uncapped, by position class

Each mutant is compared with the *round-tripped* original (baseline), so
a check item that already fails or warns on the original is never
counted as a detection.  Outcomes:

  MUTANT-INVALID   cadl could not parse the mutant (or timed out)
  DETECTED-CHECK   `cadl check` exits non-zero and reports an error absent from the baseline
  DETECTED-VERIFY  check passes, `cadl verify --format json` has a failed item absent from the baseline
  MASKED           nothing new fails, but an item the operator targets already failed on the original
  WARNING-ONLY     nothing new fails; a new warning / unknown item appears
  NOT-DETECTED     no new error, failure or warning
"""

from __future__ import annotations

import csv
import os
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
CADL = os.environ.get("CADL", "cadl")
PY = os.environ.get("PY", sys.executable)
SUBJ = HERE / "subjects"
MUT = HERE / "mutants"
CTRL = HERE / "control"
TIMEOUT = 60
NEGATIVE_CONTROL = {"alone_naive.cadl"}
OPS = ["MA1", "MA2", "MA3", "MC1", "MC2", "MC3", "MC4", "MC5", "MR1", "MR2", "MR3",
       "ML1", "ML2", "ML3", "ML4", "ML5", "ML6", "MP1", "MD1"]

sys.path.insert(0, str(HERE))


def _norm(s: str) -> str:
    return re.sub(r" at line \d+, col \d+", "", s).strip()


def run_tools(path: Path) -> dict:
    """Run `cadl check` and `cadl verify --format json` on one file."""
    r = {"path": str(path)}
    try:
        c = subprocess.run([CADL, "check", str(path)], capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {**r, "invalid": "check timeout"}
    out = c.stdout + c.stderr
    r["check_rc"] = c.returncode
    if "Parse error" in out:
        return {**r, "invalid": _norm(out.strip().splitlines()[0])}
    r["errors"] = [_norm(l) for l in c.stderr.splitlines() if "[ERROR]" in l]
    r["warnings"] = [_norm(l) for l in c.stderr.splitlines() if "[WARNING]" in l]
    try:
        v = subprocess.run([CADL, "verify", "--format", "json", str(path)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {**r, "invalid": "verify timeout"}
    r["verify_rc"] = v.returncode
    try:
        j = json.loads(v.stdout)
    except Exception:
        return {**r, "invalid": "verify output not JSON: " + (v.stdout + v.stderr)[:200]}
    items = [(x["name"], x["status"], x["message"]) for x in j["verification"] + j["deadlock"]]
    r["items"] = items
    r["summary"] = j["summary"]
    r["tc_ok"] = j["type_check"]["ok"]
    return r


def fingerprint(r: dict) -> dict:
    """What must be identical between an original and its round-trip."""
    if "invalid" in r:
        return {"invalid": r["invalid"]}
    return {"check_rc": r["check_rc"], "n_errors": len(r["errors"]), "n_warnings": len(r["warnings"]),
            "errors": sorted(r["errors"]), "warnings": sorted(r["warnings"]),
            "verify_rc": r["verify_rc"], "summary": r["summary"], "items": sorted(r["items"])}


# --------------------------------------------------------------- control

def cmd_control():
    import mutate
    CTRL.mkdir(exist_ok=True)
    rows = []
    for f in sorted(SUBJ.glob("*.cadl")):
        rt = CTRL / f.name
        rt.write_text(mutate.dump(mutate.load(f.read_text(encoding="utf-8"))), encoding="utf-8")
        a, b = run_tools(f), run_tools(rt)
        fa, fb = fingerprint(a), fingerprint(b)
        same = fa == fb
        from cadl.parser import parse_file
        ast_same = repr(parse_file(f)) == repr(parse_file(rt))
        rows.append(dict(file=f.name, identical=same, ast_identical=ast_same,
                         check_rc=fa.get("check_rc"), errors=fa.get("n_errors"), warnings=fa.get("n_warnings"),
                         verify_rc=fa.get("verify_rc"),
                         verify_total=fa.get("summary", {}).get("total"),
                         verify_passed=fa.get("summary", {}).get("passed"),
                         verify_failed=fa.get("summary", {}).get("failed"),
                         rt_check_rc=fb.get("check_rc"), rt_errors=fb.get("n_errors"),
                         rt_warnings=fb.get("n_warnings"), rt_verify_rc=fb.get("verify_rc"),
                         rt_verify_total=fb.get("summary", {}).get("total"),
                         rt_verify_passed=fb.get("summary", {}).get("passed"),
                         rt_verify_failed=fb.get("summary", {}).get("failed")))
        if not same:
            print("DIFF", f.name, json.dumps(fa, indent=1), json.dumps(fb, indent=1))
    with open(HERE / "control.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r["file"], "IDENTICAL" if r["identical"] else "DIFFERENT", "AST-same" if r["ast_identical"] else "AST-DIFF",
              f"check_rc={r['check_rc']} err={r['errors']} warn={r['warnings']} "
              f"verify_rc={r['verify_rc']} {r['verify_passed']}/{r['verify_total']} failed={r['verify_failed']}")
    print("all identical:", all(r["identical"] and r["ast_identical"] for r in rows))


# -------------------------------------------------------------- generate

def cmd_generate(out=MUT, extra=()):
    import shutil
    if out.exists():
        shutil.rmtree(out)
    files = [str(f) for f in sorted(SUBJ.glob("*.cadl")) if f.name not in NEGATIVE_CONTROL]
    subprocess.run([PY, str(HERE / "mutate.py"), str(SUBJ), str(out)] + files + list(extra), check=True)


# ------------------------------------------------------------------- run

def classify(m: dict, base: dict, r: dict) -> dict:
    exp = [re.compile(e) for e in m["expected"]]
    hit = lambda s: any(e.search(s) for e in exp)
    out = {"file": m["file"], "operator": m["op"], "instance": m["instance"],
           "mutant_path": str(Path(m["path"]).relative_to(HERE)), "description": m["description"]}
    if "invalid" in r:
        return {**out, "outcome": "MUTANT-INVALID", "first_item": r["invalid"], "on_target": "",
                "new_errors": "", "new_failed": "", "new_warnings": ""}
    bc = Counter(base["errors"])
    new_err = list((Counter(r["errors"]) - bc).elements())
    fails = lambda x: [f"{n}: {msg}" for n, s, msg in x["items"] if s == "failed"]
    warns = lambda x: x["warnings"] + [f"[{s}] {n}: {msg}" for n, s, msg in x["items"] if s in ("warning", "unknown")]
    new_fail = list((Counter(fails(r)) - Counter(fails(base))).elements())
    new_warn = list((Counter(warns(r)) - Counter(warns(base))).elements())
    if r["check_rc"] != 0 and new_err:
        outcome, items = "DETECTED-CHECK", new_err
    elif r["check_rc"] == 0 and new_fail:
        outcome, items = "DETECTED-VERIFY", new_fail
    elif any(hit(x) for x in fails(base)) and any(hit(x) for x in fails(r)):
        outcome, items = "MASKED", [x for x in fails(r) if hit(x)]
    elif new_warn:
        outcome, items = "WARNING-ONLY", new_warn
    else:
        outcome, items = "NOT-DETECTED", []
    on_target = ""
    if outcome.startswith("DETECTED"):
        on_target = "yes" if any(hit(x) for x in items) else "no"
    first = next((x for x in items if hit(x)), items[0] if items else "")
    return {**out, "outcome": outcome, "first_item": first, "on_target": on_target,
            "new_errors": " | ".join(new_err), "new_failed": " | ".join(new_fail),
            "new_warnings": " | ".join(new_warn)}


def cmd_run(mut=MUT, out_csv="results.csv"):
    import mutate
    manifest = json.loads((mut / "manifest.json").read_text())
    CTRL.mkdir(exist_ok=True)
    baselines = {}
    for f in sorted({m["file"] for m in manifest}):
        rt = CTRL / f
        rt.write_text(mutate.dump(mutate.load((SUBJ / f).read_text(encoding="utf-8"))), encoding="utf-8")
        baselines[f] = run_tools(rt)
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda m: run_tools(Path(m["path"])), manifest))
    rows = [classify(m, baselines[m["file"]], r) for m, r in zip(manifest, results)]
    fields = ["file", "operator", "instance", "mutant_path", "outcome", "first_item", "on_target",
              "description", "new_errors", "new_failed", "new_warnings"]
    with open(HERE / out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(Counter(r["outcome"] for r in rows))


# ------------------------------------------------------------- summarize

def cmd_summarize():
    manifest = json.loads((MUT / "manifest.json").read_text())
    applicable = defaultdict(dict)
    for m in manifest:
        applicable[m["op"]][m["file"]] = m["applicable_instances"]
    rows = list(csv.DictReader(open(HERE / "results.csv")))
    by = defaultdict(list)
    for r in rows:
        by[r["operator"]].append(r)
    out = []
    for op in OPS:
        rs = by.get(op, [])
        c = Counter(r["outcome"] for r in rs)
        n = len(rs)
        valid = n - c["MUTANT-INVALID"]
        det = c["DETECTED-CHECK"] + c["DETECTED-VERIFY"]
        on = sum(1 for r in rs if r["on_target"] == "yes")
        out.append({"operator": op, "applicable_files": len(applicable.get(op, {})),
                    "instances_before_cap": sum(applicable.get(op, {}).values()),
                    "mutants": n, "detected_check": c["DETECTED-CHECK"], "detected_verify": c["DETECTED-VERIFY"],
                    "warning_only": c["WARNING-ONLY"], "not_detected": c["NOT-DETECTED"],
                    "masked": c["MASKED"], "invalid": c["MUTANT-INVALID"],
                    "detected_on_target": on,
                    "detection_rate": f"{det / valid:.3f}" if valid else "n/a"})
    tot = {k: sum(r[k] for r in out) for k in out[0] if k not in ("operator", "detection_rate")}
    valid = tot["mutants"] - tot["invalid"]
    out.append({"operator": "ALL", **tot,
                "detection_rate": f"{(tot['detected_check'] + tot['detected_verify']) / valid:.3f}"})
    out[-1]["applicable_files"] = ""
    with open(HERE / "summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    hdr = ["operator", "applicable_files", "mutants", "detected_check", "detected_verify", "warning_only",
           "not_detected", "masked", "invalid", "detected_on_target", "detection_rate"]
    lines = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for r in out:
        lines.append("| " + " | ".join(str(r[h]) for h in hdr) + " |")
    (HERE / "summary_table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


_POS = ["parties", "decision_holder", "sharing", "responsibilities key", "protocol", "lifecycle on",
        "monitor observe", "incentives.rules", "violation.detect", "violation.action", "predicate-form on",
        "lifecycle when", "monitor rule", "transition"]


def position_class(desc: str) -> str:
    head = desc.split(":")[0]
    if desc.startswith("protocol"):
        return "protocol step" if head.endswith(" step") else "protocol " + head.split()[-1]
    if desc.startswith("transition"):
        return "regime transition " + head.split()[-1]
    for k in _POS:
        if desc.startswith(k):
            return k
    return "other"


def cmd_supplement():
    """Supplementary run (not part of the main table): MA2 and MA3 without
    the 10-instance cap, tabulated by position class."""
    sup = HERE / "mutants_uncapped"
    cmd_generate(sup, ["--cap", "100000", "--ops", "MA2,MA3"])
    cmd_run(sup, "results_uncapped.csv")
    rows = list(csv.DictReader(open(HERE / "results_uncapped.csv")))
    c = Counter((r["operator"], position_class(r["description"]), r["outcome"]) for r in rows)
    keys = sorted({(o, p) for o, p, _ in c})
    outs = ["DETECTED-CHECK", "DETECTED-VERIFY", "WARNING-ONLY", "NOT-DETECTED", "MASKED", "MUTANT-INVALID"]
    lines = ["| operator | position | mutants | " + " | ".join(outs) + " |", "|" + "---|" * (3 + len(outs))]
    for o, p in keys:
        n = sum(c[(o, p, x)] for x in outs)
        lines.append(f"| {o} | {p} | {n} | " + " | ".join(str(c[(o, p, x)]) for x in outs) + " |")
    (HERE / "supplement_positions.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    {"control": cmd_control, "generate": cmd_generate, "run": cmd_run,
     "summarize": cmd_summarize, "supplement": cmd_supplement}[sys.argv[1]]()
