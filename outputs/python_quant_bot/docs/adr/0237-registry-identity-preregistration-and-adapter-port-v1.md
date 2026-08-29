# ADR 0237: Registry identity preregistration and adapter port-v1

## Status

Accepted as a blocked identity preregistration and unimplemented external port.

## Context

ADR0236 defines deterministic anti-replay request and reference-transition
semantics. Its branch-local model deliberately cannot prove durable atomicity or
shared linearizability. The next architecture boundary is an external registry
port whose identity and conformance requirements are fixed before any adapter,
endpoint, credential, or target receipt is introduced.

Putting a mutable implementation in `application` or `static` would duplicate
the infrastructure boundary and risk presenting process-local behavior as an
external guarantee. A runtime-checkable Python Protocol can constrain command
and result shapes, but structural protocol matching alone is not conformance,
identity, durability, or execution evidence.

## Decision

Add two layers:

1. `interfaces/anti_replay_registry.py` defines immutable, versioned
   compare-and-consume command/result values, exact outcomes, a strict
   Node-request parser, and `AntiReplayRegistryPortV1`;
2. `application/anti_replay_registry_identity_preregistration_v1.py` seals an
   Ed25519 public-key hash, registry id, operator claim, trust domain, protocol,
   source schemas, and required capabilities before any adapter exists.

The application contract also preregisters ten external conformance cases:
first consumption, exact retry, same-scope conflict, parallel collision,
timeout-after-commit retry, restart durability, rollback resistance, receipt
substitution, unregistered key or rotation, and trusted-time monotonicity. Every
case requires an external runtime and independent observer and starts unexecuted.

An exact preregistration or plan verifier may PASS only exact reconstruction of
a still-BLOCKED document. It cannot verify registry key possession, operator
identity, adapter behavior, linearizability, trusted time, receipt signature, or
receipt issuance.

## Consumer-first order

1. blocked witness-v2 and anti-replay request/reference model-v1;
2. registry identity preregistration and adapter port-v1;
3. registry Ed25519 challenge and local key-possession verification;
4. separately authorized external adapter implementation;
5. independently observed execution of the sealed conformance plan;
6. signed target consumption receipt-v1 with trusted registry time;
7. independent witness identity/process evidence and receipt-v5;
8. explicit browser review and separate activation decision.

## Consequences

- Backend architecture now has an explicit interface boundary without an
  infrastructure implementation or endpoint coupling.
- Node consumption requests cross into immutable Python commands without raw
  nonce, signature, public-key material, private key, endpoint, or credential.
- Synthetic objects may satisfy the Protocol and return typed outcomes, but they
  contain no self-asserted fields for external linearizability or identity.
- Existing domain contracts, server, HTTP, static witness, reference model,
  current artifacts, pointer-v2, and natural-forward evidence remain unchanged.
- No external adapter, filesystem state, runtime asset, database, cache, log,
  network, service, browser, scheduler, market task, or trading path is used.
- The preregistration and plan are not identity, conformance, linearizability,
  atomicity, profitability, receipt, current, runtime, paper/live, route, mount,
  migration, or writer authority.
