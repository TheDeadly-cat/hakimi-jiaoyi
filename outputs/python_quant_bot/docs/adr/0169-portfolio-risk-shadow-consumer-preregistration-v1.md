# ADR 0169: Portfolio-risk shadow consumer preregistration v1

## Status

Accepted as an immutable BLOCKED preregistration on 2026-08-22. This version
cannot be activated by changing caller-supplied flags. A successor version is
required after its fixed blockers are closed.

## Context

The existing portfolio-shadow-risk-v1 service accepts a candidate, a backtest
report, one correlation matrix, and hypothetical equity. It does not consume
the ADR0168 dual-source receipt, complete-link audit, ADR0166 adapter, or ADR0167
projection. It is therefore a legacy shadow boundary, not a partially wired
consumer for the new correlation-cluster risk chain.

The repository already contains provider identity, key lifecycle, replay and
freshness, dataset content attestation, and common-support calendar/provider
composition contracts. Creating another signing or identity stack would
duplicate authority boundaries. The existing dataset attestation is also
deliberately narrower than the new need: it binds common-support composition
content, but does not bind the independently rebuilt legacy portfolio matrix
hash to the attested completed-price input.

## Decision

Add a hash-pinned preregistration that:

1. Pins legacy portfolio risk, legacy shadow, adapter v1, projection v1,
   dual-source receipt v1, risk service, dataset attestation, and calendar
   provider composition implementations.
2. Reuses existing provider identity, key lifecycle, attestation, and calendar
   contracts rather than creating parallel stacks.
3. Records a new narrow legacy-matrix derivation binding as the first missing
   capability.
4. Fixes consumer-first activation order from derivation binding through
   authenticated identity, native cutoff manifest, freshness, isolated shadow
   consumer, independent review, risk-service versioning, and a separate
   current-switch decision.
5. Remains BLOCKED even when all current implementation hashes match.

## Fixed blockers

- Existing shadow service is not adapter-v1 aware.
- Legacy matrix derivation is not bound to attested completed-price input.
- Provider dataset-key control and external data issuance remain unproven.
- Provider replay registry has not been checked.
- Native cutoff observation manifest is missing.
- Shadow freshness policy is missing.
- Versioned application shadow consumer is missing.
- Risk-service adapter input contract is not versioned.
- Independent shadow review is missing.
- Current switch is unauthorized.

## Consequences

The project now has an explicit answer to whether the old shadow service can
consume the new dual-gate risk chain: it cannot. Future work can close one
versioned blocker at a time without modifying this preregistration or duplicating
provider governance. No runtime route, HTTP endpoint, UI mount, current switch,
backtest, profitability evidence, paper authority, or live authority is added.

The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2.
