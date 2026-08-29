# ADR 0142: Temporal report21 lockboard exact public shape v1

## Status

Accepted for the unmounted report21 lockboard candidate on 2026-08-22.

## Context

The report21 consumer and candidate-binding public projection are already
source-bound and type-strict. Synthetic backend matrices rejected all thirteen
report-extension root aliases and all twenty-three public boolean aliases in
each candidate state.

The lockboard checked required values but did not reject additional public or
nested keys. Four adversarial examples carrying an extension hash, strategy
identity, binding facts, or report hash retained observed/candidate state. The
renderer did not reflect those values, but retaining maturity contradicted the
summary's redaction contract.

## Decision

- Define exact root and section field sets for migration and candidate-binding
  summaries in the lockboard classifier.
- Reject extra keys at the root, source, gap, maturity, permission, or redaction
  levels before interpreting any maturity state.
- Preserve a valid migration report when only candidate binding is invalid, but
  degrade the binding rail to `UNKNOWN`.
- Add direct Node contracts for candidate-bound PASS/BLOCK, candidate blocked,
  unknown, not supplied, decision mismatch, native aliases, extra private keys,
  and untrusted rendering.

## Non-activation

The lockboard remains unmounted and side-effect free. No report21 writer,
strategy-lab projection, HTTP route, current activation, paper authority, or
live authority is created by this ADR.

No browser, service, backtest, database, scheduler, or trading task is required
for this static contract hardening.
