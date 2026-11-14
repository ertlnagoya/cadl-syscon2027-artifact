# Scalability sweep (RQ2)

- Script: `scale.py` (generator and in-process timing of parse, type_check, verify, detect_deadlocks).
- Command: `~/program/cadl_repo/.venv/bin/python -I -c "import sys; sys.path.insert(0,'.'); sys.argv=['scale.py','results.csv','--reps','5']; import scale; scale.main()"`
- Toolchain: cadl 0.3.28 (commit 01658ea), Python 3.14.8, Z3 5.3.0, Apple M3, macOS 27.2, 2026-11-13.
- Results: `results.csv` (run used in the paper, load average 3.5–17 during the run), `results_0.3.28_heavy_load.csv` (first 0.3.28 run, load average up to 240, CPU times up to 2.8x larger). The 0.3.17 runs of 2026-10-21 are in `../archive-0.3.17/scale/`.
- `paired.py` runs cadl 0.3.17 (ace2679 source tree) and 0.3.28 alternately on five configurations under the same load (`paired.csv`, `paired.log`); the medians differ by at most 1%. Times are medians of 5 runs of process CPU time and wall-clock time.
- `sample_star_50.cadl` is one generated description (star topology, 50 contracts).
