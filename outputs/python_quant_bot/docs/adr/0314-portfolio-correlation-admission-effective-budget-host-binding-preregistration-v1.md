# ADR 0314: Host-Binding Preregistration v1

Date: 2026-08-24

Status: Accepted as preregistration only

## Context

ADR0313 proves exact synthetic parity between the isolated Python and JavaScript
consumers and produces a hash-only acceptance receipt. That receipt does not
identify how a future host may connect a Python provider, read-only HTTP
projection, static dependency order, isolated stylesheet, or mount slot.

Skipping an explicit host-binding preregistration would allow a future patch to
choose those boundaries while implementing them. That would combine design,
authority, and activation in one change and could bypass the consumer-first
review order.

## Decision

Add schema
portfolio-correlation-admission-effective-budget-host-binding-preregistration-v1.

The preregistration pins ADR0313 and records five candidate boundaries:

1. A Python provider candidate that accepts only the internal exact source chain
   and returns the ADR0311 result schema.
2. A read-only HTTP projection candidate that accepts only the provider result
   and forbids raw source inputs.
3. Five JavaScript assets in strict dependency order.
4. The isolated ADR0307 stylesheet while protecting the existing host
   stylesheet from mutation.
5. A symbolic inspection mount-slot contract with no selector or mount function.

Candidate paths and hashes are evidence, not active bindings. Every import,
provider registration, route, endpoint, script binding, stylesheet link,
runtime loader, selector, and browser review receipt remains null.

## Required acceptance

The future host review must consume:

- ADR0313 parity registration hash
  5870b0bb4729b37a8638600c04fffdfbf45f5240f9c6f613cb3401431bffb394.
- ADR0313 parity matrix hash
  5ca94940147858aff54a658568f61b453e19ee5ff6468d68c6657e8249a74a61.
- Exact acceptance receipt hash
  40c9af419f810b36ee32fd6ed29b1967b6394427d4ad828b3e3374c171593807.
- State-receipts hash
  d62c0582ac3b212897f2c582846ce1bfc2a731e3dc444d1e6dcbda0eebf64380.

The receipt is pinned but not bound or re-executed by ADR0314.

## Candidate JavaScript order

1. strict_canonical_json_v1.js
2. evidence portfolio correlation in-memory delivery v1
3. evidence portfolio correlation bridge v1
4. evidence portfolio correlation inspection consumer v1
5. evidence portfolio correlation parity acceptance v1

Each candidate has a null script binding. The runtime loader is null.

## Stylesheet boundary

The isolated bridge stylesheet is pinned separately. The protected host
stylesheet remains unchanged at hash
ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a,
and mutation authority is false.

## Activation order

1. Verify ADR0313 registration.
2. Verify ADR0313 acceptance receipt.
3. Verify ADR0314 preregistration.
4. Update static asset registration in a separate version.
5. Implement the Python provider binding in a separate version.
6. Implement the read-only HTTP projection in a separate version.
7. Implement JavaScript host loading in a separate version.
8. Run an explicitly authorized browser review before any mount.
9. Consider current only through a separate explicit decision.

## Fail-closed behavior

The exact verifier rejects predecessor drift, acceptance-hash drift, asset
drift, load-order drift, script binding, route injection, selector injection,
active-host-plan changes, authority promotion, extra fields, cycles, and
non-native values, including fully resealed mutations.

## Consequences

The host boundary is now reviewable before implementation, but nothing is
connected. ADR0314 does not import a provider, register an HTTP handler, add a
route, load a script, link CSS, choose a DOM selector, launch a browser, or
mount the interface.

The next version may update the isolated static asset registration only after
consuming ADR0314 exactly. Provider and HTTP implementation remain later
separate versions.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 remains unchanged
and is not automatically reissued. Synthetic contract evidence is not
profitability evidence and grants no trading permission.
