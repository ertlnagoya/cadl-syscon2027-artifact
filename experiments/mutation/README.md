# Mutation analysis of the CADL toolchain

This experiment measures which injected defects `cadl check` and `cadl verify` detect.
Results are in `summary.md`, `summary.csv` and `results.csv`.

## Environment (as run)

- Date: 2026-11-13 (JST); the first run with cadl 0.3.17 on 2026-10-21 gave identical results (kept in ../archive-0.3.17/mutation/)
- Machine: Apple M3, 8 cores, 24 GiB RAM, macOS 27.2, Darwin arm64
- `cadl --version`: `cadl 0.3.28` (a checkout of the cadl repository, git commit
  01658ea, clean working tree)
- Python 3.14.8 ($PY)
- z3-solver 5.3.0, PyYAML 6.0.3, lark 1.3.1

Nothing was downloaded.

## Subjects

`subjects/` contains copies of 16 files. `subjects/SHA256SUMS` holds their hashes.

- the 11 files examples/*.cadl of the cadl repository that existed in 0.3.17 (four of them were rewritten in 0.3.18 without changing their check results; the 20 examples added for the extensions are not used)
- cadl-explorer/designs/robot_town.cadl (commit 3ce3416, v0.5.17; only comments differ from c279098)
- case-study/{family_evening_rule, alone_naive, alone_adapted, alone_adjusted}.cadl

alone_naive.cadl is used only as a negative control and is not mutated, so 15 files are mutated.

## Commands

```sh
cd experiments/mutation
PY=/path/to/python   # with cadl 0.3.28 installed
$PY run.py control      # step 1: YAML round-trip control -> control.csv, control/
$PY run.py generate     # step 2: mutate.py -> mutants/<subject>/<OP>_<k>.cadl, mutants/manifest.json
$PY run.py run          # step 3: cadl check + cadl verify --format json per mutant -> results.csv (~6 min)
$PY run.py summarize    # step 4: -> summary.csv, summary_table.md
$PY run.py supplement   # optional: MA2/MA3 uncapped -> mutants_uncapped/, results_uncapped.csv, supplement_positions.md
```

Each mutant is checked with `cadl check FILE` and with `cadl verify --format json FILE`. Each call
has a 60 s timeout, and 8 calls run in parallel. Generation is deterministic: there is no
randomness, instances are taken in file order, and only the first 10 per operator per file are
kept. Regenerating the mutants gives byte-identical files.

## Files

- `mutate.py`: the operators. Each operator injects one defect into a deep copy of the YAML tree,
  which is then written back with PyYAML.
- `run.py`: the driver. It runs the control, generation, execution, classification and summary steps.
- `control.csv`: the round-trip control. For all 16 files the round trip leaves the results and
  the AST identical.
- `results.csv`: one row per mutant, with these columns:
  - file, operator, instance, mutant_path, outcome
  - first_item: the first on-target new item, otherwise the first new item
  - on_target, description
  - new_errors, new_failed, new_warnings
- `summary.csv` and `summary_table.md`: one row per operator.
- `summary.md`: a short human-readable table and notes.

## Classification (relative to the round-tripped original)

- MUTANT-INVALID: the mutant does not parse, its output is not JSON, or a run timed out.
- DETECTED-CHECK: `check` exits non-zero and reports an `[ERROR]` that the original does not have.
- DETECTED-VERIFY: `check` passes and `verify` has a `failed` item that the original does not have.
- MASKED: there is no new failure, but an item the operator targets already fails on the original.
- WARNING-ONLY: there is a new `[WARNING]`, or a new verify item with status warning or unknown,
  and nothing else is new.
- NOT-DETECTED: none of the above applies.

detection_rate is (DETECTED-CHECK + DETECTED-VERIFY) / (mutants − invalid).
