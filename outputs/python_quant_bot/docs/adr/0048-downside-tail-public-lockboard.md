# ADR 0048: Downside-tail public projection and unmounted lockboard

## Status

Redacted public projection and optional lockboard implemented. The component is not mounted.

## Projection

The public summary is rebuilt only from an exact downside-tail binding assessment and its verified protocol, evaluation, consumer receipt, source registration, and externally pinned hashes.

It exposes SOURCE, GAP, MATURITY, PERMISSION, and four aggregate counts only. It removes protocol, registration, evaluation, consumer, assessment, identity-set, and stratum-assignment hashes; observation ids; returns; pair identities; strata; overlap values; p-values; and profitability metrics.

Public states are NOT_SUPPLIED, UNKNOWN, CANDIDATE_BLOCKED, observed PASS, and observed BLOCK. A valid observed BLOCK remains visible. Invalid supplied input becomes generic UNKNOWN and untrusted text is not reflected.

## Visual direction

The lockboard uses the existing archive-paper language with a stronger tail-risk seal circuit. Moss marks a candidate gate clear, vermilion marks a visible blocker, amber marks non-formal candidate maturity, and graphite marks unknown or locked state. Motion is limited to a staggered circuit reveal and is disabled for reduced-motion users.

The renderer is target-scoped, uses textContent/createElement, has no ambient document dependency, and performs no automatic mount. Responsive contracts cover desktop, tablet, and narrow mobile widths.

## Authority

The words and state model never claim profitability, execution, readiness, or activation. Independence proof, vote counting, formal binding, registry activation, current admission, writers, paper, and live remain false or locked.

## Next boundary

Formal registry/persistence and any main-app mount remain separate migrations requiring explicit review. This public component does not switch current state or reissue evidence.
