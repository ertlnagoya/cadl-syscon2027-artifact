# Encoding probes (cadl 0.3.28, 2026-11-14)

Seven small descriptions, written during an internal review, that show where `cadl verify` errs.
Outputs are in `*.verify.txt`.

| File | Situation | Ground truth | `cadl verify` | Error |
|---|---|---|---|---|
| t1_threeway | Two destination contracts each guarantee one part (`shift_hours >= 9`, `commute_hours >= 2`) of what the rule assumes jointly (`shift_hours + commute_hours <= 10`) | Destination jointly makes the rule vacuous | PASSED 12/12 | missed (pairs only) |
| t2_universal | `for all t in TAXI[*]: TAXI[t].fuel >= 10` vs `TAXI[1].fuel < 5` | Contradictory | PASSED 7/7 | missed (quantifier body, index names) |
| t3_exists | Two existentials, `speed > 50` vs `speed < 10` | Satisfiable with two taxis | FAIL | spurious conflict (quantifier body) |
| t4_noshare | `network_latency <= 200ms` vs `network_latency >= 1s`, no shared party | Contradictory | PASSED 6/6 | missed (party filter) |
| t5_index | `TAXI[i].passengers == 0` vs `>= 1` in two contracts | Independent quantification | FAIL | spurious conflict (one variable per index text) |
| t6_sorts | `manual_override` as proposition vs `== 0`; `30min` vs bare `45` | Two conflicts | PASSED 17/17 | missed (sort split, units) |
| t7_chain | `queue_delay <= 0` (rule); `queue_delay == dispatch_delay` (D1); `dispatch_delay >= 1` (D2); no shared party, D2 shares no variable with the rule (added 2026-11-14 after review) | Contradictory through D1 | PASSED 10/10 | missed (party filter); `cadl fit` finds it only with the component neighbourhood (`--reach direct` misses it) |
