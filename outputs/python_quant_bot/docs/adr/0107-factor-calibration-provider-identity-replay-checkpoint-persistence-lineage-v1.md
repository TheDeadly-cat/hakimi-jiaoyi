# ADR 0107: Persisted replay checkpoint lineage segment v1

## Status

Accepted as an inactive research-only lineage consumer. It performs no I/O and
does not activate a provider, authoritative pin, `current`, paper, or live path.

## Context

ADR 0106 binds a persisted current asset to its ADR 0103 replay evaluation, but
the asset's `previous_pinned_asset_hash` remains an opaque hash. A consistency
proof is meaningful only if the pinned tree size and root correspond to the
content of the previous persisted checkpoint or the registered genesis.

## Decision

Add a single-segment lineage verifier with two exact modes:

- `REGISTERED_GENESIS`: no previous segment is accepted, the current asset must
  have a null previous hash, and ADR 0103 must pin native tree size zero and the
  preregistered genesis root.
- `PREVIOUS_PERSISTED_ASSET`: both ADR 0106 bindings are reverified; the current
  previous hash must equal the previous asset hash, pinned tree size/root must
  equal previous checkpoint content, registry and registration lineage must
  match, and tree size must increase strictly.

The highest state is
`GENESIS_OR_PREVIOUS_PERSISTED_CHECKPOINT_CONTENT_BOUND_EXTERNAL_TRUST_AND_DURABILITY_UNPROVEN`.
A previous-asset segment does not prove the previous segment's own ancestry, so
complete history remains false. Genesis mode proves only local history from the
preregistered candidate genesis.

The static fingerprint is
`20261001-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-lineage-1`.

## Authority boundary

Authoritative pin, durable write/reopen, complete history, replay registry
checked, replay absence, uniqueness, identity, admission, selection, paper, and
live authority remain false.

## Consequences

This closes one adjacent content lineage segment without claiming external
durability, trust, freshness, uniqueness, profitability, or trading permission.
## Validation evidence (2026-10-01)

- Targeted lineage contract: 25/25 PASS.
- Independent public-API double-checkpoint chain: 24/24 PASS across registered genesis, previous persisted asset content, and eight adversarial drift classes.
- Cross-lag factor calibration family: 811/811 PASS across 42 modules.
- In-memory syntax compilation: 2/2 PASS for the service and its targeted contract.
- Lean validation registration: 19 checks listed; dry-run planned 19, executed 0, runtime mutations false, paper authorization false, live order permission false.
- Explicit active-source reference audit: 0 references. The contract remains consumer-inactive.

The strongest verified state remains `GENESIS_OR_PREVIOUS_PERSISTED_CHECKPOINT_CONTENT_BOUND_EXTERNAL_TRUST_AND_DURABILITY_UNPROVEN`. These checks do not prove complete history, assertion uniqueness, replay absence, external registry trust, external durability, external time, profitability, or trading authority.
