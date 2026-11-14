#!/usr/bin/env python
"""Mutation operators for the CADL mutation analysis.

Every operator takes the parsed YAML document of a subject (a plain
dict, as returned by ``yaml.safe_load``) and returns a list of mutants.
Each mutant is a deep copy of the document with exactly one injected
defect, plus a description and the check item(s) that, if they fire,
show that the *injected* defect (not something else) was found
("expected" patterns, used only to label on-target detections).

Mutants are written back with ``dump`` (PyYAML).  The control step in
``run.py control`` shows that load+dump does not change any check or
verify result for the subjects, so YAML-level editing is sound here.

Usage:
    python mutate.py SUBJECT_DIR OUT_DIR [FILES...] [--cap N] [--ops MA2,MA3]
        writes OUT_DIR/<stem>/<OP>_<k>.cadl + OUT_DIR/manifest.json

Determinism: no randomness; instances are enumerated in file order
(YAML mapping order is preserved by PyYAML >= 5.1) and capped at
CAP = 10 per operator per file (the first 10 are kept).
"""

from __future__ import annotations

import copy
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from itertools import combinations
from pathlib import Path

import yaml

from cadl.ast_nodes import (ActorRef, BinaryOp, BoolLiteral, DurationLiteral,
                            FloatLiteral, FunctionCall, Identifier, IntLiteral,
                            MemberAccess, UnaryOp)
from cadl.parser import parse_expr, _parse_actor_ref_list

CAP = 10
GHOST = "GHOST"                 # undeclared actor name
GHOST_STATE = "GHOST_STATE"     # undeclared lifecycle state
NAME_RE = r"[A-Za-z_][A-Za-z0-9_]*"
CMP_OPS = ("<=", ">=", "==", "!=", "<", ">")
NEG = {"<=": ">", "<": ">=", ">": "<=", ">=": "<", "==": "!=", "!=": "=="}
MSG_RE = re.compile(r"^(\s*)(.+?)(\s*->\s*)(.+?)(\s*:\s*.+)$", re.S)


# ---------------------------------------------------------------- YAML I/O

def load(text: str):
    return yaml.safe_load(text)


def dump(data) -> str:
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=4096)
    # PyYAML (YAML 1.1) reads the key `on` as boolean True and writes it
    # back as `true:`. The CADL parser accepts both; restore `on:` for
    # readability. (No subject has a genuine `true:` key.)
    return re.sub(r"^(\s*(?:- )?)true:", r"\1on:", text, flags=re.M)


# ---------------------------------------------------------------- helpers

@dataclass
class Mutant:
    op: str
    instance: int
    description: str
    data: dict = field(repr=False)
    expected: list = field(default_factory=list)   # regexes on check/verify item text
    meta: dict = field(default_factory=dict)


def sos(d):
    return d["sos"]


def base_name(ref: str) -> str | None:
    m = re.match(r"\s*(" + NAME_RE + r")", str(ref))
    return m.group(1) if m else None


def actor_names(d) -> list[str]:
    out = []
    for a in sos(d).get("actors") or []:
        if isinstance(a, dict) and base_name(a.get("id", "")):
            out.append(base_name(a["id"]))
    return out


def word_occurrences(text: str, name: str):
    return [m.start() for m in re.finditer(
        r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", text)]


def replace_at(text: str, pos: int, old: str, new: str) -> str:
    assert text[pos:pos + len(old)] == old
    return text[:pos] + new + text[pos + len(old):]


def rename_ref(ref: str, name: str) -> str:
    """Rename the base name of an actor reference string (keeps the index)."""
    occ = word_occurrences(ref, name)
    return replace_at(ref, occ[0], name, GHOST)


def get_on(tr: dict):
    if "on" in tr:
        return "on"
    if True in tr:
        return True
    return None


def is_message_event(text: str) -> bool:
    return "->" in text and MSG_RE.match(text.strip()) is not None


def contracts(d):
    return [c for c in (sos(d).get("contracts") or []) if isinstance(c, dict)]


def parties_names(c) -> set[str]:
    return {r.name for r in _parse_actor_ref_list(c.get("parties", []))}


# ------------------------------------------------- site enumeration (MA2/MA3)
# A site is (path, kind, name, extra): path addresses a string value
# (kind 'value') or a mapping key (kind 'key') inside the document.
# 'part' selects the sender/receiver part of a message string.

def _get(d, path):
    for p in path:
        d = d[p]
    return d


def _set_value(d, path, value):
    _get(d, path[:-1])[path[-1]] = value


def _rename_key(d, path, new_key):
    parent = _get(d, path[:-1])
    old = path[-1]
    items = list(parent.items())
    parent.clear()
    for k, v in items:
        parent[new_key if k == old else k] = v


def _msg_sites(text, path, kind, names, cls):
    m = MSG_RE.match(text)
    out = []
    if not m:
        return out
    for grp, role in ((2, "sender"), (4, "receiver")):
        b = base_name(m.group(grp))
        if b in names:
            out.append(dict(cls=cls, path=path, kind=kind, name=b, part=grp,
                            where=f"{role} of message '{text.strip()}'"))
    return out


def _step_sites(steps, path, names):
    out = []
    if not isinstance(steps, list):
        return out
    for i, st in enumerate(steps):
        p = path + [i]
        if isinstance(st, str):
            if "->" in st:
                out += _msg_sites(st, p, "value", names, "checked")
        elif isinstance(st, dict):
            for k, v in st.items():
                ks = str(k)
                if "->" in ks:
                    # {"A -> B": msg} form: the key holds sender and receiver
                    m = re.match(r"(.+?)\s*->\s*(.+)", ks)
                    for grp, role in ((1, "sender"), (2, "receiver")):
                        b = base_name(m.group(grp))
                        if b in names:
                            out.append(dict(cls="checked", path=p + [k], kind="key",
                                            name=b, part=grp, where=f"{role} of step key '{ks}'"))
                elif ks == "parallel" or ks.startswith("if ") or ks == "else":
                    out += _step_sites(v, p + [k], names)
    return out


def enumerate_sites(d) -> list[dict]:
    """All actor-name occurrences, in file order, tagged checked/unchecked."""
    names = set(actor_names(d))
    sites: list[dict] = []
    s = sos(d)

    def text_sites(text, path, where):
        if not isinstance(text, str):
            return
        found = []
        for n in names:
            for pos in word_occurrences(text, n):
                found.append((pos, n))
        for pos, n in sorted(found):
            sites.append(dict(cls="unchecked", path=path, kind="value", name=n,
                              pos=pos, where=f"{where}: '{text}'"))

    for top, block in s.items():
        if top == "contracts":
            for ci, c in enumerate(block or []):
                if not isinstance(c, dict):
                    continue
                cp = ["sos", "contracts", ci]
                for key, val in c.items():
                    if key == "parties" and isinstance(val, list):
                        for j, r in enumerate(val):
                            if base_name(r) in names:
                                sites.append(dict(cls="checked", path=cp + ["parties", j], kind="value",
                                                  name=base_name(r), where=f"parties of {c['id']}"))
                    elif key == "authority" and isinstance(val, dict):
                        h = val.get("decision_holder")
                        if h is not None and base_name(h) in names:
                            sites.append(dict(cls="checked", path=cp + ["authority", "decision_holder"],
                                              kind="value", name=base_name(h),
                                              where=f"decision_holder of {c['id']}"))
                    elif key == "information" and isinstance(val, dict):
                        for j, e in enumerate(val.get("sharing") or []):
                            if isinstance(e, str):
                                for st in _msg_sites(e, cp + ["information", "sharing", j], "value", names, "checked"):
                                    st["where"] = f"sharing of {c['id']}: " + st["where"]
                                    sites.append(st)
                    elif key == "responsibilities" and isinstance(val, dict):
                        for k in val:
                            if base_name(k) in names:
                                sites.append(dict(cls="checked", path=cp + ["responsibilities", k], kind="key",
                                                  name=base_name(k), where=f"responsibilities key of {c['id']}"))
                    elif key == "incentives" and isinstance(val, dict):
                        for j, r in enumerate(val.get("rules") or []):
                            text_sites(r, cp + ["incentives", "rules", j], f"incentives.rules of {c['id']}")
                    elif key == "violation" and isinstance(val, dict):
                        for vk in ("detect", "action"):
                            if vk in val:
                                text_sites(val[vk], cp + ["violation", vk], f"violation.{vk} of {c['id']}")
                    elif key == "lifecycle" and isinstance(val, dict):
                        for ti, tr in enumerate(val.get("transitions") or []):
                            tp = cp + ["lifecycle", "transitions", ti]
                            for tk, tv in tr.items():
                                if tk == "when":
                                    text_sites(tv, tp + ["when"], f"lifecycle when of {c['id']}.{tr.get('id')}")
                                elif tk in ("on", True) and isinstance(tv, str):
                                    if is_message_event(tv):
                                        for st in _msg_sites(tv, tp + [tk], "value", names, "checked"):
                                            st["where"] = f"lifecycle on of {c['id']}.{tr.get('id')}: " + st["where"]
                                            sites.append(st)
                                    else:
                                        text_sites(tv, tp + [tk], f"predicate-form on of {c['id']}.{tr.get('id')}")
                    elif key == "monitors" and isinstance(val, list):
                        for mi, mon in enumerate(val):
                            mp = cp + ["monitors", mi]
                            for mk, mv in mon.items():
                                if mk == "observe":
                                    entries = mv if isinstance(mv, list) else [mv]
                                    for j, e in enumerate(entries):
                                        try:
                                            ex = parse_expr(str(e))
                                        except Exception:
                                            continue
                                        if isinstance(ex, MemberAccess) and ex.obj.name in names:
                                            path = mp + ["observe", j] if isinstance(mv, list) else mp + ["observe"]
                                            sites.append(dict(cls="checked", path=path, kind="value",
                                                              name=ex.obj.name,
                                                              where=f"monitor observe of {mon.get('id')}: '{e}'"))
                                elif mk == "rule":
                                    text_sites(mv, mp + ["rule"], f"monitor rule of {mon.get('id')}")
        elif top == "protocols":
            for pi, pr in enumerate(block or []):
                pp = ["sos", "protocols", pi]
                for key, val in pr.items():
                    if key == "steps":
                        for st in _step_sites(val, pp + ["steps"], names):
                            st["where"] = f"protocol {pr.get('id')} step: " + st["where"]
                            sites.append(st)
                    elif key in ("trigger", "precondition", "postcondition"):
                        text_sites(val, pp + [key], f"protocol {pr.get('id')} {key}")
        elif top == "transitions":
            for ti, tr in enumerate(block or []):
                for key in tr:
                    if key in ("condition", "safety_invariant"):
                        text_sites(tr[key], ["sos", "transitions", ti, key],
                                   f"transition {tr.get('from')}->{tr.get('to')} {key}")
    return sites


def apply_site(d, site):
    """Rename the actor name at `site` to GHOST in a copy of d."""
    d = copy.deepcopy(d)
    name = site["name"]
    if site["kind"] == "key":
        old = site["path"][-1]
        if "part" in site and "->" in str(old):
            m = re.match(r"(.+?)(\s*->\s*)(.+)", str(old))
            parts = [m.group(1), m.group(2), m.group(3)]
            idx = 0 if site["part"] == 1 else 2
            parts[idx] = rename_ref(parts[idx], name)
            new = "".join(parts)
        else:
            new = rename_ref(str(old), name)
        _rename_key(d, site["path"], new)
        return d, f"{old!s} -> {new}"
    old = _get(d, site["path"])
    if "part" in site:
        m = MSG_RE.match(old)
        g = list(m.groups())
        g[site["part"] - 1] = rename_ref(g[site["part"] - 1], name)
        new = "".join(g)
    elif "pos" in site:
        new = replace_at(old, site["pos"], name, GHOST)
    else:
        new = rename_ref(str(old), name)
    _set_value(d, site["path"], new)
    return d, f"'{old}' -> '{new}'"


# ------------------------------------------------- predicates (MC1..MC5)

_SYMS = (ActorRef, Identifier, MemberAccess, FunctionCall)
_LITS = (IntLiteral, FloatLiteral, DurationLiteral, BoolLiteral)


def eligible(text):
    """Return (rank, ast) if the predicate is one whose negation the SMT
    encoder represents faithfully, else None.  rank 0: symbol vs literal
    order comparison (numeric); 1: other comparison with a symbol;
    2: bare boolean symbol/call."""
    if not isinstance(text, str):
        return None
    try:
        e = parse_expr(text)
    except Exception:
        return None
    if isinstance(e, BinaryOp) and e.op in CMP_OPS:
        has_sym = isinstance(e.left, _SYMS) or isinstance(e.right, _SYMS)
        if not has_sym:
            return None
        lit = isinstance(e.left, _LITS) or isinstance(e.right, _LITS)
        if e.op in ("<", "<=", ">", ">=") and lit:
            return (0, e)
        return (1, e)
    if isinstance(e, (FunctionCall, MemberAccess)) or (isinstance(e, ActorRef) and e.index is None):
        return (2, e)
    return None


def negate(text, e):
    """Textual negation that keeps the variable spelling."""
    if isinstance(e, BinaryOp):
        toks = list(re.finditer(r"<=|>=|==|!=|<|>", text))
        if len(toks) == 1 and toks[0].group() == e.op:
            t = toks[0]
            return text[:t.start()] + NEG[e.op] + text[t.end():]
        return f"NOT ({text})"
    return f"NOT {text}"


def main_symbol_token(e):
    """The token naming the constrained variable (for the _v2 rename)."""
    if isinstance(e, BinaryOp):
        e = e.left if isinstance(e.left, _SYMS) else e.right
    if isinstance(e, MemberAccess):
        return e.member
    if isinstance(e, (FunctionCall, Identifier, ActorRef)):
        return e.name
    return None


def pick(preds):
    """First eligible predicate, lowest rank first, then file order."""
    cands = []
    for i, p in enumerate(preds or []):
        r = eligible(p)
        if r:
            cands.append((r[0], i, p, r[1]))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[1]))
    return cands[0][2], cands[0][3]


def _cid(c):
    return re.escape(str(c["id"]))


# ---------------------------------------------------------------- operators

def op_MA1(d):
    out = []
    actors = sos(d).get("actors") or []
    checked = enumerate_sites(d)
    for i, a in enumerate(actors):
        name = base_name(a.get("id", ""))
        m = copy.deepcopy(d)
        del sos(m)["actors"][i]
        refs = len(word_occurrences(dump(m), name))
        if refs == 0:
            continue
        nchk = sum(1 for s in checked if s["name"] == name and s["cls"] == "checked")
        out.append(Mutant("MA1", 0, f"delete actor '{a.get('id')}' (textual refs elsewhere={refs}, refs in MA2-checked positions={nchk})",
                          m, [rf"Undefined actor '{re.escape(name)}'", rf"'{re.escape(name)}' is not a declared actor"],
                          {"refs": refs, "refs_checked": nchk}))
    return out


def _ma(d, cls, op):
    out = []
    for s in enumerate_sites(d):
        if s["cls"] != cls:
            continue
        m, change = apply_site(d, s)
        out.append(Mutant(op, 0, f"{s['where']}: {change}", m,
                          [r"Undefined actor 'GHOST'", r"'GHOST' is not a declared actor"]))
    return out


def op_MA2(d):
    return _ma(d, "checked", "MA2")


def op_MA3(d):
    return _ma(d, "unchecked", "MA3")


def op_MC1(d):
    out = []
    for ci, c in enumerate(contracts(d)):
        m = copy.deepcopy(d)
        mc = contracts(m)[ci]
        cand = pick((c.get("assume") or []) + (c.get("guarantee") or []))
        if cand:
            p, e = cand
            added = [negate(p, e)]
            src = "assume" if p in (c.get("assume") or []) else "guarantee"
            desc = f"{c['id']}: guarantee += '{added[0]}' (contradicts own {src} '{p}')"
        else:
            added = ["cadl_mut_v > 1", "cadl_mut_v < 0"]
            desc = f"{c['id']}: no eligible predicate; guarantee += {added}"
        mc["guarantee"] = list(mc.get("guarantee") or []) + added
        out.append(Mutant("MC1", 0, desc, m, [rf"Contract '{_cid(c)}' consistency"]))
    return out


def op_MC2(d):
    out = []
    for ci, c in enumerate(contracts(d)):
        cand = pick(c.get("assume"))
        if not cand:
            continue
        p, e = cand
        m = copy.deepcopy(d)
        mc = contracts(m)[ci]
        mc["assume"] = list(mc["assume"]) + [negate(p, e)]
        out.append(Mutant("MC2", 0, f"{c['id']}: assume += '{negate(p, e)}' (contradicts assume '{p}')",
                          m, [rf"Contract '{_cid(c)}' assumptions"]))
    return out


def _cross(d, op, share: bool, rename: bool):
    out = []
    cs = contracts(d)
    for i, j in combinations(range(len(cs)), 2):
        shared = bool(parties_names(cs[i]) & parties_names(cs[j]))
        if shared != share:
            continue
        choice = None
        for a, b in ((i, j), (j, i)):
            cand = pick(cs[a].get("assume"))
            if cand:
                choice = (a, b, "assume", cand)
                break
        if choice is None:   # neither contract has an eligible assume
            for a, b in ((i, j), (j, i)):
                cand = pick(cs[a].get("guarantee"))
                if cand:
                    choice = (a, b, "guarantee", cand)
                    break
        if choice is None:
            continue
        a, b, src, (p, e) = choice
        neg = negate(p, e)
        if rename:
            tok = main_symbol_token(e)
            occ = word_occurrences(neg, tok)
            neg = replace_at(neg, occ[0], tok, tok + "_v2")
        m = copy.deepcopy(d)
        mb = contracts(m)[b]
        mb["guarantee"] = list(mb.get("guarantee") or []) + [neg]
        A, B = cs[a]["id"], cs[b]["id"]
        exp = [rf"Cross-contract '({re.escape(A)}|{re.escape(B)})' x '({re.escape(A)}|{re.escape(B)})'"]
        out.append(Mutant(op, 0, f"{B}.guarantee += '{neg}' vs {A}.{src} '{p}' (share party: {shared})",
                          m, exp, {"A_source": src}))
    return out


def op_MC3(d):
    return _cross(d, "MC3", share=True, rename=False)


def op_MC4(d):
    return _cross(d, "MC4", share=True, rename=True)


def op_MC5(d):
    return _cross(d, "MC5", share=False, rename=False)


def _transitions(d):
    return sos(d).get("transitions") or []


def op_MR1(d):
    out = []
    groups: dict = {}
    for i, t in enumerate(_transitions(d)):
        groups.setdefault(t.get("from"), []).append(i)
    for reg, idx in groups.items():
        if len(idx) < 2:
            continue
        t1, t2 = _transitions(d)[idx[0]], _transitions(d)[idx[1]]
        if not t1.get("condition"):
            continue
        m = copy.deepcopy(d)
        _transitions(m)[idx[1]]["condition"] = t1["condition"]
        out.append(Mutant("MR1", 0,
                          f"{reg}->{t2.get('to')} condition '{t2.get('condition')}' := '{t1['condition']}' (copy of {reg}->{t1.get('to')})",
                          m, [rf"Transition exclusivity: {re.escape(str(reg))} -> {re.escape(str(t1.get('to')))} vs {re.escape(str(reg))} -> {re.escape(str(t2.get('to')))}"]))
    return out


def _regimes(d):
    seen = []
    for t in _transitions(d):
        for r in (t.get("from"), t.get("to")):
            if r not in seen:
                seen.append(r)
    return seen


def op_MR2(d):
    out = []
    for r in _regimes(d):
        m = copy.deepcopy(d)
        # No condition: avoids triggering the exclusivity check as a side effect.
        _transitions(m).append({"from": r, "to": "NEWREGIME"})
        out.append(Mutant("MR2", 0, f"add transition {r} -> NEWREGIME (NEWREGIME has no outgoing transition)",
                          m, [r"Regime dead states", r"Regime 'NEWREGIME' is a dead-end"]))
    return out


def op_MR3(d):
    if not _transitions(d):
        return []
    m = copy.deepcopy(d)
    # A 2-cycle so that the new regimes are not dead ends and the inferred
    # initial regime (first from-regime never targeted) does not change.
    _transitions(m).extend([{"from": "NEWREGIME_A", "to": "NEWREGIME_B"},
                            {"from": "NEWREGIME_B", "to": "NEWREGIME_A"}])
    return [Mutant("MR3", 0, "add NEWREGIME_A <-> NEWREGIME_B, not reachable from the initial regime",
                   m, [r"Regime reachability"])]


def _lifecycles(d):
    for ci, c in enumerate(contracts(d)):
        if isinstance(c.get("lifecycle"), dict):
            yield ci, c


def op_ML1(d):
    out = []
    for ci, c in _lifecycles(d):
        for ti, tr in enumerate(c["lifecycle"].get("transitions") or []):
            m = copy.deepcopy(d)
            mt = contracts(m)[ci]["lifecycle"]["transitions"][ti]
            if isinstance(mt.get("on_violation"), dict):
                old = mt["on_violation"].get("transition")
                mt["on_violation"]["transition"] = GHOST_STATE
                desc = f"{c['id']}.{tr.get('id')}: on_violation.transition '{old}' -> {GHOST_STATE}"
            else:
                mt["on_violation"] = {"transition": GHOST_STATE, "severity": "Major"}
                desc = f"{c['id']}.{tr.get('id')}: add on_violation.transition {GHOST_STATE}"
            out.append(Mutant("ML1", 0, desc, m, [r"\(L-5\)"]))
    return out


def op_ML2(d):
    out = []
    for ci, c in _lifecycles(d):
        for ti, tr in enumerate(c["lifecycle"].get("transitions") or []):
            for end in ("from", "to"):
                m = copy.deepcopy(d)
                mt = contracts(m)[ci]["lifecycle"]["transitions"][ti]
                old = mt.get(end)
                if end == "from" and isinstance(old, list):
                    mt["from"] = [GHOST_STATE] + list(old[1:])
                else:
                    mt[end] = GHOST_STATE
                out.append(Mutant("ML2", 0, f"{c['id']}.{tr.get('id')}: {end} '{old}' -> {mt[end]}", m, [r"\(L-2\)"]))
    return out


def op_ML3(d):
    out = []
    for ci, c in _lifecycles(d):
        lc = c["lifecycle"]
        term = set(lc.get("terminal") or []) if isinstance(lc.get("terminal"), list) else {lc.get("terminal")}
        m = copy.deepcopy(d)
        mc = contracts(m)[ci]
        mlc = mc["lifecycle"]
        removed, dropped = [], []
        keep = []
        for tr in mlc.get("transitions") or []:
            if tr.get("to") in term:
                removed.append(tr.get("id"))
                continue
            ov = tr.get("on_violation")
            if isinstance(ov, dict) and ov.get("transition") in term:
                del tr["on_violation"]
                dropped.append(f"{tr.get('id')}.on_violation")
            keep.append(tr)
        mlc["transitions"] = keep
        for mon in mc.get("monitors") or []:
            om = mon.get("on_match")
            if isinstance(om, dict) and om.get("transition") in term:
                del om["transition"]
                dropped.append(f"{mon.get('id')}.on_match.transition")
        if not removed and not dropped:
            continue
        out.append(Mutant("ML3", 0,
                          f"{c['id']}: removed transitions into terminal {sorted(term)}: {removed}; also removed edges into terminal: {dropped}",
                          m, [r"\(L-3\)"]))
    return out


def op_ML4(d):
    out = []
    for ci, c in _lifecycles(d):
        m = copy.deepcopy(d)
        old = contracts(m)[ci]["lifecycle"].get("initial")
        contracts(m)[ci]["lifecycle"]["initial"] = GHOST_STATE
        out.append(Mutant("ML4", 0, f"{c['id']}: initial '{old}' -> {GHOST_STATE}", m, [r"initial state .*\(L-1\)"]))
    return out


def op_ML5(d):
    out = []
    for ci, c in enumerate(contracts(d)):
        for mi, mon in enumerate(c.get("monitors") or []):
            m = copy.deepcopy(d)
            mm = contracts(m)[ci]["monitors"][mi]
            om = mm.get("on_match")
            if not isinstance(om, dict):
                om = mm["on_match"] = {}
            old = om.get("transition")
            om["transition"] = GHOST_STATE
            out.append(Mutant("ML5", 0, f"{c['id']}.{mon.get('id')}: on_match.transition '{old}' -> {GHOST_STATE}",
                              m, [r"\(M-3\)"]))
    return out


def op_ML6(d):
    out = []
    for ci, c in enumerate(contracts(d)):
        for mi, mon in enumerate(c.get("monitors") or []):
            m = copy.deepcopy(d)
            mm = contracts(m)[ci]["monitors"][mi]
            obs = mm.get("observe")
            obs = list(obs) if isinstance(obs, list) else ([obs] if obs else [])
            mm["observe"] = obs + [f"{GHOST}.cadl_mut_attr"]
            out.append(Mutant("ML6", 0, f"{c['id']}.{mon.get('id')}: observe += '{GHOST}.cadl_mut_attr'",
                              m, [r"\(M-1\)"]))
    return out


def op_MP1(d):
    out = []
    for ci, c in enumerate(contracts(d)):
        for blk, key in (("authority", "beta"), ("information", "alpha"), ("incentives", "lambda")):
            if isinstance(c.get(blk), dict) and key in c[blk]:
                m = copy.deepcopy(d)
                old = c[blk][key]
                contracts(m)[ci][blk][key] = 1.5
                out.append(Mutant("MP1", 0, f"{c['id']}.{blk}.{key}: {old} -> 1.5", m,
                                  [rf"{key} parameter must be in \[0, 1\]"]))
    return out


def _first_message(steps):
    for st in steps or []:
        if isinstance(st, str):
            mm = MSG_RE.match(st)
            if mm and "->" in st:
                return mm.group(2).strip(), mm.group(4).strip()
        elif isinstance(st, dict):
            for k, v in st.items():
                ks = str(k)
                if "->" in ks and not (ks == "parallel" or ks.startswith("if ")):
                    a, b = re.match(r"(.+?)\s*->\s*(.+)", ks).groups()
                    return a.strip(), b.strip()
                if ks == "parallel" or ks.startswith("if ") or ks == "else":
                    r = _first_message(v)
                    if r:
                        return r
    return None


def op_MD1(d):
    out = []
    names = actor_names(d)
    for pi, pr in enumerate(sos(d).get("protocols") or []):
        pair = _first_message(pr.get("steps"))
        if not pair or pair[0] == pair[1]:
            if len(names) < 2:
                continue
            pair = (names[0], names[1])
        A, B = pair
        m = copy.deepcopy(d)
        steps = sos(m)["protocols"][pi].setdefault("steps", [])
        new = [f"{A} -> {B} : cadl_mut_x", f"{B} -> {A} : cadl_mut_y"]
        par = next((s for s in steps if isinstance(s, dict) and "parallel" in s
                    and isinstance(s["parallel"], list)), None)
        if par is not None:
            par["parallel"].extend(new)
            how = "appended as two new branches of the existing parallel block"
        else:
            steps.append({"parallel": new})
            how = "added a new parallel block with two branches"
        out.append(Mutant("MD1", 0, f"protocol {pr.get('id')}: {new} {how}", m,
                          [rf"Protocol '{re.escape(str(pr.get('id')))}' deadlock"]))
    return out


OPERATORS = {
    "MA1": op_MA1, "MA2": op_MA2, "MA3": op_MA3,
    "MC1": op_MC1, "MC2": op_MC2, "MC3": op_MC3, "MC4": op_MC4, "MC5": op_MC5,
    "MR1": op_MR1, "MR2": op_MR2, "MR3": op_MR3,
    "ML1": op_ML1, "ML2": op_ML2, "ML3": op_ML3, "ML4": op_ML4, "ML5": op_ML5, "ML6": op_ML6,
    "MP1": op_MP1, "MD1": op_MD1,
}


def generate(subject: Path, cap: int = CAP, ops=None):
    d = load(subject.read_text(encoding="utf-8"))
    result = {}
    for name, fn in OPERATORS.items():
        if ops and name not in ops:
            continue
        ms = fn(d)
        result[name] = (len(ms), ms[:cap])
        for k, m in enumerate(result[name][1], 1):
            m.instance = k
    return result


def main(argv):
    # Optional (supplementary run only): --cap N  --ops MA2,MA3
    cap, ops = CAP, None
    if "--cap" in argv:
        i = argv.index("--cap"); cap = int(argv[i + 1]); del argv[i:i + 2]
    if "--ops" in argv:
        i = argv.index("--ops"); ops = set(argv[i + 1].split(",")); del argv[i:i + 2]
    subj_dir, out_dir = Path(argv[1]), Path(argv[2])
    files = [Path(a) for a in argv[3:]] or sorted(subj_dir.glob("*.cadl"))
    manifest = []
    for f in files:
        gen = generate(f, cap, ops)
        dst = out_dir / f.stem
        dst.mkdir(parents=True, exist_ok=True)
        for op, (total, ms) in gen.items():
            for m in ms:
                p = dst / f"{op}_{m.instance:02d}.cadl"
                p.write_text(dump(m.data), encoding="utf-8")
                manifest.append(dict(file=f.name, op=op, instance=m.instance, path=str(p),
                                     description=m.description, expected=m.expected,
                                     applicable_instances=total, meta=m.meta))
        print(f.name, {op: f"{len(ms)}/{t}" for op, (t, ms) in gen.items() if t})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print("mutants:", len(manifest))


if __name__ == "__main__":
    main(sys.argv)
