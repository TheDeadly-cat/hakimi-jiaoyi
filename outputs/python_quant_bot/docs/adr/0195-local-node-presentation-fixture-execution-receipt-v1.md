# ADR 0195: Local Node presentation fixture execution receipt v1

## Status

Accepted as local deterministic, synthetic process evidence only. It is not an
authenticated process attestation, signed receipt, independent review, DOM or
browser result, registration activation, mount authorization, or trading proof.

## Context

ADR0194 preregistration-v7 pins the fixture and registration contracts but keeps
fixture execution evidence unbound. ADR0192 tests fixture composition, yet a
test result alone is not a portable, minimized evidence document. A cross-runtime
receipt is needed without importing Node execution into production Python or
embedding projection, descriptor, or markup payloads.

## Decision

Add a Node-only fixture execution receipt builder. It accepts projection-v3 and
an observed fixture descriptor, rebuilds the descriptor through the pinned
fixture, requires exact canonical equality, verifies unmounted facts and locked
authority, and emits only hashes and state summaries. A public Node verifier
requires exact receipt reconstruction.

Add a Python evidence envelope that accepts only the Node receipt and expected
projection hash. It strictly verifies exact keys and scalar types, pinned
projection/card/fixture hashes, four-stage order, all Node checks, canonical
SHA-256, local-only facts, and authority locks. Python never starts Node and
never accepts projection, descriptor, or markup instances.

## Trust boundary

A Python envelope `PASS` means only that a deterministic local Node receipt was
canonically valid and bound to the expected projection hash. Both layers state:

1. Node process identity is unauthenticated.
2. The receipt is unsigned.
3. External execution authority is unverified.
4. Independent review was not performed.
5. DOM and browser visual review were not performed.
6. Runtime, registration, mount, paper, and live authority remain false.

## Adversarial matrix

Contracts cover fresh, stale risk increase, stale risk reduction, descriptor
tamper, projection authority tamper, extra fields, scalar aliases, exact Node
receipt rebuild, Node/Python canonical-hash equality, projection-hash
cross-splice, receipt-hash tamper, deterministic non-mutation, raw-payload
redaction, implementation pins, process/signature trust denial, import/API
boundaries, neutral wording, and permanent permission locks.

## Compatibility and evidence boundaries

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 fields and hash contract
are unchanged and no pointer is reissued. No runtime assets, market tasks,
backtests, services, browsers, schedulers, or trading paths are used.
