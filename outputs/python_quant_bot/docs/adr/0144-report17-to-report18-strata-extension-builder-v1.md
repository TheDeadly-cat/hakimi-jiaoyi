# ADR 0144: Report17 to report18 strata extension builder v1

## Status

Accepted as a non-persistent, non-current research builder on 2026-08-22.

## Context

Report18 already had a strict consumer, protocol registration, and redacted
public projection. Production code could verify report18 but could not build it.
Tests and downstream report19 fixtures manually assembled 18 root fields and
nine fields per entry, duplicating decision and source-binding logic.

A pure synthetic proof showed that the hand-built chain can produce both a
verified PASS and a verified descriptive BLOCK. The missing capability is a
source-bound transformation, not a new statistic, threshold, or authority.

## Decision

- Add a deterministic in-memory report17-to-report18 builder.
- Require one exact, versioned input per report17 identity. Each input supplies
  preregistered strata dimensions, an already sealed registry asset, a selection
  cutoff, and expected registry/classification-source hashes.
- Verify report17 and every registry asset before rebuilding strata
  registration, strata gate, registry binding, blockers, and the report18 seal.
- Match the exact identity set and emit entries in canonical identity order.
- Preserve valid complete-link, strata-gate, and registry-binding BLOCK states.
- Run the existing report18 consumer over the complete result before returning.
- Raise `ValueError` for malformed, mismatched, or unverifiable inputs.

The builder does not create a registry asset and does not attest that a supplied
classification source, timestamp, or hash is externally authentic. Those facts
remain caller-supplied candidate evidence and stay visible through binding state.

## Activation order

1. Existing report18 consumer and strict public projection.
2. This source-bound in-memory builder and adversarial tests.
3. A future delivery envelope with externally anchored registry evidence.
4. Only then reconsider strategy-lab, HTTP, current, or UI mounting.

This ADR authorizes step 2 only. The builder performs no filesystem, database,
network, scheduler, pointer, registry-write, paper, or live operation. It does
not alter the natural-forward chain or authorize profitability claims.

## Acceptance criteria

- Deterministic PASS and descriptive BLOCK construction.
- Exact report17 identity, base-hash, registry-asset, and expected-binding
  enforcement.
- Strict rejection of malformed inputs and coherently resealed schema/authority
  aliases.
- Native false writer, current, paper, and live fields.
- Zero references from existing activation entrypoints.

## Validation

- Affected report17-builder, report18-consumer, and report18-builder contracts:
  `16/16 PASS` with exact class discovery.
- In-memory compilation: `2/2 PASS`; `ResourceWarning`: `0`.
- Independent public-API matrix: `17` attacked candidates, `17` rejected,
  `0` accepted. Coverage includes source/hash/identity/input shape drift and all
  nine coherently resealed fixed-contract numeric aliases.
- Deterministic PASS plus valid strata-gate and registry-binding BLOCK outputs
  were rebuilt with unchanged inputs. File and socket access were denied during
  the valid builder calls; external I/O attempts were `0`.
- Four explicit activation entrypoints contain zero references.
- Builder SHA-256:
  `2AEB7059B0342F1249B83CB11E925F352740FE28D00CF2B27969A0074BFBE059`.
  Builder-test SHA-256:
  `9297FF8EF6CA3371C0CBB18EEF9BFBAD790D8C691CB40D4742DB077F240989C0`.
  Existing report18-consumer SHA-256 remains
  `4DF82827273A768E7BF02AA1385F01136C5240C5B81125C901F9836CA579F759`.

These receipts are synthetic contract evidence only. They do not authenticate
an external registry, prove profitability, activate current, or authorize paper
or live trading.
