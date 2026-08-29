# ADR 0233: Post-registration receipt-v5 issuance preregistration-v1

## Status

Accepted as a blocked, synthetic issuance preregistration.

## Context

Registration-v7 requires a future post-registration execution receipt. The
existing witness candidate-v1 cannot be reused for that receipt because it is
schema-bound to receipt-v3, evidence-v3, and registration-v5. Its detached
Ed25519 signature verifies local key possession, but it explicitly does not
bind a shared anti-replay registry, trusted time, witness organization identity,
or independent execution observation. A challenge nonce can therefore be
signed repeatedly without evidence of globally unique consumption.

Issuing receipt-v5 before freezing nonce consumption would create a replayable
authority-looking artifact. Mutating receipt-v4 is also invalid because its
formal-registration absence is already covered by evidence-v4 and
registration-v7 hashes.

## Decision

Add post-registration execution issuance preregistration-v1. It exactly verifies
the blocked registration-v7 candidate and binds these hash edges:

1. registration-v7;
2. execution evidence-v4;
3. pre-registration receipt-v4;
4. projection-v6;
5. local execution preregistration-v1.

The caller supplies an issuance identifier and only a SHA-256 nonce commitment.
The raw nonce is not accepted or embedded. The preregistration derives a sealed
anti-replay scope from the namespace, registration hash, evidence hash,
pre-registration receipt hash, issuance identifier, commitment, and sequence
number.

The future registry contract is frozen as:

- linearizable consistency;
- atomic `put-if-absent` followed by consume-once;
- one challenge use;
- one receipt issue;
- replay key composed from namespace, registration hash, issuance identifier,
  and nonce commitment;
- a separate anti-replay consumption receipt-v1.

Future receipt-v5, witness policy-v2, challenge-v2, detached attestation-v2,
witness verification-v2, and anti-replay consumption receipt-v1 schema names
are frozen. No implementation of those artifacts is claimed by this ADR.

## Fail-closed boundaries

The preregistration remains `BLOCKED` even when all local hashes are exact.
Its verifier PASS means only that the blocked preregistration was rebuilt
exactly. The following remain blockers:

- witness policy-v2 is not implemented;
- no external anti-replay registry is bound;
- atomic nonce consumption and duplicate rejection are unverified;
- nonce entropy and trusted time are unverified;
- witness identity and independent process observation are unverified;
- receipt-v5 is not issued;
- browser, route, mount, current, and activation remain unauthorized.

`CLEAR`, `TAIL_BLOCK`, and `EXACT_UNKNOWN` evidence states remain distinct and
all produce a blocked preregistration. None is trading or registration
authority.

## Consumer-first order

1. exact blocked registration-v7 candidate;
2. issuance preregistration-v1;
3. witness policy and challenge-v2;
4. external linearizable anti-replay registry;
5. atomic nonce consumption receipt-v1;
6. independent witness attestation-v2;
7. post-registration receipt-v5;
8. Python post-registration receipt evidence;
9. explicit browser review and a separate production activation decision.

## Consequences

- The post-registration path now has a versioned one-use contract before any
  receipt implementation exists.
- Existing receipt-v4, evidence-v4, registration-v7, current artifacts, and
  pointer-v2 remain immutable.
- No key, raw nonce, source document, runtime asset, database, cache, log,
  service, browser, scheduler, market task, or trading path is accessed.
- This preregistration is not profitability evidence and grants no paper/live,
  current, writer, route, mount, registry, migration, or runtime authority.
