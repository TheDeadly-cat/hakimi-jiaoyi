# ADR 0138: Complete-link report public projection v1

## Status

Accepted on 2026-08-22.

## Context

The report-17 complete-link extension already has a strict, verifier-only
consumer. A valid extension carries the aggregate PASS or BLOCK decision, but it
also contains report hashes, strategy and lane identities, preregistration,
correlation matrices, selection cells, and raw complete-link gates.

A pure-synthetic verified PASS extension exposed nine representative private
markers: `extension_hash`, `base_report_hash`, `strategy_id`, `variant_id`,
`RAW_EXCESS`, `correlation_matrix`, `selection_cells`, `gate_v2`, and
`complete_link_audit`. No report-specific redacted projection existed. The older
complete-link migration projection describes protocol-registration availability;
it does not project report-17 decision evidence.

## Decision

Add a source-bound, verifier-backed public summary with schema
`strategy-correlation-complete-link-report-public-summary-v1`.

The summary exposes only:

- SOURCE: verified report-extension and version status.
- GAP: aggregate PASS/BLOCK decision plus registry, writer, and current gaps.
- MATURITY: consumer evidence status while writer and current remain unavailable.
- PERMISSION: fixed research-only, descriptive, non-authoritative values.
- REDACTION: explicit false exposure flags for hashes, identities, matrix, cells,
  raw gate, and decision blockers.

Invalid or mismatched source evidence projects `UNKNOWN`. Both valid PASS and
valid BLOCK decisions remain descriptive evidence. Verification strictly rebuilds
the summary from the source extension and expected base report hash.

## Consumer-first activation order

1. Keep the existing report-17 extension verifier as source authority.
2. Add this non-current redacted projection.
3. Add a strategy-lab wrapper only after a report-17 writer/envelope supplies a
   source-bound extension without weakening the external base-hash contract.
4. Do not switch current, issue a writer, or bind a formal registry in this ADR.

## Consequences

- A verified report-17 decision can be presented without exposing raw research
  identities or artifacts.
- No report writer, persistence path, route, polling loop, or current activation
  is added.
- PASS is not profitability evidence or paper/live authorization.
- Validation remains pure synthetic and in memory; runtime files, database,
  cache, logs, services, browser, scheduler, backtest, and trading tasks remain
  untouched.
