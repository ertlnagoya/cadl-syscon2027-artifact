# Real transplant: an EU U-space rule into US UTM (2026-11-14)

The rule is the strategic deconfliction of UAS flight authorisation in the EU U-space regulation:
the U-space service provider (USSP) accepts a request only if the flight is "free of intersection in
space and time with any other notified UAS flight authorisations" (Regulation (EU) 2021/664,
Art. 10(2)(b)). The destination is the US UTM as described by the FAA UTM Concept of Operations v2.0
(2020). Both are documented systems of systems with many operators, competing service providers, a
state authority, and air traffic control.

## Sources

| ID | Document | Used for |
|---|---|---|
| EAR | EASA, Easy Access Rules for U-space (Reg. (EU) 2021/664), May 2024 | source contracts; "Page x of 157" |
| 666 | Reg. (EU) 2021/666, SERA.6005(c) | E_CONSPICUITY |
| ConOps | FAA NextGen, UTM Concept of Operations v2.0, 3/2/2020 | destination contracts; printed page numbers |
| RID | 14 CFR Part 89, 86 FR 4390 (Jan 15, 2021) | REMOTE_ID |

Each contract in the two files carries the article or page it formalizes. The research notes with
quotations are not included; the article or page of each contract is given in a comment.

## Modelling decisions (threats to validity)

- Predicates are propositions the provisions make true (for example `priority_order_defined`).
  We chose the **same proposition names** on both sides where the documents speak about the same
  matter. The conflicts found depend on this alignment; it is an analyst's judgement, as a role map
  is. With different names, `--map` renames them.
- The ConOps is a concept document, not regulation. The proposed Part 108/146 (90 FR 38212, 2025)
  would give a certificated provider strategic deconfliction for some BVLOS operations; it is not
  final and is not modelled.
- The rule's assumptions are the preconditions that other EU provisions establish (Art. 3(2),
  SERA.6005(c), Art. 10(8)–(10), Art. 7(5)); `fit` in the source confirms that they are established
  there (`outputs/fit_in_source.txt`).
- Numbers (4D volumes, times) are not modelled.

## Results

cadl verify: 0.3.28 (tag v0.3.28; same results with v0.3.29 and the fit branch). cadl fit: commit 5934498, re-run with 2d59e60 (connected-component neighbourhood: the neighbourhood now also lists MANNED_PARTICIPATION, findings unchanged; 74775be gave the same verdicts; it reported only EQUITY on the naive copy, because it stopped at disjoint conflicts).

| Step | File | `cadl verify` | `cadl fit -c FLIGHT_AUTHORISATION` |
|---|---|---|---|
| rule in the source | source_eu_uspace.cadl (83 lines) | PASSED 33/33 | FITS; the source's guarantees establish all 5 assumptions |
| destination | destination_us_utm.cadl (82 lines) | PASSED 48/48 | - |
| naive copy (no map) | outputs/naive.cadl (98 lines) | FAILED 49/50 (type check only; no pair shares a party) | MISFIT: F1 × 4 (USSP, UAS_OPERATOR), review: COMPETENT_AUTHORITY; F3 already vacuous with EQUITY and with UVR |
| mapped (`USSP=USS UAS_OPERATOR=OPERATOR COMPETENT_AUTHORITY=FAA`) | adapted.cadl | FAILED 54/57 (3 pairs, unclassified) | MISFIT: F3 vacuous [EQUITY], F3 vacuous [UVR], F3 guarantee [STRATEGIC_DECONFLICTION] |
| adjusted (3 changes to the rule) | adjusted.cadl | PASSED 57/57 | FITS; info: `every_flight_authorised`, `manned_traffic_conspicuous` not established |

Reading of the findings:

- **F1**: the EU roles USSP (an authorising, certified provider) and UAS operator have no namesake.
  Mapping USSP to USS removes the F1 failure but not the mismatch of responsibility, which F3 then
  shows as a guarantee conflict with STRATEGIC_DECONFLICTION (the USS assists, the operator
  de-conflicts; ConOps p.23, p.37).
- **F3 vacuous**: the rule assumes a priority order (Art. 10(8)–(9)) and withdrawal on restrictions
  (Art. 10(10)); the destination guarantees neither (ConOps p.32 Equity, p.33 UVR). The rule as
  written never applies in the destination.
- **After adjustment**: `cadl verify` passes and gives no further signal. `cadl fit` names the two
  assumptions that the destination does not establish: every flight is authorised (VLOS operators
  need not share intent, ConOps p.24, p.26, fn. 27 p.37) and manned traffic is conspicuous (manned
  aircraft need not participate, p.14). The guarantee "no intersecting authorised flights" then
  holds only among flights that take part; unannounced VLOS and manned traffic are outside it. In
  the EU these assumptions are established by Art. 3(2) and SERA.6005(c), provisions that are not
  part of the transplanted rule. This is the "incomplete transfer" of Dolowitz and Marsh at the
  level of preconditions.

Size and runs: 165 lines for the two descriptions, written from the notes; 3 runs of `cadl fit`
(about 0.3 s each); 3 changes to the rule. Writing time was not measured.

What `cadl verify` alone gives on adapted.cadl: the same three pairs as "contradictory when
combined", without the class or the role mismatch, and nothing on adjusted.cadl.

Contract-theory baseline (`experiments/baseline/baseline.py` on adapted.cadl,
`outputs/baseline_adapted.txt`): all three failing pairs are consistent and compatible; two are
classified F3a, one F3b, as `cadl fit` does.

## From documents to predicates

Encodings of the US side are of two kinds. Where the ConOps makes an explicit statement about the
matter, we encode it as a guarantee, and in three cases (marked "negation") we encode the statement as
the negation of the EU precondition. This is our interpretation: the ConOps describes processes
(the operator de-conflicts, assisted by its USS, p.37), not prohibitions, and does not say that a USS
may not reject a request. Where it is silent or only says that something is not required,
we write nothing, so the precondition is unspecified, and `fit` reports it as not established.

| Item | EU basis (source) | US basis (ConOps) | US encoding | Reading | Result |
|---|---|---|---|---|---|
| A1 every flight authorised | Art. 3(2), 6(4) | VLOS need not share intent (p.24, 26; fn. 27 p.37) | none on A1 | unspecified | not established |
| A2 manned traffic conspicuous | SERA.6005(c) | manned aircraft "not required to participate" (p.14) | none on A2 | unspecified | not established |
| A3 priority order | Art. 10(8)–(9) | "no assumption of a priority scheme" (p.32) | `priority_order_defined == false` | negation | F3a [EQUITY] |
| A4 providers coordinate | Art. 7(5)(a), 10(6) | USS Network "must implement a shared paradigm" (p.11) | `... == true` | explicit | established |
| A5 withdrawal on restriction | Art. 10(10) | "UVRs do not exclude UTM participants" (p.33) | `authorisations_withdrawable_on_restriction == false` | negation | F3a [UVR] |
| G provider rejects intersecting requests | Art. 10(2)(b) | "the Operator strategically de-conflicts" (p.37); USS assists (p.23) | `USS.rejects_intersecting_requests == false` | negation | F3b [STRATEGIC_DECONFLICTION] |

### Sensitivity to the reading (`destination_us_utm_weak.cadl`)

The three negations replaced by the positive content of the statements only
(`operators_negotiate_contention`, `participants_exercise_caution_in_uvr`, and no statement on the
USS rejecting): `cadl verify` PASSED 48/48 (destination) and 57/57 (mapped rule); `cadl fit` FITS and
names four assumptions not established: A1, A2, A3, A5 (`outputs/fit_mapped_weak.txt`).
So every difference in the preconditions is reported under both readings, as a misfit (strong
reading) or as an unestablished assumption (weak reading); the difference of authority is reported
only under the strong reading, because `fit` reports assumptions, not guarantees, that the destination
does not support.
