# ADR 0182: Shadow consumer preregistration v4 readiness-contract pin

- Status: Accepted as blocked preregistration; evidence not bound
- Date: 2026-08-22
- Scope: Static source and contract pins only

## Context

ADR0177 preregistration v3 pins the ADR0176 content-issuance replay contract while
leaving evidence unbound.  Its API and implementation manifest predate ADR0178
through ADR0181.  A synthetic call proved that changing unrelated ADR0181 hashes
does not change the v3 document and that no readiness-v3 schema is bound.

ADR0181 now defines a 14-input application readiness envelope with a signed local
time quorum.  It remains `UNKNOWN / ...EXTERNAL_TRUST_UNPROVEN / DENIED` and is not
an executed shadow consumer.

## Decision

Add preregistration v4 that fully reverifies immutable v3 and pins the current
source chain for:

1. ADR0178 readiness envelope v1.
2. ADR0179 readiness envelope v2.
3. ADR0180 trusted-clock authority v3.
4. ADR0181 readiness envelope v3.
5. ADR0177 shadow preregistration v3.

The v4 API deliberately accepts no readiness-envelope instance and no trusted-clock
attestation.  Therefore it cannot claim that ADR0181 evidence is bound or exactly
verified.

## Preserved blocker accounting

The three local blocker closures from ADR0177 remain byte-for-byte preserved.  V4
does not close a fourth blocker.  It adds a contract capability pin with:

- `contract_pinned=true`
- `evidence_bound=false`
- `consumer_executed=false`
- `external_authority_verified=false`

The preregistration status remains `BLOCKED`.

## New fail-closed blockers

- `readiness_envelope_v3_evidence_not_bound`
- `readiness_envelope_v3_exact_hash_not_verified`
- `signed_time_external_authority_trust_unproven`
- `trusted_clock_nonce_and_replay_durability_unproven`

Existing provider identity, issuance, external registry, runtime consumer, risk
service, review, current-switch, paper, and live blockers remain in force.

## Activation order

ADR0181 evidence must be supplied and fully publicly reverified before an isolated
shadow consumer is implemented.  Durable nonce/replay handling, independent review,
versioned risk-service inputs, and a separately authorized current switch remain
later gates.

## Compatibility and authority

ADR0177 and ADR0181 remain unchanged.  V4 is a new detached preregistration and is
not current.  The natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 remains publicly `UNKNOWN`.  Pointer-v2 fields, hash contract, and
non-reissuance behavior remain unchanged.  No profitability or trading authority
is implied.

## Validation boundary

Validation is limited to synthetic contract tests, predecessor-family tests, an
independent public API matrix, and in-memory compilation.  No runtime, database,
cache, network, service, browser, scheduler, return backtest, formal blind test,
paper task, or live task is used.
