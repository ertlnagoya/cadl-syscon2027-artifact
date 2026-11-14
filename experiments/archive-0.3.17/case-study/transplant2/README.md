# Transplant 2: robot-town road-use rule -> autonomous taxi fleet

Toolchain: `cadl 0.3.17` (`outputs/version.txt`). Every `.cadl` file here was run with `cadl check` and `cadl verify`. Outputs are in `outputs/<file>.check.txt` and `outputs/<file>.verify.txt`, and each one ends with `rc=<exit code>`.

## Files

| File | Role |
|---|---|
| `robot_town_source.cadl` | Source: unchanged copy of `cadl-explorer/designs/robot_town.cadl` (Collaborative; TOWN_STEWARD, ROBOT[1..N], COUNCIL) |
| `taxi_destination.cadl` | Destination baseline: unchanged copy of `cadl_repo/examples/c_sos_taxi_fleet.cadl` (Collaborative; TAXI[1..N], PASSENGER[1..M], TRAFFIC_CENTER) |
| `road_use_naive.cadl` | ROAD_USE, the DISTRIBUTED<->CENTRALIZED regime switch with its safety invariant, and the SWITCH protocol, all copied unchanged into the destination |
| `road_use_adapted.cadl` | ROAD_USE with roles mapped and preconditions stated. The destination's RIDE_SERVICE and ROAD_SHARING are kept unchanged |
| `road_use_adjusted.cadl` | The adapted file with the conflict resolved |
| `probes/*.cadl` | One-line variants that test what the toolchain does not detect |

## What was transplanted

The transplanted rule is the contract `ROAD_USE`. It states the guarantee `hold_time <= hold_limit` and has a lifecycle Holding/Overstay/Released/Evicted. The release transition has a 60 s deadline. The `blocking_guard` monitor evicts a vehicle that blocks 3 or more others. A sanction incentive applies, and the decision holder is COUNCIL acting collectively. The naive version also carries the robot town's regime switch, whose safety invariant is `robots_on_road == 0`.

## Role mapping (adapted)

| Source | Destination | Rationale |
|---|---|---|
| ROBOT[*] | TAXI[*] | These are the vehicles that hold road space |
| TOWN_STEWARD | TRAFFIC_CENTER | It receives reports, records holds and overstays, and publishes occupancy. The destination says it issues no commands |
| COUNCIL (decision holder) | TAXI[*], `mode: collective` | The destination has no rule-making body. In a Collaborative fleet the members set the rule together |
| message `node_released` | `position_update` | TAXI's output interface has no `node_released` |
| garage (where released robots go) | fleet depot | Literal mapping (adapted) |

Preconditions added: `TAXI[i].is_available == true` (the rule covers idle taxis), `pickup_time >= depot_drive_time` and `depot_drive_time >= 900s`. The 900 s figure is an engineering estimate for a single depot at the edge of the 100-block city.

The regime switch was not carried into the adapted version. The destination already has its own regime axis (NORMAL/PEAK_DEMAND/INCIDENT_RESPONSE). The safety invariant "no vehicle on the road" also cannot be met by a taxi fleet in service.

## Conflict and resolution

**Conflict:** In the robot town, a released robot goes back to the garage. Applied to taxis, this sends every idle taxi that leaves the kerb back to the depot, so the next pickup starts there: at least 900 s away. RIDE_SERVICE (which shares TAXI[*]) promises every passenger a pickup within 600 s.

`verify` reports: `[FAIL] Cross-contract 'RIDE_SERVICE' x 'ROAD_USE': Contracts are contradictory when combined`.

**Resolution (adjusted):** A released taxi goes to the nearest public taxi rank instead of the depot. This takes the robot town's CENTRALIZED waiting areas and makes them permanent. Each taxi picks the rank itself from the occupancy that TRAFFIC_CENTER publishes, so the destination's "no commands" principle still holds. The new preconditions are `pickup_time >= rank_drive_time`, `rank_drive_time <= 300s` and `rank_capacity >= idle_taxis`.

## Results

| Version | Lines | `cadl check` | `cadl verify` | Findings |
|---|---|---|---|---|
| source (robot_town) | 147 | pass | PASSED 13/13 | - |
| destination (taxi fleet) | 208 | pass | PASSED 13/13 | - |
| naive | 263 | **12 errors** | FAILED 16/18 | Type check fails. Regime reachability fails (CENTRALIZED and DISTRIBUTED unreachable). There is **no** cross-contract check for ROAD_USE, because it shares no party name with any destination contract |
| adapted | 264 | pass | FAILED 16/17 | RIDE_SERVICE x ROAD_USE contradictory (depot return vs 600 s pickup) |
| adjusted | 265 | pass | PASSED 17/17 | - |

### Naive errors by position (12)

| Position | Count | Actors |
|---|---|---|
| parties | 3 | TOWN_STEWARD, ROBOT, COUNCIL |
| authority (decision holder) | 1 | COUNCIL |
| lifecycle `on` message, sender | 1 | ROBOT |
| lifecycle `on` message, receiver | 1 | TOWN_STEWARD |
| monitor `observe` (M-1) | 1 | ROBOT[i].blocking |
| protocol SWITCH, message step sender | 2 | TOWN_STEWARD, ROBOT |
| protocol SWITCH, message step receiver | 2 | ROBOT, TOWN_STEWARD |
| protocol SWITCH, compute step | 1 | TOWN_STEWARD |
| sharing, views, responsibilities, assume/guarantee | 0 | ROAD_USE has no entries of these kinds that name an actor |

## References to absent actors in unchecked positions (naive)

The checker reported none of these:

- monitor `rule`: `"ROBOT.blocking >= 3 AND state IN [Holding, Overstay]"` names ROBOT.
- incentives `rules`: `"penalty(ROBOT[i], lambda) when overstay"` names ROBOT.
- regime `safety_invariant` `"robots_on_road == 0"` and `condition` `"orders_in_window < 22"` / `">= 26"`: these use source vocabulary. They are not actor references, but they have no meaning in the destination.
- message names `node_released` and `regime_notice` appear in no destination actor's interface. Message names are not checked against interfaces.

`probes/probe_stale_robot_in_rule.cadl` is the adjusted file with ROBOT restored in the monitor rule and the incentive rule. It passes check and verify (17/17), even though the eviction monitor can now never match a taxi.

## Defects the toolchain did not detect

1. **Units:** `probes/probe_unitless_depot_time.cadl` writes `depot_drive_time >= 15` (meaning minutes) instead of `900s`. Durations are encoded in ms and bare numbers have no unit, so the conflict disappears and verify passes 17/17.
2. **Vacuous source guarantee:** `hold_time <= hold_limit` relates two free variables. The limit exists only as the 60 s deadline plus an `@amend` comment, so the naive copy constrains nothing. The adapted version writes `60s` explicitly.
3. **Semantic role mismatch:** The destination describes TRAFFIC_CENTER as aggregation-only ("does not issue commands"), but the lifecycle still has an `Evicted` outcome. Nothing checks who enforces an eviction, and capabilities and interfaces are not compared with roles.
4. **Release event:** `position_update` passes the check, but it does not mean "kerb released". Event semantics are not checked.
5. **Unattainable invariant:** `robots_on_road == 0` passes the regime safety-invariant check, because it is satisfiable together with its condition. A taxi fleet in service can never reach it.
6. **Scope gap and time abstraction:** Scoping the rule to idle taxis leaves kerb holds during pickup and drop-off uncovered. Scoping it to occupied taxis instead (`probes/probe_scope_occupied_taxis.cadl`, `is_available == false`) makes verify report a **spurious** conflict with RIDE_SERVICE. The pairwise check A1∧G1∧A2∧G2 cannot tell that the two states hold for one taxi at different times.
