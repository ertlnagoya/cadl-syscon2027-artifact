# `cadl fit` on the mutants, cases, and probes (2026-11-14)

`cadl fit` is a prototype on branch `feature/fit-check` of the cadl repository (first run at commit
f36d269 on 0.3.30, re-run with 5934498, 3c91f0b, and 2d59e60 with the same counts; the verifier is
unchanged from 0.3.28). It is not released.

Commands (from this directory; `FIT_SRC` is the `src/` of the fit branch):

```
$PY -I run_fit.py FIT_SRC ../mutation/results.csv results_fit.csv > run_fit.log
```

- `run_fit.py`: every contract of every mutant and subject; `results_fit.csv`.
- Mutants (compared with `cadl verify` in ../mutation/results.csv):
  - MA3 (actor name inside a predicate): 54 of 95 flagged by the `review` warning; all 54 in
    contract positions (incentive rules 31, violation action 9, monitor rule 7, predicate-form
    `on` 7); the 41 not flagged are in protocol conditions, which `fit` does not transplant.
    `cadl verify` flagged 0.
  - MA2: 143 of 150 by F1; the 7 others are protocol steps.
  - MC1–MC3: same 57 of 58 as `cadl verify`; MC4: 0 of 10 (unchanged).
  - MR, MD (regime graph, protocol deadlock): out of scope of `fit` (checked by `cadl verify`).
- Unmodified subjects: 25 contracts; no review warning, no F3 failure except the two contracts of
  `alone_adapted.cadl`, which conflict by design.
- Cases: delivery and road use (adapted) → F3 vacuous; delivery transplanted from the source with
  `--map DISPATCHER=TASK_OWNER --map CUSTOMER=TASK_OWNER` → fits (the adapted precondition is not
  stated); naive delivery → 10 F1 errors + review warning for DISPATCHER; occupied-taxi probe →
  F3 exclusion (warning); stale-robot and stale-dispatcher probes → review warnings.
- Encoding probes (../encoding_probes): t1 three-way → F3 vacuous (found, jointly by D1, D2);
  t4 shared variable without shared party → F3 vacuous (found); t2 → unknown with a quantifier
  warning (the conflict is still not reported); t3 → spurious F3 with a quantifier warning; t5 → spurious F3;
  t6 → missed.
- Time (`timing.py`, `timing.csv`; process CPU, median of 5, load average 3–7): 200 contracts 2.2 s (star) and
  1.8 s (chain), of which parsing and type checking, measured separately, 1.7 s. Earlier runs under load 30–130 are
  in `timing_heavy_load.csv` (older commit).

## 2d59e60: connected-component neighbourhood (2026-11-14)

The neighbourhood is now the connected component of the rule (chains of shared parties or variables);
`--reach direct` gives the old one. Re-run of run_fit.py, ../classification/cases.py, ../taxonomy (taxonomy.py,
mapping.py): identical results. Transplant outputs: identical except that the flight-authorisation
neighbourhood now includes MANNED_PARTICIPATION (findings unchanged). New probe t7_chain (conflict through an
intermediate contract): found (F3 guarantee, jointly D1, D2); `--reach direct` fits. Conflicts that depend on
reduced quantifiers or index variables are marked "can be spurious: review": t3 and t5 are marked, none of the
transplant conflicts. Timing (`timing.csv`, load 5-6): 200 contracts 2.4 s (star) and 2.6 s (chain, now 199
contracts in the neighbourhood), of which parsing and type checking 1.8 and 1.9 s. The direct-neighbourhood
timing is kept in `timing_direct_3c91f0b.csv`.

## 443213f: disabling class and maximal-set enumeration (2026-11-14)

`vacuous` is split into `vacuous` (G_K => not A_c) and `disabling` (G_c => not A_K). Maximal sets of contracts that
can be in force together are enumerated with the solver (find a set not contained in those found, grow it), at most
64 sets; the old subset search stopped at 14 neighbours. run_fit: counts unchanged (MC3 kinds now list
`disabling;vacuous` for 5 subjects). Taxonomy: MK and MV 13 of 14 each (the PART_TIME_JOB mutants of alone_adapted
are no longer masked, because the subject's own failure is now `disabling`); MN with mapping 13 of 14.
Classification: case 'reverse' relabelled `disabling`; 16 of 17. Transplants and probes: identical outputs.
`modes.py` / `modes.csv`: exclusive modes, (n, m) = (10,2) ... (200,32), fits and misfit variants, all as expected;
200 contracts in 32 modes 6.1 s (fits) and 6.2 s (misfit, 6 minimal conflicts), load 6-9.
`timing.csv` (443213f, load 5-8): 200 contracts 2.3 s in both topologies, parsing and type checking 1.8 s;
`timing_2d59e60.csv` and `timing_direct_3c91f0b.csv` are the earlier runs.
