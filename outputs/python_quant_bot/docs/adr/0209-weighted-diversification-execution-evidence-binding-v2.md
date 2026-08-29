# ADR 0209: Weighted diversification execution evidence binding v2

Date: 2026-08-23

Status: accepted for detached local evidence binding only

## Context

ADR 0208 produced a sealed Node receipt-v2 and Python execution evidence-v2 for
the weighted-diversification consumer. The immutable binding-v1 remains pinned
to the old v3 preregistration and execution family. A real receipt/evidence-v2
pair passes its own contracts but correctly fails binding-v1 fixture identity.

The next boundary is a detached successor that independently calls the
registration-v2 and evidence-v2 verifiers, pins the new receipt/evidence
implementations, and cross-binds all summary hashes without embedding source
documents or granting activation.

## Decision

Add
`strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2.py`
with two exact contexts:

- registration verification context: the registration-v2 artifact manifest;
- execution evidence context: Node receipt-v2, expected projection hash, and
  expected registration candidate hash.

The binding independently pins four implementations: immutable binding-v1,
registration-v2, receipt-v2 JavaScript, and evidence-v2. It requires real
registration/evidence verifier receipts and closes four identity chains:

1. registration document -> context -> Node receipt -> Python evidence;
2. projection context -> Node receipt -> Python evidence;
3. Node receipt seal -> Python evidence source;
4. descriptor hash -> Python evidence source.

It also checks projection, strict SHA, card, and consumer implementation pins
across registration, receipt, and evidence documents. Every source document
must retain locked authority. Output contains only canonical summary hashes,
checks, calibrated facts, and a sealed binding hash.

Binding `PASS` means exact local document and implementation agreement only.
The registration candidate remains `BLOCKED`; activation remains false.

## Remaining gaps

- artifact identities are locally pinned but not externally attested;
- Node process identity remains unauthenticated;
- execution receipt remains unsigned;
- independent review is incomplete;
- CSS, DOM, and browser execution remain unproven;
- HTTP, registration activation, mount, `current`, paper, and live remain
  unauthorized.

## Adversarial matrix

- missing, extra, drifted, and bool-alias manifests block;
- missing, extra, projection-spliced, and registration-spliced contexts block;
- each registration/projection/receipt/descriptor hash chain break blocks;
- every production implementation pin mismatch blocks;
- source status promotion, authority leakage, and non-boolean aliases block;
- verifier failures and exceptions block;
- a resealed binding authority/fact tamper fails exact rebuild;
- real registration-v2 and evidence-v2 contracts bind without mocked receipts;
- inputs remain immutable and output deterministic.

## Non-claims

This detached binding is not external artifact attestation, authenticated or
signed execution provenance, independent review, CSS/DOM/browser evidence,
HTTP registration, runtime activation, natural-forward maturity, profitability
evidence, paper/live authorization, or permission to trade. The established
natural-forward chain, legacy pack-v5 behavior, and pointer-v2 contract remain
unchanged.
