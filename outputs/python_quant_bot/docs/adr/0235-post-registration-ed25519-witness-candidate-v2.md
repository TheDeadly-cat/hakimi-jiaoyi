# ADR 0235: Post-registration Ed25519 witness candidate-v2

## Status

Accepted as a blocked, synthetic local key-possession candidate.

## Context

ADR0234 provides the sealed Python-to-Node verification envelope required by a
post-registration witness consumer. The legacy witness-v1 is bound to the old
receipt-v3/evidence-v3/registration-v5 chain and cannot be schema-aliased to the
new issuance preregistration.

Node supports strict-canonical JSON and in-memory Ed25519. A local verifier can
therefore prove that a detached signature matches a preregistered public-key
hash without reading or receiving private-key material. That proof still cannot
show who controls the key, whether the signer independently observed execution,
whether a shared registry consumed the nonce, or when the signature occurred.

## Decision

Add witness candidate-v2 with four contracts:

1. a blocked witness policy-v2 that binds issuance preregistration-v1 and its
   sealed Python verification envelope;
2. a blocked challenge-v2 that verifies the supplied raw nonce against the
   preregistered commitment without embedding the raw nonce;
3. a sealed detached attestation-v2 shape;
4. a blocked verification-v2 that verifies Ed25519 key possession locally.

The production module receives public-key material and a detached signature. It
never receives a private key. Tests generate ephemeral Ed25519 keypairs entirely
in memory and sign outside the production module.

For an exact signature, `local_signature_status` is `PASS`, while the overall
verification status remains `BLOCKED`. A public exact-rebuild verifier may PASS
the blocked verification document; that means only that the local candidate was
reproduced exactly.

Any anti-replay consumption document is rejected until consumption receipt-v1
has its own implementation and exact verifier. The module cannot silently treat
an arbitrary registry-looking object as nonce consumption.

## Remaining blockers

- external linearizable anti-replay registry is unbound;
- atomic nonce consumption and duplicate rejection are unverified;
- trusted signature time is unverified;
- witness organization identity is unverified;
- independent execution observation is unverified;
- post-registration receipt-v5 does not exist;
- browser, route, mount, current, and activation remain unauthorized.

## Consumer-first order

1. issuance preregistration-v1;
2. sealed Python verification envelope-v1;
3. local witness policy/challenge/signature candidate-v2;
4. external anti-replay registry contract and consumption receipt-v1;
5. independently governed witness identity and process observation;
6. post-registration receipt-v5;
7. Python receipt evidence;
8. explicit browser review and separate activation decision.

## Consequences

- The new chain now has a real cross-runtime Ed25519 possession check without
  importing legacy v1 schemas.
- `CLEAR`, `TAIL_BLOCK`, and `EXACT_UNKNOWN` remain distinct and blocked.
- No private key, raw nonce output, registry, runtime asset, database, cache,
  log, service, browser, scheduler, market task, or trading path is used.
- The candidate is not witness identity, anti-replay, profitability, receipt,
  current, runtime, paper/live, route, mount, migration, or writer authority.
