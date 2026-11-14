# Scalability sweep (RQ2)

- Script: `scale.py` (generator and in-process timing of parse, type_check, verify, detect_deadlocks).
- Command: `~/program/cadl_repo/.venv/bin/python -I -c "import sys; sys.path.insert(0,'.'); sys.argv=['scale.py','results.csv','--reps','5']; import scale; scale.main()"`
- Toolchain: cadl 0.3.17 (commit ace2679), Python 3.14.8, Z3 5.3.0, Apple M3, macOS 27.0.1, 2026-10-21.
- Results: `results.csv` (run used in the paper, load average 2.9–67 during the run), `results_under_load.csv` (earlier run, load average up to 83). Times are medians of 5 runs of process CPU time and wall-clock time.
- `sample_star_50.cadl` is one generated description (star topology, 50 contracts).
