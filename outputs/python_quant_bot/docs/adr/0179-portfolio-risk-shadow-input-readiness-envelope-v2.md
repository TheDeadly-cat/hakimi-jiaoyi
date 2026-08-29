# ADR0179: Portfolio-risk shadow input readiness envelope v2

Status: Accepted as an unmounted research-only application candidate on
2026-08-22.

## Context

ADR0178 binds the ADR0176 replay/source chain and intentionally marks six
portfolio inputs NOT_SUPPLIED. Independent valid fixtures are not sufficient:
each document can rebuild successfully while referring to a different
attestation, composition, symbol universe, cutoff, legacy matrix, cluster
matrix, or freshness registration.

A pure in-memory assembly proved that all six documents can be built from one
ADR0176 content-attestation lineage. The resulting dual-source receipt is PASS
with aligned provider metadata even though the legacy A/B correlation and the
cluster-protocol A/B correlation differ. The adapter separately evaluates both
risk views. This distinction must remain visible instead of treating verifier
PASS as a trading permission.

## Decision

Add application readiness envelope v2. It publicly reverifies ADR0178 and:

- dual-source receipt v1;
- portfolio-risk adapter v1;
- legacy matrix derivation binding v1;
- native cutoff manifest v1;
- session freshness registration v1;
- session freshness evaluation v1.

The envelope additionally requires exact cross-document equality for:

- legacy payload between dual-source and derivation binding;
- cluster payload between dual-source and adapter;
- completed-price input, matrix replay, derivation receipt, composition
  document, and composition context between binding and cutoff manifest;
- dataset attestation document, registration, public key, and receipt between
  ADR0176 and the legacy binding;
- symbol universe and observation cutoff across both matrix sources and the
  native manifest;
- native manifest between cutoff and freshness registration;
- freshness registration and registration inputs between policy and
  evaluation;
- future evaluation ID between ADR0176 readiness and the common composition.

All thirteen inventory entries become locally VERIFIED only when each public
verifier passes, each gate document has its expected non-blocked outcome, and
all cross-lineage equalities hold.

## Claim calibration

The positive state is LOCAL_INPUT_SET_VERIFIED with maturity
LOCAL_INPUT_SET_VERIFIED_EXTERNAL_TRUST_UNPROVEN. Overall status remains
UNKNOWN and permission remains DENIED.

This proves only deterministic local document compatibility. It does not prove
external provider key control, provider data issuance truth, registry or
auditor authority, durable publication, external time authority, global
uniqueness, runtime replay enforcement, future replay absence, shadow
execution, risk-service safety, independent review, robustness, profitability,
paper authorization, live authorization, or current admission.

## Consumer-first activation order

1. Keep readiness v2 unmounted and detached from shadow and risk services.
2. Authenticate provider, registry, auditor, publication, and time trust.
3. Specify a versioned application shadow-consumer request and response without
   replacing the legacy service.
4. Specify a versioned risk-service input contract.
5. Execute only independently authorized synthetic shadow calls.
6. Add a neutral SOURCE -> GAP -> MATURITY -> PERMISSION presentation after the
   application contract is stable.
7. Require separate current authorization and never auto-reissue pointer-v2.

## Adversarial matrix

The matrix covers every public verifier, verifier exceptions, missing and extra
inputs and contexts, blocked dual and adapter outcomes, legacy and cluster
payload drift, binding/native composition drift, attestation drift, symbol and
cutoff drift, freshness native-manifest and registration drift, authority
injection, exact 13/13 inventory, gate-outcome preservation, hash-only lineage,
payload/context/signature/proof redaction, deterministic rebuild, coherent
authority resealing, input immutability, no READY wording, and execution
dependency exclusion.

## Compatibility

ADR0179 changes no domain contract, legacy shadow service, risk service,
report, writer, server, engine, CLI, mounted UI, paper, live, or pointer
behavior. The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
Legacy pack-v5 public reads remain UNKNOWN. pointer-v2 fields and hash contract
remain unchanged, and no pointer is automatically reissued.
