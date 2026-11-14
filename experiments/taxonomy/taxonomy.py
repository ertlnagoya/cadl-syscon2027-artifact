"""Mutants from a defect taxonomy beyond the encoder's fragment.

    python -I taxonomy.py FIT_SRC out.csv

For every contract c of every subject (../mutation/subjects) that assumes a
numeric comparison `x OP k` (x a symbol, k a literal, x on the left), four
operators add destination contracts that make c's assumption impossible:

  MK  three-way:   D1 guarantees x >= aux (or <=), D2 guarantees aux > k
                   (or <, ...); every pair is satisfiable, the three are not.
  MV  no shared party: a new actor EXTERNAL and a contract with parties
                   [EXTERNAL] guaranteeing NOT (x OP k).
  MU  unit:        only for a duration k: a contract sharing a party
                   guarantees x beyond k written as a bare number of
                   minutes (the intended conflict is invisible to the
                   encoder, which keeps durations in milliseconds).
  MN  renamed:     a contract sharing a party guarantees NOT (x_v2 OP k)
                   (the same attribute under another name).

Each mutant is checked with `cadl verify` (new failed item) and with
`cadl fit -c <c>` (new failed or unknown finding for c).
"""
import copy, csv, json, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mutation'))
import mutate as M
from cadl.parser import parse_expr
from cadl.ast_nodes import BinaryOp, DurationLiteral

FIT_SRC = sys.argv[1]
OUT = sys.argv[2]
CADL = os.environ.get('CADL', 'cadl')
PY = os.environ.get('PY', sys.executable)
SUBJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mutation', 'subjects')
HERE = os.path.dirname(os.path.abspath(__file__))
FLIP = {'<=': ('>=', '>'), '<': ('>=', '>='), '>=': ('<=', '<'), '>': ('<=', '<=')}


def numeric_assumption(c):
    for p in c.get('assume') or []:
        r = M.eligible(p)
        if not r or r[0] != 0:
            continue
        e = r[1]
        if not isinstance(e, BinaryOp) or e.op not in FLIP:
            continue
        if not isinstance(e.left, M._SYMS):
            continue
        toks = list(re.finditer(r'<=|>=|<|>', p))
        if len(toks) != 1:
            continue
        x, k = p[:toks[0].start()].strip(), p[toks[0].end():].strip()
        return p, e, x, k
    return None


def party(c):
    return sorted(M.parties_names(c))[0]


def add(d, cid, parties, guarantee, actor=None):
    m = copy.deepcopy(d)
    s = M.sos(m)
    if actor:
        s['actors'] = list(s.get('actors') or []) + [{'id': actor, 'role': 'external'}]
    s['contracts'] = list(s.get('contracts') or []) + [{'id': cid, 'parties': parties, 'guarantee': guarantee}]
    return m


def mutants(d):
    out = []
    for c in M.contracts(d):
        hit = numeric_assumption(c)
        if not hit:
            continue
        p, e, x, k = hit
        ge, rel = FLIP[e.op]
        pa = party(c)
        m = add(d, 'TAX_D1', [pa], [f'{x} {ge} aux_bound'])
        s = M.sos(m); s['contracts'].append({'id': 'TAX_D2', 'parties': [pa], 'guarantee': [f'aux_bound {rel} {k}']})
        out.append(('MK', c['id'], p, m))
        out.append(('MV', c['id'], p, add(d, 'TAX_EXT', ['EXTERNAL'], [M.negate(p, e)], actor='EXTERNAL')))
        if isinstance(e.right, DurationLiteral):
            mult = {'ms': 1/60000, 's': 1/60, 'min': 1, 'h': 60}[e.right.unit]
            minutes = e.right.value * mult
            bare = int(minutes) + 1 if e.op in ('<=', '<') else max(int(minutes) - 1, 0)
            g = f'{x} {">=" if e.op in ("<=", "<") else "<="} {bare}'
            out.append(('MU', c['id'], p, add(d, 'TAX_U', [pa], [g])))
        tok = M.main_symbol_token(e)
        neg = M.negate(p, e)
        occ = M.word_occurrences(neg, tok)
        if occ:
            out.append(('MN', c['id'], p, add(d, 'TAX_N', [pa], [M.replace_at(neg, occ[0], tok, tok + '_v2')])))
    return out


def verify_failed(path):
    v = subprocess.run([CADL, 'verify', '--format', 'json', path], capture_output=True, text=True, timeout=120)
    j = json.loads(v.stdout)
    return {(x['name'], x['message']) for x in j['verification'] + j['deadlock'] if x['status'] == 'failed'}


def fit_findings(path, cid):
    code = ("import sys,json; sys.path.insert(0, sys.argv[1]); import yaml; from cadl.fit import fit_check;"
            "r=fit_check(yaml.safe_load(open(sys.argv[2])), sys.argv[3]);"
            "print(json.dumps([[f.condition,f.status,f.kind or ''] for f in r.findings if f.status in ('failed','unknown')]))")
    o = subprocess.run([PY, '-I', '-c', code, FIT_SRC, path, cid], capture_output=True, text=True, timeout=120)
    return {tuple(x) for x in json.loads(o.stdout)}


rows = []
work = os.path.join(HERE, 'mutants'); os.makedirs(work, exist_ok=True)
for f in sorted(os.listdir(SUBJ)):
    if not f.endswith('.cadl') or f == 'alone_naive.cadl':
        continue
    d = M.load(open(os.path.join(SUBJ, f), encoding='utf-8').read())
    base_v = verify_failed(os.path.join(SUBJ, f))
    for n, (op, cid, p, m) in enumerate(mutants(d)):
        path = os.path.join(work, f'{f[:-5]}_{op}_{cid}.cadl')
        open(path, 'w', encoding='utf-8').write(M.dump(m))
        base_f = fit_findings(os.path.join(SUBJ, f), cid)
        nv = verify_failed(path) - base_v
        nf = fit_findings(path, cid) - base_f
        rows.append({'file': f, 'operator': op, 'contract': cid, 'assumption': p,
                     'verify': int(bool(nv)), 'fit': int(bool(nf)),
                     'fit_kind': ';'.join(sorted({x[2] for x in nf}))})
        print(rows[-1], flush=True)
with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
from collections import Counter
agg = {}
for r in rows:
    a = agg.setdefault(r['operator'], Counter()); a['n'] += 1; a['verify'] += r['verify']; a['fit'] += r['fit']
for k, v in sorted(agg.items()):
    print(k, dict(v))
