# Transplant 4: a conflict that only three contracts create (constructed)

The SLA of transplant 3, adapted in its own wording (no `NOT all_active_robots_claim_before_assignment()`,
see `../transplant3/probes/probe_own_vocabulary_precondition.cadl`), assumes `assignment_latency <= 5s`, the
latency budget of the source dispatcher. The destination is `raspimouse_c_sos` with its claim timing made
explicit, which we added for this case:

- `DELIVERY_ASSIGNMENT_CONTRACT` guarantees `assignment_latency >= claim_wait + 1s` (a goal is assigned after all
  active robots have claimed and the delivery interval of 1 s has passed);
- a new contract `CLAIM_TIMEOUT` guarantees `claim_wait >= 5s` (TASK_OWNER waits `max_claim_delay` = 5 s, as
  in the destination's protocol DELIVERY_ASSIGNMENT).

Each pair of the three contracts is satisfiable; the three are not.

| File | Lines | `cadl verify` (0.3.28) | `cadl fit -c DELIVERY_SLA` (f36d269) |
|---|---|---|---|
| destination.cadl | 306 | PASSED 17/17 | - |
| adapted.cadl | 361 | PASSED 22/22 | MISFIT: F3 vacuous, only jointly: CLAIM_TIMEOUT, DELIVERY_ASSIGNMENT_CONTRACT |
| adjusted.cadl (`assignment_latency <= 7s`) | 361 | PASSED 22/22 | FITS |

Outputs are in `outputs/`. The `cadl fit` results are the same with commits 443213f (the paper),
b3f1f16 and f2be5d9. Command: `PYTHONPATH=FIT_SRC python -m cadl.cli fit adapted.cadl -c DELIVERY_SLA` (likewise for
`adjusted.cadl`).
