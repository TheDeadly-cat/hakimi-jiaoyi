# ADR 0051: Cross-lag preregistration adapter prerequisite

- Status: P1 complete through independently reviewed P1b; C2 not started
- Date: 2026-08-21
- Scope: Research evidence only
- Authority: None

## Context

Cross-lag C1 verifies a candidate evaluation by replaying the official gate with
an in-memory `identity -> stratum` mapping and its strict assignment hash. The
existing strata protocol separately verifies a versioned protocol registration.
There is currently no verified adapter proving that those two objects describe
the same frozen identities, strata, classification source, or evidence order.

Creating a C2 binding that compares only caller-supplied hash strings would allow
a confused-deputy failure: a valid cross-lag evaluation could be paired with an
unrelated valid strata registration. That would add apparent maturity without a
real provenance link.

## Decision

Cross-lag C2 is prohibited until a pure preregistration adapter v1 exists and
passes an independent adversarial review. C1 remains the highest implemented
stage. No protocol, projection, UI, registry, writer, or pointer is activated by
this ADR.

The adapter must consume a verified strata protocol registration, its verified
classification/registry evidence, the exact cross-lag assignment mapping, and the
cross-lag analytic policy. It must rebuild every digest rather than trust a copied
hash field.

## Adapter v1 output contract

The candidate schema will be
`strategy-correlation-cross-lag-preregistration-adapter-candidate-v1` and must
strict-canonically bind at least:

- source strata protocol schema and registration hash;
- source registry asset and binding-assessment hashes;
- classification source id, version, and strict content hash;
- classification effective date and selection cutoff date;
- frozen timestamp and first eligible observation timestamp;
- exact sorted identity set and its hash;
- exact sorted `identity -> stratum` assignment and its hash;
- assignment count and distinct stratum count;
- fixed lag family `-2, -1, +1, +2`;
- family alpha `0.05`;
- one global cross-stratum pair-by-lag Bonferroni family;
- minimum observation count `64`;
- minimum effective sample size `20`;
- adjusted absolute lower-bound threshold `0.75`;
- lag direction convention and pair ordering convention;
- every maturity and permission field;
- an adapter hash over the complete document.

The public adapter receipt may expose aggregate counts and hashes, but not raw
returns, symbol-local observations, local paths, or untrusted descriptive text.

## Required temporal rules

The adapter must fail closed unless all of the following are proved with strict
native types:

1. Classification effective date is no later than selection cutoff date.
2. Frozen timestamp is no later than the first eligible observation timestamp.
3. The assignment mapping is identical to the mapping used by gate replay.
4. The identity set is identical to the identities used by gate replay.
5. The lag family and all thresholds were frozen in the adapter before evidence.

A unit test timestamp or current wall-clock time cannot prove historical ordering.
Missing ordering evidence must remain `UNKNOWN`, not inferred as pass.

## Authority contract

Even a verified adapter remains candidate-only. These fields must be native
booleans and remain false:

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

`descriptive_only` is the only authority-related field allowed to be true.

## Adversarial acceptance matrix

| Attack or gap | Required result |
| --- | --- |
| Valid registration paired with another assignment | `UNKNOWN` |
| Valid assignment paired with another identity set | `UNKNOWN` |
| Copied source hash without source replay | `UNKNOWN` |
| Registry asset or binding hash mismatch | `UNKNOWN` |
| Classification content changed and coherently resealed | `UNKNOWN` |
| Effective date after selection cutoff | `UNKNOWN` |
| Frozen timestamp after first observation | `UNKNOWN` |
| Missing timezone or non-second UTC timestamp | `UNKNOWN` |
| Missing, duplicate, reordered, or extra lag | `UNKNOWN` |
| Threshold, alpha, or multiplicity-policy drift | `UNKNOWN` |
| Boolean, numeric, or string authority alias | `UNKNOWN` |
| Extra untrusted field | Not reflected |
| Verifier exception | `UNKNOWN`, no exception escape |
| File, network, database, callback, or writer attempt | Test failure |
| Valid candidate evidence | Verified candidate, every permission false |

At least one coherent-reseal test must alter a real non-default value and assert
the precondition before mutation, preventing no-op tamper coverage.

## Revised activation order

1. C0 core gate: implemented.
2. C1 read-only report consumer: implemented and independently reviewed.
3. P1a registry-to-identity assignment adapter: implemented and reviewed.
4. P1b protocol-v5 and lag-direction binding: implemented and reviewed.
5. C2 protocol binding: prohibited until P1b is complete.
6. C3 redacted projection: prohibited until C2 is complete.
7. C4 unmounted presentation: prohibited until C3 is complete.
8. C5 formal state: separate authorization and migration only.

## Consequences

This prerequisite adds one narrow provenance boundary instead of duplicating the
downside-tail protocol with weaker inputs. It delays presentation work, but it
prevents a valid-looking registration from lending authority to unrelated
cross-lag evidence. No backtest, simulation, natural-forward observation, or test
result is profitability evidence or trading authorization.

## P1a implementation evidence

- Adapter schema:
  `strategy-correlation-cross-lag-registry-assignment-adapter-candidate-v1`
- Static fingerprint: `20260821-cross-lag-registry-assignment-adapter-2`
- Registry asset and binding assessment are replayed through their official
  verifiers before identity assignment is derived.
- Cluster membership and selected registry dimension are expanded into one exact,
  sorted `identity -> stratum` assignment and strict assignment hash.
- Registry freeze time is required to be no later than the first eligible
  observation timestamp.
- The derived mapping is accepted by the cross-lag gate under the same assignment
  hash.
- Targeted adapter tests: 15/15 passed.
- C0 gate plus C1 consumer plus P1a adapter tests: 47/47 passed.
- Independent probe: no file or network I/O, no return/observation/path fields,
  a real non-default assignment reseal was rejected, verifier exceptions failed
  closed, and authority values remained native booleans.
- Lean v2: 9 planned, 0 completed, 0 executed, 0 reused; adapter test and syntax
  entries are registered; runtime mutation, paper, and live authority remain false.

P1a remains `CANDIDATE_REGISTRY_BOUND_NOT_PROTOCOL_BOUND`. Its versioned direction
contract removes `CROSS_LAG_DIRECTION_CONVENTION_NOT_EXPORTED`; it intentionally
retains only `CROSS_LAG_PROTOCOL_REGISTRATION_UNBOUND`. It does not complete P1b
or authorize C2-C5.

## Direction contract evidence

- Contract schema: `strategy-correlation-cross-lag-direction-contract-v1`
- Static fingerprint: `20260821-cross-lag-direction-contract-1`
- Index relation: `RIGHT_INDEX_EQUALS_LEFT_INDEX_PLUS_LAG`
- Sign convention:
  `POSITIVE_LAG_MEANS_RIGHT_IDENTITY_FOLLOWS_LEFT_IDENTITY`
- A deterministic non-periodic construction with `B[t] = A[t-1]` produced one
  dependent result at lag `+1`; the reversed lead produced one at lag `-1`.
- Direction contract tests: 8/8 passed.
- Direction contract plus P1a v2 tests: 23/23 passed.
- C0 gate plus C1 consumer plus direction contract plus P1a v2: 55/55 passed.
- Independent probe bound the exact direction-contract hash into P1a, rejected a
  coherently resealed real index-relation change, attempted no file/network I/O,
  and retained native-boolean authority locks.
- The gate-v1 schema, static fingerprint, and implementation bytes are unchanged;
  interpretation is added through a separate versioned contract.

## P1b implementation evidence

- Binding schema:
  `strategy-correlation-cross-lag-preregistration-adapter-binding-candidate-v1`
- Static fingerprint: `20260821-cross-lag-preregistration-adapter-binding-1`
- The binding replays protocol-v5, P1a v2, and direction-contract verifiers.
- The cluster preregistration hash in protocol-v5 must equal both the replayed
  source preregistration hash and the P1a source preregistration hash.
- Two separately valid but unrelated protocol/registry sources fail closed,
  preventing a confused-deputy binding.
- Valid output is redacted to aggregate hashes, counts, dates, facts, blockers,
  and native-boolean authority locks; identity assignments and observations are
  not copied.
- Targeted P1b tests: 15/15 passed.
- C0 gate plus C1 consumer plus direction contract plus P1a plus P1b: 70/70
  passed.
- Independent probe: all same-source facts were true, file/network I/O was
  denied, a coherently resealed real source-hash change was rejected, verifier
  exceptions failed closed, and authority values remained native booleans.
- Lean v2: 9 planned, 0 completed, 0 executed, 0 reused; P1b test and syntax
  entries are registered; runtime mutation, paper, and live authority remain
  false.

P1b closes the preregistration-adapter prerequisite only. Its state is
`CANDIDATE_PROTOCOL_AND_REGISTRY_BOUND_NOT_FORMAL` and it intentionally retains
`CROSS_LAG_C2_PROTOCOL_NOT_IMPLEMENTED`. C2-C5 remain absent and unauthorized.
