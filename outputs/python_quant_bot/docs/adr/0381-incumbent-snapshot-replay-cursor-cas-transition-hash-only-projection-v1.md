# ADR0381: Incumbent Snapshot Replay Cursor CAS Hash-Only Projection v1

## Status

Accepted as an unmounted, synthetic, read-only consumer candidate.

## Context

ADR0380 returns exact transition intent, receipt, and cursor documents. Those
documents are appropriate for an internal provider boundary but are too
material-rich for a public consumer: they contain the raw stream identifier,
request nonce hash, high-water attestation hash, and complete consumed
attestation set.

A consumer must be able to distinguish duplicate BLOCK, CAS-conflict UNKNOWN,
and synthetic-advance UNKNOWN without receiving those materials or trusting a
caller-resealed receipt.

## Decision

Add a hash-only read-only projection whose builder reruns the exact ADR0380
simulation from its source objects. The exact verifier reruns the builder and
requires strict document equality plus an independently supplied projection
hash.

The allowlisted projection contains only:

- contract, intent, freshness-result, attestation, projection, cursor, and
  receipt lineage hashes;
- outcome, gate status, bounded sequence observations, and whether the returned
  synthetic cursor differs;
- fixed false authority claims;
- explicit redaction declarations.

It omits raw stream identifiers, request nonce hashes, cursor documents,
high-water attestation hashes, full consumed-attestation sets, intent/receipt
documents, incumbent snapshots, proposals, holdings, keys, and signatures.

`ADVANCED_IN_RETURNED_CURSOR` remains `UNKNOWN`. The projection has no PASS,
READY, paper, live, profitability, storage-commit, durability, or linearizable
read path.

## Consumer-first activation order

1. Keep the projection and verifier unmounted.
2. Add an unmounted neutral presenter with SOURCE -> GAP -> MATURITY ->
   PERMISSION ordering.
3. Define a provider port and authenticated durable receipt in a later version.
4. Add an exact provider-receipt-to-projection adapter without accepting legacy
   synthetic receipt promotion.
5. Review HTTP/current mounting independently.

## Adversarial matrix

- exact synthetic advance projects UNKNOWN with all authority false;
- CAS conflict remains UNKNOWN and returns no mutation claim;
- duplicate consumption preserves BLOCK;
- raw stream, nonce, cursor, consumed set, holdings, keys, and signatures are
  absent;
- coherently resealed PASS, permission, or atomicity promotion is rejected;
- coherently resealed raw-material aliases are rejected;
- wrong expected hashes fail closed;
- a resealed ADR0379 blocked result cannot rebuild an ADR0380 intent;
- repeated builds are deterministic;
- no mount, write, persist, or publish API exists.

## Non-claims

This projection does not read or write runtime state, storage, cache, database,
service, browser, scheduler, market data, or holdings. It proves neither atomic
CAS execution nor durable/linearizable provider behavior. It does not prove
strategy performance, profitability, paper authority, or live authority.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. pointer-v2 remains unchanged
and is not reissued.
