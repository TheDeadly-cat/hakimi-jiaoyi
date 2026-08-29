# ADR 0053: Cross-lag C3 aggregate public projection

- Status: Accepted and implemented for C3; C4 remains unmounted
- Date: 2026-08-21
- Scope: Research evidence only
- Authority: None

## Context

C2 now provides a strict-canonical candidate protocol registration and a
triple-binding assessment that replays P1b, C0 evaluation, and C1 receipt. C2
preserves valid PASS and BLOCK evidence but is not suitable for direct public/UI
consumption because its verifier context includes registry, assignment, protocol,
and aligned-observation inputs.

C3 must expose a small aggregate projection without copying those inputs or
weakening verification. It is a consumer-only boundary, not an endpoint, writer,
registry, pointer, or mounted presentation.

## Decision

C3 is one pure builder plus one exact verifier:

- `build_strategy_correlation_cross_lag_public_summary`
- `verify_strategy_correlation_cross_lag_public_summary`

The builder must invoke the official C2 binding-assessment verifier with the full
in-memory context. It may project a result only after that replay passes. It must
perform no file, database, network, scheduler, callback, writer, or pointer I/O.

## Versioned contract

Public summary schema:
`strategy-correlation-cross-lag-public-summary-v1`

Verification schema:
`strategy-correlation-cross-lag-public-summary-v1-verification-v1`

Static fingerprint:
`20260821-cross-lag-public-summary-1`

The summary is strict-canonically sealed with `public_summary_hash`.

## Four-axis state model

Every summary exposes exactly these neutral axes:

The public presentation order is `SOURCE -> GAP -> MATURITY -> PERMISSION`.

1. `SOURCE`
2. `GAP`
3. `MATURITY`
4. `PERMISSION`

| Input | Public state | SOURCE | GAP | MATURITY | PERMISSION |
| --- | --- | --- | --- | --- | --- |
| Missing | `NOT_SUPPLIED` | `NOT_SUPPLIED` | `SOURCE_NOT_SUPPLIED` | `NOT_EVALUATED` | `LOCKED` |
| Invalid | `UNKNOWN` | `UNKNOWN` | `SOURCE_INVALID` | `UNKNOWN` | `LOCKED` |
| Valid C2 pass | `OBSERVED_PASS` | `VERIFIED_C2` | `SEQUENCE_ORDER_UNATTESTED` | `CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL` | `LOCKED` |
| Valid C2 block | `OBSERVED_BLOCK` | `VERIFIED_C2` | `CROSS_LAG_DEPENDENCE_OBSERVED` | `CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL` | `LOCKED` |

`OBSERVED_BLOCK` must remain visible. C3 absence or future C4 absence may not
degrade a valid dependence block to `UNKNOWN`.

## Public field allowlist

C3 may expose only:

- public schema, verification schema, and static fingerprint;
- four-axis states and public state;
- C2 assessment schema, static fingerprint, and assessment hash;
- C2 protocol-registration hash;
- P1b binding hash;
- C0 evaluation hash and C1 receipt hash;
- assignment, direction-contract, and analytic-policy hashes;
- gate decision and fixed reason code;
- cross-stratum pair, lag-test, and dependent-test counts;
- maximum adjusted absolute lower bound as a dependence diagnostic string;
- aggregate facts, blockers, and authority fields;
- the public summary hash.

Hashes are provenance identifiers only. They do not imply correctness, formal
registration, profitability, readiness, or execution authority.

## Redaction denylist

C3 must never copy:

- identity set or `identity -> stratum` assignment;
- cluster members, symbols, or per-identity fields;
- raw returns, prices, bars, or aligned observations;
- per-pair or per-lag result arrays;
- correlation or effective-sample values for individual tests;
- classification source text or untrusted descriptions;
- local paths, URLs, callbacks, service handles, writers, or pointers.

Unknown and not-supplied projections must be built from fixed constants only and
must not reflect any invalid source value.

## Blocker mapping

C3 consumes the C2 blocker
`CROSS_LAG_C3_PUBLIC_PROJECTION_NOT_IMPLEMENTED`. A valid C3 summary replaces it
with `CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED`.

Valid PASS blockers:

- `CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED`
- `CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED`

Valid BLOCK blockers:

- `CROSS_LAG_DEPENDENCE_DETECTED`
- `CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED`
- `CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED`

This replacement marks component availability only. It does not increase formal
maturity or permission.

## Authority contract

`descriptive_only` is the only authority-related field allowed to be true. Every
other field remains native false, including sequence, strata timing, formal
preregistration, independence, candidate activation, registry, current, pointer,
paper, live, and profitability authority.

The public copy must not contain `READY`, profit, expected-return, recommendation,
execution, activation, or authorization language.

## Adversarial acceptance matrix

| Attack or gap | Required result |
| --- | --- |
| Missing C2 assessment | `NOT_SUPPLIED` |
| Non-mapping or incomplete assessment | `UNKNOWN` |
| Broken or coherently resealed assessment hash | `UNKNOWN` |
| Valid assessment paired with another evaluation | `UNKNOWN` |
| Valid assessment paired with another C1 receipt | `UNKNOWN` |
| PASS/BLOCK, reason, or count mismatch | `UNKNOWN` |
| Assignment, direction, or policy hash mismatch | `UNKNOWN` |
| Boolean, numeric, or string authority alias | `UNKNOWN` |
| Extra untrusted field | Not reflected |
| C2 verifier exception | `UNKNOWN`, no exception escape |
| File/network/database/callback/writer attempt | Test failure |
| Valid C2 PASS | `OBSERVED_PASS`, every permission false |
| Valid C2 BLOCK | `OBSERVED_BLOCK`, dependence blocker first |
| Resealed public-state or permission tamper | Exact verifier rejects |

At least one tamper must alter a real non-default aggregate value and assert the
precondition before mutation.

## C4 boundary

C3 does not modify `index.html`, `app.js`, the main stylesheet, or any mounted DOM.
Only after C3 passes an independent adversarial review may C4 add an unmounted,
target-scoped component that renders the four neutral axes with text nodes, native
DOM style APIs, responsive layout, and reduced-motion support.

No C3 or future C4 result is profitability evidence or paper/live trading
authorization. Formal state, current pointers, and execution remain outside this
chain.

## Implementation closure (2026-08-21)

C3 is implemented in
`exchange_terminal/services/strategy_correlation_cross_lag_public_projection.py`
with the contract fingerprint `20260821-cross-lag-public-summary-1`. Its exact
verifier rebuilds the summary from the complete C2 context and rejects a supplied
document unless the rebuilt strict-canonical document matches it.

The implementation was closed with this targeted evidence:

- C3 projection contract: 16/16 tests passed;
- complete C0-C3 cross-lag matrix: 117/117 tests passed;
- projection, projection test, and lean runner passed `py_compile`;
- independent synthetic probe exposed `OBSERVED_PASS` and `OBSERVED_BLOCK`, found
  no raw-detail keys, kept 11 authority-related booleans false, rejected a
  coherently resealed real nonzero dependent-count mutation, and failed closed to
  `UNKNOWN` when the C2 verifier raised;
- the independent probe denied file and socket access;
- lean list/dry-run reported 9 planned checks, 0 completed, 0 executed, 0 reused,
  and all runtime mutation and paper/live authority fields false.

Implementation fingerprints at closure:

- projection: `9DBD22012F0021C21E8DBD1E8AEC02E7F2B7E1C386F5E9F7C6F36A3294B9210D`;
- projection tests: `14783CFF566F26031A29D30E102EEB10F3C603F392F0BCF581E6DB90B89F1BDD`;
- lean runner: `F315295B3AC66EF2EF14BFF1AD65A5D431CE086A25C2E8A7AAF43EFD221E02EA`;
- C0 gate remained `822865D7CB5B9CF940A14D18027573675230782D3666086FE14189AD1548EA95`;
- `quant_bot/engine.py` remained
  `26F0FAA5704A2867500674D5A9C65311FE0252AD29271A0956A8D52A4F6C17B7`.

C4 remains absent and unmounted. Sequence order, formal registration, current
activation, profitability, paper, and live authority remain false. This closure
does not change the natural-forward chain, legacy pack-v5 behavior, or pointer-v2.
