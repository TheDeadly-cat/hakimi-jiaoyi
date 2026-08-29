# ADR 0246: Neutral registry identity evidence gap presentation v2

## Status

Accepted as an unmounted, neutral, versioned successor presentation candidate.

## Context

ADR0239 presentation-v1 is frozen by registration-v8 and shows only local
registry key possession plus seven external system gaps. ADR0245 now provides a
blocked local aggregate for six signed organization-identity artifacts. Editing
v1 would invalidate its frozen asset manifest, while adding a parallel card
would duplicate the presentation boundary.

The correct evolution is a v2 successor that preserves the visual language,
stage order, seven system gaps, and unmounted authority while refining the
organization-identity evidence explanation.

## Decision

Add projection-v2, card-v2, and consumer fixture-v2.

Projection-v2 consumes one exact v1 predecessor projection and one exact
ADR0245 aggregate. It cross-binds registry id and registry public-key hash. It
preserves SOURCE to GAP to MATURITY to PERMISSION and keeps the original seven
system gaps open.

The new identity evidence ledger contains eight rows:

1. registry key possession is OBSERVED-LOCAL;
2. six artifact hash and signature bindings are OBSERVED-LOCAL;
3. Python verification process authentication is UNVERIFIED;
4. evidence payload semantics are UNVERIFIED;
5. signer-role identity is UNVERIFIED;
6. external source trust is UNVERIFIED;
7. revocation content is UNVERIFIED;
8. registry organization identity is UNVERIFIED.

The card reuses the frozen v1 stylesheet and its existing scoped classes. It
adds a second ledger panel without modifying the stylesheet, shared styles,
app, HTML shell, routes, or DOM mounts. The fixture remains sealed and
UNMOUNTED.

Observed-local wording is intentionally distinct from identity maturity,
permission, or readiness. The card uses no success color contract and makes no
profitability or trading claim.

## Adversarial matrix

- exact v1 and ADR0245 inputs build one blocked v2 projection;
- registry id or key-hash cross-binding mismatch is rejected;
- aggregate identity-promotion evidence is rejected;
- two local observations remain separate from six unverified identity gaps;
- all seven system gaps remain open and every permission remains locked;
- stage order is exact and rendered in source-to-permission order;
- rendered copy contains no READY, profitability, return, alpha, or win-rate
  language;
- payload, key, signature, and private-key material remain absent;
- projection and fixture tampering fail exact reconstruction;
- a real Python-to-Node six-signature aggregate builds the unmounted v2 source;
- v1 assets and shared styles remain byte-for-byte unchanged.

## Consumer-first order

1. frozen ADR0239 presentation-v1 and registration-v8;
2. ADR0245 six-artifact cryptographic aggregate;
3. ADR0246 unmounted presentation-v2 successor;
4. blocked registration-v9 for exact v2 assets;
5. independently governed signer-role and external-source evidence;
6. per-schema payload semantic validators;
7. process-authenticated cross-runtime receipt;
8. explicit browser visual review;
9. separate route, mount, current, and activation decision.

## Consequences

- Reviewers gain a more precise view of cryptographic progress without hiding
  the remaining identity and external-system gaps.
- Existing v1 projection, card, fixture, stylesheet, registration-v8,
  styles.css, app, index, current, pointer-v2, and natural-forward artifacts
  remain unchanged.
- Static source and contract checks are not browser visual review.
- No credential, endpoint, runtime asset, database, cache, log, service,
  browser, scheduler, market task, backtest, blind test, paper order, or live
  order is used.
- The candidate is not source legitimacy, signer identity, organization
  identity, adapter conformance, trusted time, profitability, current, runtime,
  route, mount, writer, paper, or live authority.
