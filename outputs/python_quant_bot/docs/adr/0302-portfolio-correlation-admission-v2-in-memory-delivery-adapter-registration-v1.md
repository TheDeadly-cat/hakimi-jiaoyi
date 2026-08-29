# ADR 0302: Portfolio correlation admission v2 in-memory delivery adapter registration v1

## Status

Accepted as an additive, execution-unbound, dual-runtime asset registration and
hash-only envelope binding. Presentation rail, stylesheet, host, endpoint,
route, current, paper, and live remain absent or unauthorized.

## Context

ADR0301 adds a Python in-memory envelope and JavaScript verification/extraction
adapter without pinning the two implementations to each other. This avoids a
bidirectional source-hash cycle, but no immutable consumer boundary currently
registers both assets, both tests, their strict-canonical dependency, ADR0301,
function names, or load order.

Designing the presentation rail before this registration would permit asset or
schema drift between the verified Python and JavaScript handoff.

## Decision

Add
`portfolio-correlation-admission-v2-in-memory-delivery-adapter-registration-v1`.
The registration pins:

- ADR0300 consumer preregistration hash;
- ADR0301 envelope and payload schemas plus static fingerprint;
- Python builder/verifier names, paths, implementation hash, and test hash;
- JavaScript browser global, five function exports, paths, implementation hash,
  and Node test hash;
- strict-canonical JavaScript hash and ADR0301 hash; and
- relative JavaScript load order: strict canonical, then delivery adapter.

Payload source, presentation rail, isolated stylesheet, app importer, HTML
script, host slot, endpoint, and route remain null.

Add
`portfolio-correlation-admission-v2-in-memory-delivery-adapter-binding-v1`.
The builder snapshots registration, envelope, full ADR0301 source chain, and
identity arguments exactly once. It exact-verifies the registration and rebuilds
the delivery envelope before recording registration, envelope, payload,
candidate, ADR0300 preregistration, consumer-binding, and dual-runtime adapter
hashes.

The binding embeds no envelope, payload, source document, symbol list, or
identity. Exact PASS or BLOCK envelopes both produce a `BLOCKED` integrity
binding. Invalid, drifting, promoted, non-native, cyclic, or source-spliced input
returns `UNKNOWN` without partial source hashes.

## Consumer-first activation order

1. Freeze ADR0301 Python/JavaScript implementations and test hashes in ADR0302.
2. Independently verify exact PASS and BLOCK envelope bindings.
3. Add a separate v2 presentation rail and isolated stylesheet as unmounted
   assets.
4. Register the rail against the ADR0302 adapter binding.
5. Review the unmounted descriptor and neutral copy independently.
6. Only a later explicit migration may change host imports or current consumers.

No step automatically activates the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact PASS envelope | hash-only `BLOCKED` adapter binding |
| Exact common-universe BLOCK envelope | hash-only `BLOCKED` adapter binding |
| Registration or envelope promotion | `UNKNOWN` |
| Candidate/source identity splice | `UNKNOWN` |
| Non-native or cyclic input | `UNKNOWN` |
| Binding resealed after execution promotion | exact verifier rejection |
| Python/JavaScript/test/ADR/dependency hash drift | registration conformance failure |

## Non-duplication boundary

ADR0302 does not implement another delivery adapter, payload, receipt, admission
gate, presentation rail, stylesheet, or host patch. ADR0301 remains the sole
cross-runtime delivery implementation. ADR0302 only freezes its assets and exact
envelope provenance.

## Permission and evidence boundary

Registration does not invoke Python, load JavaScript, extract a payload, execute
a consumer, render markup, access DOM, run a browser, or mount UI. Production
code performs no file, DB, cache, network, persistence, scheduler, writer,
service, publication, or trading action.

Adapter registration and envelope integrity do not prove market quality,
profitability, fresh holdout maturity, forward observation, visual quality,
consumer activation, release approval, paper authority, or live authority.

The public natural-forward evidence chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
