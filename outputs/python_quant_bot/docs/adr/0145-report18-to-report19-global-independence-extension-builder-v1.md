# ADR 0145: Report18 to report19 global-independence builder v1

## Status

Accepted as a non-persistent, non-current research builder on 2026-08-22.

## Context

Report19 already had a strict consumer, protocol registration, and aggregate
public projection. It had no production builder. Tests and the downstream
report20 fixture manually copied 19 root fields and eight fields per identity,
then independently duplicated global-independence gate and blocker logic.

A pure synthetic chain using the report18 builder proved both required states:
singleton strata produce report19 PASS, while a three-dimension conflict ring
still passes report18 but reduces exact independent capacity to one and blocks
report19. No new market statistic or external source is required.

## Decision

- Add a deterministic in-memory report18-to-report19 builder.
- Require the expected base-report hash and the same external registry bindings
  needed to independently verify report18.
- Rebuild every global-independence gate from the exact report18 registration,
  complete-link gate, strata gate, and source preregistration.
- Match report18 identities exactly, emit canonical identity order, preserve
  inherited report18 BLOCK, and add global-independence blockers monotonically.
- Strictly seal report19 and run the existing report19 consumer before return.
- Raise `ValueError` for invalid report18 evidence, expected bindings, hashes,
  containers, gate rebuilds, or self-verification failures.

## Non-activation

The builder adds no external input schema, registry claim, threshold, writer,
delivery envelope, persistence, route, UI mount, scheduler, pointer mutation,
paper authority, or live authority. It consumes only already required report18
verification context and computes the frozen exact graph policy.

## Acceptance criteria

- Deterministic singleton PASS and three-dimension conflict-ring BLOCK.
- Monotone inherited strata and registry-binding BLOCK preservation.
- Exact source identity, base hash, expected binding, gate, and native JSON type
  enforcement.
- Input immutability and native false writer/current/paper/live fields.
- Zero references from existing activation entrypoints.

No backtest, market task, service, database, browser, scheduler, writer, or
trading task is part of this decision.

## Validation

- Affected report18-builder, report19-consumer, and report19-builder contracts:
  `18/18 PASS` with exact class discovery.
- In-memory compilation: `2/2 PASS`; `ResourceWarning`: `0`.
- Independent public-API matrix: `19` attacked candidates, `19` rejected,
  `0` accepted. It covers report18/hash/binding/container drift, ten coherently
  resealed fixed-value aliases, nested graph-audit resealing, and a resealed
  BLOCK-to-PASS decision upgrade.
- Singleton PASS, report18-PASS conflict-ring BLOCK, and inherited registry-
  binding BLOCK were deterministic. Inputs were unchanged. File and socket
  access were denied during valid builder calls; external I/O attempts were `0`.
- Four explicit activation entrypoints contain zero references.
- Builder SHA-256:
  `FDA3C9370B83251E43B4FAEDC25CD40AE0DB9AAF9A6DDE21145090C6AC38BB0E`.
  Builder-test SHA-256:
  `BD56043BFAA0175085E0410D7965EEB160294AB1DB76AC88DFA5350ABB25A7EA`.
  Existing report19-consumer SHA-256 remains
  `5F703B1ED25AC786A700AC257C76412D6A011CA7887AB47DF7E589A36267A6E5`.

These are synthetic graph-contract receipts, not market observations,
profitability evidence, current admission, or paper/live authorization.
