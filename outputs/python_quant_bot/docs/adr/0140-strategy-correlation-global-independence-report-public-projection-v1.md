# ADR 0140: Report-19 global-independence public projection v1

## Status

Accepted as a non-current, consumer-first research contract on 2026-08-22.

## Context

The report-19 consumer already verifies report-18 strata evidence, external
registry and classification-source bindings, and the global-independence gate.
A synthetic matrix confirmed that all ten top-level `bool`/`int` and
`int`/`float` aliases are rejected after resealing. The consumer does not need
rewriting.

The verified extension is not a public document. It exposes identities, hashes,
base strata evidence, source registrations, registry assets, nested gates,
decision blockers, and graph-level audit details. No report-specific redacted
projection existed.

## Decision

- Add a source-bound report-19 public projection that first calls the existing
  consumer verifier and otherwise returns `UNKNOWN`.
- Distinguish inherited complete-link, preregistered-strata, registry-binding,
  and report-19 global-independence gaps using aggregate counts only.
- Exclude inherited gate failures from the global-independence count so one root
  cause is not presented as two independent gaps.
- Preserve registry and classification-source verification as maturity facts,
  without exposing source values, hashes, assets, or identities.
- Verify the full public summary with strict JSON type equality.

## Activation order

1. Existing report-19 consumer and adversarial contract.
2. Redacted non-current public projection.
3. A future source-bound report-19 writer/envelope.
4. Only then reconsider strategy-lab, HTTP, or UI mounting.

This ADR authorizes only step 2. It does not alter the natural-forward chain,
current writers, pointer-v2, paper trading, or live trading.

## Adversarial matrix

- Canonical PASS and valid BLOCK evidence remain descriptive research data.
- Invalid external hashes, bindings, source types, or nested evidence project
  `UNKNOWN`.
- Every public `bool`/`int` and `int`/`float` alias fails exact rebuild.
- PASS, BLOCK, and UNKNOWN omit identities, hashes, registry assets, source
  registrations, nested gates, blocker details, and graph structure.

No backtest, market task, service, database, scheduler, writer, or trading path
is part of this decision.
