# ADR 0311: Portfolio Correlation Hash Envelope Source Consumer v1

Date: 2026-08-24

Status: Accepted as an isolated, host-unbound implementation

## Context

ADR0309 registers the exact dual-runtime delivery adapters. ADR0310
preregisters the Python hash-only source consumer before any host binding.

The ADR0306 Python adapter remains directly callable. Its public builder accepts
the complete correlation binding source chain but does not accept or verify an
ADR0309 adapter registration or ADR0310 consumer preregistration. That is
correct for an isolated adapter, but it leaves a missing enforcement point for
the future host path.

## Synthetic gap proof

A pure synthetic, in-memory call demonstrated the gap:

1. Build the existing exact synthetic correlation binding.
2. Mutate and reseal ADR0310 by injecting an unauthorized implementation
   binding.
3. Confirm the ADR0310 verifier rejects that preregistration.
4. Call ADR0306 directly with the same synthetic binding.
5. Confirm ADR0306 still returns an exact, verifiable envelope and does not
   mutate the input.

The observed synthetic envelope hash was
939f3215036c0eb1599f168b63a7b938374110b39ba5c5b0bc0f24437458d485.
This is gap evidence only. It is not market, runtime, profitability, or trading
evidence.

## Decision

Add an isolated Python consumer with result schema
portfolio-correlation-admission-effective-budget-hash-envelope-source-consumer-result-v1.

Before invoking ADR0306, the consumer verifies:

1. The exact ADR0309 adapter registration.
2. The exact ADR0310 consumer preregistration.
3. The exact Python consumer subcontract.
4. That the preregistered consumer remains implementation-, provider-, route-,
   writer-, and host-unbound.

If any gate fails, ADR0306 is not called. The consumer returns a sealed BLOCKED
result with no envelope or source hashes.

If all gates pass, the consumer calls the existing ADR0306 builder in memory and
then verifies the returned envelope against the complete source chain. An
unverified candidate is discarded. A verified KNOWN or UNKNOWN envelope is
returned with only its source hashes and envelope hash.

## Exact contract pins

- ADR0309 adapter registration hash:
  4c6eb60d842611d2babaf072527fe93d2a68f67bc6a7c2658b80fd1b9f07f4cb
- ADR0310 consumer preregistration hash:
  4cc6352fb4083d8589d656481ecfd8fe3a33d6bba44bac6383ce2ca1f6d72987
- ADR0310 Python consumer contract hash:
  fd402270f5c03c5225201f9df8768859b398cc1912658a0880f367ff7afc882a
- ADR0310 authority hash:
  0e657c14f87546c71ec1454c7e86fe044a597e704ddb4813d6ce46f5e6f406a6
- ADR0310 host-plan hash:
  639a93033c80d2f49629889d82051b32a57b46ddde727429345864818123768f

## Result boundary

The sealed result contains:

- Exact required contract hashes.
- Four gate booleans.
- The verified ADR0306 envelope or null.
- Binding, admission, effective-budget, and presentation-payload hashes only.
- In-memory transport facts.
- Explicit blockers and false authority.

It does not embed the binding inputs, positions, proposed symbol, raw
correlations, prices, bars, account identity, runtime state, or credentials.

## Fail-closed behavior

The exact verifier rebuilds the consumer result from the complete in-memory
source chain and supplied gate documents. It rejects non-native, cyclic,
extra-field, gate-drifted, envelope-drifted, authority-promoted, and fully
resealed mutations.

A canonical BLOCKED result can be verified against the same invalid gate
documents. That receipt does not become valid against exact gate documents.

## Consequences

The Python consumer implementation now exists as a pure isolated function, but
it is not registered as a provider and is not imported by a host. ADR0310
remains unchanged and host-unbound. The next consumer-first step is a separate
JavaScript consumer implementation and cross-runtime parity review, not a
route, endpoint, browser mount, or current activation.

This decision creates no network, storage, database, cache, environment,
scheduler, provider, route, endpoint, host import, browser execution, DOM mount,
current activation, paper authority, live authority, or writer capability.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 remains unchanged
and is not automatically reissued. Synthetic contract evidence is not
profitability evidence and grants no trading permission.
