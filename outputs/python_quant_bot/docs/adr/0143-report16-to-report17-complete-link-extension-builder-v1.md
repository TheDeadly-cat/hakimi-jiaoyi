# ADR 0143: Report16 to report17 complete-link extension builder v1

## Status

Accepted as a non-persistent, non-current research builder on 2026-08-22.

## Context

Report16 multiplicity evidence already has a deterministic builder and strict
verifier. Report17 complete-link evidence had only a verifier; all tests created
the extension by hand. That left no production path proving that a verified
report16 replay could be transformed into the report17 contract without source
or identity drift.

The report16 evidence contains a canonical evidence hash, replayed
preregistration, correlation matrix, selection cells, and strategy identity. It
still requires the caller-supplied source protocol for independent verification.

## Decision

- Add an in-memory builder that verifies report16 evidence against its source
  protocol before extracting any replay data.
- Use the report16 `evidence_hash` as the only report17 base-report hash.
- Recompute the complete-link v2 gate from preregistration, matrix, cells, and
  identity; never copy the legacy gate decision.
- Preserve valid PASS and valid BLOCK evidence.
- Strictly seal the result and run the existing report17 consumer before return.
- Raise `ValueError` for invalid inputs or self-verification failure rather than
  returning an incomplete or UNKNOWN extension.

## Non-activation

The builder performs no filesystem write and does not implement an artifact
writer, delivery envelope, strategy-lab mount, HTTP route, current admission,
paper authority, or live authority. Returned extensions retain all report17
permission locks.

No backtest, market task, service, database, scheduler, or trading task is part
of this decision.

## Validation

- In-memory compilation covers the builder and both affected test modules:
  `3/3 PASS`.
- Real module discovery across report16 research evidence, the report17
  consumer, and the builder is exactly `15` tests; all `15/15 PASS` with zero
  `ResourceWarning` instances. The builder fixture now forwards nested cleanup,
  and the report16 test imports its source fixture as a module so imported
  `TestCase` classes are not collected twice.
- An independent synthetic matrix rejects all `10/10` attacked candidates:
  three invalid source/protocol/replay inputs and seven coherently resealed
  numeric aliases for schema or authority booleans. Accepted attacks: `0`.
- PASS and BLOCK builds are deterministic and retain native false writer,
  current, paper, and live fields. Four explicit activation entrypoints contain
  zero builder references.
- Builder SHA-256:
  `FFDA1459DBA812238A63AA41F471727101F6C4687E62DF4CDA1BF52FC079ECB1`.
  Builder-test SHA-256:
  `419819DF9B595934B3C3C47AEE01E094779BB6940EE4799872C8D4AD62A231DF`.
  Report16 research-test SHA-256:
  `F12C17D7EE617DEE0917B669535BACB6404F26194DEF5A3045FAE4EB405BC4BC`.

This validation is synthetic contract evidence only. It does not change the
natural-forward evidence chain, legacy pack-v5 public UNKNOWN behavior,
pointer-v2, current admission, profitability posture, paper authorization, or
the permanent live lock.
