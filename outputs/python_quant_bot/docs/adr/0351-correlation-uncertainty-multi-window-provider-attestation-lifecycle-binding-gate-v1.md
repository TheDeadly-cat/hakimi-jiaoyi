# ADR 0351: Multi-window provider-attestation lifecycle binding gate v1

- Status: Accepted as an unmounted synthetic research candidate
- Date: 2026-08-24

## Context

ADR0350 proves that each ADR0349 observation membership, price grid, sample
count, and uncertainty replay is covered by an exact ADR0120 provider dataset-
content signature. ADR0120 intentionally proves only historical signature
validity under a locally registered dataset key. It has no reference time,
rotation epoch, revocation snapshot, custody claim, or lifecycle verifier.

ADR0121 already closes that immutable-signature gap for one ADR0120
attestation. It verifies a separate governance-key signature, freshness,
non-revocation, provider-key binding, dataset-key custody, custody-domain
separation, rotation epoch, and previous-key commitment at an explicit
reference time. Reimplementing those checks in ADR0350 would duplicate source
contracts and risk time or revocation drift.

Because each ADR0121 registration binds one exact ADR0120 attestation
verification hash, one lifecycle document cannot silently stand in for a
different window even when both windows use the same dataset key.

## Decision

Add ADR0351 as an unmounted post-gate adapter. Do not modify ADR0121, ADR0350,
ADR0349, ADR0346, or any active consumer.

ADR0351 preregisters one ordered lifecycle binding per ADR0350 window:

- ADR0120 attestation verification, attestation, and dataset-registration
  hashes;
- provider ID, dataset-key ID, and dataset public-key hash;
- ADR0121 registration, governance receipt, and gate verification hashes;
- governance-key ID and public-key hash;
- key epoch and previous-key lineage;
- rotation, revocation-registry, and custody policies;
- revocation snapshot hash/time, governance receipt issue time, and reference
  time.

If several windows use the same provider dataset key, their governance key,
epoch, previous-key lineage, policies, revocation snapshot, and reference time
must match exactly. This prevents a caller from presenting stronger lifecycle
evidence for one window and weaker or stale governance semantics for another.

At evaluation ADR0351:

1. Exactly rebuilds ADR0350 and preserves its `BLOCK`.
2. Calls the ADR0121 public verifier for every preregistered window from the
   complete ADR0120 attestation context.
3. Requires ADR0121 `PASS` facts for governance signature, rotation lineage,
   fresh non-revocation, provider binding, custody, and custody-domain
   separation.
4. Cross-binds all provider key and ADR0120 source hashes to the matching
   ADR0350 window receipt.
5. Returns `UNKNOWN` for signature failure, revocation, staleness, source
   splice, expected-pin drift, missing or reordered windows, or lifecycle fact
   drift.

ADR0351 does not independently recalculate time, freshness, revocation, or
custody decisions. ADR0121 remains their sole semantic owner.

## Claim calibration

A local ADR0351 `PASS` means each provider-attested observation window has a
fresh, validly signed ADR0121 lifecycle claim stating non-revocation, provider
binding, custody, and domain separation at the preregistered reference time.

It does not prove external governance authority, provider key control,
revocation-registry durability, lifecycle-receipt uniqueness, content-issuance
uniqueness, authoritative time, durable publication, market authenticity,
statistical independence, profitability, or trading authorization.

## Consumer-first activation order

1. Keep ADR0351 synthetic and unmounted.
2. Bind exact ADR0122 lifecycle-replay evidence per ADR0121 receipt.
3. Bind exact ADR0176 content-issuance replay evidence per ADR0120 attestation.
4. Require durable external checkpoints and independent consistency observers.
5. Add a versioned ADR0346 successor requiring ADR0351 and both replay layers
   as mandatory vetoes.
6. Add neutral reporting and `SOURCE -> GAP -> MATURITY -> PERMISSION`
   presentation only after the consumer contract stabilizes.
7. Require separate explicit authorization for current migration and never
   auto-reissue pointer-v2.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Fresh positive lifecycle claims for all windows | research-only `PASS` |
| Signed revocation or wrong governance signature | `UNKNOWN` |
| Sealed lifecycle output, fact, or ADR0120 source drift | `UNKNOWN` from exact ADR0121 rebuild failure |
| ADR0121 verifier accepts a missing required positive fact | local defense still returns `UNKNOWN` |
| Missing or reordered lifecycle bundle | `UNKNOWN` |
| Same dataset key uses different governance policy | preregistration rejected |
| Provider-attestation overlap chain is blocked | preserve `BLOCK` |
| Resealed authority promotion | verification failure |
| Governance key/signature/source documents in output | rejected |

## Boundary

Validation uses only synthetic in-memory dates, prices, dataset keys,
governance keys, signatures, receipts, and reference times. The production
module accepts no private key. This ADR starts no historical-data task,
backtest, service, browser, scheduler, database, cache, log, broker, paper, or
live path. It changes no report, writer, server, engine, CLI, frontend, current
pointer, natural-forward artifact, legacy pack-v5 behavior, or pointer-v2
contract.
