# ADR 0106: Replay evaluation to persisted checkpoint binding v1

## Status

Accepted as an inactive research-only composition candidate. It performs no I/O
and does not activate a provider, durable pin, `current`, paper, or live path.

## Context

ADR 0103 verifies replay checkpoint signature, inclusion, and consistency. ADR
0105 verifies signed write/reopen receipts for a sealed checkpoint asset. ADR
0105 deliberately treats the source replay-verifier receipt hash as opaque, so
the persisted asset is not yet proven to represent the verified ADR 0103 result.

## Decision

Add a composition verifier that reruns both underlying verifiers from exact input
bundles and then binds:

- the identical ADR 0102 registration and registration receipt lineage;
- the asset source hash to the verified ADR 0103 evaluation receipt hash;
- replay registry ID and namespace;
- checkpoint tree size, root hash, and checkpoint hash;
- persistence asset hash and previous-asset hash;
- ADR 0104 persistence registration receipt lineage.

No caller-provided verification boolean is accepted. Input bundle fields are
exact and extra compatibility fields fail closed.

The highest state is
`REPLAY_EVALUATION_AND_PERSISTED_ASSET_BOUND_EXTERNAL_TRUST_AND_DURABILITY_UNPROVEN`.
It closes the opaque source hash only. It does not prove previous persisted-pin
content, external registry trust, external persistence-provider trust, storage
durability, external time, uniqueness, or replay absence.

The static fingerprint is
`20260930-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-binding-1`.

## Authority boundary

Authoritative pin, durable write/reopen, replay registry checked, replay absence,
uniqueness, identity, admission, selection, paper, and live authority remain
false.

## Consequences

This composition makes the persisted current checkpoint cryptographically
traceable to ADR 0103 while keeping external and trading claims fail closed.

## Validation

- Targeted composition tests: 26/26.
- Independent real ADR0103-to-ADR0105 chain: 16/16.
- Factor-calibration family: 786/786.
- In-memory compile: 2/2.
- Lean list/dry-run: planned 19, executed 0, runtime mutations false.
- Active integration references: 0.

These checks close the opaque current-checkpoint source hash only. Previous pin
content, external trust, durability, time, uniqueness, replay absence,
profitability, and trading authorization remain unproven.