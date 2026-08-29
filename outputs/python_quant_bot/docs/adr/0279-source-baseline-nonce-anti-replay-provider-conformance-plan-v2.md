# ADR0279: Source-Baseline Anti-Replay Provider Conformance Plan v2

## Status

Accepted as an unmounted, provider-unbound preregistration contract.

## Context

ADR0278 introduced a namespace-parameterized anti-replay registry PortV2. The
repository already has V1 registry identity, organization identity intake, and
signer source-trust preregistrations. Those contracts should be reused as exact
source evidence instead of creating a parallel identity system.

The existing identity builder rejects
`anti-replay-compare-and-consume-port-v2` as a protocol alias. Its V1 adapter
conformance plan therefore cannot be relabeled as V2. A pure synthetic gap proof
confirmed the rejection with zero provider calls and zero runtime mutations.

The public V1 exact verifiers return `status=PASS` for exact documents, while
keeping `registry_identity_verified=false` and
`external_source_trust_verified=false`. `PASS` means exact rebuild only.

## Decision

Add two versioned V2 application documents:

- a source-baseline provider identity binding;
- a provider conformance plan.

The identity binding exact-verifies the existing namespace, V1 registry identity,
organization identity intake, and signer source-trust preregistrations. It binds
only their hashes and hashed claims to the PortV2 namespace. It explicitly records
that the source protocol is V1, the target protocol is V2, and the V1 conformance
plan does not apply to V2.

The binding remains `BLOCKED` and `CLAIM_BOUND_UNAUTHENTICATED`. It does not
promote exact source verification into registry identity, organization identity,
external source trust, signer-role identity, key governance, or provider
conformance.

The conformance plan preregisters fourteen required external cases:

1. exact request acceptance;
2. namespace rebinding rejection;
3. scope rebinding rejection;
4. consumption-key rebinding rejection;
5. duplicate rejection;
6. compare-and-consume conflict;
7. consumed receipt binding;
8. receipt-schema alias rejection;
9. registry-revision monotonicity;
10. concurrent same-key single consumer;
11. restart replay retention;
12. durable commit acknowledgement;
13. identity key rotation and revocation;
14. trusted registry revision source.

Every case is `required=true`, `execution_status=NOT_RUN`, and has no evidence
hash. The plan is `BLOCKED`, embeds no provider endpoint or credentials, and
performs no provider call.

## Consumer-first activation order

1. Keep identity binding and plan import-only and unmounted.
2. Implement an external provider adapter separately against PortV2.
3. Bind authenticated provider identity and source-trust records.
4. Run the fourteen cases only in an explicitly authorized isolated environment.
5. Verify durable and linearizable semantics independently from structural
   Protocol matching.
6. Require authenticated consumption receipts before any later progression gate.
7. Review HTTP and neutral UI projection separately.

## Adversarial matrix

- V2 protocol alias through the V1 builder: rejected;
- exact V1 identity/source-trust documents: source binding only;
- namespace, identity, intake, or source-trust substitution: binding `UNKNOWN`;
- resealed identity/conformance promotion: exact verification failure;
- duplicate or missing conformance case: exact verification failure;
- raw operator claim, registry ID, trust domain, endpoint, credential, or private
  key in public documents: forbidden;
- structural PortV2 match without external cases: still unverified.

## Non-claims

This contract does not implement, bind, or call a provider; access a network,
database, cache, runtime artifact, browser, or scheduler; execute conformance
cases; or issue a consumption receipt. It does not prove provider identity,
source trust, key governance, atomicity, durability, linearizability, HTTP/UI
activation, paper/live authority, market validity, strategy performance, or
profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
