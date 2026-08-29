# ADR 0137: Multiplicity public summary strict equality v1

## Status

Accepted on 2026-08-22.

## Context

The non-current multiplicity consumer chain already contains a protocol v3
registration, report evidence, and redacted public summary. The protocol and
report documents recompute their own canonical hashes before replay comparison;
targeted no-reseal and outer-reseal probes therefore accepted no top-level
boolean aliases and require no production change.

The public summary has no self-hash. Its fixed-value checks and optional
source-bound rebuild comparison used Python ordinary equality, which treats
`False == 0`, `True == 1`, `16 == 16.0`, and `8 == 8.0` as equal.

Pre-fix probes found thirteen accepted aliases in each verification mode:

- Eleven fixed boolean fields, including maturity, permission, and activation
  facts.
- `required_report_schema_version` as `16.0`.
- `required_matrix_report_schema_version` as `8.0`.
- Standalone verification accepted 13 of 13 attacks.
- Source-bound verification accepted 13 of 13 attacks.
- Total accepted: 26 of 26 attacks.

These aliases did not grant trading authority, but a public evidence contract
must not accept non-canonical types.

## Decision

Use `strict_json_contract_equal` for:

- Every fixed public value comparison.
- The optional source-bound final summary rebuild comparison.

Keep the public summary v1 schema, builder output, status vocabulary, gap
categories, `DESCRIPTIVE_ONLY` maturity, `RESEARCH_ONLY` permission, report
versions, and current activation state unchanged.

Add a pure-synthetic contract covering all thirteen aliases in both standalone
and source-bound modes. All 26 attacks must return `BLOCK`; canonical summaries
must remain `PASS` in both modes.

## Consequences

- Public multiplicity summaries are type-strict with and without source binding.
- Protocol registration and report evidence remain unchanged because their hash
  and rebuild chain already blocked the tested aliases.
- This is consumer hardening, not current activation, profitability evidence, or
  paper/live authorization.
- No runtime files, database, cache, logs, services, browser, scheduler, backtest,
  or trading task are involved.
