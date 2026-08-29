# ADR 0234: Issuance preregistration Python verification envelope-v1

## Status

Accepted as a sealed, summary-only cross-runtime verification bridge.

## Context

ADR0233 provides a Python public verifier for the blocked post-registration
issuance preregistration. Its verifier result is an in-process return value, not
a sealed document. A future JavaScript witness-v2 consumer cannot independently
distinguish that return value from a caller-created object and should not trust
only a resealed preregistration document.

The JavaScript runtime already supports strict canonical JSON and in-memory
Ed25519. The missing prerequisite is therefore a versioned Python-to-JavaScript
bridge, not a new signature or receipt.

## Decision

Add verification envelope-v1. The Python builder invokes the public issuance
preregistration verifier, independently cross-binds the registration-v7,
evidence-v4, pre-registration receipt-v4, projection-v6, local execution
preregistration-v1, issuance identifier, nonce commitment, and anti-replay scope
hash, then emits a strict-canonical sealed summary.

The envelope also verifies that:

- the underlying preregistration remains `BLOCKED` while locally complete;
- `CLEAR`, `TAIL_BLOCK`, and `EXACT_UNKNOWN` remain distinct;
- all future receipt/witness/consumption schema names are exact;
- anti-replay registry, atomic consumption, duplicate rejection, trusted time,
  witness identity, and receipt issuance remain explicitly false;
- all authority remains locked.

Envelope PASS means only that the blocked preregistration and its hash edges
were exactly verified by the pinned Python contract. It does not authenticate a
Python process, sign a challenge, consume a nonce, or authorize witness-v2.

## Consumer-first order

1. blocked issuance preregistration-v1;
2. sealed Python verification envelope-v1;
3. JavaScript witness policy/challenge-v2 candidate;
4. external linearizable anti-replay registry and consumption receipt;
5. independent witness attestation-v2;
6. post-registration receipt-v5;
7. Python receipt evidence;
8. explicit browser review and separate activation decision.

## Consequences

- witness-v2 can consume one sealed, hash-only Python summary instead of
  trusting an unsealed verifier return value or embedding the full source chain.
- Existing preregistration, registration, evidence, receipt, projection,
  current artifacts, and pointer-v2 remain unchanged.
- No Node process, key, raw nonce, signature, registry, runtime asset, database,
  cache, log, service, browser, scheduler, market task, or trading path is used.
- The envelope is not profitability evidence and grants no issuance, registry,
  route, mount, current, runtime, paper/live, migration, or writer authority.
