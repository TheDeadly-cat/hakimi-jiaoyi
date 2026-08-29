# ADR 0272: Stratified multi-window common-observation membership HTTP mount preregistration-v1

## Status

Accepted as a deterministic, blocked policy preregistration. It is not mount
approval, route registration, source-audit authentication, or execution
authority.

## Context

Route-contract-v1 defines a proposed research-only method and path while
correctly reporting registration evidence as absent. A synthetic audit showed
that it does not define six mount-control groups: authentication, rate limit,
request-body limit, trusted candidate/context provider, request-log redaction,
and independent mount review.

The project already has deterministic HTTP mount preregistration services for
other research candidates. Those services pin candidate and source baselines,
declare required transport controls, leave every control unregistered, and
verify by exact rebuild. This established boundary is reused instead of adding
a parallel source-snapshot evidence model.

## Decision

Add membership HTTP mount preregistration-v1 with no inputs and no I/O. It pins:

- route-contract-v1 schema, static fingerprint, and implementation SHA-256
- candidate-v11 lock-4 implementation SHA-256
- current `server.py` and `services/http_contract.py` baseline SHA-256 values
- proposed method and route from ADR0271

The policy requires loopback-only, same-origin, JSON, no-store, security-header,
read-only, no-runtime-read, no-cache, and no-request-body-logging controls.
Candidate documents and verification contexts cannot be client supplied.

Authentication, rate limiting, request-body limit, trusted candidate/context
provider, request-log redaction, consumer binding review, independent mount
review, and route registration remain unregistered or incomplete. Each has a
fixed blocker. No placeholder mechanism, numeric limit, provider ID, policy
ID, review ID, or registration ID is invented.

The policy remains `BLOCKED`; all authority fields other than
`descriptive_only` are false. Exact verification rebuilds the complete
preregistration document with the shared strict canonical service.

## Consumer-first order

1. Keep preregistration-v1 deterministic and import-only.
2. Require a separately authenticated source-baseline review before consuming its pins.
3. Register concrete transport controls in separate versioned documents.
4. Complete consumer-binding and independent mount reviews.
5. Add route registration only through a separately authorized source change.
6. Define a UI consumer after the route is genuinely registered.
7. Require a separate current-admission decision; paper/live remain unauthorized.

## Adversarial matrix

- exact policy is deterministic, blocked, and verifiable
- proposed transport remains unregistered and not externally callable
- runtime/cache reads and mutations remain false
- auth, rate limit, and body limit have no invented values
- trusted provider is absent and client-supplied context is denied
- request-body logging remains denied
- consumer and independent reviews remain incomplete
- route/candidate/source pins are exact
- authority remains locked
- resealed route-registration promotion fails exact rebuild
- resealed client-context promotion fails exact rebuild
- independent builds do not share mutable objects

## Consequences

The next mount prerequisites are explicit without weakening fail-closed
governance. No service, browser, scheduler, runtime asset, historical data,
backtest, paper trade, or live trade is started or authorized.
