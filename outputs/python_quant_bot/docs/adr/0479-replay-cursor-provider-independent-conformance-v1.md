# ADR0479: Replay cursor provider independent conformance plan and observer quorum v1

## Status

Accepted as an unmounted, synthetic, research-only conformance evidence contract. It does not call a provider, execute conformance cases, mutate a replay cursor, or authorize current, runtime, paper, live, writer, execution, profitability, or trading activity.

## Context

ADR0478 closes unsigned structural `ADVANCED` result substitution by verifying a domain-separated signature from the provider's preregistered key. Source-reference audit found no downstream consumer beyond the preregistration declaration of the signed-receipt schema. More importantly, a provider key can sign unsupported claims about its own invocation, atomicity, durability, linearizability, rollback resistance, or implementation. A provider signature cannot independently prove provider conformance.

A wrapper that merely relabeled ADR0478 evidence as a cursor candidate would duplicate the same boundary without adding source truth. The next consumer-first step must instead fix the independent conformance protocol before any producer or external adapter is activated.

## Decision

Add two unmounted contracts:

- an exact conformance plan with 19 preregistered `NOT_RUN` cases covering advance acceptance, unsigned-result rejection, command/intent/registry rebinding, cursor CAS and proposed-cursor binding, duplicate ordering, rejected-result non-advance, receipt exactness/signature binding, timeout idempotency, concurrency, linearizable read-after-write, restart recovery, rollback refusal, durable acknowledgement, revision monotonicity, and key rotation/revocation;
- signed observer reports and deterministic 2-of-3 quorum evidence that consume the exact ADR0478 verification evidence.

The plan requires exactly three structurally distinct observer IDs, Ed25519 key hashes, organization-claim hashes, and trust domains. Observer keys must differ from the provider key. These structural checks are not observer identity, independence, governance, or source-trust proof.

Each report binds the plan, provider preregistration, exact ADR0478 evidence, observer, run context, every case status, and per-case evidence hashes. A valid quorum may set only local signature/report-claim facts. Observer identity, key continuity, independence, test-execution source truth, provider endpoint/implementation/conformance, atomicity, durability, linearizability, rollback resistance, restart recovery, and all authority remain false or `BLOCKED`.

## Consumer-first activation order

1. Exact replay-cursor CAS intent, command, and structural result contracts.
2. Provider preregistration, signed registration, and ADR0478 signed receipt.
3. ADR0479 fixed conformance matrix and observer quorum format.
4. Independently authorized observer identity, key-continuity, revocation, and transcript-verification adapters.
5. Authorized external provider endpoint and real concurrency, timeout, restart, durability, linearizability, and rollback tests.
6. Separately reviewed and explicitly authorized current transition.

ADR0479 completes step 3 only. It is not mounted into `current`.

## Adversarial matrix

- provider self-signature with no independent reports: conformance remains false;
- duplicate observer ID, key, organization claim, trust domain, or provider-key reuse: plan rejected;
- missing or reordered case: report rejected;
- failed case, one report, or duplicate signed observer: quorum blocked;
- wrong key, invalid signature, or tampered report: blocked;
- changed ADR0478 evidence: exact upstream verifier blocks the quorum;
- two valid reports plus one invalid report: local 2-of-3 signature quorum may pass;
- reordered valid reports: deterministic evidence is unchanged;
- resealed permission promotion: exact rebuild verifier rejects it;
- valid two-report quorum: local report signatures pass while every external source-truth and permission fact remains blocked.

## Consequences and limits

ADR0479 makes ADR0478 an exact upstream of a preregistered independent-observer protocol and prevents the provider key from serving as its own conformance authority. It does not run the 19 cases, call a provider, verify observers, prove their independence, inspect execution transcripts, establish provider identity or implementation, or prove atomicity, durability, linearizability, rollback resistance, restart recovery, execution, profitability, paper, live, or trading permission.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and is not reissued.
