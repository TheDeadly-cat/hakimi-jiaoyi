# ADR 0041: Temporal stability report21 and protocol-v10 preregistration

Date: 2026-08-21

## Status

Accepted as a verifier-only consumer and preregistration. Not activated.

## Context

The temporal cluster-stability gate is a complete consumer-only contract, but report20
and protocol-v9 intentionally know only the full-window stability gate. Mutating those
contracts would blur compatibility and could make old artifacts appear to contain
evidence they never carried.

## Decision

Add a report21 extension and protocol-v10 preregistration without modifying report20
or protocol-v9.

The report21 verifier treats the exact report20 extension as its base. For every report
identity it derives the full-window gate from report20 and the complete-link gate plus
preregistration from report20's nested report19 extension. The caller must separately
supply the source uncertainty audit, matrix, selection cells, and expected temporal
gate hash. The verifier requires exact identity sets and reconstructs every temporal
gate before separating contract status from research decision.

Protocol registration-v8 freezes three 20-return windows, one pair-by-window
Bonferroni family, effective-sample and threshold rules, external binding fields,
payload exclusions, and all writer activation prerequisites.

## Consequences

- Report20 remains valid and contains no temporal evidence.
- Report21 entries do not copy source audits, matrices, selection cells, raw returns,
  or completed-price datasets.
- A valid temporal BLOCK remains a valid report21 contract with decision BLOCK.
- Re-sealed identity, hash, native-type, nested-gate, or authority drift fails closed.
- No writer, pointer, current migration, formal registry activation, paper authority,
  live authority, or execution path is introduced.
- Report21 activation requires a separate sole-writer implementation and migration
  audit; this preregistration cannot activate it.
