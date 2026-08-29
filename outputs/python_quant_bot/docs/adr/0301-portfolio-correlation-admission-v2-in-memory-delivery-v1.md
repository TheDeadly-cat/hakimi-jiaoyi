# ADR 0301: Portfolio correlation admission v2 in-memory delivery v1

## Status

Accepted as an additive, endpoint-free, cross-runtime delivery candidate. It
does not register a presentation consumer, render function, host import, route,
browser, current admission, paper authority, or live authority.

## Context

ADR0300 preregisters and exact-binds ADR0299 v2 candidates, but deliberately
leaves delivery and presentation null. A future rail needs a bounded handoff
that preserves the common-universe decision without embedding source reports,
symbol lists, strategy identifiers, or granting runtime authority.

## Decision

Add a Python delivery envelope and a JavaScript extraction adapter in one
cross-runtime version.

The Python builder takes one native-JSON snapshot of the ADR0300 registration,
binding, exact v2 candidate, source documents, and identity arguments. It
exact-verifies ADR0300 and its v2 binding before constructing a separately
sealed presentation payload.

The payload contains only:

- v2 candidate status and first blocking tier;
- common-universe and v1 admission statuses;
- the fixed v2 tri-state checks and blocker identifiers;
- candidate, common-universe binding, and source-report hashes; and
- fixed research-only permission and redaction facts.

It omits strategy/variant identifiers, source reports, correlation documents,
symbol lists, and the full v2 candidate.

The envelope transport is fixed to `IN_MEMORY_JSON_DOCUMENT`, `NO_STORE`, UTF-8
JSON, null endpoint, null route, no wire bytes, no network, and no persistence.
Building the envelope is not a delivery attempt.

The JavaScript adapter strictly verifies the envelope and nested payload,
including tri-state dependency order, blocker derivation, common-universe/v1
status relations, permission locks, provenance equality, and both seals. It can
return a detached frozen payload and build a sealed extraction receipt. The
receipt records in-memory extraction while presentation execution, rendering,
DOM, browser, mount, current, paper, and live remain false.

## Consumer-first activation order

1. Freeze ADR0300 registration and binding hashes.
2. Validate Python-to-JavaScript envelope verification and extraction in memory.
3. Register the final Python and JavaScript assets plus both test hashes.
4. Add a separate v2 rail and isolated stylesheet registration.
5. Review the unmounted rail descriptor and neutral copy independently.
6. Only a later explicit migration may alter host imports or current consumers.

No step automatically activates the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact v2 research pass | bounded endpoint-free envelope |
| Exact common-universe block | block payload; v1 remains `NOT_EVALUATED` |
| Registration, binding, candidate, or source splice | Python `UNKNOWN` with no payload |
| Non-native or cyclic input | Python `UNKNOWN` |
| Candidate/payload/envelope hash substitution | JavaScript rejection |
| Downstream v1 pass after common-universe block | JavaScript rejection after reseal |
| Payload permission promotion | JavaScript rejection after reseal |
| Exact payload extraction | blocked receipt; render/DOM/browser remain false |
| Receipt execution promotion | exact receipt verifier rejection |

## Non-duplication boundary

ADR0301 does not reproduce the v2 admission algorithm or build a presentation
rail. Python remains the authoritative producer verifier. JavaScript validates
only the bounded delivery projection and its dependency semantics. Rendering
and visual styling remain a later consumer responsibility.

## Permission and evidence boundary

Production code performs no file, DB, cache, network, endpoint, persistence,
DOM, browser, scheduler, writer, service, publication, or trading operation.
Node tests read only explicit source files and invoke Python only for pure
synthetic fixture construction. No frontend host asset is changed.

An in-memory envelope or extraction receipt does not prove market quality,
profitability, fresh holdout maturity, forward observation, browser quality,
consumer activation, release approval, paper authority, or live authority.

The public natural-forward evidence chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
