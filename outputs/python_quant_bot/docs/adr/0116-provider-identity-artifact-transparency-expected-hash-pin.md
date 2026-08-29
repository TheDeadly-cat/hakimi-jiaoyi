# ADR 0116: Provider identity artifact-transparency expected-hash pin

## Status

Accepted as a pre-activation hardening revision for the unmounted ADR0114/ADR0115 card. No active page, server, engine, CLI, paper, or live path is changed.

## Context

ADR0115 made the browser recompute the strict-canonical presentation seal. That proves the supplied envelope is internally self-consistent, but an attacker able to replace both content and hash could still provide a coherently resealed envelope. Semantic guards reject authority and external-truth promotion, yet permitted descriptive text and lineage substitutions would remain self-consistent.

The detached consumer therefore needs a second value from a separate trust path: an expected presentation hash pinned by its caller rather than read from the envelope being verified.

## Decision

Strengthen the pre-activation card API in place:

1. `buildProviderIdentityArtifactTransparencyModelV1(envelope, expectedPresentationHash)` requires a lowercase SHA-256 expected hash.
2. `createProviderIdentityArtifactTransparencyCardV1(envelope, documentRef, expectedPresentationHash)` forwards the same required pin.
3. Verification order is exact top-level shape, expected-hash validity, envelope identity and hash shape, actual/expected equality, strict-canonical seal recomputation, then semantic and DOM contracts.
4. Missing or malformed expected hashes fail closed.
5. A coherently resealed modification still fails when checked against the original pin.
6. Semantic adversarial tests may pass the resealed candidate hash only to isolate downstream semantic guards; this is not the attack-path test.
7. Envelope schema, static fingerprint, display state, CSS, and unmounted status remain unchanged.

## Proof boundary

Expected-hash equality proves binding only to the value supplied through the caller's separate parameter. It does not prove that the caller obtained that value from a trusted registry, authenticated transport, or external authority. It also does not prove ADR0113 external facts, public availability, persistence, profitability, or trading permission.

## Validation evidence

1. Current detached Node contracts pass 14/14. Coverage includes required and malformed pin rejection, original-pin rejection of coherently resealed drift, unsealed hash rejection, resealed semantic rejection, CommonJS/browser-global parity, missing-verifier failure, and safe DOM projection.
2. Shared canonical utility, card, and Node test pass `node --check` 3/3.
3. An actual Python-produced envelope passes a 6/6 Python-to-Node expected-pin matrix: valid model and DOM acceptance, missing-pin rejection, original-pin rejection of a resealed replacement, unsealed drift rejection, and resealed authority-promotion rejection.
4. Synthetic envelopes contain newly generated keys, so their presentation hashes vary between fixture runs. Validation asserts same-input cross-language equality rather than treating one synthetic hash as a permanent fingerprint.
5. The current research lean profile lists and dry-runs 15 grouped checks. The card test occurs once; executed, completed, and reused counts are zero; runtime mutation, paper, and live flags are false.
6. Eight named active entrypoints contain zero card, browser-global API, or `expectedPresentationHash` references.
7. The JS-only hardening does not affect the previously verified 1064/1064 Python family; that family was not rerun for ADR0116.

Implementation fingerprints:

- Card JavaScript SHA-256: `E02C68EBF6E28BBE15F0B7EECEFF6188FC66A357BCE6E487264D85B97C881820`.
- Node test SHA-256: `1648B288EEA5BEC1B25B918755BAE19DA0BFDADDF5AF07368FFF4E82C785C821`.
- Lean manifest SHA-256: `1B0159F829E6E83FE13CE8BC0BE95A698EEF7F647E221BEE64C389B0048F4089`.
- Lean plan hash: `134cf9c2ca9d35cbe876f87bbfde07b9e7b7a3f429c71cc497d3f065bb4aabfb`.

No browser or real-device visual QA is claimed.

## Activation boundary

No default expected hash is allowed. A future active consumer must identify and review the independent source of the pin, load the canonical verifier first, and obtain separate migration authorization before mounting the card.
