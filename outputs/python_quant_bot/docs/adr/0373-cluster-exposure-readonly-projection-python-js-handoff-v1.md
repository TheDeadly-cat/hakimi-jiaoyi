# ADR 0373: Cluster Exposure Python-to-JavaScript Handoff v1

- Status: implemented, additive, unmounted
- Date: 2026-08-24
- Scope: exact in-memory interface bridge
- Authority: none; paper and live remain unauthorized

## Context

ADR0372 deliberately treats its JavaScript verification envelope as a trust
handoff rather than claiming to recompute the ADR0371 cryptographic hash. A
caller could otherwise forge the exact-status string and matching hash strings
without ever invoking the Python verifier.

The missing bridge must be small, deterministic, and impossible to use as a
compatibility bypass. It must derive the envelope only after recomputing the
complete ADR0371 verified-batch chain.

## Decision

Add the interface module:

`strategy_correlation_cluster_exposure_readonly_projection_handoff_v1`

The builder accepts the ADR0371 projection plus every authoritative input needed
by the ADR0371 exact verifier. It returns the four-field ADR0372 envelope only
when exact verification succeeds:

1. `schema_version`
2. `verification_status`
3. `expected_readonly_projection_hash`
4. `projection`

The projection is copied through strict JSON encoding and decoding with NaN and
non-serializable values rejected. The returned object does not alias the source
projection.

The exact handoff verifier rebuilds the envelope from the full upstream chain
and compares the complete mapping. It does not trust a supplied verification
status.

## Invariants

1. ADR0371 exact verification must succeed against ADR0367, ADR0369, ADR0370,
   policy, proposal occurrence order, projection hash, and verification context.
2. The expected ADR0371 hash is lowercase SHA-256.
3. The envelope has exactly the four fields expected by ADR0372.
4. The verification status is emitted only by this exact builder.
5. Projection copying is JSON-safe, deterministic, and non-aliasing.
6. No raw receipt, symbol, or cluster map is introduced by the bridge.
7. Wrong hash, resealed authority promotion, upstream drift, or envelope mutation
   fails closed.
8. Production code has no file, network, Node, subprocess, route, runtime,
   pointer, storage, or DOM operation.
9. The bridge remains unmounted and cannot grant authority.

## Cross-language conformance

The targeted test passes the in-memory Python envelope to the actual ADR0372
Node presenter through standard input. No temporary file is created. It covers:

- within-limit observation;
- shared-cluster limit breach through duplicate proposal occurrences;
- unknown policy with hidden metrics.

Node acceptance proves schema interoperability only. It does not mount a DOM or
prove browser rendering.

## Consumer-first activation order

1. Keep ADR0373 callable only from synthetic tests.
2. Independently verify ADR0367 through ADR0373 composition.
3. Define an explicit read-only delivery boundary that can invoke ADR0373 but
   cannot serialize raw receipts or set verification status itself.
4. Add a separate static-mount ADR only after that boundary is proven.
5. Require fresh projected evidence and explicit authorization before any
   current consumer registration. This ADR performs no registration.

## Non-goals

- No HTTP route, file writer, artifact reader, engine, runtime, browser, DOM,
  scheduler, pointer, publication, paper, or live operation.
- No market data, historical K-line, G50/G51, blind test, or return backtest.
- No order, strategy recommendation, profitability, or readiness claim.
- No natural-forward chain change.

## Evidence boundary

Python and Node tests prove exact envelope construction, mutation resistance,
JSON interoperability, and presenter acceptance only. They do not prove market
validity, rendered UI, evidence maturity, profitability, or trading authority.
