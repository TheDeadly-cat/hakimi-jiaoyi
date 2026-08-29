# ADR 0139: Report-18 strata strict contract and public projection v1

## Status

Accepted as a non-current, consumer-first research contract on 2026-08-22.

## Context

The report-18 strata consumer already verifies the complete-link source, the
preregistered strata gate, the registry asset, and externally supplied registry
and classification-source bindings. Two downstream gaps remained:

1. A purely synthetic reseal matrix showed that five of nine `bool`/`int` or
   `int`/`float` fixed-contract aliases were accepted after recomputing the
   extension hash.
2. The verified extension contains identities, hashes, classification-source
   values, registry assets, nested gates, and decision blockers. The existing
   strata public projection describes protocol/registry migration and cannot be
   used as a report-18 summary.

## Decision

- Compare every report-18 fixed-contract value with strict JSON type equality.
- Add a source-bound report-18 public projection that first calls the existing
  consumer verifier and otherwise returns `UNKNOWN`.
- Preserve complete-link, strata, and registry-binding gap classes using only
  aggregate counts.
- Expose classification-source binding verification as a maturity fact without
  exposing source values or hashes.
- Rebuild the entire public summary with strict JSON equality.

## Activation order

1. Consumer verifier and adversarial contract.
2. Redacted non-current public projection.
3. A future source-bound report-18 writer/envelope.
4. Only then reconsider strategy-lab, HTTP, or UI mounting.

This ADR does not authorize step 3 or step 4. It does not change the natural
forward chain, current writers, pointer-v2, paper trading, or live trading.

## Adversarial matrix

- Canonical report-18 PASS/BLOCK evidence remains descriptive research data.
- All nine fixed-contract alias attacks must fail, with or without resealing.
- Every public `bool`/`int` and `int`/`float` alias must fail exact rebuild.
- PASS, BLOCK, and UNKNOWN projections must omit identities, hashes, registry
  assets, classification-source values, nested gates, and blocker details.

No backtest, market task, service, database, scheduler, writer, or trading path
is part of this decision.
