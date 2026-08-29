# ADR 0390: Registration challenge consumption command binding v1

## Status

Accepted as an isolated application contract. It constructs a command only, is not mounted into current, and never invokes a provider.

## Context

ADR0388 produces exact redacted evidence that signed multi-authority time observations are structurally bound to a signed registration challenge while keeping trusted current time and freshness unproved. ADR0389 defines a specialized consume-once provider port but intentionally accepts primitive command fields. Without an application binding, a caller could substitute the signed-challenge hash, registration nonce, or clock-binding evidence hash before command construction.

## Decision

Add a fail-closed application consumer that:

1. Rebuilds ADR0388 from the complete caller-supplied clock, challenge, key, receipt, and expected-hash inputs.
2. Requires the ADR0388 evidence hash, PASS status, bounded local facts, and all authority values to be exact.
3. Extracts the signed-challenge hash only from the exact ADR0388 source and requires the supplied signed challenge to match it.
4. Extracts the registration-nonce hash only from the exact ADR0387 challenge binding.
5. Calls only the pure ADR0389 command builder with those values plus the caller-supplied expected registry head/revision and request-id hash.
6. Emits a redacted BLOCKED evidence document that proves command construction but states that consume_once was not called and no provider result was observed.

Production code does not invoke the Protocol, generate keys, access files or clocks, use network or storage, mutate runtime state, or create a provider fake.

## Consumer-first activation order

1. Keep ADR0390 isolated and freeze exact evidence-to-command binding.
2. Preregister an external ADR0389 provider identity, implementation, namespace, and signing key.
3. Execute the frozen conformance matrix against that external provider under separate authorization.
4. Verify signed result receipts, duplicate-before-conflict behavior, crash recovery, rollback resistance, durability, and linearizable read-after-write.
5. Only then consider a versioned current consumer change under separate authorization.

## Adversarial matrix

Tests cover clock-binding mutation and expected-hash drift, signed-challenge substitution, registration-nonce substitution, registry head/revision/request binding, bool-as-int and role-hash collisions, evidence mutation, raw-material redaction, determinism, input immutability, expected command-hash drift, and forbidden provider/runtime capabilities.

## Consequences

ADR0390 closes the half-wired application boundary between ADR0388 and ADR0389. It does not consume a challenge or prove provider registration, atomicity, durability, linearizability, freshness, current time, profitability, or trading permission. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
