# ADR 0056: Cross-lag common-factor conditional diagnostic

- Status: Accepted design; implementation complete; consumer activation not started
- Date: 2026-08-21
- Scope: Pure synthetic research diagnostic only
- Authority: None

## Context

The existing C0 cross-lag gate correctly blocks cross-stratum tickets when any
preregistered pair and lag has a conservative adjusted lower bound above the
fixed threshold. It does not accept a common-factor series, frozen factor
exposures, or a residualization receipt.

That omission is safe for ticket independence because shared-factor dependence
must still block raw independent counting. It leaves a different research gap:
the current evidence cannot distinguish a common-factor-mediated lag pattern
from residual cross-identity transmission. The distinction matters for
descriptive diagnosis, model retirement, and future hedge research, but it must
never weaken the raw C0 block.

An explicit source-and-test search found no residualization, partial-dependence,
common-factor, market-beta, factor-neutral, orthogonalization, or conditional
dependence contract in the strategy-correlation modules.

## Synthetic gap evidence

Two deterministic, in-memory, 1000-observation cases were passed through the
unchanged C0 gate with file and socket access denied.

### Common-factor-only case

- one AR(1) factor with coefficient `0.90`;
- two independent residual series with standard deviation `0.04`;
- both raw series equal factor plus their own residual;
- raw lag-1 correlation: `0.885609`;
- residual lag-1 correlation: `-0.015241`;
- raw C0: `BLOCK`, 2 dependent tests, maximum adjusted absolute lower
  `0.824669475022`;
- residual C0: `PASS`, 0 dependent tests;
- raw evaluation hash:
  `d9e4896a5442106cb064c96b56e08ef0294381e7639fba97782d1ef242e2277f`;
- residual evaluation hash:
  `1c752b1c1902214a08ea0270810f99beb17b730f2bc634dc1739b67f2d914b20`.

The residual hash above is intentionally not accepted as an implementation
fixture until the implementation task replays and records the complete current
value. This ADR does not treat a manually transcribed hash as authority.

### Common factor plus direct residual lead-lag

- the same AR(1) factor coefficient `0.90`;
- identity B residual includes `0.96 * A[t-1]` plus small independent noise;
- raw C0: `BLOCK`, 1 dependent test, maximum adjusted absolute lower
  `0.851446775184`;
- residual C0: `BLOCK`, 1 dependent test, maximum adjusted absolute lower
  `0.994895883777`;
- raw evaluation hash:
  `447e9e412baf270d53af29050c94cab5b37d22a4c7aa6a5182e13ccd04e7f3dd`;
- residual evaluation hash:
  `5b340fae195dd59ba7c1215c7ca00f2bc50338383c98293ff21093257e6aca83`.

These cases prove a mechanism-classification gap. They do not prove a profitable
factor model, a causal relation, independent residual tickets, or trading
permission.

## Decision

Add an F0 common-factor conditional diagnostic in:

`exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_diagnostic.py`

with a dedicated test module:

`tests/test_strategy_correlation_cross_lag_factor_conditional_diagnostic.py`

F0 runs the official C0 gate twice:

1. once on the exact raw aligned observations;
2. once on residual observations constructed from a preregistered factor series
   and frozen pre-evaluation identity exposures.

Both C0 outputs must pass the official C0 verifier against their own exact input.
F0 then emits an aggregate mechanism classification. It does not replace C0,
change C0 constants, combine p-values, fit exposures, or create an independence
permission.

## Versioned contracts

Diagnostic schema:
`strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1`

Diagnostic static fingerprint:
`20260822-cross-lag-factor-conditional-diagnostic-1`

Residualization registration schema:
`strategy-correlation-cross-lag-factor-residualization-registration-candidate-v1`

Residualization registration fingerprint:
`20260822-cross-lag-factor-residualization-registration-1`

Factor observation schema:
`strategy-correlation-cross-lag-factor-observations-candidate-v1`

The diagnostic is strict-canonically sealed with `diagnostic_hash`. The
registration is independently sealed with `registration_hash`. Factor rows are
bound with `factor_observations_hash`. Residual rows are never emitted, persisted,
or returned.

## Residualization registration

F0 accepts one plain mapping with exactly these fields:

- schema version and static fingerprint;
- ASCII `factor_id`;
- strict SHA-256 `factor_source_hash`;
- strict SHA-256 `calibration_receipt_hash`;
- strict SHA-256 `identity_order_hash`;
- ordered identity list matching the C0 identity set exactly;
- `beta_by_identity`, with exactly one frozen decimal-string beta per identity;
- `calibration_cutoff_date`;
- `selection_cutoff_date`;
- fixed estimator label `FROZEN_PRE_EVALUATION_OLS_V1`;
- fixed intercept policy `NO_INTERCEPT_RETURN_RESIDUAL_V1`;
- fixed factor policy `CONTEMPORANEOUS_SINGLE_FACTOR_V1`;
- fixed missing policy `FAIL_CLOSED`;
- `registration_hash`.

Every beta is parsed as a finite decimal in the closed interval `[-10, 10]`.
Boolean, float, exponent, NaN, infinity, whitespace-padded, and duplicate textual
forms are rejected. The ordered beta keys must match the ordered identity list.

The registration must state
`calibration_cutoff_date < selection_cutoff_date`. F0 verifies the claim and hash
but does not verify how the calibration receipt was produced. Therefore
`calibration_receipt_attested` remains native false and maturity remains
`CANDIDATE_RESIDUALIZED_NOT_FORMAL`.

F0 must not estimate, refit, shrink, optimize, select, or update beta values from
evaluation observations. A future registration-binding layer may attest the
calibration receipt; F0 cannot.

## Factor observations

Factor observations contain:

- schema version;
- factor id and source hash matching the registration;
- ordered rows with contiguous sequence numbers;
- observation id exactly matching the raw C0 row at each sequence;
- observation timestamp exactly matching the raw C0 row when present;
- one finite native numeric factor return per row;
- factor observations hash.

The factor row count must equal the raw observation count. Missing, duplicate,
reordered, sparse, bool, nonfinite, or extra rows fail closed. The factor series
must have nonzero variance. F0 performs no interpolation, forward fill,
winsorization, timezone conversion, or alignment repair.

## Residual construction

For identity `i` and sequence `t`, F0 computes only in memory:

`residual[i,t] = raw_return[i,t] - beta[i] * factor_return[t]`

The operation order is fixed and inputs are finite. A nonfinite residual fails
closed. Observation ids, timestamps, sequence numbers, and identity ordering are
copied exactly into the private residual C0 input. Raw, factor, beta, and residual
values never enter the F0 output.

The residual input receives a strict aggregate hash for replay binding. That hash
is provenance only and does not authorize persistence or publication.

## Mechanism classification

F0 preserves both C0 decisions and derives one diagnostic state:

| Raw C0 | Residual C0 | Diagnostic state |
| --- | --- | --- |
| `PASS` | `PASS` | `NO_CONDITIONAL_DEPENDENCE_DETECTED` |
| `BLOCK` | `PASS` | `COMMON_FACTOR_MEDIATED_CANDIDATE` |
| `BLOCK` | `BLOCK` | `RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED` |
| `PASS` | `BLOCK` | `SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY` |
| Any invalid/unknown | Any | `UNKNOWN` |

`COMMON_FACTOR_MEDIATED_CANDIDATE` does not change the raw C0 `BLOCK`. A residual
pass is not proof of independence because the beta registration is not formally
attested, factor choice is candidate-only, and raw portfolio dependence remains.

`SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY` is a blocker, not evidence that the
factor model improved the strategy.

## Multiplicity boundary

Raw and residual C0 each retain the existing fixed pair-by-lag Bonferroni family.
F0 does not combine their p-values, report a joint family pass, or convert the two
candidate evaluations into a new statistical permission. Running two candidate
families may increase descriptive classification uncertainty; therefore every F0
state remains candidate-only and all authority fields remain locked.

Any future gate that uses raw and residual results to grant a new permission must
pre-register and implement a single global view-by-pair-by-lag multiplicity
family. That is explicitly outside F0.

## Aggregate output allowlist

F0 may expose only:

- schema and static fingerprint;
- source and maturity state;
- diagnostic state and fixed reason code;
- raw and residual C0 schema, fingerprint, evaluation hash, decision, reason,
  observation count, pair count, lag-test count, dependent-test count, and
  maximum adjusted absolute lower string;
- factor id, factor source hash, calibration receipt hash, registration hash,
  factor observations hash, identity-order hash, and residual-input hash;
- fixed aggregate facts, blockers, and authority fields;
- diagnostic hash.

F0 must not expose identities, beta values, factor values, raw returns, residual
returns, observation ids, timestamps, pair/lag result arrays, paths, URLs,
callbacks, writers, model descriptions, or calibration source text.

## Authority contract

`descriptive_only` is the only authority-related field allowed to be true. Every
other field remains native false, including:

- raw or residual independence proven;
- common-factor causality proven;
- calibration receipt attested;
- factor registration formal;
- sequence timing attested;
- candidate activation, registry, current, pointer, paper, live, profitability,
  allocation, hedge, and execution authority.

No F0 output may contain `READY`, expected-return, target-return,
recommendation, allocation, hedge ratio, order, or profitability language.

## Adversarial acceptance matrix

| Attack or gap | Required result |
| --- | --- |
| Common-factor-only synthetic case | Raw `BLOCK`, residual `PASS`, mediated candidate, raw block preserved |
| Common factor plus direct residual lag | Raw `BLOCK`, residual `BLOCK`, residual dependence observed |
| Independent raw and residual sequences | Both `PASS`, candidate non-detection only |
| Raw `PASS`, residual `BLOCK` suppression case | Instability state and blocker |
| Missing or malformed registration | `UNKNOWN` |
| Registration hash mismatch | `UNKNOWN` |
| Bool, float, exponent, NaN, infinity, or out-of-range beta | `UNKNOWN` |
| Identity order or beta key mismatch | `UNKNOWN` |
| Calibration cutoff not before selection cutoff | `UNKNOWN` |
| Missing, duplicate, reordered, or extra factor row | `UNKNOWN` |
| Factor id/source/hash mismatch | `UNKNOWN` |
| Zero-variance or nonfinite factor | `UNKNOWN` |
| Raw/factor observation id or timestamp mismatch | `UNKNOWN` |
| C0 builder/verifier exception or native-bool alias | `UNKNOWN`, no exception escape |
| Refit beta from evaluation rows | No API exists; static source test fails if added |
| Extra raw, beta, factor, residual, path, URL, or callback field | Never reflected |
| Valid F0 paired with another raw/factor/registration context | Exact verifier rejects |
| Real nonzero raw or residual dependent count changed and resealed | Exact verifier rejects |
| File, database, socket, clock, random, UUID, callback, or writer attempt | Test failure |
| Any diagnostic state | All formal/current/paper/live/profitability authority false |

The implementation tests must assert real nonzero dependent counts before both
raw and residual tamper mutations.

## Consumer-first activation sequence

1. Accept this ADR while no F0 source or test file exists.
2. Implement the pure F0 diagnostic and dedicated synthetic contract suite.
3. Independently replay the two documented synthetic cases with denied I/O.
4. Add an F1 read-only report consumer that accepts only exact F0 output.
5. Design an F2 protocol that binds the frozen beta registration and calibration
   receipt; do not mark the receipt attested in F0 or F1.
6. Only after F0-F2 independent review, consider an aggregate projection.
7. Do not add endpoints, current pointers, writers, mounted UI, paper, or live
   paths as part of F0-F2.

No step automatically activates the next one. A residual pass, protocol, public
projection, or UI component is not independence proof or trading permission.

## F0 implementation acceptance

F0 implementation is complete only when current-tree evidence proves:

- one new service module and one dedicated test module exist;
- the unchanged C0 gate and engine fingerprints remain stable;
- registration, factor observations, raw evaluation, residual evaluation, and
  F0 output are all strict-canonically bound;
- both documented synthetic cases reproduce their decision matrix without using
  runtime or persisted data;
- independent, suppression, malformed, timing, identity, beta, factor, alias,
  exception, redaction, context mismatch, and real nonzero tamper tests pass;
- denied file/network/database/time/random/UUID/callback/writer probes report zero
  calls;
- targeted `py_compile`, F0 tests, and the existing C0 suite pass;
- lean list/dry-run plans F0 tests and syntax but executes zero;
- implementation evidence and limitations are synchronized to ADR 0056 and all
  three baseline documents.

## Consequences

F0 can distinguish candidate mechanisms without weakening the conservative raw
ticket-dependence gate. It adds preregistered factor and frozen-beta complexity,
and deliberately leaves calibration attestation and global two-view multiplicity
unresolved for later layers.

F0 remains unimplemented at acceptance of this ADR. C0-C5, the natural-forward
chain, pointer-v2, unmounted C4, absent HTTP/mount, paper lock, and permanent live
lock remain unchanged.

## F0 implementation closure (2026-08-21)

Status: `IMPLEMENTED_CANDIDATE_NOT_ACTIVATED`.

- Service: `exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_diagnostic.py`.
- Test: `tests/test_strategy_correlation_cross_lag_factor_conditional_diagnostic.py`.
- Contract schema: `strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1`.
- Registration schema: `strategy-correlation-cross-lag-factor-residualization-registration-candidate-v1`.
- Static fingerprint: `20260822-cross-lag-factor-conditional-diagnostic-1`.
- The implementation accepts only strictly sealed preregistration, fixed pre-evaluation beta registration, and exactly aligned factor observations. It evaluates the official C0 contract independently on raw and residual rows and verifies both views by exact reconstruction.
- Classification is descriptive only. A raw C0 `BLOCK` is never relaxed by a residual `PASS`; `raw_block_relaxed=false` and all candidate/current/paper/live/profitability authority fields remain false.
- Pure synthetic evidence: common-factor-only produced raw `BLOCK` with 2 dependent tests and residual `PASS` with 0, classified `COMMON_FACTOR_MEDIATED_CANDIDATE`; a true direct residual lag produced raw `BLOCK` and residual `BLOCK`, each with 1 dependent test, classified `RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED`.
- Independently resealed raw and residual dependent-count tampering was rejected. Aggregate output exposes no observation rows, identities, betas, or factor values.
- Targeted evidence: F0 `17/17 OK`; C0+F0 `34/34 OK`; independent two-case probe `PASS`.
- Lean research registration contains the F0 test and service exactly once. `--list` and `--dry-run --no-receipts` report 4 planned checks, 0 completed, 0 executed, `runtime_mutations_allowed=false`, and paper/live false; `--fresh` was not used.
- The service is not referenced by the runtime server, CLI, application/interface adapters, engine, data layer, Electron runtime contract, or mounted UI. F1 report consumption, calibration attestation, and global two-view multiplicity registration remain unimplemented blockers.
- Implementation SHA-256: `0077AF4E24A6FCFFCE2ADED8BB4DC4CD3170193E2949D3BD5E2317CB75CB28F6`; test SHA-256: `7208DA8E1C25DE3CBCDB3F9E31032E9D93A6AB0248F930ABEA7A38429A383022`; lean runner SHA-256 after registration: `C7AB44476D5D3ED2F3A18C908C42BE2B566CE8FD0A4B652BFF7762CB285A3C48`.
- C0 and engine fingerprints remained `822865D7CB5B9CF940A14D18027573675230782D3666086FE14189AD1548EA95` and `26F0FAA5704A2867500674D5A9C65311FE0252AD29271A0956A8D52A4F6C17B7` during validation.
