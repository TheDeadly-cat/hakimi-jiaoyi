# ADR 0370: Cluster Exposure Source Receipt Adapter v1

- Status: implemented, additive, inactive
- Date: 2026-08-24
- Scope: exact synthetic in-memory adapter only
- Authority: none; paper and live remain unauthorized

## Context

ADR0369 introduced a source-owned `symbol -> cluster` receipt so proposal
callers cannot choose their own cluster ids. ADR0367 is the intended producer,
but its public preflight deliberately redacts raw symbols and cluster ids and
retains only their hashes. That redaction is correct for a public evidence
surface, but it means the public document alone cannot safely construct the
ADR0369 receipt.

A loose adapter that accepts a second unverified mapping would reopen the exact
boundary the cluster gate is meant to close. The mapping must come from the same
ADR0365 projection verification context that produced the exactly verified
ADR0367 preflight, and it must bind back to ADR0367's occurrence and cluster
hashes.

## Decision

Add an unmounted application adapter with two functions:

- `build_cluster_exposure_source_receipt_v1`
- `evaluate_cluster_exposure_from_verified_batch_v1`

The builder performs the following sequence:

1. Exactly verifies the ADR0367 document against its expected preflight hash,
   ADR0365 projection hash, proposed-symbol occurrences, and projection
   verification context.
2. Requires the original ADR0367 schema, static fingerprint, unmounted status,
   projected-but-immature decision, exact authority lock, and exact neutral
   facts.
3. Reconstructs the source partition only from the verified structural budget
   preregistration inside that same context.
4. Requires every proposal symbol to belong to the projected subset. Excluded
   and unknown symbols produce no receipt.
5. Recomputes occurrence-bound unique-symbol hashes, source-order cluster
   hashes, and all ticket counts and compares them to the ADR0367 document.
6. Emits a canonically sorted, ephemeral receipt whose source fingerprint is
   the exact ADR0367 preflight hash and whose permission is false.

The evaluator derives the ADR0367 proposed-symbol occurrence list directly from
the ADR0369 exposure proposal tuple. The same exact batch document therefore
cannot be reused with reordered, added, removed, or substituted proposals.

## Security and authority properties

1. Proposal rows never contain cluster ids.
2. The adapter accepts no caller-supplied symbol map.
3. Raw symbols and cluster ids exist only in the short-lived Python receipt.
4. The adapter has no serializer, writer, storage, network, HTTP, engine,
   scheduler, pointer, or runtime registration path.
5. Any preflight, projection, context, hash, authority, fact, count, order, or
   evidence mismatch returns `None`.
6. A valid receipt still represents structural research evidence only.
7. ADR0369 always returns `permission=false` and `UNAUTHORIZED`, including
   `WITHIN_PREREGISTERED_LIMIT`.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact current projected fixture | Receipt binds its two symbols to two source clusters |
| Synthetic correlated source partition plus ADR0367 derivation | Shared cluster id and hash binding agree |
| Duplicate proposal occurrences | One receipt mapping, summed exposure |
| Excluded symbol | No receipt |
| Unknown symbol | No receipt |
| Paper-authority tamper | No receipt |
| Wrong expected ADR0367 hash | No receipt |
| Reordered occurrences with original document | No receipt |
| Structural budget context drift | No receipt |
| Invalid exposure policy after valid receipt | ADR0369 `UNKNOWN`, permission false |
| Correlated aggregate over shared cap | ADR0369 `LIMIT_BREACH`, permission false |

## Consumer-first activation order

1. Keep ADR0370 unmounted and pure synthetic.
2. Prove exact fixture conformance across ADR0365, ADR0367, ADR0369, and this
   adapter.
3. Add a separately versioned read-only projection that exposes only hashes,
   counts, neutral blocker codes, and permission false. Do not expose the
   ephemeral raw mapping.
4. Add static UI presentation only after that projection is independently
   verified.
5. Require a future explicit ADR and fresh evidence cycle before any current
   consumer registration. This ADR does not activate one.

## Non-goals

- No market data, historical K-line, G50/G51, blind test, or return backtest.
- No portfolio recommendation, order construction, execution, or profitability
  claim.
- No database, cache, log, key, service, browser, scheduler, publication, paper,
  or live operation.
- No natural-forward artifact-chain change.
- No `current` pointer update or reissue.

## Evidence boundary

Tests may reuse only the existing in-memory ADR0365/ADR0367 synthetic fixture.
The current exact projection fixture contains two projected singleton clusters,
so exact end-to-end adapter verification covers that shape. Correlated A/B
coverage is composed from the existing ADR0367 derivation contract, the
ADR0370 partition and hash-binding layer, and the independent ADR0369 shared
exposure aggregation contract. It is not evidence that a second exact
ADR0365 projection fixture with A/B in one cluster was built or verified.

Passing these tests proves local contract composition only, not market
validity, evidence maturity, profitability, or trading authorization. A fresh
exact correlated-cluster projection fixture remains required before any
consumer activation review.
