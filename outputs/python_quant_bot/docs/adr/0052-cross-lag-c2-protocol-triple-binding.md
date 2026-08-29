# ADR 0052: Cross-lag C2 protocol triple binding

- Status: C2 candidate protocol implemented and independently reviewed; C3 not started
- Date: 2026-08-21
- Scope: Research evidence only
- Authority: None

## Context

The cross-lag chain now has five independently verified candidate boundaries:

1. C0 cross-lag gate evaluation.
2. C1 read-only aggregate consumer receipt.
3. Versioned lag-direction contract.
4. P1a registry-to-identity assignment adapter.
5. P1b protocol-v5 same-source preregistration-adapter binding.

P1b proves that the protocol-v5 cluster preregistration, frozen registry evidence,
derived identity assignment, and lag-direction policy share one source. It does not
bind a specific C0 evaluation or C1 receipt. C2 must close that gap without
creating formal preregistration, projection, registry, pointer, paper, or live
authority.

## Decision

C2 has two separate candidate documents:

- a protocol registration that freezes the expected P1b and analytic contracts;
- a binding assessment that replays P1b, C0, and C1 and binds their exact hashes.

Registration and assessment must not be collapsed into one document. The former
contains no observed decision or metric. The latter may preserve an observed
PASS/BLOCK result but may not upgrade maturity or permission.

## C2 registration v1

Schema:
`strategy-correlation-cross-lag-protocol-registration-candidate-v1`

Verification schema:
`strategy-correlation-cross-lag-protocol-registration-candidate-v1-verification-v1`

The registration must strict-canonically bind:

- exact P1b schema, static fingerprint, and binding hash;
- exact cluster preregistration hash;
- protocol-v5 registration hash;
- P1a adapter hash and assignment hash;
- direction-contract hash and lag-direction convention;
- C0 evaluation schema and gate static fingerprint;
- C1 consumer schema and consumer static fingerprint;
- fixed lag family `-2, -1, +1, +2`;
- global pair-by-lag Bonferroni policy;
- family alpha, observation minimum, effective-sample minimum, and lower-bound
  threshold;
- registry freeze timestamp and first eligible observation timestamp;
- every maturity and permission field;
- a registration hash over the entire document.

The registration must not contain evaluation hash, gate decision, dependent-test
count, correlations, lower bounds, or consumer receipt hash.

## Sequence-order limitation

The current chain does not prove that a C2 registration existed before the first
eligible observation. P1a proves registry freeze order, not C2 registration order.
Therefore every C2 registration and assessment must retain:

- `sequence_order_attested = false`
- `formal_preregistration_bound = false`
- blocker `CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED`

A generated timestamp, current wall clock, file modification time, unit-test time,
or coherently resealed document cannot repair this gap. A future formal migration
would require an externally anchored pre-observation registration receipt under a
separate ADR.

## C2 binding assessment v1

Schema:
`strategy-correlation-cross-lag-protocol-binding-candidate-v1`

The assessment must replay, not trust:

1. P1b preregistration-adapter binding verifier.
2. C0 cross-lag evaluation verifier using the exact P1a assignment and aligned
   in-memory observations.
3. C1 consumer-receipt verifier using the same evaluation and observations.
4. C2 registration verifier using the same P1b document.

It must then require exact equality for:

- P1b binding hash;
- C2 registration hash;
- P1a assignment hash and C0 stratum-assignment hash;
- C0 evaluation hash and C1 source-evaluation hash;
- C1 receipt hash;
- gate decision, reason, dependent-test count, lag-test count, and pair count;
- direction-contract hash and analytic-policy hash;
- cluster preregistration, protocol-v5, registry asset, and registry-binding
  hashes.

## Assessment states

| Source result | C2 state | Required blockers |
| --- | --- | --- |
| Missing | `NOT_SUPPLIED` | `CROSS_LAG_PROTOCOL_EVIDENCE_NOT_SUPPLIED` |
| Invalid or mismatched | `UNKNOWN` | `CROSS_LAG_PROTOCOL_EVIDENCE_INVALID` |
| Valid C1 pass | `OBSERVED_PASS_CANDIDATE_PROTOCOL` | sequence-order gap, C3 absent |
| Valid C1 block | `OBSERVED_BLOCK_CANDIDATE_PROTOCOL` | dependence detected, sequence-order gap, C3 absent |

Both observed states retain maturity
`CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL` and `PERMISSION=LOCKED`.

The C3 blocker is `CROSS_LAG_C3_PUBLIC_PROJECTION_NOT_IMPLEMENTED`. Its presence
does not hide a valid dependence block.

## Redaction contract

C2 may expose only schemas, fingerprints, hashes, aggregate counts, frozen dates,
fixed policy, observed decision/reason, facts, blockers, and authority fields. It
must not copy:

- identity assignment or identity set;
- raw return series or aligned observations;
- per-pair or per-lag metrics;
- untrusted source text;
- local paths, URLs, callbacks, writers, or service handles.

## Authority contract

`descriptive_only` is the only authority-related field allowed to be true. Every
other authority field remains a native false boolean, including:

- `formal_preregistration_bound`
- `sequence_order_attested`
- `strata_timing_attested`
- `independence_proven`
- `count_as_independent_allowed`
- `candidate_binding_activation_allowed`
- `formal_registry_activation_allowed`
- `formal_registry_written`
- `current_admission_allowed`
- `current_writer_activation_allowed`
- `current_pointer_written`
- `paper_authorized`
- `live_order_allowed`
- `profitability_claim_allowed`

## Adversarial acceptance matrix

| Attack or gap | Required result |
| --- | --- |
| Valid P1b paired with another valid evaluation | `UNKNOWN` |
| Valid evaluation paired with another valid C1 receipt | `UNKNOWN` |
| Valid C2 registration paired with another valid P1b | `UNKNOWN` |
| P1a assignment hash differs from C0 assignment hash | `UNKNOWN` |
| C0 evaluation hash differs from C1 source hash | `UNKNOWN` |
| PASS/BLOCK or reason mismatch | `UNKNOWN` |
| Pair, lag, or dependent count mismatch | `UNKNOWN` |
| Direction or policy hash mismatch | `UNKNOWN` |
| Missing, duplicate, reordered, or extra lag | `UNKNOWN` |
| Coherently resealed non-default metric change | `UNKNOWN` |
| Coherently resealed registration policy change | `UNKNOWN` |
| Boolean, numeric, or string authority alias | `UNKNOWN` |
| Extra untrusted field | Not reflected |
| Any verifier exception | `UNKNOWN`, no exception escape |
| File, network, database, callback, writer, or pointer attempt | Test failure |
| Valid dependence evidence | Visible BLOCK, never hidden as UNKNOWN |
| Valid independent evidence | Visible PASS, still candidate-only |

At least one tamper test must assert that the selected source value is non-default
before changing and resealing it, preventing no-op adversarial coverage.

## Consumer-first activation order

1. C2 registration pure builder and exact verifier.
2. Registration negative and coherent-reseal tests.
3. C2 triple-binding assessment and exact verifier.
4. PASS/BLOCK, cross-source, replay, authority, redaction, and I/O tests.
5. Independent adversarial probe.
6. Lean list/dry-run registration with zero executed checks.
7. ADR and three-baseline synchronization.
8. Consider C3 redacted projection in a separate change.

No C2 result may create or update a registry, pointer, service, scheduler, paper
account, or live authority. Synthetic, test, backtest, simulation, and
natural-forward evidence are not profitability proof or trading authorization.

## Implementation evidence

- Registration schema:
  `strategy-correlation-cross-lag-protocol-registration-candidate-v1`
- Registration static fingerprint:
  `20260821-cross-lag-protocol-registration-1`
- Binding schema:
  `strategy-correlation-cross-lag-protocol-binding-candidate-v1`
- Binding static fingerprint: `20260821-cross-lag-protocol-binding-1`
- Registration tests: 14/14 passed.
- Binding assessment tests: 17/17 passed.
- C0 through complete C2 targeted chain: 101/101 passed.
- Registration contains no evaluation hash, receipt hash, observed decision,
  observed count, or per-lag result.
- Binding assessment replays C2 registration, P1b, C0 evaluation, and C1 receipt;
  valid PASS and valid BLOCK remain separately visible.
- Independent probe: PASS/BLOCK visibility, aggregate-only redaction, no
  file/network I/O, native-boolean authority locks, verifier-exception fail-closed
  behavior, and rejection of a coherently resealed real nonzero count were proved.
- Lean v2: 9 planned, 0 completed, 0 executed, 0 reused; C2 registration and
  binding tests plus protocol syntax are registered; runtime mutation, paper, and
  live authority remain false.

C2 remains `CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL`. Sequence order is not attested,
C3 is absent, and no writer, registry, pointer, paper, or live capability exists.
