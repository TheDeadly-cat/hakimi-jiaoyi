# ADR 0350: Multi-window observation-membership provider-attestation binding gate v1

- Status: Accepted as an unmounted synthetic research candidate
- Date: 2026-08-24

## Context

ADR0349 rejects duplicate or excessively overlapping observation memberships,
but its evidence producer supplies the observation identifiers and source
hashes. ADR0349 deliberately reports both
`membership_issuer_exactly_verified=false` and
`date_grid_audits_exactly_verified=false`. A locally consistent caller can
therefore submit arbitrary memberships of the right size and still satisfy the
overlap policy.

ADR0267 and ADR0268 do not close this gap. They prove that pair commitments use
one common membership hash and that the exact commitment chain is internally
consistent. Both explicitly avoid deriving observation identifiers and admit
that a dishonest producer can commit consistently to dishonest inputs.

The project already has the required signing primitive and source lineage:

- ADR0119 exactly derives `common_price_index_hash`,
  `common_observation_index_hash`, observation count, provider binding, and
  `source_matrix_replay_hash` from one complete replay and calendar/provider
  context.
- ADR0120 verifies an Ed25519 dataset-content signature over a receipt that
  binds the exact ADR0119 `composition_hash` and all dataset hashes.
- ADR0121, ADR0122, and ADR0176 separately cover dataset-key lifecycle,
  lifecycle replay, and content-issuance replay.

Creating another key role or signature domain would duplicate these contracts.

## Decision

Add ADR0350 as an unmounted adapter gate. Do not modify ADR0119, ADR0120,
ADR0349, or ADR0346.

ADR0350 preregisters one ordered provider-attestation binding per ADR0349
window. Each binding pins:

- provider ID hash;
- dataset key ID and public-key hash;
- ADR0120 registration, attestation, and verification hashes;
- ADR0119 composition and dataset-provider binding hashes;
- source matrix-replay hash;
- common price-index and common observation-index hashes;
- common observation count.

The preregistration sequence must follow ADR0349 policy registration and
precede ADR0349 membership evidence.

At evaluation, ADR0350:

1. Exactly rebuilds ADR0349 and preserves an ADR0349 `BLOCK`.
2. Exactly verifies one ADR0120 result from its complete ADR0119 source context
   for every preregistered window.
3. Requires the signed composition replay hash to equal the replay embedded in
   the exactly verified uncertainty audit.
4. Requires the signed common price-index hash to equal the ADR0349 price-grid
   commitment.
5. Requires the signed common observation-index hash to equal the ADR0349
   membership commitment.
6. Requires the signed common observation count to equal ADR0349's common
   sample count.
7. Returns `UNKNOWN` for any missing, reordered, malformed, signature-invalid,
   expected-pin-drifted, or cross-window-spliced source.

The output contains only hashes and counts. It excludes observation IDs,
dates, public-key bytes, signatures, source documents, and verification
contexts.

## Claim calibration

An ADR0350 research-only `PASS` proves that a valid signature under the locally
registered ADR0120 dataset key covers the exact composition from which the
ADR0349 membership, price grid, sample count, and replay were derived.

It does not prove external provider control of that key, external provider data
issuance, current key lifecycle, issuance uniqueness, durable registry truth,
calendar governance, market authenticity, statistical independence,
profitability, or trading authority.

## Consumer-first activation order

1. Keep ADR0350 synthetic and unmounted.
2. Bind exact ADR0121 dataset-key lifecycle evidence per provider key.
3. Bind ADR0122 lifecycle-replay and ADR0176 content-issuance replay evidence.
4. Require durable externally published checkpoints and independent observers.
5. Add a versioned ADR0346 successor that requires ADR0350 and all remaining
   issuer-governance layers as mandatory vetoes.
6. Add a neutral report and `SOURCE -> GAP -> MATURITY -> PERMISSION`
   presentation only after the consumer contract is stable.
7. Require separate explicit authorization for any current migration; never
   auto-reissue pointer-v2.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Two disjoint memberships matching signed compositions | research-only `PASS` |
| ADR0349 passes arbitrary self-declared membership | ADR0350 `UNKNOWN` |
| Price-grid hash differs from signed composition | `UNKNOWN` |
| Provider signature or verification document tampered | `UNKNOWN` |
| Provider bundle missing or reordered | `UNKNOWN` |
| Preregistered attestation/composition/replay pin drift | `UNKNOWN` |
| Provider-attested duplicate windows | preserve ADR0349 `BLOCK` |
| Duplicate or reordered issuer preregistration rows | registration rejected |
| Resealed authority promotion | verification failure |
| Raw IDs, dates, keys, signatures, or source documents in output | rejected |

## Boundary

All validation uses synthetic in-memory dates, prices, keys, signatures, and
contexts. The production module accepts no private key. This ADR accesses no
historical K-line task, runtime asset, database, cache, log, credential,
service, browser, scheduler, broker, paper account, or live account. It changes
no report, writer, server, engine, CLI, frontend, current pointer, natural-
forward single-look artifact, legacy pack-v5 behavior, or pointer-v2 contract.
