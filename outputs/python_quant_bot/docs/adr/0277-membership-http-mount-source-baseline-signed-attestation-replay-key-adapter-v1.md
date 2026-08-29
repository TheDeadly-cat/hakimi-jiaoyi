# ADR0277: Signed Attestation to Replay-Key Exact Adapter v1

## Status

Accepted as an unmounted, pure, research-only compatibility adapter.

## Context

ADR0274 produces an exactly verified, claim-bound signed-review evidence document.
ADR0275 consumes a replay-key document. Before this decision, a caller had to
manually extract three commitments from two ADR0274 documents and pass them to
the ADR0275 builder. That manual splice creates a version-drift boundary even
when both contracts remain individually valid.

A real synthetic call-chain proof first passed the ADR0274 exact evidence
verifier, then required these three manual extractions:

| ADR0275 field | Authoritative ADR0274 path |
| --- | --- |
| `signed_attestation_hash` | `evidence.source_lineage.signed_attestation_hash` |
| `reviewer_key_sha256` | `registration.key_binding.public_key_sha256` |
| `review_nonce_hash` | `evidence.source_lineage.review_nonce_hash` |

No runtime source, database, cache, browser, service, or scheduler was accessed.

## Decision

Add one exact adapter that accepts the full ADR0274 verification context. It
first delegates to the ADR0274 evidence verifier with explicit expected
registration, signed-attestation, and nonce hashes. Only an exact source result
may be mapped. Target construction is delegated to the public ADR0275 replay-key
builder and therefore inherits its strict canonical contract.

Successful mapping returns `status=PASS`, `mapping_status=ADAPTED`, and
`permission_state=UNKNOWN`. Failure returns a sealed `UNKNOWN` adapter receipt
with no replay key. Adapter success is not gate passage or authorization.

The output includes only source document hashes and the three bounded replay-key
commitments. It excludes raw reviewer identifiers, public-key material, and
signature material.

## Adversarial matrix

- exact ADR0274 evidence: deterministic ADR0275 replay key;
- tampered source evidence or registration: `UNKNOWN`;
- expected signed hash, nonce hash, or registration hash substitution: `UNKNOWN`;
- resealed source-authentication promotion: `UNKNOWN`;
- extra signed-attestation field: `UNKNOWN`;
- raw key, signature, or reviewer identity in output: forbidden;
- exact replay-key passed to ADR0275 snapshot gate: duplicate `BLOCK`;
- exact replay-key passed to ADR0276 reserve protocol: synthetic reserve remains
  `UNKNOWN`, with durability false.

## Consumer-first activation order

1. Keep the adapter import-only and unmounted.
2. Consume its exact replay-key output in ADR0275 and ADR0276 tests.
3. Define a registry provider port separately from the adapter.
4. Require authenticated durable atomic-reserve evidence before any later gate
   version can consider `PASS`.
5. Review HTTP registration and neutral UI projection independently.

## Non-claims

This adapter does not authenticate reviewer identity, reviewer independence,
registry authority, key governance, nonce uniqueness, durable storage, atomic
storage execution, or linearizable concurrency. It does not register HTTP, mount
UI, change current evidence, authorize paper/live activity, prove market
validity, demonstrate strategy performance, or prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
