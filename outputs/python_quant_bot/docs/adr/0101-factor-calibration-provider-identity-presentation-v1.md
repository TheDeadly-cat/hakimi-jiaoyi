# ADR 0101: Factor calibration provider identity presentation v1

## Status

Accepted as an unmounted, research-only presentation candidate. It is not an
active page component or authority surface.

## Context

ADR0100 can verify a registry-key signature and frozen snapshot membership while
keeping external registry authority, external time, replay, provider identity,
and all admission permissions unresolved. A UI that compresses this state into
"identity verified" would erase the most important distinction in the contract.

The project also needs a consumer-first frontend boundary before any active
mount is discussed. That boundary must consume a reverified sealed envelope,
not a caller-generated label or raw assertion receipt.

## Decision

Introduce a Python presentation envelope and detached JavaScript evidence card.

The envelope:

1. Replays the complete ADR0100 verifier context.
2. Exposes aggregate provider, subject, registry, snapshot, proof-count/index,
   validity window, and lineage hashes only.
3. Redacts public-key bytes, signature bytes, and Merkle proof siblings.
4. Preserves the exact four-axis order `SOURCE -> GAP -> MATURITY -> PERMISSION`.
5. Maps the positive cryptographic candidate to
   `CRYPTOGRAPHIC_PROOF_BOUND_EXTERNAL_TRUST_GAP`, never to identity truth.
6. Is sealed as
   `strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-identity-presentation-envelope-v1`.

The detached card uses a warm registry-dossier visual language: paper grain,
ink-blue lineage, orange gap markers, a four-stop proof route, and a compact
Merkle-position strip. It uses scoped `.pirl1-*` CSS, local font fallbacks,
900px and 560px responsive breakpoints, one dossier entrance and route-scan
animation, and a reduced-motion override.

The renderer uses `textContent` and `createElement` only. It has no network
request, button, event listener, page query, active mount hook, raw receipt
consumer, or trading action.

## Failure semantics

Hash drift, extra fields, schema/fingerprint drift, axis reordering, blocker
reordering, proof-count arithmetic drift, lineage errors, authority promotion,
external-trust promotion, provider-identity promotion, and promotional copy are
rejected. An unverified Python source maps to a sealed `UNKNOWN` envelope.

## Activation order

1. Land and independently validate the sealed envelope.
2. Validate the detached card in Node and across the Python-to-JavaScript hash
   boundary.
3. Keep active references at zero.
4. Implement external trust-root, external-time, and replay consumers first.
5. Require a separate design and migration review before any page mount.

## Consequences

Users can inspect cryptographic progress without confusing it with provider
identity, admission, profitability, or trading authority. This candidate adds
no browser-verified layout claim, active UI, service, scheduler, paper/live
authorization, or current-pointer change.

## Revision 2: strict UNKNOWN normalization

Cross-language adversarial review found that the initial JavaScript consumer
required positive-source summary and lineage values even when the sealed Python
envelope was `UNKNOWN`. A partial unknown source therefore failed on one null
lineage hash, while a fully absent source failed on null summary fields.

Revision 2 keeps all positive checks unchanged and permits `null` only in an
`UNKNOWN` envelope. Lineage entries must each be null or strict SHA-256.
Membership index/count/tree-size must be either all null or all valid and
arithmetically consistent. The presentation model normalizes missing text and
proof aggregates to the literal `UNKNOWN`; it never renders `null`, negative
tree arithmetic, or inferred evidence.

## Revision 3: browser-script branch regression

The Node suite now executes the strict-canonical helper and card in an isolated
script context with no CommonJS `module` or `require`. It requires the helper to
publish `HakimiStrictCanonicalJsonV1`, the card to publish
`ProviderIdentityEvidenceCardV1`, and the browser-global API to build the same
sealed positive presentation model. This is a UMD wiring check only; it does
not claim browser layout, font, viewport, or device QA.
