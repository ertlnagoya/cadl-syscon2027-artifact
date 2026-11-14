# Artifact: Static Fit Checking for Governance Rules Transplanted Between Systems of Systems

Descriptions, scripts, and raw results for the paper *Will the Rule Still Work There? Static Fit
Checking for Governance Rules Transplanted Between Systems of Systems* (submitted to IEEE SysCon 2027).

## Tools

| Tool | Version |
|---|---|
| `cadl` (check, verify) | 0.3.28, commit 01658ea, https://github.com/ertlnagoya/cadl |
| `cadl fit` | branch `feature/fit-check`, pull request ertlnagoya/cadl#76; evaluated at commit 443213f (9e9ce43 adds tests and changes one message) |
| `cadl fit` history | prototype on top of `cadl` 0.3.30 whose parser and verifier are those of 0.3.28 (its type checker differs only in messages and for the norms extension); commits f36d269 (first experiments), 5934498, 3c91f0b, 2d59e60 (connected-component neighbourhood), 443213f (F3d split, maximal-set enumeration; the paper's results), 9e9ce43 (tests, one message). Earlier commits gave the same counts except for one MK, one MV, and one mapped MN mutant that the F3d split unmasked. |
| CADL specification | commit f7b148a, https://github.com/ertlnagoya/cadl-spec |
| Python / Z3 | 3.14.8 / 5.3.0 |

Scripts take the path of the `cadl` sources (`src/`) of the fit branch as their first argument, or use
the environment variables `CADL` (the `cadl` command) and `PY` (the Python interpreter). Run them from the
directory they are in unless their README says otherwise; `experiments/mutation/run.py` reads
`mutants/manifest.json`, whose paths are relative to the root of this artifact.

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
subject comes from CADL Explorer (both Apache-2.0). The flight-authorization case formalizes Regulation
(EU) 2021/664 (via the EASA Easy Access Rules), SERA.6005(c) of Regulation (EU) 2021/666, the FAA UTM
Concept of Operations v2.0, and 14 CFR Part 89; each contract names the article or page it formalizes.
The proposition names, and hence the conflicts, follow the authors' reading of these documents.

## License

Apache License 2.0 (see `LICENSE`), as for `cadl` and CADL Explorer, from which some subjects are taken.
