# ADR 0239: Neutral anti-replay registry gap presentation-v1

## Status

Accepted as an unmounted, neutral, source-level presentation candidate.

## Context

ADR0238 proves only local possession of a preregistered registry key. The result
is useful to reviewers but can be visually misread as registry readiness if it
is shown without the remaining external prerequisites and permission locks.

The existing terminal uses the neutral sequence `SOURCE -> GAP -> MATURITY ->
PERMISSION`. A new presentation must preserve that order, avoid promotional
language and success colors, and remain separate from `styles.css`, routes,
`app.js`, DOM mounts, and browser claims until an explicit activation decision.

## Decision

Add four source-level presentation components:

1. a sealed projection-v1 consuming only exact local registry key-possession
   evidence;
2. a pure card view-model and escaped HTML renderer;
3. a sealed unmounted consumer fixture with no route, selector, or app import;
4. a fully scoped responsive stylesheet under `.ar-gap-card`.

The projection exposes only hash-bound source identifiers, local key possession,
seven explicit external gaps, local-only maturity, and locked permissions. The
gaps are organization identity, adapter conformance, shared linearizability,
durable atomic consumption, trusted registry time, signed consumption receipt,
and post-registration receipt-v5.

The card uses a warm paper, ink, rust, and steel visual system with condensed
display typography, a four-stage evidence rail, numbered gap register, and
locked permission chips. It includes responsive and reduced-motion behavior but
is not browser reviewed or mounted.

## Adversarial matrix

- exact ADR0238 evidence builds one blocked projection;
- stage order is exact and seven gaps cannot become PASS through aliases;
- all projection and fixture authority remains false;
- projection schema aliases, permission drift, fixture mount drift, and seal
  tampering fail closed;
- rendered copy contains no READY, profitability, return, alpha, or win-rate
  language;
- raw nonce, detached signature, public-key DER, and private-key material are
  absent from HTML and presentation documents;
- scoped CSS does not modify `body`, `html`, `:root`, or the existing stylesheet.

## Consumer-first order

1. exact blocked registry key-possession evidence;
2. unmounted neutral gap projection and card-v1;
3. independently governed registry organization-identity evidence;
4. separately authorized external adapter and conformance execution;
5. signed target consumption receipt-v1 with trusted registry time;
6. post-registration receipt-v5;
7. explicit browser review;
8. separate route, mount, current, and activation decision.

## Consequences

- Reviewers can inspect local progress without hiding external blockers or
  inferring execution authority.
- Existing `styles.css`, `evidence_presentation.js`, `app.js`, route definitions,
  DOM mounts, current artifacts, pointer-v2, and natural-forward evidence remain
  unchanged.
- Static-source and contract checks do not constitute browser visual review.
- No endpoint, runtime asset, database, cache, log, network, service, browser,
  scheduler, market task, paper/live path, or trading path is used.
- The candidate is not organization identity, adapter conformance,
  linearizability, atomicity, trusted time, profitability, receipt, current,
  runtime, paper/live, route, mount, migration, or writer authority.
