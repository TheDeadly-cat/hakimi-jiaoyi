# ADR 0141: Report-20 cluster-stability public projection v1

## Status

Accepted as a non-current, consumer-first research contract on 2026-08-22.

## Context

The report-20 consumer already verifies the report-19 hash, registry bindings,
external stability bindings, stability-gate hashes, gate replay, research-only
authority, and the full extension through strict canonical reconstruction. A
synthetic reseal matrix confirmed that all twelve top-level `bool`/`int` and
`int`/`float` aliases are rejected. The consumer does not need rewriting.

The verified extension is not public evidence. It contains identities, hashes,
the complete report-19 extension, uncertainty audits, correlation matrices,
selection cells, stability gates, decision blockers, and effective-sample
diagnostics. No report-specific redacted projection existed.

## Decision

- Add a source-bound report-20 public projection that first calls the existing
  verifier and otherwise returns `UNKNOWN`.
- Use verifier-produced gate counts rather than recomputing stability outcomes.
- Distinguish inherited report-19 blocking from a new cluster-stability block.
- State that the external report-19 hash and stability bindings were verified,
  without copying hashes or binding payloads.
- Verify the entire public summary with strict JSON type equality.

## Activation order

1. Existing report-20 consumer and adversarial contract.
2. Redacted non-current public projection.
3. A future source-bound report-20 writer/envelope.
4. Only then reconsider strategy-lab, HTTP, or UI mounting.

Formal-persistence candidates remain a later layer and do not satisfy step 3.
This ADR authorizes only step 2. It does not alter the natural-forward chain,
current writers, pointer-v2, paper trading, or live trading.

## Adversarial matrix

- Canonical stability PASS and low-effective-sample BLOCK remain descriptive.
- Invalid report-19 hashes, stability bindings, source types, or nested gates
  project `UNKNOWN`.
- Every public `bool`/`int` and `int`/`float` alias fails exact rebuild.
- PASS, BLOCK, and UNKNOWN omit identities, hashes, base extensions, uncertainty
  audits, matrices, selection cells, gates, blockers, and diagnostics.

No backtest, market task, service, database, scheduler, writer, or trading path
is part of this decision.
