# ADR 0353: Multi-window lifecycle-replay checkpoint persistence registration v1

- Status: Accepted as an unmounted synthetic research preregistration
- Date: 2026-08-24

## Context

ADR0352 binds every lifecycle receipt to exact ADR0122 replay evidence under one
common checkpoint root and complete-scan snapshot. Its strongest local state
still has `durable_checkpoint_publication_verified=false` and exposes no
persistence evidence. A caller-supplied pinned checkpoint is not durable or
authoritative merely because its hash is preregistered.

ADR0104 through ADR0109 provide a sound consumer-first layering pattern for
provider-identity replay checkpoints, but their schemas, domains, source
receipts, and key lineages are specific to provider-identity assertions. Direct
reuse would merge that trust domain with lifecycle-replay common-view evidence.

## Decision

Add ADR0353 as a no-I/O persistence consumer preregistration for one exact
ADR0352 preregistration. It fixes:

- persistence provider, namespace, adapter, implementation hash, key ID, and
  public-key hash;
- a persistence-provider key role distinct from every ADR0352 registry,
  occurrence-auditor, dataset, governance, identity-registry, and timestamp-
  adapter public key;
- exact common-view checkpoint root, tree size, issue time, reference time,
  registry lineage, study identity, and window order;
- future checkpoint-asset, signed write-receipt, and signed reopen-receipt
  schemas;
- strict canonical encoding, Ed25519 digest-signature format, and separate
  asset/write/reopen domains;
- exactly-one-record, distinct write/reopen session, exact source-binding, and
  external-receipt-only policies;
- preregistered maximum write/reopen delays and minimum reopen separation.

The caller supplies the four public-key hashes excluded for each ADR0352
window. ADR0353 verifies their canonical set hash against the exact ADR0352
binding before enforcing persistence-key role separation. The sealed output
retains only each set commitment and a distinct-key count, not the raw key lists
or public key.

ADR0353 does not build an asset, accept a private key, sign a receipt, perform a
write, reopen a record, or access a filesystem, database, cache, network, or
runtime provider.

## Claim calibration

The highest state is
`PERSISTENCE_CONSUMER_REGISTERED_RECEIPTS_UNOBSERVED`. It proves only that a
future consumer contract is sealed against one exact ADR0352 common view and
that the supplied persistence public key is role-separated.

It does not prove that a write or reopen occurred, that any receipt exists,
that a provider is externally authoritative, that storage is durable, that an
external timestamp is correct, that the checkpoint is an authoritative future
pin, that split views are absent, or that lifecycle receipts are globally
unique. Profitability, paper authority, and live authority remain false.

## Consumer-first activation order

1. Keep ADR0353 synthetic and unmounted.
2. Add a pure verifier for one sealed common-view asset plus independently
   signed write and reopen receipts.
3. Bind the verified asset source hash to an exact ADR0352 evaluation.
4. Add adjacent persisted-checkpoint lineage and rollback detection.
5. Accumulate bounded longitudinal common-view coverage.
6. Establish independent provider trust and durable publication separately.
7. Bind ADR0176 content-issuance replay before any ADR0346 consumer successor.
8. Require an explicit current migration decision and never auto-reissue
   pointer-v2.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR0352 source and role-separated key | preregistration accepted |
| ADR0352 preregistration drift | rejected |
| Missing or extra configuration field | rejected |
| Noncanonical public key or implementation hash | rejected |
| Replay, auditor, or any upstream key reuse | rejected |
| Replay/auditor key-ID reuse | rejected |
| Missing, reordered, duplicated, or drifted excluded-key set | rejected |
| Bool, zero, excessive, or inconsistent delay policy | rejected |
| Registration declared after checkpoint issue | rejected |
| Raw public key or upstream key list in output | rejected |

## Boundary

Validation uses only synthetic in-memory keys, hashes, timestamps, and ADR0352
fixtures. This ADR changes no existing service, report, writer, server, engine,
CLI, frontend, current pointer, natural-forward artifact, legacy pack-v5
behavior, or pointer-v2 contract. It starts no historical-data task, backtest,
service, browser, scheduler, database, cache, log, broker, paper, or live path.
