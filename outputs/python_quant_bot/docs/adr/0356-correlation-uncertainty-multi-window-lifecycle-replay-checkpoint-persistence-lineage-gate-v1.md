# ADR 0356: Multi-window lifecycle-replay checkpoint persistence lineage gate v1

- Status: Accepted as an unmounted synthetic research lineage candidate
- Date: 2026-08-24

## Context

ADR0355 exactly binds one persisted asset to a verified ADR0352 common-view
evaluation but deliberately leaves `persisted_checkpoint_lineage_verified=false`.
Its asset's `previous_persisted_asset_hash` is either null or only an opaque
hash. A Merkle consistency proof is not a persisted-asset lineage proof unless
the pinned tree content is connected to a registered anchor or a fully
reverified previous persisted asset.

ADR0107 provides the relevant two-mode lineage pattern under the provider-
identity domain. ADR0356 applies that pattern to strict ADR0355 segments.

## Decision

Add ADR0356 as a pure one-segment lineage gate. Each segment contains an exact
ADR0355 gate plus all source and persistence inputs required to rerun its public
verifier. Caller-provided verification booleans are not accepted.

ADR0356 supports two modes:

- `REGISTERED_SOURCE_PIN`: no previous segment is supplied, the current asset
  must have a null previous-asset hash, and its current checkpoint must grow
  strictly from the previous root/tree/hash already preregistered by ADR0352.
- `PREVIOUS_PERSISTED_ASSET`: both ADR0355 segments are reverified, the current
  asset's previous hash must equal the previous asset hash, the current pinned
  root/tree must equal the previous current root/tree, and tree size and asset
  creation time must increase strictly.

Previous-asset mode also requires stable study/window identity, lifecycle
receipt hashes, replay-registry identity/key, occurrence-auditor identity/key,
and persistence-provider identity/key/namespace across both segments.

The current ADR0355 `BLOCK` is preserved after lineage verification. Outputs
contain only hashes, mode, counts, and tree sizes, not segment bundles, assets,
keys, signatures, or proofs.

## Claim calibration

A local anchor `PASS` proves one asset is connected to its preregistered source
pin. A local previous-asset `PASS` proves one exact adjacent persisted-asset
content segment with strict tree growth.

Neither mode proves external provider authority, actual I/O, real durability,
authoritative pinning, the anchor's external truth, ancestry before the one
verified segment, complete history, longitudinal coverage, split-view absence,
global uniqueness, future replay absence, content-issuance replay,
profitability, or trading authorization.

## Consumer-first activation order

1. Keep ADR0356 synthetic and unmounted.
2. Accumulate at least three contiguous ADR0356 segments under a preregistered
   bounded tree-size window.
3. Require no missing tree-size step, stable identities, unique hashes, and
   strictly increasing observation times.
4. Add independent provider trust, durable publication, rollback, and split-
   view observation.
5. Bind ADR0176 content-issuance replay before any ADR0346 consumer successor.
6. Require explicit current migration and never auto-reissue pointer-v2.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact asset connected to preregistered source pin | local `PASS` |
| Exact tree-size 3 to 4 previous-asset segment | local `PASS` |
| Segment shape or ADR0355 verification drift | `UNKNOWN` |
| Anchor mode with non-null previous asset | `UNKNOWN` |
| Previous asset hash mismatch | `UNKNOWN` |
| Previous root/tree mismatch or non-growth | `UNKNOWN` |
| Registry, auditor, provider, study, window, or receipt drift | `UNKNOWN` |
| Current ADR0355 is validly blocked | preserve `BLOCK` |
| Resealed authority promotion | verification failure |
| Raw segment, asset, key, signature, or proof in output | rejected |

## Boundary

Validation uses only synthetic in-memory keys, signatures, Merkle proofs,
assets, receipts, and source bundles. This ADR performs no I/O and changes no
existing service, report, writer, server, engine, CLI, frontend, current
pointer, natural-forward artifact, legacy pack-v5 behavior, or pointer-v2
contract. It starts no historical-data task, backtest, service, browser,
scheduler, database, cache, log, broker, paper, or live path.
