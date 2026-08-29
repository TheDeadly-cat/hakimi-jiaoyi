# ADR0426: Witness ownership snapshot storage persistence admission presentation v1

## Status

Accepted as an unmounted, synthetic-contract-only implementation. It is not
registered with a route, loaded by the current UI, connected to a backend, or
authorized for paper/live activity.

## Context

ADR0425 reduced the complete local harness lineage to a persistence admission
decision. The strongest valid result is still only a structural candidate for
a future explicitly authorized isolated backend test. Six independent gaps
remain open and the decision is `DO_NOT_MOUNT`.

Presenting the ADR0425 document directly would duplicate policy in a UI
consumer and expose a much larger internal structure than the UI needs. A
bounded projection and a pure consumer are required before any host integration
can be considered.

## Decision

Add a Python presentation projection with the fixed order:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

The projection:

- exact-verifies the ADR0425 decision and its full lineage evaluation;
- exposes only four source hashes, blocker and component counts, blocker codes,
  maturity facts, and locked authority;
- maps invalid inputs to a sealed `UNMOUNTED_UNKNOWN` projection;
- never maps structural completeness to isolated-test authorization;
- keeps mount, writer, current, paper, and live authority false;
- does not embed source documents, component hash maps, keys, signatures, or
  runtime locators.

Add an unmounted JavaScript view-model consumer. The consumer requires the
expected presentation hash as an out-of-band argument, verifies the sealed
projection and exact schema shape, applies bounded plain-JSON inspection, and
maps all invalid inputs to an `UNKNOWN` model with permission blocked.

## Consumer-first activation order

1. Keep the Python projection and JavaScript view model unmounted.
2. Obtain independent review of projection redaction and hash commitment
   handling.
3. Preregister a presentation consumer and its exact source commitment.
4. Preregister any asset and host-route integration without activating it.
5. Require explicit authorization and separate evidence before isolated host
   execution.
6. Do not switch current through this contract. Current activation needs a
   separate decision and remains blocked here.

## Adversarial contract

The targeted contracts cover:

- source decision tampering and expected-hash substitution;
- resealed authority promotion;
- extra-field injection and non-echo of injected values;
- cycles, accessors, custom prototypes, oversized strings, and malformed
  canonical inputs;
- exact stage order and six-gap preservation;
- no DOM, network, storage, service, or runtime operation;
- neutral wording and locked current, writer, paper, and live authority.

## Consequences

This closes the presentation boundary without changing protected UI assets.
It does not verify real identity source truth, external observer identity, real
adapter execution, isolated-domain confinement, external persistence, or an
explicit isolated-test authorization. It changes no natural-forward artifact,
legacy compatibility behavior, pointer contract, current selection, or trading
permission.
