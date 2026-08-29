# ADR0414: Witness ownership provider independent conformance plan and observer quorum v1

## Status

Accepted as an unmounted, synthetic, research-only conformance evidence contract. No provider, observer, runtime, current, paper, live, writer, migration, or trading activation is authorized.

## Context

ADR0413 verifies a domain-separated signature by the provider's preregistered key. That closes unsigned receipt substitution, but the provider can still sign unsupported claims about atomicity, durability, linearizability, rollback resistance, or implementation behavior. A provider signature cannot independently prove provider conformance.

The existing anti-replay conformance v2 plan correctly preregisters `NOT_RUN` cases and leaves provider calls, identity, external source trust, and conformance false. ADR0414 preserves that fail-closed distinction while defining ownership-specific cases and a future independent observer evidence format.

## Decision

Add an exact provider conformance plan with 18 required cases covering exact advance, single-use consumption, duplicate ordering, state/revision CAS conflicts, rebinding rejection, receipt exactness, signed receipt binding, timeout idempotency, concurrency, linearizable read-after-write, restart recovery, rollback refusal, durable acknowledgement, revision monotonicity, and provider key rotation/revocation.

The plan preregisters exactly three observer profiles and requires a 2-of-3 signature quorum. Observer IDs, keys, and organization-claim hashes must be structurally unique, and observer keys must differ from the provider key. These structural checks are not observer identity, independence, governance, or source-trust proof.

Each report binds the plan, ADR0413 exact signed-receipt evidence, observer, run context, every case result, and per-case evidence hashes. Observer signatures use a dedicated domain and the shared strict Ed25519 parser.

A valid quorum may set `signed_observer_report_quorum_verified=true` and `all_required_case_results_claimed_by_quorum=true`. It must keep observer identity, key continuity, independence source truth, test-execution source truth, provider endpoint and implementation, external provider conformance, atomic-operation source truth, durability, linearizability, and rollback resistance false. Admission remains `BLOCKED`.

## Consumer-first activation order

1. ADR0412 exact unmounted consumer.
2. ADR0413 provider preregistration and signed receipt.
3. ADR0414 fixed conformance matrix and observer quorum format.
4. Independently authorized observer source adapters, identity anchors, key continuity, revocation, and execution transcript verification.
5. Authorized external provider endpoint and real restart, concurrency, timeout, durability, linearizability, and rollback tests.
6. Separately reviewed current transition.

This ADR completes step 3 only.

## Adversarial matrix

- ADR0413 provider self-signature with no observer evidence: conformance remains false.
- duplicate observer ID, key, organization claim, or provider-key reuse: plan rejected.
- missing/reordered case or invalid case status/evidence hash: report rejected.
- failed case, one report, or duplicate signed observer: quorum blocked.
- wrong key, invalid signature, tampered report, or cross-domain signature: report blocked.
- two valid reports plus one invalid report: local 2-of-3 quorum may pass.
- resealed permission promotion: exact rebuild verifier rejects it.
- valid two-report quorum: local signature/report claims pass while every external source-truth and authority field remains blocked.

## Consequences and limits

ADR0414 prevents a single provider key from serving as its own conformance authority and fixes the future test matrix before producer activation. It does not run tests, call a provider, verify observers, prove independence, inspect transcripts, establish durability or linearizability, activate runtime/current, prove profitability, or authorize paper/live/trading.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and not reissued.
