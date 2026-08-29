# ADR0480: Replay cursor provider conformance transcript binding v1

## Status

Accepted as an unmounted, synthetic, research-only transcript-binding contract. It does not retrieve transcript artifacts, run conformance cases, call a provider, mutate a replay cursor, or authorize current, runtime, paper, live, writer, execution, profitability, or trading activity.

## Context

ADR0479 fixes a 19-case independent-observer plan and verifies a local 2-of-3 signature quorum. Its observer reports sign per-case `evidence_hash` values, but those values previously had no required transcript schema. A pure synthetic proof showed that hashes of arbitrary labels could populate all 19 rows and still form a local `PASS` quorum while execution source truth correctly remained false.

Adding another signature would not close this gap because ADR0479 already signs the report. The missing contract is a canonical preimage for each signed case evidence hash.

## Decision

Add one unmounted binding contract with three deterministic layers:

- a case transcript evidence hash that commits to case ID/status, report run context, runner implementation hash, environment manifest hash, transcript artifact hash, command/result trace hashes, stdout/stderr hashes, and positive attempt count;
- one exact transcript manifest per passing observer, containing all 19 cases in preregistered order and requiring every computed case hash to equal the corresponding hash in the signed ADR0479 report;
- aggregate binding evidence requiring an exact ADR0479 quorum and an exact manifest for every passing observer.

The observer's existing ADR0479 signature commits to the report, the report commits to each case evidence hash, and ADR0480 fixes each hash's complete transcript descriptor preimage. No second signature or duplicate authority boundary is introduced.

Manifests contain hashes only. They do not embed raw transcripts, commands, results, stdout, stderr, credentials, runtime state, or provider data.

## Consumer-first activation order

1. ADR0478 exact signed provider receipt.
2. ADR0479 fixed conformance plan and signed observer quorum.
3. ADR0480 exact signed-report to transcript-manifest binding.
4. Independently authorized artifact retrieval, content verification, runner/environment provenance, observer identity/independence, and execution source adapters.
5. Authorized external provider endpoint and real concurrency, timeout, restart, durability, linearizability, and rollback tests.
6. Separately reviewed and explicitly authorized current transition.

ADR0480 completes step 3 only. It is not mounted into `current`.

## Adversarial matrix

- arbitrary label hashes from the pre-ADR0480 report fixture: cannot build a manifest;
- changed run context, runner, environment, artifact, command/result trace, stdout, or stderr hash: changes the case evidence hash;
- missing, reordered, or modified case descriptor: manifest rejected;
- wrong signed report hash: rejected;
- missing, duplicate, or non-passing observer manifest: aggregate binding blocked;
- changed ADR0479 quorum: exact upstream verifier blocks binding;
- resealed manifest or aggregate permission promotion: exact rebuild verifiers reject it;
- reversed manifest order: deterministic binding evidence is unchanged;
- complete manifests for every passing observer: local structural binding passes while artifact retrieval, execution source truth, provider conformance, and all authority remain blocked.

## Consequences and limits

ADR0480 closes arbitrary case-hash substitution by defining and enforcing the signed hash preimage. It does not show that any referenced artifact exists, is retrievable, contains the claimed trace, came from the claimed runner/environment, or records a real provider invocation. It does not verify observer identity/independence, test execution, provider conformance, atomicity, durability, linearizability, rollback resistance, restart recovery, execution, profitability, paper, live, or trading permission.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and is not reissued.
