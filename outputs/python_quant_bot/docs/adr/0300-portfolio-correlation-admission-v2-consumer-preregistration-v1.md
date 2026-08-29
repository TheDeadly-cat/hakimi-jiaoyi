# ADR 0300: Portfolio correlation admission v2 consumer preregistration v1

## Status

Accepted as an additive, hash-only, consumer-first preregistration and binding
candidate. Delivery, presentation, host, route, current, paper, and live remain
unregistered or unauthorized.

## Context

ADR0299 closes the proven cross-universe splice gap with
`portfolio-correlation-admission-v2`. The producer is exact and synthetic, but
no consumer contract pins its implementation, test, ADR, v1 dependency, or
exact verifier. Directly adding a presentation or host import would skip the
consumer-first boundary declared by ADR0299.

## Decision

Add `portfolio-correlation-admission-v2-consumer-preregistration-v1`. The
registration pins:

- the v2 schema, static fingerprint, implementation SHA-256, contract-test
  SHA-256, ADR0299 SHA-256, candidate hash field, and exact verifier name;
- the unchanged v1 schema and implementation SHA-256;
- accepted exact v2 candidate statuses `PASS` and `BLOCK`; and
- an explicit pure in-memory hash-only binding mode.

The registration leaves delivery adapter, presentation consumer, application
importer, HTML mount, and route fields null.

Add `portfolio-correlation-admission-v2-consumer-binding-v1`. The binding takes
one native-JSON snapshot of the registration, v2 candidate, all producer source
documents, and identity arguments. It exact-verifies the registration and then
rebuilds and verifies v2 from those same sources.

An exact v2 research `PASS` becomes
`EXACT_V2_RESEARCH_PASS_BOUND_CONSUMER_UNACTIVATED`. An exact v2 `BLOCK`,
including a common-universe mismatch, becomes
`EXACT_V2_BLOCK_BOUND_CONSUMER_UNACTIVATED`. Both binding outputs remain
`BLOCKED`; candidate integrity is not consumer activation.

The binding stores only registration, candidate, common-universe binding, v1
candidate, and source-report hashes plus bounded status fields. It embeds no raw
candidate, source report, correlation evidence, or symbol list.

Invalid registration, candidate drift, source-context splice, non-native input,
cycles, or verification exceptions return `UNKNOWN` without partial hashes.

## Consumer-first activation order

1. Freeze ADR0299 producer and exact verifier fingerprints.
2. Preregister and independently verify the ADR0300 hash-only binding.
3. Add a separate versioned in-memory delivery adapter.
4. Add a separate v2 presentation rail and isolated stylesheet registration.
5. Review the unmounted descriptor and neutral copy independently.
6. Only a later explicit migration may change host imports or current consumers.

No step automatically activates the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact v2 research pass | hash-only `BLOCKED` binding |
| Exact v2 common-universe block | hash-only `BLOCKED`; v1 hash remains empty |
| Registration resealed after consumer promotion | `UNKNOWN` |
| Candidate resealed after authority promotion | `UNKNOWN` |
| Candidate and source identity splice | `UNKNOWN` |
| Non-native or cyclic registration/candidate/source | `UNKNOWN` |
| Binding resealed after consumer execution promotion | exact verifier rejection |
| Source/test/ADR fingerprint drift | registration conformance failure |

## Non-duplication boundary

ADR0300 does not build another admission gate, presentation model, delivery
envelope, or host patch. ADR0299 remains the sole common-universe producer. This
slice only freezes its consumer contract and proves exact hash-only binding.

## Permission and evidence boundary

No file, DB, cache, network, runtime, DOM, browser, scheduler, writer, service,
or trading operation is performed by production code. No frontend asset is
registered or changed. Current activation, automatic internal backtest
activation, paper authorization, live orders, profitability, fresh holdout,
forward observation, browser quality, and release approval remain unproven or
false.

The public natural-forward evidence chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
