# ADR 0102: Provider identity assertion replay adapter registration v1

## Status

Accepted as an inactive, research-only candidate contract. It is not wired into
`current`, the natural-forward evidence chain, admission, paper, or live paths.

## Context

ADR 0100 verifies a strict provider identity assertion signature and declared
registry membership while intentionally leaving external trust, checkpoint
time, and replay state unproven. ADR 0101 presents those gaps without authority.

Existing replay services cannot close this gap. `EventReplayService` rebuilds
persisted paper-order evidence, while selection and calibration replay recompute
research outcomes from frozen inputs. No layered module provides an append-only
external provider-identity assertion log. Reuse would merge trust boundaries.

## Decision

Add the sealed candidate schema
`strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-adapter-registration-candidate-v1`.
It preregisters registry and adapter identities, implementation SHA-256,
digest/signature encodings, append-only inclusion and consistency protocols,
exact hash domains, empty-tree genesis, and three separate public-key roles.

Extra fields fail closed. Provider receipt signing, identity registry trust,
and replay registry trust key IDs and public-key hashes must be pairwise distinct.
No private key, credential, runtime state, database, cache, or network source is
accepted.

The highest state is `REPLAY_ADAPTER_REGISTERED_RECEIPT_UNOBSERVED`. It means
only that a candidate consumer contract is sealed. Replay registry checked,
checkpoint signature, inclusion, consistency, external trust/time, provider
identity, admission, selection, paper, and live claims remain false.

The static fingerprint is
`20260926-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-adapter-registration-1`.

## Consumer-first activation order

1. Land and adversarially test this inactive registration consumer contract.
2. Add a separate verifier consuming the registration, a signed checkpoint, an
   assertion inclusion proof, and consistency from a pinned prior checkpoint.
3. Add a producer only after malformed, equivocal, stale, rollback, split-view,
   and key-role-reuse fixtures fail closed.
4. Wire ADR 0100 only after independent external trust, time, and checkpoint
   history evidence exists.
5. Add presentation and `current` integration under a separate decision.

## Adversarial matrix

Synthetic tests cover shape, hashes, IDs, protocols, encodings, domains,
genesis, all key-role collisions, tampering, mutable input, deterministic
sealing, and UNKNOWN authority leakage.

## Consequences

This closes only preregistration design. Receipt production and verification,
external trust/time, replay status, profitability, and trading authorization
remain unresolved.
