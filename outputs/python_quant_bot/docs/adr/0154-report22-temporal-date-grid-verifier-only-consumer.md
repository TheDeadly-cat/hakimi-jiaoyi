# ADR 0154: Report22 temporal date-grid verifier-only consumer

- Status: Accepted, unactivated verifier-only candidate
- Date: 2026-08-22

## Context

ADR0153 preregistered report22/protocol-v11 but explicitly left the report22
consumer unavailable. The existing report21 verifier remains valid for its
temporal-v1 contract and must not be rewritten to imply date-grid coverage.

## Decision

Add a report22 extension verifier that embeds an independently verified
report21 extension and one temporal date-grid gate per report identity. The
caller must continue to provide the report21 temporal source bindings and must
also provide an exact identity-to-expected-date-grid-gate-hash binding set.

For each identity, the verifier rebuilds the gate from the report21 temporal
gate, report20 stability gate, report19 preregistration and complete-link gate,
and the external temporal source binding. The embedded gate must equal that
rebuild and its hash must equal the caller-supplied expected hash.

Contract status and decision remain separate:

- a report21 PASS plus all date-grid PASS decisions produces report22 PASS;
- a structurally valid date-grid BLOCK produces a valid report22 contract with
  decision BLOCK;
- changing that BLOCK decision to PASS fails exact report reconstruction.

The report22 entry contains only identity, the date-grid gate and its hash. It
does not copy source audits, matrices, selection cells, raw price rows or raw
dates.

## Adversarial requirements

- Report21 remains valid without retroactive date-grid fields.
- Aligned inputs produce a valid report22 PASS candidate.
- A 40-common-date input produces a valid report22 BLOCK candidate.
- A resealed decision PASS cannot override a BLOCK gate.
- Missing, duplicate, wrong-hash and identity-drift bindings fail closed.
- Coherently resealed gate type aliases fail independent gate verification.
- Root native aliases and authority escalation fail closed.
- No builder, writer, route, current switch or runtime I/O is exported.

## Boundary

This ADR adds verification only. It does not add a report22 builder, writer,
migration, current admission, pointer reissue, publication, market-data
authenticity, profitability evidence, paper permission or live authority. The
public single-look chain and legacy pack-v5 UNKNOWN behavior remain unchanged.
