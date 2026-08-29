# ADR0178: Portfolio-risk shadow input readiness envelope v1

Status: Accepted as an unmounted research-only application candidate on
2026-08-22.

## Context

ADR0177 pins the ADR0176 content-issuance replay contract but intentionally
does not bind a concrete replay verification document. The legacy shadow
service still accepts unversioned dictionaries and is not adapter-v1 aware.
Calling it before all source and trust gates are satisfied would collapse
SOURCE, GAP, MATURITY, and PERMISSION into one unsafe execution path.

The application layer already hosts market-data and presentation envelopes.
The domain MarketDataEnvelope remains the generic row/source carrier, while
presentation envelopes map unverifiable sources to UNKNOWN. The missing
boundary is a portfolio-shadow-specific readiness envelope that can bind local
source evidence without invoking the shadow or risk services.

## Decision

Add an application-layer, unmounted readiness envelope that:

- publicly reverifies the exact ADR0177 preregistration and a concrete ADR0176
  verification document from their complete contexts;
- maps the seven ADR0176 source/evidence inputs to VERIFIED;
- maps the six portfolio-risk inputs not supplied by this slice to
  NOT_SUPPLIED;
- exposes only hashes, schema versions, counts, neutral axes, false facts,
  blockers, and denied authority;
- never embeds documents, contexts, public keys, signatures, Merkle proofs, or
  source payloads;
- returns UNKNOWN rather than raising when either source contract, context,
  authority shape, or semantic pin is invalid;
- remains UNKNOWN / PARTIAL_LOCAL_EVIDENCE / DENIED even when all seven local
  replay inputs verify;
- never imports or invokes portfolio_shadow_risk, portfolio_shadow,
  risk_service, server, writers, paper, or live paths.

## Input inventory

Locally verified through ADR0176:

- provider dataset content-attestation verification;
- provider dataset-key lifecycle-replay verification;
- content-issuance replay registration;
- pinned checkpoint;
- successor checkpoint;
- occurrence audit;
- content-issuance replay gate verification.

Still NOT_SUPPLIED:

- dual-source receipt;
- portfolio-risk adapter result;
- legacy matrix derivation binding;
- native cutoff manifest;
- session freshness registration;
- session freshness evaluation.

## Claim calibration

The positive source state means only that the supplied local documents rebuild
and verify under their registered public contracts. It does not prove external
provider key control, provider data issuance truth, registry completeness,
auditor authority, durable publication, external time, global uniqueness,
runtime consumption idempotency, future replay absence, robustness,
profitability, paper authorization, live authorization, or current admission.

## Consumer-first activation order

1. Keep the readiness envelope unmounted and detached from shadow execution.
2. Bind the remaining six portfolio inputs through their public verifiers.
3. Authenticate external provider, registry, auditor, publication, and time
   trust under separate contracts.
4. Add a versioned risk-service input only after the complete application input
   set verifies.
5. Conduct an independently authorized synthetic shadow review.
6. Add a neutral SOURCE -> GAP -> MATURITY -> PERMISSION presentation only
   after the application contract is stable.
7. Require a separate explicit current migration and never auto-reissue
   pointer-v2.

## Adversarial matrix

The matrix covers missing, extra, and non-object contexts; v3 verification
failure; ADR0176 verification failure and exceptions; semantic source tamper;
authority injection; exact 7/6 inventory counts; schema uniqueness; UI
exclusion; external-trust false facts; hash-only lineage; signature/proof and
context redaction; positive and UNKNOWN determinism; envelope tamper; coherent
authority resealing; input immutability; no READY wording; and production API
exclusion of execution dependencies.

## Compatibility

ADR0178 changes no domain contract, legacy shadow service, risk service,
report, writer, server, engine, CLI, mounted UI, paper, live, or pointer
behavior. The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
Legacy pack-v5 public reads remain UNKNOWN. pointer-v2 fields and hash contract
remain unchanged, and no pointer is automatically reissued.
