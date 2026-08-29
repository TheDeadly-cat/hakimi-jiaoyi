# ADR 0457: Paper risk authorization identity and replay attribution v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Synthetic paper lifecycle authorization only

## Context

`PaperExecutor.submit` validated a stripped risk request identifier but consumed
the original string. Leading or trailing whitespace therefore created distinct
authorization identities. The idempotent replay path intentionally permits a
new valid risk authorization to retrieve an existing order after restart, but
its response exposed only the authorization identifier stored on the order.
Consumers could not distinguish a matching replay authorization from a rotated
one without retaining the submitted request out of band.

Pure in-memory calls demonstrated both gaps before implementation:

- `" risk-auth-whitespace "` reached `FILLED` and was stored verbatim.
- A replay submitted with `risk-auth-different` returned the order created with
  `risk-auth-original`, but did not explicitly attribute the replay gate to the
  rotated identifier.

## Decision

Introduce the paper risk authorization identity and replay attribution v1
contract:

1. A new risk request identifier must be a non-empty string no longer than 160
   characters and must already equal its stripped representation.
2. A noncanonical identifier fails before lifecycle creation with
   `risk_request_id_noncanonical`.
3. `risk_request_id` remains the immutable authorization identity stored on the
   original order.
4. An idempotent replay reports the current gate as
   `replay_authorization_request_id` and reports
   `risk_authorization_rotated=true` only when it differs from the stored ID.
5. Both matching and rotated valid authorizations retain the established
   successful replay behavior and return the original order.

Activation is consumer-first: tighten authorization validation, make replay
provenance explicit for response consumers, lock the rejection and compatible
paths with synthetic contracts, then record the baseline. No external pointer
or current evidence artifact is switched by this change.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Leading, trailing, or tab whitespace in `request_id` | Reject before order creation |
| Canonical `request_id` | Preserve exact value and proceed under existing gates |
| Same idempotency key, different valid `request_id` | Return the original order and mark rotated attribution |
| Same idempotency key, same `request_id` | Return the original order and mark matching attribution |

## Boundaries

- This does not authorize paper or live execution.
- This does not change matching, balances, broker selection, or persistence
  schemas.
- Tests use only synthetic in-memory inputs and no network, database, runtime,
  cache, log, or secret.
- The public natural-forward evidence chain and pointer-v2 contract are
  unchanged.
