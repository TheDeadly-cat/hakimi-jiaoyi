# ADR0385: Replay Cursor Provider Identity and Capability Preregistration v1

## Status

Accepted as an unmounted, synthetic, fail-closed preregistration and external
conformance plan.

## Context

ADR0384 defines a provider port but intentionally supplies no production
provider. Before any implementation can be considered, consumers need an exact
identity, key-hash, implementation-claim, capability, schema, and external-test
commitment that cannot be supplied after results are known.

The existing generic anti-replay identity preregistration remains bound to its
own compare-and-consume namespace and schemas. ADR0385 follows its governance
pattern without aliasing that unrelated port.

## Decision

Add two sealed documents:

- replay-cursor provider identity and capability preregistration;
- eleven-case external provider conformance plan.

The preregistration binds registry id, operator identity claim, Ed25519 public
key SPKI hash, trust domain, provider implementation claim hash, ADR0384 port
schema, ADR0380 implementation, strict canonical implementation, required
capabilities, and a future signed-receipt schema.

Exact local verification returns `status=PASS` only for document equality. The
preregistration and plan remain operationally `BLOCKED`. Provider identity, key
possession, implementation authenticity, external conformance, atomicity,
durability, linearizability, registration, writer permission, paper authority,
and live authority remain false.

The conformance plan preregisters first advance, duplicate, stale-base conflict,
same/different-intent parallel collisions, timeout retry, restart recovery,
rollback resistance, receipt substitution, key rotation, and linearizable
read-after-write. Every case requires an external provider and independent
observer and is marked unexecuted.

## Consumer-first activation order

1. Keep preregistration and plan unmounted and BLOCKED.
2. Define an authenticated provider-registration receipt signed by the
   preregistered key.
3. Bind independent observer identity and trusted test orchestration.
4. Execute the frozen conformance plan only against an explicitly authorized
   temporary provider.
5. Verify durability, restart, rollback, timeout, and linearizable-read evidence.
6. Review current/HTTP activation independently; legacy structural results
   remain non-promotable.

## Adversarial matrix

- identity or implementation-claim drift changes the preregistration hash;
- malformed identity, hash, or cross-port protocol alias is rejected;
- tampering and coherently resealed schema aliases fail exact rebuild;
- requirements and conformance cases are unique and frozen;
- an exact plan grants no authority and executes no case;
- plan case tampering returns UNKNOWN/BLOCK;
- ADR0384, ADR0380, and strict-canonical source pins must remain exact;
- production contract has no provider invocation, I/O, network, route, storage,
  or current-pointer operation.

## Non-claims

No endpoint, private key, secret, provider, external runtime, network, storage,
database, cache, service, browser, scheduler, market data, or holdings are
accessed. This work does not prove provider identity, key control, atomicity,
durability, linearizability, real holdings, strategy performance, profitability,
paper authority, or live authority.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. pointer-v2 remains unchanged
and is not reissued.
