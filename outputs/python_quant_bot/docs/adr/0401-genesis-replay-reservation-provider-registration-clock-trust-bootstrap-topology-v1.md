# ADR 0401: Genesis Replay Reservation Provider Clock Trust Bootstrap Topology v1

- Status: Accepted for isolated synthetic research only
- Date: 2026-08-24
- Supersedes: nothing
- Activates current: no

## Context

ADR0400 binds signed clock observations to the exact ADR0399 registration handoff, but its verification_time_ms remains caller supplied. Asking that same runtime clock chain to authorize its own registration or to register the replay provider would recreate the original challenge, freshness, and replay dependency indefinitely.

A finite bootstrap therefore needs an explicit genesis exception whose trust roots are configured out of band and whose local contract does not depend on current time, a replay registry, ADR0400, or any runtime consumer.

## Decision

Add an isolated non-circular topology with three independently scoped commitments:

1. An exact trusted_clock_authority_v3 registration and its registered operational key hashes.
2. A preregistered independent verification-time source identity, key hash, implementation claim, trust domain, and monotonic epoch namespace.
3. At least three offline governance roots with a threshold of at least two, distinct authority IDs, key IDs, organization claims, and key hashes.

Offline root keys must not overlap any operational clock key or verification-time-source key. The topology publishes an acyclic dependency graph in which the offline roots, clock registration, and verification-time source feed a future genesis admission; only that admission may feed a runtime clock-binding consumer. Reverse edges are explicitly forbidden.

ADR0401 also emits an exact admission plan bound to distinct ceremony and nonce hashes. The plan is deliberately unexecuted and contains no signature verification or runtime mutation.

## Consumer-first activation order

1. Preregister static commitments and key separation in ADR0401.
2. Add a separate threshold-signed genesis admission verifier.
3. Require out-of-band root identity and organization-independence evidence.
4. Require monotonic verification-time evidence and rollback protection.
5. Only then may a future consumer evaluate trusted current time and freshness.
6. Do not switch current, reissue pointer-v2, register a provider, or grant paper/live/writer authority here.

## Adversarial matrix

Fourteen cases cover exact blocked preregistration, acyclic topology, unexecuted plan, tampered clock registration, expected-hash drift, wrong clock key, duplicate root identities/keys/organization claims, operational-key overlap, verification-time-key overlap, boolean and out-of-range thresholds, preregistration drift and extra fields, ceremony/nonce aliasing, topology mutation, verifier reconstruction, deterministic redaction, input immutability, and absence of private-key/I/O/system-clock/runtime/consumer imports.

## Consequences

- The recursive bootstrap problem is represented explicitly instead of being hidden behind another registration challenge.
- Local topology validity does not establish external root identity, member independence, root signatures, clock governance, verification-time trust, trusted current time, freshness, replay consumption, provider registration, external conformance, profitability, current activation, paper, live, or writer authority.
- The natural-forward public chain remains audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
- Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 is not reissued.
