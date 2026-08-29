# ADR 0008: Redacted Multiplicity Public Ledger

- Status: Accepted for read-only consumer use
- Date: 2026-08-21

## Context

Schema16 can now produce replayable correlation multiplicity evidence, while
schema8 remains a dormant envelope. The strategy lab already explains cluster
independence and pair-level uncertainty, but omitting family-wise adjustment
leaves users unable to distinguish one-pair confidence from a preregistered
cross-cluster family conclusion.

Exposing the raw evidence would leak symbols, pair identities, protocol and
registration hashes, nested audits, and internal blockers. Treating a valid
local decision as readiness would also overstate external validity and trading
authority.

## Decision

- Add `strategy-correlation-multiplicity-public-summary-v1` as an exact-field,
  UNKNOWN-first child contract under the unchanged
  `strategy-lab-research-projection-v1` parent.
- Build the summary only from a verified
  `strategy-correlation-multiplicity-report-evidence-v1` attached to report
  schema16 and protocol-v5.
- Treat a full schema16 formal report as a summary-only source. Its selection,
  dataset, governance, and row payloads are not passed into the legacy
  strategy-lab projector.
- Publish only expected/observed family size, Bonferroni family alpha,
  derived per-pair alpha, aggregate decision, and a bounded gap category.
- Recursively remove raw multiplicity evidence, audits, family assessments,
  symbols, pairs, protocol identities, hashes, and blockers from the public
  payload.
- Render one neutral SOURCE -> GAP -> MATURITY -> PERMISSION ledger after the
  uncertainty ledger. A segmented alpha-budget rail is the only new visual
  signature.
- Keep formal/current report binding, writer/admission, parameter selection,
  performance claims, paper, and live permissions false. No pointer or request
  path changes.

## Consequences

- A verified local PASS is displayed as "no family-wise block observed", not
  READY, profitable, independent in the future, or tradable.
- Invalid, missing, extra-field, type-drifted, or authority-elevated summaries
  render UNKNOWN.
- The natural-forward single-look chain and pointer-v2 remain unchanged.
- Synthetic and isolated evidence remains research-only and does not establish
  external authenticity or profitability.
