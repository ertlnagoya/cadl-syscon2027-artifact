# Artifact for “Diagnosing Why a Governance Rule Will Not Work in Another System of Systems: Contract-Based Fit Checking”

Descriptions, scripts, and raw results for the paper above (submitted to IEEE SysCon 2027).

## Tools

| Tool | Version |
|---|---|
| `cadl` (check, verify) | 0.3.28, commit 01658ea, https://github.com/ertlnagoya/cadl |
| `cadl fit` | branch `feature/fit-check`, pull request ertlnagoya/cadl#76; evaluated at commit 443213f (9e9ce43 adds tests and changes one message) |
| `cadl fit` history | prototype on top of `cadl` 0.3.30 whose parser and verifier are those of 0.3.28 (its type checker differs only in messages and for the norms extension); commits f36d269 (first experiments), 5934498, 3c91f0b, 2d59e60 (connected-component neighbourhood), 443213f (F3d split, maximal-set enumeration; the paper's results), 9e9ce43 (tests, one message). Earlier commits gave the same counts except for one MK, one MV, and one mapped MN mutant that the F3d split unmasked. |
| `cadl fit` after the paper | the branch was merged with `cadl` 0.3.31 and 0.3.32 (commit 2469844), with 0.3.33 to 0.3.36 (commit 369f030), and with 0.3.37 and 0.3.38 (commit b3f1f16); `fit.py` and its tests are unchanged since 9e9ce43, and `run_fit.py`, `classification/cases.py`, and `taxonomy/mapping.py` give identical results at all three commits. `cadl fit` does not use the regime bindings or the amendment extension added in 0.3.32, nor their application at run time added in 0.3.33 to 0.3.36, nor the decision records of 0.3.37 and 0.3.38. |
| CADL specification | commit f7b148a, https://github.com/ertlnagoya/cadl-spec |
| Python / Z3 | 3.14.8 / 5.3.0 |

## Setup

The scripts need Python 3.14 with `z3-solver` 5.3.0, `PyYAML` 6.0.3 and `lark` 1.3.1, and two checkouts of
https://github.com/ertlnagoya/cadl:

- `cadl` 0.3.28 (tag `v0.3.28`, commit 01658ea), installed into that Python (`pip install -e .` in the
  checkout). `experiments/mutation/`, `experiments/baseline/`, `experiments/scale/` and
  `experiments/taxonomy/taxonomy.py` import it, and `run.py` calls the `cadl` command (environment
  variable `CADL`, default `cadl`; `PY` selects the interpreter, default the running one).
- The branch `feature/fit-check` (commit 443213f or later). The scripts of `experiments/fit/`,
  `experiments/classification/` and `experiments/taxonomy/mapping.py` take the path of its `src/` as their
  first argument (`FIT_SRC` below). `experiments/scale/paired.py` takes two `src/` paths (OLD and NEW).

Run each script from the directory it is in. The command of each script is given in its README and in
the first lines of the script.

## Contents and the paper

| Paper | Directory |
|---|---|
| RQ1, Table IV (upper part): mutation analysis | `experiments/mutation/` (`run.py`, `results.csv`, `mutants/`), `experiments/fit/run_fit.py`, `results_fit.csv` |
| RQ1: contract-theory baseline | `experiments/baseline/` |
| RQ2, Table IV (lower part): MK, MV, MU, MN | `experiments/taxonomy/` (`taxonomy.py`, `mapping.py`, results) |
| RQ2: classification cases (16 of 17) | `experiments/classification/` (`cases.py`, `results.csv`) |
| RQ2, Table V: encoding probes t1–t7 | `experiments/encoding_probes/`; `cadl fit` outputs in `experiments/fit/outputs/` |
| RQ3, Table VI: delivery, road use, claim window | `case-study/transplant3/`, `case-study/transplant2/`, `case-study/transplant4/` |
| RQ3, Table VII: EU U-space → US UTM | `case-study/real_utm/` (sources, modelling decisions, outputs, weak reading) |
| Household transplant (mutation subject) | `case-study/alone_*.cadl`, `case-study/family_evening_rule.cadl` |
| RQ4: scalability, exclusive modes | `experiments/scale/`, `experiments/fit/timing.py`, `timing.csv`, `modes.py`, `modes.csv` |
| Results of earlier tool versions | `experiments/archive-0.3.17/`, `experiments/fit/timing_*.csv` |

Each directory has a README with the commands and the results. Times are process CPU times on an
Apple M3 under the load averages given in the logs.

## Provenance

Eleven mutation subjects are example descriptions distributed with `cadl` 0.3.17, and the robot-town
subject comes from CADL Explorer 0.5.17 (commit 3ce3416; the file is unchanged in Explorer 1.1.0) (both Apache-2.0). The flight-authorization case formalizes Regulation
(EU) 2021/664 (via the EASA Easy Access Rules), SERA.6005(c) of Regulation (EU) 2021/666, the FAA UTM
Concept of Operations v2.0, and 14 CFR Part 89; each contract names the article or page it formalizes.
The proposition names, and hence the conflicts, follow the authors' reading of these documents.

## How to cite

Yutaka Matsubara, “Diagnosing Why a Governance Rule Will Not Work in Another System of Systems:
Contract-Based Fit Checking,” submitted to the IEEE International Systems Conference (SysCon) 2027.

## License

Apache License 2.0 (see `LICENSE`), as for `cadl` and CADL Explorer, from which some subjects are taken.
