# ADR 0240: Blocked presentation registration-v8 and suite-v18

## Status

Accepted as a blocked static registration and accessibility contract.

## Context

ADR0239 adds an unmounted anti-replay registry gap card. Its asset names and
source hashes are not yet bound into the existing Python presentation consumer
registration chain. The latest static suite also establishes reduced-motion and
forced-colors expectations; the new scoped stylesheet initially included the
former but not the latter.

Creating a separate JavaScript catalog would duplicate registration-v7 and make
the consumer boundary ambiguous. Editing `app.js`, `index.html`, or the shared
stylesheet would instead imply a mount decision that has not been authorized.

## Decision

Add registration-v8 as an exact successor of registration-v7. It independently
invokes the v7 public verifier, binds seven ADR0239 decision, production, and
verification assets, fixes their manifest hash and count, and records the
consumer as `UNMOUNTED` with exact `SOURCE -> GAP -> MATURITY -> PERMISSION`
order.

Strengthen the isolated card stylesheet with a scoped `forced-colors: active`
contract using system `Canvas` and `CanvasText` colors. The evolved stylesheet
hash is versioned by registration-v8 without changing `styles.css`.

Add suite-v18 to statically verify:

- anti-replay card identifiers remain absent from `app.js` and `index.html`;
- stage order, evidence-gap wording, local-only maturity, and locked permission
  wording remain neutral;
- fixture source declares no route, mount, app import, or browser review;
- CSS remains scoped and includes mobile, reduced-motion, and forced-colors
  behavior;
- the shared stylesheet fingerprint remains unchanged.

## Adversarial matrix

- exact v7 predecessor and seven exact asset pins build one blocked v8 document;
- `CLEAR`, `TAIL_BLOCK`, and `EXACT_UNKNOWN` produce distinct blocked hashes;
- missing, extra, or substituted asset pins fail closed;
- predecessor substitution and resealed authority promotion fail closed;
- public verifier PASS means exact reconstruction of a blocked, unmounted
  registration only;
- suite-v18 cannot establish browser rendering, route binding, or mount status.

## Consumer-first order

1. exact blocked registration-v7;
2. exact ADR0239 assets and accessibility contract;
3. blocked registration-v8 and suite-v18;
4. independently governed registry identity and external conformance evidence;
5. signed consumption receipt-v1 and post-registration receipt-v5;
6. explicit browser visual review;
7. separate route, mount, current, and activation decision.

## Consequences

- There is one Python presentation registration chain rather than a duplicate
  static catalog.
- The new card gains high-contrast source support without global CSS changes.
- Existing `styles.css`, `evidence_presentation.js`, `app.js`, `index.html`,
  routes, DOM mounts, current artifacts, pointer-v2, and natural-forward evidence
  remain unchanged.
- Static suite PASS is source evidence, not browser visual evidence.
- No endpoint, runtime asset, database, cache, log, network, service, browser,
  scheduler, market task, paper/live path, or trading path is used.
- Registration-v8 is not registry identity, conformance, linearizability,
  atomicity, trusted time, profitability, receipt, current, runtime, paper/live,
  route, mount, migration, or writer authority.
