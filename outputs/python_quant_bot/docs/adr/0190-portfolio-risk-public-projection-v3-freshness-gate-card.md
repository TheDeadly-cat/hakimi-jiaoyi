# ADR 0190: Portfolio-risk public projection v3 and freshness-gate card

## Status

Accepted as a detached, unmounted, research-only presentation contract. It is
not `current` and grants no runtime, paper, live, registry, writer, migration,
or shadow-consumer authority.

## Context

ADR0189 closes the local policy gap between portfolio-risk/temporal stability
and completed-session freshness. Its rich verification context is not suitable
for public presentation, and its `status` represents a local policy decision,
not whether a public projection is structurally valid.

## Decision

Add `strategy-correlation-cluster-portfolio-risk-projection-v3`. The projection
invokes the public adapter-v3 exact verifier and emits only hashes, local state,
blockers/warnings, four neutral stages, minimal facts, and locked authority.

Projection validity and local policy maturity remain distinct:

1. An exact adapter-v3 `BLOCK` produces projection `PASS` with a declared `GAP`
   and `LOCAL_POLICY_BLOCKED` maturity.
2. An invalid or tampered adapter-v3 produces projection `BLOCK`, `UNKNOWN`
   source/gap/maturity, and `UNAUTHORIZED` permission.
3. Permission is always `UNAUTHORIZED`, including exact local policy `PASS` and
   the verified risk-reduction exemption.

The stage order is frozen as `SOURCE -> GAP -> MATURITY -> PERMISSION`. No
`READY`, profitability, execution, or authorization wording is permitted.

## Presentation

Add an unmounted `portfolio-risk-freshness-gate-card-v3` consumer. It requires
exact top-level and nested shapes, version/fingerprint pins, strict scalar types,
four-stage order, maturity/decision consistency, summary-only facts, valid hash
shapes, and all authority locks. Any drift renders `UNKNOWN` while permission
remains `UNAUTHORIZED`.

The visual direction is a warm research ledger rather than a generic status
dashboard: paper texture, rust/ochre/teal evidence rail, editorial serif titles,
monospace evidence labels, staged reveal, responsive 4/2/1-column layouts,
reduced-motion handling, and forced-colors support.

## Consumer-first activation order

1. Keep projection-v3 and card-v3 detached.
2. Prove Python projection and Node presentation contracts independently.
3. Pin both artifacts in a later versioned shadow-consumer preregistration.
4. Perform browser visual QA only with explicit authorization.
5. Consider mounting or `current` migration only through a separate decision.

## Adversarial matrix

Contracts cover fresh local pass, stale risk-increase gap, stale risk-reduction
exemption, base-budget block, source tamper, projection tamper, extra fields,
stage reorder, authority promotion, scalar aliases, hash-shape drift, maturity
mismatch, permission promotion, HTML escaping, no-readiness wording, summary
redaction, non-mutation, and Python-to-Node projection consumption.

## Compatibility and evidence boundaries

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 fields and hash contract
are unchanged and no pointer is reissued. No runtime assets, market tasks,
backtests, services, browsers, schedulers, or trading paths are used.
