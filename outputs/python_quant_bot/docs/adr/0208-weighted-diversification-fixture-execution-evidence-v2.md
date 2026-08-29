# ADR 0208: Weighted diversification fixture execution evidence v2

Date: 2026-08-23

Status: accepted for local synthetic execution evidence only

## Context

ADR 0207 added a blocked static registration-v2 candidate for projection-v4,
card-v4, and consumer-v4. The immutable execution receipt-v1 and Python
execution evidence-v1 remain pinned to the v3 presentation family. A real
projection-v4 produces a `PASS/KNOWN` descriptor-v4, but both v1 execution
layers correctly reject it.

The next consumer-first boundary is to prove that a local Node process invoked
the exact consumer-v4 and reproduced an exact unmounted descriptor. This must
remain distinct from process identity, signatures, independent review, DOM or
browser execution, CSS execution, registration activation, and mount authority.

## Decision

Add two independent versioned contracts:

- a Node receipt-v2 that rebuilds consumer-v4 output from projection-v4,
  compares the observed descriptor canonically, hashes only the descriptor
  summary, and emits a sealed local receipt;
- a Python evidence-v2 contract that independently verifies the receipt schema,
  canonical hash, six blocking checks, implementation pins, projection hash,
  registration-v2 candidate hash, summary-only facts, and authority lock.

The Node receipt pins projection-v4, the strict SHA dependency, card-v4,
consumer-v4, registration-v2 implementation, and the deterministic
registration-v2 candidate hash. The Python evidence accepts the expected
projection and registration hashes as separate arguments, preventing
cross-splicing.

Receipt `PASS` means only that a local Node contract process reproduced the
exact sealed descriptor and remained unmounted. The receipt explicitly records
all of the following as false:

- Node process identity authentication;
- receipt signature verification;
- external execution authority;
- CSS execution;
- DOM and browser review;
- network access;
- runtime consumer binding;
- profitability proof.

## Activation order

1. Build and verify the synthetic Node receipt-v2.
2. Bind and verify Python evidence-v2 against projection and registration
   hashes.
3. Add a separate successor binding that independently pins the receipt and
   evidence implementations.
4. Perform an independent render-descriptor review.
5. Only after separate authorization, consider isolated DOM and browser review.
6. Keep registration activation, HTTP, mount, `current`, paper, and live
   authority separate and locked.

This ADR completes only steps 1 and 2.

## Adversarial matrix

- valid-shape projection hash substitution blocks the Node receipt;
- descriptor mutation and extra fields block exact rebuild;
- receipt hash mutation blocks Python evidence;
- projection and registration hash cross-splicing block independently;
- bool aliases and extra receipt fields block;
- evidence authority tamper fails exact verification;
- receipt and evidence builds are deterministic and do not mutate inputs;
- neither layer embeds projection, descriptor, markup, positions, returns, or
  correlation matrices.

## Non-claims

This is synthetic local process evidence, not authenticated process identity,
signed execution provenance, independent review, DOM evidence, browser visual
QA, CSS execution, HTTP registration, runtime activation, natural-forward
maturity, profitability evidence, paper/live authorization, or permission to
trade. The established natural-forward chain, legacy pack-v5 behavior, and
pointer-v2 contract remain unchanged.
