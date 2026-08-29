# ADR 0402: Clock Trust Threshold Genesis Admission v1

- Status: Accepted for isolated synthetic research only
- Date: 2026-08-24
- Supersedes: nothing
- Activates current: no

## Context

ADR0401 defines a non-circular offline-root topology and an exact but unexecuted genesis admission plan. It intentionally performs no signature verification. Without a separate verifier, a caller could present an arbitrary root set or promote plan fields without proving possession of the preregistered offline keys.

The verifier must not reintroduce time, replay-registry, runtime-consumer, or installation dependencies into genesis.

## Decision

Add an isolated threshold-signature contract with four artifacts:

1. An exact genesis claim binding the ADR0401 topology hash, plan hash, root-set hash, clock-registration hash, verification-time-source preregistration hash, policy, ceremony, nonce, and expected out-of-band genesis commitment hash.
2. A signed candidate containing canonical Ed25519 DER-SPKI material and detached signatures over the strict-canonical claim hash.
3. Redacted evidence that rebuilds the claim and candidate, verifies every supplied signature, matches each signer to a preregistered root key hash, and requires the configured threshold.
4. A deterministic commitment artifact derived only from exact local-PASS evidence. The artifact remains uninstalled and cannot mutate runtime state.

All supplied signatures must be valid and preregistered. Adding an outsider, substituting a valid key under another root ID, duplicating a signer record, or changing any topology, plan, claim, or expected commitment binding fails closed.

## Consumer-first activation order

1. Keep ADR0401 topology and plan immutable.
2. Produce ADR0402 claim and candidate only in an isolated offline ceremony.
3. Verify configured threshold signatures and derive a redacted commitment.
4. Compare that commitment with an independently configured out-of-band value.
5. Add explicit installation, rollback-protection, and rotation contracts.
6. Only later may clock governance and verification-time trust feed a runtime freshness consumer.
7. Do not switch current, reissue pointer-v2, register a provider, or grant paper/live/writer authority here.

## Adversarial matrix

Fifteen cases cover exact claim binding, valid local threshold, below-threshold signatures, wrong-key self-signatures, outsider signers, signature tampering, duplicated signer records, forged governance promotion, plan mutation and hash drift, topology drift, exact uninstalled commitment, expected-commitment sensitivity, redaction, determinism and input immutability, malformed public keys, and absence of private-key/I/O/system-clock/replay/runtime dependencies.

## Consequences

- Local possession of the configured threshold of root keys can now be demonstrated without circular time or replay dependencies.
- A local PASS does not prove external root identity, governance, organization independence, out-of-band commitment equality, installation, rollback protection, clock governance, verification-time trust, trusted current time, freshness, replay consumption, provider registration, profitability, current activation, paper, live, or writer authority.
- The natural-forward public chain remains audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
- Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 is not reissued.
