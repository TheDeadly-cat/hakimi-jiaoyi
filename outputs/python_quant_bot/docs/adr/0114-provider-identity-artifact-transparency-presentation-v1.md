# ADR 0114: Provider identity artifact transparency presentation v1

## Status

Accepted as an unmounted, fail-closed research presentation candidate. It is not connected to app, server, engine, CLI, current evidence, paper, or live paths.

## Context

ADR0113 separates locally supplied artifact-content consistency and signed transparency/retrieval claims from external log trust and public availability. Its service receipt is deliberately machine-oriented and must not be rendered directly: doing so could leak implementation detail or visually promote signed claims into public-availability truth.

## Decision

Add a sealed Python presentation envelope and detached JavaScript/CSS card.

The envelope:

1. Replays the ADR0113 public verifier and binds its exact receipt hash, schema, and static fingerprint.
2. Projects only aggregate artifact, byte, checkpoint, inclusion, observer, and signed-claim counts plus lineage hashes.
3. Rejects source shape drift, bool-as-int values, insufficient checkpoint scope, observer receipt collapse, external-fact promotion, and authority promotion.
4. Emits deterministic UNKNOWN output with null summary and lineage fields when verification fails.
5. Never projects payloads, locators, URLs, keys, signatures, requirement vectors, or runner results.

The card:

1. Validates exact envelope, summary, lineage, fact, authority, and axis shapes.
2. Enforces count arithmetic and distinct observer receipt hashes.
3. Renders only through `textContent` and remains detached from the active page.
4. Uses a scoped responsive observatory visual with reduced-motion support.
5. Preserves the ordered neutral axes `SOURCE -> GAP -> MATURITY -> PERMISSION`.

The highest display state is `LOCAL_ARTIFACTS_AND_SIGNED_RETRIEVAL_CLAIMS_BOUND_EXTERNAL_AVAILABILITY_GAP`.

## Proof boundary

The view proves only that a locally verified ADR0113 receipt was sealed into an aggregate presentation contract. It does not prove public reachability, real network retrieval, external log governance, observer independence, persistence, external time truth, true suite completeness, profitability, or any trading permission.

The initial revision made Python the presentation-seal authority. ADR0115 added browser-side strict-canonical seal recomputation, and ADR0116 then required a separately supplied expected-hash pin. These pre-activation revisions supersede the initial limitation. No browser or real-device visual QA has been performed.

## Validation evidence

1. Python envelope contracts pass 21/21; envelope and test compile in memory 2/2.
2. Current detached Node contracts pass 12/12; shared canonical utility, card, and test pass `node --check` 3/3.
3. An independent Python component matrix passes 10/10. The positive path executes the real ADR0113 verifier while isolating only the older ADR0111 synthetic fixture boundary.
4. Node accepts an actual Python-produced envelope and passes a 5/5 cross-language seal matrix: Python/JavaScript canonical hashes agree, local aggregates remain 4 artifacts, 172 bytes, and 8 signed retrieval claims, unsealed drift stops at the hash boundary, and resealed authority drift stops at the semantic boundary.
5. The explicit factor-calibration family passes 1064/1064 across 49 TestCase classes.
6. The current research lean profile lists and dry-runs 15 grouped checks. The new Python TestCase, application source, and Node test each occur once; executed, completed, and reused counts are zero; runtime mutation, paper, and live flags are false.
7. Eight named active entrypoints contain zero envelope, card, schema, or display-state references.

Implementation fingerprints:

- Envelope SHA-256: `D028EEDE3A46CDE12C50BB14B9953AEEA6397B487C5420A3714481F2E3631F88`.
- Python test SHA-256: `C7966F0BD9EE2FD496B812B85599A0643C36C1BF5B0C808793B9C58522EAF8C9`.
- Shared canonical utility SHA-256: `6BD330FAA256140E54A5C067C7292D55BBA4CC29F83CD583CB7BF463B6E3AB39`.
- Card JavaScript SHA-256: `8A1DCB43D2636C2BC692FD461DC56C91AF37E224541642946A805FFEF6849B29`.
- Card CSS SHA-256: `716E3B63A70F97ACDEAC025B0EA53C835BC2D1E04BEEBA1F4A8CDF71E3E58DF4`.
- Node test SHA-256: `12319540647CCFC03FD417C168E616F5AEEEA432944E069158FC266684A851D2`.
- Lean manifest SHA-256: `1B0159F829E6E83FE13CE8BC0BE95A698EEF7F647E221BEE64C389B0048F4089`.
- Lean plan hash: `abfc2756f57ae55061e148f292192e8e49cb103ad1cea8e849b674132e027613`.

## Activation order

1. Keep the envelope and card unmounted and test only with synthetic in-memory inputs.
2. Review cross-language shape and authority behavior independently.
3. Obtain external log and repeated retrieval evidence under a separate contract.
4. Require a new migration ADR and explicit authorization before any active UI integration.

No browser, service, scheduler, market data, backtest, paper path, or live path is used by this candidate.
