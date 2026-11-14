# Transplant 3: dispatcher-assigned delivery SLA -> collaborative Raspimouse swarm

Toolchain: `cadl 0.3.17` (`outputs/version.txt`). Every `.cadl` file here was run with `cadl check` and `cadl verify`. Outputs are in `outputs/<file>.check.txt` and `outputs/<file>.verify.txt`, and each one ends with `rc=<exit code>`.

## Files

| File | Role |
|---|---|
| `delivery_source.cadl` | Source: unchanged copy of `cadl_repo/examples/a_sos_robot_delivery.cadl` (Acknowledged; DISPATCHER, ROBOT[1..N], CUSTOMER[1..M]) |
| `raspimouse_destination.cadl` | Destination baseline: unchanged copy of `cadl_repo/examples/raspimouse_c_sos.cadl` (Collaborative; ARBITRATOR, TASK_OWNER, ROBOT[1..5]) |
| `delivery_sla_naive.cadl` | DELIVERY_SLA copied unchanged into the destination |
| `delivery_sla_adapted.cadl` | Authority moved to peer robots. The destination's ROUTE_VERIFICATION and DELIVERY_ASSIGNMENT_CONTRACT are kept unchanged |
| `delivery_sla_adjusted.cadl` | The adapted file with the conflict resolved |
| `probes/*.cadl` | One-line variants that test what the toolchain does not detect |

### Why this destination

- `raspimouse_c_sos.cadl` is in the same domain as the source: robot delivery on a shared graph.
- It is Collaborative, and the robots hold route authority (`decision_holder: ROBOT[*]`). The ARBITRATOR only checks a proposed hop. TASK_OWNER is a passive first-come-first-served claim arbiter with `beta: 0.1`, not a dispatcher that plans routes and tasks.
- The other variants do not fit. `raspimouse_d_sos` is Directed, with a central ARBITRATOR. `raspimouse_mcp_sos` is Acknowledged, with an LLM_AGENT as decision holder. `c_sos_taxi_fleet` is already used in Transplant 2.

## What was transplanted

The transplanted rule is the contract `DELIVERY_SLA`. It assumes `DISPATCHER.is_operational` and `ROBOT[i].battery > 20`, and guarantees `delivery_time <= 300s` and `all_routes_conflict_free()`. Authority is centralized in DISPATCHER (`beta: 0.8`). It includes views and sharing for DISPATCHER and CUSTOMER, incentives, and a violation/escalation block.

## Role mapping (adapted)

| Source | Destination | Rationale |
|---|---|---|
| DISPATCHER, task assignment (Hungarian method) | ROBOT[*], peer self-assignment: the first free robot claims a goal and takes it at once | Authority moves to the peers |
| DISPATCHER, route planning (ECBS) | ROBOT[*] local Dijkstra, checked by ARBITRATOR | The destination's route mechanism |
| `DISPATCHER.is_operational` | `ARBITRATOR.is_operational` | The remaining shared infrastructure |
| CUSTOMER[*] | TASK_OWNER | Owner of the goal sequence. It records claims and delivery times |
| `all_routes_conflict_free()` | `edge_mutual_exclusion()` | A global, ECBS-only property is weakened to what the destination guarantees |

Preconditions added: `first_free_robot_takes_goal_at_once()`, `NOT all_active_robots_claim_before_assignment()` and `assignment_latency <= 5s` (the source's TASK_DISPATCH `max_total`).

## Conflict and resolution

**Conflict:** The SLA's 300 s budget was set for a dispatcher that assigns each order at once. Its peer version therefore assumes that the first free robot takes a goal without waiting. The destination's FCFS contract (which shares ROBOT[*]) guarantees the opposite: no goal is assigned until every active robot has submitted its claim (all-robot-wait).

`verify` reports: `[FAIL] Cross-contract 'DELIVERY_ASSIGNMENT_CONTRACT' x 'DELIVERY_SLA': Contracts are contradictory when combined`.

**Resolution (adjusted):** The SLA adopts the destination's all-robot-wait rule, which the destination relies on for reproducible runs. It budgets the bounded claim wait instead: `claim_wait <= 5s` (maxClaimDelaySec) and `assignment_latency <= claim_wait + 1s` (deliveryInterval). TASK_OWNER assigns each goal to the earliest claimer, and the robots keep route choice.

## Results

| Version | Lines | `cadl check` | `cadl verify` | Findings |
|---|---|---|---|---|
| source (A-SoS delivery) | 192 | pass | PASSED 12/12 | - |
| destination (Raspimouse C-SoS) | 288 | pass | PASSED 13/13 | - |
| naive | 329 | **10 errors** | FAILED 16/17 | Only the type check fails. All cross-contract checks pass, because ROBOT[*] is shared and the SLA's predicates do not touch the destination's |
| adapted | 344 | pass | FAILED 16/17 | DELIVERY_ASSIGNMENT_CONTRACT x DELIVERY_SLA contradictory (immediate self-assignment vs all-robot-wait) |
| adjusted | 343 | pass | PASSED 17/17 | - |

### Naive errors by position (10)

| Position | Count | Actors |
|---|---|---|
| parties | 2 | DISPATCHER, CUSTOMER |
| assume, attribute term | 1 | DISPATCHER.is_operational |
| authority (decision holder) | 1 | DISPATCHER |
| information views | 2 | DISPATCHER, CUSTOMER |
| information sharing endpoints | 4 | DISPATCHER x3, CUSTOMER x1 |
| responsibilities, messages, monitors | 0 | The SLA has none |

## References to absent actors in unchecked positions (naive)

The checker reported none of these:

- `violation.action`: `"notify(DISPATCHER) AND log_violation"` names DISPATCHER. `probes/probe_stale_dispatcher_in_violation.cadl` puts this string back into the adjusted file, and it passes check and verify (17/17).
- `violation.escalation`: `"after 3 violations: reassign_tasks"` assumes a reassigning dispatcher.
- `violation.detect`: `"position_report_delay > 5s"` refers to `position_report`, which is a message in no destination interface.
- `incentives.rules`: `"penalty(ROBOT[i], -5) when path_deviation"`. ROBOT exists, but "deviation" assumes an assigned path that peer robots do not have.
- sharing message names `position_report`, `route_assignment` and `delivery_notification` appear in no destination interface. The checker does not report them, because those entries already fail on their actor endpoints.

## Defects the toolchain did not detect

1. **Vocabulary dependence:** The conflict is found only because the adapted precondition reuses the destination's predicate name. `probes/probe_own_vocabulary_precondition.cadl` keeps only `first_free_robot_takes_goal_at_once()`, so the two contracts share no symbol, and verify passes 17/17.
2. **Unattainable guarantee kept:** The naive version keeps `all_routes_conflict_free()`. This is an ECBS property that local Dijkstra plus a hop verifier cannot provide, and the destination even has a COLLISION_RECOVERY protocol. As an opaque predicate it passes.
3. **Silent actor rebinding:** ROBOT[*] binds without complaint to a different population: 10 robots on a 30x30 grid with 100 ms steps in the source, 5 Raspimice on an 11-node graph with 0.8 to 3 m edges here. The 300 s budget was never recalibrated.
4. **Undeclared attribute:** `ROBOT[i].battery > 20` passes, but the destination does not model a battery. Attributes are not declared anywhere, so nothing is checked.
5. **Governance mismatch:** The naive version keeps `mode: "centralized"` with `beta: 0.8` inside an SoS of `type: Collaborative`. Nothing checks authority mode against SoS type.
