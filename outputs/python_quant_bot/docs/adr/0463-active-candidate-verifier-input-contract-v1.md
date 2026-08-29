# ADR 0463: Active candidate verifier input contract v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Active registry verification and activation request validation

## Context

The active registry verifier used `dict()` and `int()` coercion on externally
parsed values. Four synthetic inputs escaped the fail-closed path as uncaught
`ValueError`: a non-object registry, a nonnumeric activation timestamp, a
non-object clock attestation, and a non-object experiment completion receipt.

The activation producer used the same coercions and could fail before returning
a structured result.

## Decision

Introduce `active-candidate-verifier-input-v1`:

1. Registry, clock attestation, and completion receipt must be objects.
2. Activation and attested timestamps must be native, non-boolean positive
   integers.
3. Invalid verifier input returns a structured research-only `BLOCK` and never
   raises to the caller.
4. Invalid activation requests are blocked before registry creation.
5. Valid `active-portfolio-candidate-v3` verification semantics remain
   unchanged and expose the input-contract version in diagnostic output.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Non-object registry | Structured BLOCK |
| Nonnumeric or boolean activation timestamp | BLOCK |
| Non-object clock attestation | BLOCK |
| Non-object completion receipt | BLOCK |
| Valid v3 registry | PASS with input-contract version |
| Invalid producer request | BLOCK and no registry file |

## Boundaries

- Tests use synthetic objects and isolated temporary files only.
- No user registry, formal candidate, or runtime artifact is read or changed.
- No market task, backtest, service, browser, scheduler, runtime database, paper
  order, or live order is started.
- Active research remains research-only; paper/live remain unauthorized.
