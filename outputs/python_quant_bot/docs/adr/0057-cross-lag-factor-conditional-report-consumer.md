# ADR 0057: Versioned F0-v2 migration before the F1 read-only report consumer

- Status: design accepted; implementation complete; runtime and presentation activation not started.
- Date: 2026-08-21.
- Scope: pure synthetic research evidence and unmounted read-only contracts only.
- Authority: no current admission, pointer write, paper/live order, profitability claim, or automatic activation.

## Context

F0-v1 is a sealed, exactly replayed factor-conditional diagnostic. It correctly preserves raw C0 precedence and classifies the four raw/residual decision combinations. Its schema and fingerprint are:

- `strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1`
- `20260822-cross-lag-factor-conditional-diagnostic-1`

F0-v1 also seals the implementation-status blocker `F1_REPORT_CONSUMER_NOT_IMPLEMENTED`. That text is true before an F1 implementation exists, but becomes stale as soon as F1 code exists, even while F1 remains unmounted. A consumer cannot silently remove or relabel that blocker because both operations break exact F0-v1 replay.

## Read-only gap evidence

A deterministic common-factor-only fixture was evaluated through the public F0-v1 function while file, socket, SQLite, wall-clock, random, and UUID access remained denied.

- Original F0-v1 hash: `da58bf78a66d60539793fc1241020522c98839f293da308b79f8f2368079df83`.
- Original document exactly verified and retained locked authority.
- The dynamic marker was present.
- Removing the marker and strictly resealing produced `2e3b9bd031f8a5c54594cbc88383d3e3fada2ed5e8dbeff8dd617bd4544f3dcc`; exact verification returned false.
- Relabeling it to `FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED` and strictly resealing produced `ae7128f880ce6ed0ac92dc8c6aaf5127f674d5a6e0671fd09c390ab622ec8fff`; exact verification returned false.

Therefore a direct F1-on-v1 projection has only three choices, all unacceptable: expose stale semantics, omit sealed provenance, or rewrite an exactly verified source.

## Decision

Freeze F0-v1 unchanged and introduce a narrow F0-v2 governance adapter before implementing F1.

### F0-v1 compatibility

- Existing F0-v1 evaluator and verifier remain byte-for-byte unchanged.
- Existing v1 evidence remains verifiable but is never eligible for F1 observed output.
- If supplied to F1, v1 maps to `UNKNOWN_UNSUPPORTED_SOURCE_VERSION` and does not auto-migrate.
- No v1 artifact, current pointer, or scheduled evidence is rewritten or reissued.

### F0-v2 adapter

The adapter is a pure function in a new module. It calls the official F0-v1 evaluator, requires exact v1 verification against the full source context, and deterministically projects a v2 document. It must not duplicate residualization or C0 mathematics.

- Schema: `strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v2`.
- Static fingerprint: `20260822-cross-lag-factor-conditional-diagnostic-2`.
- Hash field: `diagnostic_hash`.
- Provenance field: `source_v1_diagnostic_hash`.
- Stable blocker: `FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED`.
- Stable declaration: `report_contract.schema_version = strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v1`.
- Stable declaration: `report_contract.activation_state = UNMOUNTED`.

The adapter replaces only the dynamic implementation-status blocker. It preserves source state, classification, raw and residual evaluations, registration/factor/context hashes, maturity, facts, and locked authority. Its exact verifier recomputes v1, verifies v1, rebuilds v2, and requires strict whole-document equality.

### F1 consumer contract

- Schema: `strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v1`.
- Static fingerprint: `20260822-cross-lag-factor-conditional-report-consumer-1`.
- Hash field: `verification_hash`.
- Accepted source: exact F0-v2 only.
- Source binding: expected F0-v2 diagnostic hash plus the same preregistered strata, aligned observations, residualization registration, factor observations, and three expected context hashes used by F0.
- Execution: pure function; no filesystem, network, SQLite, time, random, UUID, service, scheduler, browser, or pointer access.

Required observed output fields:

- `source_state = OBSERVED`.
- `source_schema_version`, `source_static_fingerprint`, `source_diagnostic_hash`, and `source_v1_diagnostic_hash`.
- `source_registration_hash`, `source_factor_observations_hash`, `source_identity_order_hash`, `source_raw_evaluation_hash`, and `source_residual_evaluation_hash`.
- `diagnostic_state`, `diagnostic_reason`, `report_state`, `gap_state`, `maturity_state`, and `permission_state = LOCKED`.
- Aggregate-only `raw_evaluation` and `residual_evaluation` summaries.
- Stable effective blockers, facts, locked authority, schema, fingerprint, and verification hash.

The report must not expose observation rows or IDs, identity labels, registered betas, factor values, residual values, pair-level lag tests, calibration payloads, or untrusted extra fields.

### Missing and invalid closure

- Missing source: `source_state = MISSING`, `report_state = UNKNOWN`, blocker `F0_V2_DIAGNOSTIC_MISSING`.
- F0-v1 source: `source_state = UNSUPPORTED`, `report_state = UNKNOWN`, blocker `F0_V1_PRECONSUMER_CONTRACT`.
- Supplied but invalid F0-v2: `source_state = INVALID`, `report_state = UNKNOWN`, blocker `F0_V2_DIAGNOSTIC_INVALID`.
- Expected hash mismatch: invalid, never missing.
- Any exception: fixed UNKNOWN document; no caller-controlled text is reflected.
- UNKNOWN documents remain authority-locked and exactly verifiable by rebuilding the same closure from the same inputs.

### Four observed states

| F0-v2 diagnostic state | F1 report state | Gap state | Raw precedence |
| --- | --- | --- | --- |
| `NO_CONDITIONAL_DEPENDENCE_DETECTED` | `OBSERVED_NO_CONDITIONAL_DEPENDENCE` | `NO_CONDITIONAL_DEPENDENCE_OBSERVED` | Candidate-only; independence is not proven |
| `COMMON_FACTOR_MEDIATED_CANDIDATE` | `OBSERVED_COMMON_FACTOR_MEDIATED_CANDIDATE` | `COMMON_FACTOR_MEDIATION_CANDIDATE` | Any raw BLOCK remains binding |
| `RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED` | `OBSERVED_RESIDUAL_CROSS_LAG_DEPENDENCE` | `RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED` | Raw and residual BLOCK remain binding |
| `SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY` | `OBSERVED_SUPPRESSION_OR_MODEL_INSTABILITY` | `FACTOR_MODEL_INSTABILITY_OBSERVED` | Residual BLOCK prevents any independence claim |

No state proves causality, independence, calibration validity, profitability, or execution permission.

## Locked authority

Only `descriptive_only` is true. At minimum the following remain false:

- `formal_factor_registration_bound`
- `factor_calibration_attested`
- `global_two_view_multiplicity_registered`
- `common_factor_causality_proven`
- `raw_independence_proven`
- `residual_independence_proven`
- `candidate_activation_allowed`
- `current_admission_allowed`
- `current_pointer_written`
- `paper_authorized`
- `live_order_allowed`
- `profitability_claim_allowed`

## Consumer-first implementation order

1. Freeze this ADR and its synthetic gap hashes.
2. Add the F0-v2 adapter and exact verifier without modifying F0-v1.
3. Close F0-v2 positive, negative, tamper, and denied-I/O tests.
4. Add F1 as a pure aggregate consumer of exact F0-v2.
5. Close F1 four-state, UNKNOWN, context-binding, redaction, tamper, and denied-I/O tests.
6. Register only targeted tests and syntax paths in lean; run list/dry-run without receipts or fresh execution.
7. Synchronize the three baseline documents.
8. Optionally build an unmounted neutral presentation model using `SOURCE -> GAP -> MATURITY -> PERMISSION`.
9. Keep runtime, current pointers, scheduled chains, server routes, and mounted UI unchanged unless a later ADR and explicit authorization close every external gate.

## Adversarial matrix

| ID | Case | Required result |
| --- | --- | --- |
| F1-01 | Common factor only | Observed mediated candidate; raw BLOCK preserved |
| F1-02 | True direct residual lag | Observed residual dependence; both BLOCK |
| F1-03 | Raw PASS and residual PASS | Observed no conditional dependence; no independence authority |
| F1-04 | Raw PASS and residual BLOCK | Suppression/instability blocker |
| F1-05 | Missing source | Fixed MISSING/UNKNOWN |
| F1-06 | Valid F0-v1 supplied | Fixed UNSUPPORTED/UNKNOWN; no migration |
| F1-07 | Wrong expected diagnostic hash | INVALID/UNKNOWN |
| F1-08 | Broken F0-v2 hash | INVALID/UNKNOWN |
| F1-09 | Resealed top-level F0-v2 metric tamper | Exact verification false |
| F1-10 | Resealed nested raw metric tamper | Exact verification false |
| F1-11 | Resealed nested residual metric tamper | Exact verification false |
| F1-12 | Strata, registration, factor, or row context mismatch | INVALID/UNKNOWN |
| F1-13 | Duplicate, removed, reordered, or extra stable blocker | Exact verification false |
| F1-14 | Extra untrusted source field | Not reflected; invalid source |
| F1-15 | Pseudo-boolean, subclass container, or non-finite number | INVALID/UNKNOWN |
| F1-16 | Authority alias added to source or receipt | Exact verification false |
| F1-17 | Observation, identity, beta, factor, residual, or pair-test leak | Test failure |
| F1-18 | Resealed F1 report-state, hash, count, or authority tamper | Exact verification false |
| F1-19 | File, socket, SQLite, time, random, or UUID use | Test failure |
| F1-20 | Runtime/server/CLI/Electron/UI source reference | Must remain zero before activation |

## Activation gates

Implementation completion is not activation. F1 remains unmounted until all of the following are separately versioned, evidenced, and explicitly authorized:

- frozen pre-evaluation calibration receipt and exact source binding;
- registered global multiplicity across raw and residual views;
- sequence and strata timing attestation;
- stable report consumer and presentation contracts;
- independent adversarial review;
- no change to paper/live permanent authorization boundaries;
- an explicit current-admission decision that does not auto-write or reissue pointer-v2.

The existing natural-forward chain remains unchanged: `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 fields and hash semantics remain untouched.

## Consequences

- F0-v1 evidence stays reproducible and immutable.
- F0-v2 removes implementation-timeline language from a sealed data contract.
- F1 can expose a neutral aggregate report without rewriting source evidence.
- One small adapter is added, but residualization and cross-lag math retain a single implementation boundary.
- No return backtest or profitability number is generated by this decision.

## Implementation closure: F0-v2 and F1 (2026-08-21)

Status: `IMPLEMENTED_UNMOUNTED_READ_ONLY`.

- F0-v1 remained byte-for-byte unchanged at `0077AF4E24A6FCFFCE2ADED8BB4DC4CD3170193E2949D3BD5E2317CB75CB28F6`. Valid v1 is reported by F1 only as `UNSUPPORTED/UNKNOWN`; no migration, rewrite, or reissue occurs.
- F0-v2 adapter: `exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_diagnostic_v2.py`; schema `strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v2`; fingerprint `20260822-cross-lag-factor-conditional-diagnostic-2`.
- F1 consumer: `exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_report_consumer.py`; schema `strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v1`; fingerprint `20260822-cross-lag-factor-conditional-report-consumer-1`.
- F0-v2 calls and exactly verifies F0-v1, preserves all raw/residual evaluations, replaces only the dynamic implementation blocker with `FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED`, adds the v1 diagnostic hash, and declares the report contract `UNMOUNTED`.
- F1 accepts exact F0-v2 only. Missing source closes as `MISSING/UNKNOWN`, valid v1 as `UNSUPPORTED/UNKNOWN`, and malformed or context-mismatched v2 as `INVALID/UNKNOWN`.
- Four synthetic observed states were independently reproduced: mediated raw `BLOCK` / residual `PASS`; direct residual raw `BLOCK` / residual `BLOCK`; no conditional dependence raw `PASS` / residual `PASS`; suppression raw `PASS` / residual `BLOCK`.
- Independent F1 receipt hashes were `2a06998b701ffe74b4ce408c984e8e980f93a7f5986fa3c407d3d9254a50cd1a`, `98a1688a41c2eda2baef8d0941cf539aeecff46dbff2f1b3868dd79a7ecbb49c`, `bb829470f777e7230268504da1f03093f567857a3a18a73bf6eadc6b0ec66aa4`, and `9f8655742a0d2ddd3700a21c56f66b979c53b49bd340186e31e76f5b976434be` respectively. Re-sealed receipt tampering was rejected in every state.
- Validation: F0-v2 `17/17 OK`; F1 `20/20 OK`; C0 + F0-v1 + F0-v2 + F1 `71/71 OK`; independent four-state and three-UNKNOWN probe `PASS`.
- Output is aggregate-only. Observation rows/IDs, identities, betas, factor/residual values, and pair-lag tests are not exposed. Only `descriptive_only=true`; current, pointer, paper/live, profitability, causality, and independence authority remain false.
- Lean registration contains F0-v1, F0-v2, and F1 test/service entries exactly once. Research list/dry-run reports 4 planned, 0 completed, 0 executed, receipts disabled, runtime mutations false, paper/live false, and no fresh run.
- Explicit runtime, server, CLI, application/interface, engine/data, Electron, and mounted UI source paths contain no F0-v2 or F1 references.
- SHA-256: F0-v2 service `AF8F41D40ACC562E5C1B4D758E34792AE8723EE517F648697097AE17B164469F`; F0-v2 test `EFB491BA9B13C1F7B20211A84ED2A660704383D0EEE8B270D5AAB3A8F9BF0BEC`; F1 service `C18BFF9E755E93B0CA77EA693C60073AB107C315EEFF2AC3FBCBFC719B0C8CFA`; F1 test `62A290710F73C865721E06584430DF540BC927851A2EDC5A6EFD6BB6EAD5182E`; lean runner `5F8183A2A44BAC09336AE440622E2491A5EBC784BF01505911958CC589A98CA7`.
