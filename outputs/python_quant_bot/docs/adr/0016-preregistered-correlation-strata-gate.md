# ADR 0016: Preregistered correlation strata gate

## Status

Accepted as a consumer-first research contract. No formal writer, current
pointer activation, paper authority, or live authority is created.

## Gap

Complete-link gate-v2 validates every internal pair inside each registered
cluster. It does not constrain how clusters are assigned to a higher-level
asset family, sector, region, or common risk factor.

A pure synthetic call proved the gap. Two singleton clusters with low
cross-correlation and PASS selection cells produced a 2-of-2 PASS in gate-v2,
even when an external parent-stratum declaration assigned both clusters to one
maximum-one-vote risk layer. The declaration was not an input to the gate and
therefore could not affect the decision.

## Decision

Add strategy-correlation-preregistered-strata-registration-v1 and
strategy-correlation-preregistered-strata-gate-v1.

Every registered dimension must partition every source cluster exactly once.
Each stratum contributes at most one vote and passes only when every member
cluster passes. Every dimension must satisfy both a minimum of two independent
passing strata and a fixed 60 percent passing-strata fraction. Any blocking
dimension blocks the overall strata gate.

The registration binds the verified source preregistration hash. The gate binds
the strict canonical hashes of the registration and complete-link gate-v2.
Verification rebuilds the complete document exactly. Recursive authority fields
remain native false.

Gate construction and gate verification both require the original source
preregistration as an explicit input. They independently rebuild the strata
registration before counting votes, so a re-sealed partition cannot duplicate a
passing cluster, omit another cluster, or manufacture independent strata.

## Activation order

1. Land the consumer, exact verifier, synthetic adversarial tests, and lean
   registration.
2. Define and fingerprint the formal hierarchy registry asset.
3. Add a future report-schema consumer that requires independent verification
   of both gate-v2 and the strata gate.
4. Add a formal writer only after the registry and report schema are frozen.
5. Consider current activation only through a separate review and migration.

## Consequences

The gate can block apparently diversified clusters that share a preregistered
parent risk layer. This is intentional and descriptive. It is not profitability
evidence and grants no paper or live trading authority.
