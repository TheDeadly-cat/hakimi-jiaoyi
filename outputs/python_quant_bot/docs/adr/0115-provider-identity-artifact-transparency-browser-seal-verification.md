# ADR 0115: Provider identity artifact-transparency browser seal verification

## Status

Accepted as a pre-activation hardening revision for the unmounted ADR0114 card. No active page, server, engine, CLI, paper, or live path is changed.

ADR0116 subsequently strengthens the same unmounted card with a mandatory independently supplied expected-hash pin. The evidence and fingerprints below record the ADR0115 acceptance revision rather than the later current card implementation.

## Context

ADR0114 made Python the presentation-seal authority and gave JavaScript exact shape, aggregate, fact, authority, and DOM guards. The detached card checked that `presentation_hash` looked like a lowercase SHA-256 value but did not independently recompute it. A coherently shaped but unsealed modification could therefore reach presentation logic if a future caller skipped the Python verifier.

The repository already contains `strict_canonical_json_v1.js`, a browser-compatible synchronous strict-canonical serializer, UTF-8 SHA-256 implementation, document sealer, and sealed-document verifier used by other detached evidence cards. Duplicating that implementation would create an unnecessary cryptographic boundary.

## Decision

Strengthen `provider_identity_artifact_transparency_card_v1.js` in place before activation:

1. Reuse `strict_canonical_json_v1.js` in CommonJS and `HakimiStrictCanonicalJsonV1` in browser-global mode.
2. Require `verifySealedDocument(envelope, "presentation_hash")` before source, summary, fact, authority, count, or DOM projection checks.
3. Fail closed when the browser-global verifier is absent.
4. Keep semantic adversarial tests meaningful by resealing intentionally modified fixtures before testing downstream contract rejection.
5. Add a distinct unsealed-tamper test that must fail at the hash boundary.
6. Preserve the ADR0114 envelope schema, static fingerprint, display state, API names, CSS, and unmounted status.

## Proof boundary

Successful recomputation proves only byte-equivalent strict-canonical agreement between the supplied envelope fields and its hash. It does not prove that the envelope came from a trusted process, that ADR0113 evidence is externally true, that artifacts are publicly available, or that browser rendering has been visually reviewed.

## Validation evidence

1. Current detached Node contracts pass 12/12, including CommonJS and browser-global seal verification, unsealed tamper rejection, resealed semantic rejection, missing-verifier fail-closed behavior, and safe DOM projection.
2. Shared canonical utility, card, and Node test pass `node --check` 3/3.
3. An actual Python-produced envelope passes a 5/5 Python-to-Node seal matrix. Both languages produce presentation hash `04741b203a60c8520fcf31666a784a15aa13bc8200db80b4bbeef713befb3db9` for the same synthetic envelope.
4. The current research lean profile lists and dry-runs 15 grouped checks. The card test occurs once; executed, completed, and reused counts are zero; runtime mutation, paper, and live flags are false.
5. Eight named active entrypoints contain zero card, browser-global API, or strongest-display-state references.
6. The JS-only hardening does not affect the previously verified 1064/1064 Python family; that family was not rerun for this revision.

Implementation fingerprints:

- Shared canonical utility SHA-256: `6BD330FAA256140E54A5C067C7292D55BBA4CC29F83CD583CB7BF463B6E3AB39`.
- Card JavaScript SHA-256: `8A1DCB43D2636C2BC692FD461DC56C91AF37E224541642946A805FFEF6849B29`.
- Node test SHA-256: `12319540647CCFC03FD417C168E616F5AEEEA432944E069158FC266684A851D2`.
- Lean manifest SHA-256: `1B0159F829E6E83FE13CE8BC0BE95A698EEF7F647E221BEE64C389B0048F4089`.
- Lean plan hash: `abfc2756f57ae55061e148f292192e8e49cb103ad1cea8e849b674132e027613`.

No browser or real-device visual QA is claimed.

## Activation boundary

The card remains detached. Browser loading order must provide `strict_canonical_json_v1.js` before the card. Any future bundling or active mount requires a separate migration review and explicit authorization.
