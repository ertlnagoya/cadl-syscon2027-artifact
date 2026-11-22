# Mutants from a defect taxonomy (2026-11-14)

`taxonomy.py` adds destination contracts that make a contract's numeric assumption `x OP k`
impossible in ways the original MC operators do not cover (see the docstring). Each mutant is
checked with `cadl verify` (cadl 0.3.28 installed; verifier unchanged since 0.3.28) and with
`cadl fit -c <contract>` (branch feature/fit-check). Results: `results.csv`, `run.log`, `mutants/`.

| Operator | Mutants | verify | fit |
|---|---|---|---|
| MK three-way (two new contracts, pairwise satisfiable) | 14 | 0 | 13 |
| MV conflict on a shared attribute, no shared party | 14 | 0 | 13 |
| MU duration written as a bare number of minutes | 2 | 0 | 0 |
| MN same attribute under another name | 14 | 0 | 0 |

The MK and MV mutants that `fit` does not flag target EVENING_ROUTINE in `alone_adapted.cadl`, which
already fails F3 as vacuous; the new finding has the same class and message (masked). With cadl fit
443213f, PART_TIME_JOB's existing failure is classified `disabling` (it makes EVENING_ROUTINE
vacuous), so its MK and MV mutants, previously masked (12 of 14), are now flagged as vacuous.

## Attribute mapping (`mapping.py`, `results_mapping.csv`)

For each MN mutant, the transplanted contract's attribute `x` is renamed to the destination's `x_v2`
(what `cadl fit --map x=x_v2` does for a contract taken from a source). `cadl fit` then flags 13 of 14
(the other is masked in `alone_adapted.cadl`; 12 of 14 before 443213f); without the mapping, 0 of 14.

Commands (from this directory; `FIT_SRC` is the `src/` of the fit branch; `mapping.py` reads
`../mutation/subjects`):

```
$PY -I taxonomy.py FIT_SRC results.csv
$PY -I mapping.py FIT_SRC results.csv results_mapping.csv
```
