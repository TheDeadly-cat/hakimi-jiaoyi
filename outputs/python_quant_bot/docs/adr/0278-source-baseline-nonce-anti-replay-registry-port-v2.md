# ADR0278: Source-Baseline Nonce Anti-Replay Registry Port v2

## Status

Accepted as an unmounted, provider-unbound architecture contract.

## Context

The repository already contains `AntiReplayRegistryPortV1`, identity and signer
trust preregistrations, organization identity evidence contracts, and a
cross-runtime reference model. A second V1-shaped port would duplicate an
existing boundary.

Read-only audit showed that V1 is not actually namespace-parameterized. Its
constructor exposes namespace and target-receipt arguments, but rejects any
namespace other than the preregistered portfolio-risk post-registration value.
A pure gap proof constructed a valid V1 default command and confirmed that the
source-baseline namespace is rejected. No provider was called and no runtime
state was mutated.

The existing reference request also remains explicitly `BLOCKED`: external
registry identity, linearizability, atomic nonce consumption, trusted time, and
target receipt issuance are all unverified.

## Decision

Preserve V1 without modification and add `AntiReplayRegistryPortV2` as a truly
namespace-parameterized successor. Reuse the existing outcome enum:

- `CONSUMED`;
- `DUPLICATE_REJECTED`;
- `CONFLICT_REJECTED`.

V2 replaces portfolio-risk-specific command fields with generic commitments:

- explicit anti-replay namespace and namespace-preregistration hash;
- anti-replay scope hash;
- subject and challenge hashes;
- namespace/scope-bound consumption key;
- policy and request-context hashes;
- actor and evidence hashes;
- explicit target receipt schema and request hash.

The consumption key is the shared strict-canonical hash of
`anti_replay_namespace` and `anti_replay_scope_hash`. Requests are exact sealed
documents; commands are frozen dataclasses built only from exact requests.

V2 results require `CONSUMED` to carry a receipt that binds namespace,
preregistration, request, consumption key, and target schema. Rejected outcomes
cannot carry a receipt. A result is still only a provider result object; it does
not independently prove provider conformance or durable commit.

Add a source-baseline namespace preregistration and a consumer-first request
candidate builder. The builder verifies ADR0277 exactly, rebuilds the ADR0276
reserve request, maps only hash commitments, constructs the V2 request and
command, and remains `BLOCKED` because no external provider or durable receipt
is bound.

## Architecture audit

- Existing V1 port: closed for its fixed portfolio-risk namespace.
- Existing identity/trust preregistrations: present but external records remain
  unobserved or unproven.
- Existing provider implementation: absent from explicit source directories.
- Duplicate boundary avoided: V1 remains unchanged and V2 has distinct generic
  semantics and schema versions.
- Source-baseline provider binding: intentionally absent and fail-closed.

## Adversarial matrix

- V1 source-baseline namespace attempt: rejected;
- V2 preregistered source-baseline namespace: accepted structurally;
- namespace or scope rebinding: different consumption key;
- request-field or request-hash tampering: rejected;
- source adapter or reserve-request tampering: candidate `UNKNOWN`;
- resealed preregistration promotion: candidate `UNKNOWN`;
- structural Protocol match: not provider conformance;
- `CONSUMED` without exactly bound receipt: rejected;
- rejected outcome with receipt: rejected;
- raw public key or signature in candidate: forbidden.

## Consumer-first activation order

1. Keep V1 unchanged and V2 unmounted.
2. Keep source-baseline namespace and request candidate `BLOCKED`.
3. Define an external provider adapter against V2 without runtime activation.
4. Verify provider identity, key governance, and V2 conformance independently.
5. Prove atomic compare-and-consume, linearizability, durable commit, trusted
   revision, and authenticated receipt issuance.
6. Only a later evidence gate may consider progression; HTTP and UI remain
   separate reviews.

## Non-claims

This change does not implement or call a registry provider, access a database,
cache, network, runtime artifact, browser, or scheduler, or issue a consumption
receipt. It does not prove registry identity, provider conformance, atomic or
durable storage, linearizability, reviewer identity, paper/live authority,
market validity, strategy performance, or profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
