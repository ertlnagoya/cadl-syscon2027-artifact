# CADL mutation analysis — summary

Toolchain: cadl 0.3.17 (cadl_repo commit ace2679, clean tree), z3 5.3.0, PyYAML 6.0.3, Python 3.14.8.
Run: 2026-10-21. 15 mutated subjects (alone_naive.cadl is a negative control and is not mutated).
556 mutants, 0 invalid, 0 timeouts. Full per-mutant data: `results.csv`; numbers: `summary.csv`.

## Control (step 1)

All 16 subjects (alone_naive included) give identical `cadl check` exit code, error/warning
lists, `cadl verify --format json` exit code, summary counts and per-item status/message
after a PyYAML load+dump round trip. Their parsed ASTs are identical too (`control.csv`).
So every operator edits the YAML tree; none needed text editing. Baselines: 14 subjects pass both
tools. alone_adapted passes check but fails verify on one item (cross-contract
EVENING_ROUTINE x PART_TIME_JOB, as intended by the case study). alone_naive fails check with
6 errors.

## Results

A mutant counts as detected only if a check error or failed verify item appears that is **not
present on the unmutated (round-tripped) original**. "on-target" means that at least one of the new
items is the check the operator targets. The rate is (check + verify) / valid mutants, and MASKED
mutants stay in the denominator.

| op | files | mutants | det. check | det. verify | warn-only | not det. | masked | invalid | on-target | rate |
|---|---|---|---|---|---|---|---|---|---|---|
| MA1 missing actor | 15 | 43 | 43 | 0 | 0 | 0 | 0 | 0 | 43 | 1.000 |
| MA2 GHOST in checked position | 15 | 150 | 150 | 0 | 0 | 0 | 0 | 0 | 150 | 1.000 |
| MA3 GHOST in predicate string | 15 | 95 | 0 | 0 | 0 | 95 | 0 | 0 | 0 | 0.000 |
| MC1 self-contradictory contract | 15 | 25 | 0 | 25 | 0 | 0 | 0 | 0 | 25 | 1.000 |
| MC2 unsatisfiable assume | 14 | 23 | 0 | 23 | 0 | 0 | 0 | 0 | 23 | 1.000 |
| MC3 cross-contract conflict | 10 | 10 | 0 | 9 | 0 | 0 | 1 | 0 | 9 | 0.900 |
| MC4 same, variable renamed `_v2` | 10 | 10 | 0 | 0 | 0 | 9 | 1 | 0 | 0 | 0.000 |
| MC5 conflict, no shared party | 0 | 0 | – | – | – | – | – | – | – | n/a |
| MR1 overlapping transitions | 5 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 1.000 |
| MR2 dead-end regime | 9 | 24 | 0 | 24 | 0 | 0 | 0 | 0 | 24 | 1.000 |
| MR3 unreachable regimes | 9 | 9 | 0 | 9 | 0 | 0 | 0 | 0 | 9 | 1.000 |
| ML1 on_violation target (L-5) | 5 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 14 | 1.000 |
| ML2 transition endpoint (L-2) | 5 | 28 | 28 | 0 | 0 | 0 | 0 | 0 | 28 | 1.000 |
| ML3 terminal unreachable (L-3) | 5 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 1.000 |
| ML4 initial state (L-1) | 5 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 1.000 |
| ML5 on_match.transition (M-3) | 5 | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 1.000 |
| ML6 observe undeclared actor (M-1) | 5 | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 1.000 |
| MP1 alpha/beta/lambda = 1.5 | 15 | 62 | 62 | 0 | 0 | 0 | 0 | 0 | 62 | 1.000 |
| MD1 parallel mutual send | 12 | 29 | 0 | 29 | 0 | 0 | 0 | 0 | 29 | 1.000 |
| **all** | | 556 | 323 | 127 | 0 | 104 | 2 | 0 | 450 | 0.809 |

Without the two blind-spot operators (MA3, MC4), 450 of the 451 mutants are detected, all
on target. The one exception is MC3 on alone_adapted (masked, see below).

Supplementary run (`supplement_positions.md`, `results_uncapped.csv`): MA2 and MA3 without the
10-instance cap. MA2 is detected in 329/329 cases across all 7 position classes: parties 55,
decision_holder 23, sharing 88, responsibilities 17, protocol step 124, lifecycle `on` 12,
monitor observe 10. MA3 is detected in 0/106 cases: incentives.rules 31, protocol trigger 26,
postcondition 12, precondition 10, violation.action 9, monitor rule 7, predicate-form `on` 7,
regime condition 4. No subject has an actor name inside `when`, `violation.detect` or a regime
`safety_invariant`, so those MA3 positions are not exercised.

## Notes

1. **Blind spot confirmed (MA3).** An undeclared actor inside a predicate string passes both
   tools silently. Example: robot_town `MA3_02` turns `on: ROBOT[i].status == Delivered` into
   `GHOST[i].status == Delivered`, and the tool prints only
   `Type check passed: mutants/robot_town/MA3_02.cadl`. The predicate-form `on` and the monitor
   `rule` are parsed (E.3), but actor names in them are not resolved. In contrast, the same name
   in `assume`/`guarantee` member access is checked.
2. **Name-matching threat confirmed (MC4).** The same contradiction as MC3, but with the
   variable spelled `x_v2`, is not detected in 9/9 cases. Example robot_town `MC4_01`:
   `[PASS] Cross-contract 'DELIVERY_SLA' x 'ROAD_USE': Contracts are jointly satisfiable`.
   Related: indexed references are encoded by their text (`ROBOT[i].battery` becomes
   `ROBOT_i_battery`), so `ROBOT[i]` vs `ROBOT[j]` would also not be linked. This was not mutated.
3. **MC5 is inapplicable.** Every pair of contracts in every multi-contract subject shares at
   least one party, so no MC5 mutant exists. In the verifier source, the cross-contract check runs
   only for pairs with `parties1 & parties2`, so such a conflict would go unreported by design.
   This is not measured empirically.
4. **Masking (alone_adapted).** The baseline already fails cross-contract
   EVENING_ROUTINE x PART_TIME_JOB. MC3 and MC4 on that pair therefore produce no new failure
   and are counted as MASKED, not as detections.
5. **MR2 is only a warning in `cadl check`.** `cadl check` reports
   `[WARNING]: Regime 'NEWREGIME' is a dead-end (no outgoing transitions)` and exits 0. Only
   `cadl verify` fails it:
   `[FAIL] Regime dead states: Dead-end states (no outgoing transitions): NEWREGIME`. A
   workflow that runs only `check` would miss all 24 MR2 mutants.
6. **Collateral items are logically implied, not spurious.** Some detections add extra new
   items besides the target, and every one of them follows from the injected defect:
   - MC1/MC2: an unsatisfiable contract also makes its cross-contract pairs fail.
   - MC2: an unsatisfiable assume also fails that contract's consistency check.
   - ML2: an undeclared endpoint can also break L-3 reachability.
   - ML3: removing an on_violation block raises an L-4 warning.
7. **ML3 definition matters.** `cadl check` counts on_violation targets and monitor on_match
   targets as ways to reach a state. A naive ML3 that removes only `transitions` whose `to` is
   terminal is *not* a defect in 3 of 4 lifecycles (the terminal stays reachable through
   on_violation or a monitor), and check correctly passes it. The implemented ML3 also removes
   those edges into terminal states, so the terminal state is genuinely unreachable.
8. **Operator selection favours the encoder.** MC1–MC4 contradict a predicate that the SMT
   encoder parses (a comparison or a boolean symbol). Opaque predicates were never picked, so
   these rates are upper bounds for contradictions written in arbitrary text. Examples of opaque
   predicates: `retention_period <= 30d` (`d` is not a duration unit) and
   `goal_sequence is non-empty`. robot_town has no `assume`, so its MC3 contradicts a
   *guarantee* of contract A (fallback, recorded in `mutants/manifest.json` meta.A_source).

Example diagnostics (verbatim):

```
robot_town/MA2_07:  [ERROR]: Undefined actor 'GHOST' referenced in 'on' of the lifecycle transition 'release' of contract 'ROAD_USE' (sender)
raspimouse_mcp_sos/MD1_03:  [FAIL] Protocol 'DEADLOCK_RESOLUTION' deadlock: Circular dependency detected (1 cycle(s))
        - ROBOT[i] -> LLM_AGENT -> ROBOT[i]
smart_city_traffic/MR1_02:  [FAIL] Transition exclusivity: CONGESTED -> NORMAL vs CONGESTED -> EMERGENCY: Transition conditions can be simultaneously true (non-exclusive)
```

Manual inspection: at least 2 mutants per operator were diffed against the round-tripped
original (MA1 a_sos/01 and supply_chain/04, MA2 robot_town/07 and sos_dsl/09, MA3 robot_town/02 and
raspimouse_mcp/05, MC1 iot/02 and robot_town/01, MC2 smart_city/01 and a_sos/02, MC3 robot_town/01
and a_sos/01, MC4 robot_town/01 and c_sos/01, MR1 supply_chain/01 and smart_city/02, MR2
robot_delivery/01 and supply_chain/04, MR3 robot_delivery/01 and smart_city/01, ML1 family/01 and
robot_town/03, ML2 sos_dsl/03 and robot_town/05, ML3 robot_town/02 and sos_dsl/01, ML4 family/01
and robot_town/02, ML5 robot_town/01 and sos_dsl/02, ML6 robot_town/01 and family/01, MP1 household/03 and iot/01,
MD1 raspimouse_mcp/03 and household/01). Every diff contained exactly the claimed defect, and no
operator needed fixing.
