# ADR0174: Session-freshness presentation sealed consumer review v1

## Status

Accepted as an immutable static review with status
`CANDIDATE_BOUND_NOT_MOUNTED`. It is not a mount, route, browser review,
runtime review, shadow consumer, current switch, paper permission, or live
permission.

## Context

ADR0173 established an exact Python projection, a Python-to-Node invocation, a
standalone UMD card, stylesheet contracts, and suite-v17 mount absence. Passing
commands alone do not identify which source versions were reviewed, and a later
file change could otherwise be confused with the validated candidate.

## Decision

Add a deterministic no-argument review artifact that pins SHA-256 values for:

1. ADR0172 session-freshness evaluation source.
2. ADR0173 public projection source.
3. ADR0173 card JavaScript and stylesheet.
4. The current `app.js` and `index.html` versions reviewed for mount absence.
5. ADR0172 tests, the Python cross-runtime test, Node card tests, and suite-v17.

The review records source schemas/fingerprints, exact axis order, public state
matrix, complete source-hash requirement, CommonJS/browser-global/Python-to-Node
availability, UNKNOWN fallback, and UNAUTHORIZED permission fallback. It pins
test definitions but does not embed execution results or historical totals.

Pinning `app.js` and `index.html` is deliberate. Any future frontend change,
even unrelated, requires a successor review before mount-absence claims can be
carried forward. ADR0174 is immutable rather than silently refreshed.

## Review boundary

Static source review is complete for the pinned versions. Actual HTTP transport,
DOM mount, browser-process visual review, runtime assets, independent review,
external time-authority authentication, shadow binding, and external freshness
proof remain false or blocked.

The review does not start a service or browser, access runtime state, register a
route, modify the natural-forward chain or pointer-v2, claim profitability, or
grant current, paper, or live authority.

## Successor order

1. Preserve this review unchanged.
2. Add independent review against the same pinned hashes.
3. Authenticate external time-authority roles separately.
4. Create a successor shadow-only mount/HTTP preregistration.
5. Require authorized browser review before any DOM mount.
6. Require a separate current migration decision; paper/live remain locked.

## Validation evidence

- Sealed review and hash-pin contract: 13/13 PASS.
- ADR0174, ADR0173, and ADR0172 Python dependency matrix: 39/39 PASS.
- ADR0173 card and suite-v17 Node matrix: 14/14 PASS.
- In-memory Python compilation: 2/2 PASS.

The review artifact itself still embeds no execution results or historical test
totals. These validation results belong to this development baseline and do not
change its immutable authority fields. Source and current app/index files were
read; runtime assets, services, DOM, and browser processes were not accessed.
