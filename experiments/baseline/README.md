# Contract-theory baseline (novelty check)

`baseline.py` evaluates, on the Z3 encoding of the cadl verifier (cadl 0.3.28), the checks of
assume/guarantee contract theory on saturated contracts and their parallel composition
(consistency: G' satisfiable; compatibility: A satisfiable; C1 (x) C2 = ((A1 and A2) or not G', G'1 and G'2))
next to the fit conditions (F2) and (F3), and reports whether a pair has a vacuous rule (G_d implies not A_c).

```sh
PY=/path/to/python   # with cadl 0.3.28 installed
$PY -I baseline.py ../../case-study/alone_adapted.cadl ...       # cases
$PY -I run_mutants.py ../mutation/results.csv mutants_baseline.csv  # MC1-MC4 mutants
```

Results (2026-11-13):

- Transplant cases: in all three adapted transplants, every contract and every composed pair is consistent and
  compatible, while (F3) fails for exactly one pair, in which the destination makes the transplanted rule vacuous.
  After adjustment all checks pass. In the probe that restricts the road-use rule to occupied taxis, (F3) fails
  but no rule is vacuous: the assumptions exclude each other.
- MC1-MC4 mutants (68): the contract-theory checks flag 26 (MC1 2/25, MC2 23/23, MC3 1/10, MC4 0/10), the fit
  conditions 57 (25, 23, 9, 0), identical to `cadl verify`. Every mutant flagged by contract theory is also
  flagged by the fit conditions. The three MC1/MC3 mutants that contract theory flags are in robot_town.cadl,
  whose contracts have no assumptions (A is true, so G' = G).
