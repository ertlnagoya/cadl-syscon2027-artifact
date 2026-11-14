"""Contract-theory baseline for the fit check.

For every contract and every pair of contracts that share a party, this script
evaluates, on the encoding of the cadl verifier (same Z3 translation, same
skipping of untranslatable predicates):

  * the checks of assume/guarantee contract theory (Benveniste et al.) on the
    saturated contracts and on their parallel composition:
      consistency   G' = G or not A           is satisfiable
      compatibility A                         is satisfiable
    with C1 (x) C2 = ((A1 and A2) or not G', G'1 and G'2);
  * the fit conditions (F2) A and G, and (F3) A1 and G1 and A2 and G2,
    and the class of a failing (F3) pair: F3a vacuous (G_d implies not A_c),
    F3b guarantee conflict (G1 and G2 unsat), F3c exclusion (A1 and A2 unsat).

    python -I baseline.py FILE...            -> one JSON line per file
"""
import json, sys
from itertools import combinations
import z3
from cadl.parser import parse_file
from cadl.verifier import Z3Context, _to_z3_bool


def conj(preds, ctx):
    out = []
    for p in preds:
        try:
            out.append(_to_z3_bool(p, ctx))
        except Exception:
            pass
    return z3.And(out) if out else z3.BoolVal(True)


def sat(f):
    s = z3.Solver(); s.set('timeout', 5000); s.add(f)
    r = s.check()
    return 'sat' if r == z3.sat else 'unsat' if r == z3.unsat else 'unknown'


def analyse(path):
    sos = parse_file(path)
    out = {'file': path, 'single': [], 'pairs': []}
    for c in sos.contracts:
        ctx = Z3Context(); A = conj(c.assume, ctx); G = conj(c.guarantee, ctx)
        out['single'].append({'contract': c.id, 'ct_consistency': sat(z3.Or(G, z3.Not(A))),
                              'ct_compatibility': sat(A), 'F2': sat(z3.And(A, G))})
    for c1, c2 in combinations(sos.contracts, 2):
        if not ({p.name for p in c1.parties} & {p.name for p in c2.parties}):
            continue
        ctx = Z3Context()
        A1, G1, A2, G2 = (conj(c1.assume, ctx), conj(c1.guarantee, ctx), conj(c2.assume, ctx), conj(c2.guarantee, ctx))
        Gp = z3.And(z3.Or(G1, z3.Not(A1)), z3.Or(G2, z3.Not(A2)))
        Ac = z3.Or(z3.And(A1, A2), z3.Not(Gp))
        out['pairs'].append({'pair': [c1.id, c2.id], 'ct_consistency': sat(Gp), 'ct_compatibility': sat(Ac),
                             'F3': sat(z3.And(A1, G1, A2, G2)),
                             'vacuous_c1': sat(z3.And(G2, A1)) == 'unsat', 'vacuous_c2': sat(z3.And(G1, A2)) == 'unsat'})
        q = out['pairs'][-1]
        if q['F3'] != 'unsat':
            q['class'] = '-'
        elif q['vacuous_c1'] or q['vacuous_c2']:
            q['class'] = 'F3a vacuous'
        elif sat(z3.And(G1, G2)) == 'unsat':
            q['class'] = 'F3b guarantee conflict'
        elif sat(z3.And(A1, A2)) == 'unsat':
            q['class'] = 'F3c exclusion'
        else:
            q['class'] = 'other'
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(json.dumps(analyse(p)), flush=True)
