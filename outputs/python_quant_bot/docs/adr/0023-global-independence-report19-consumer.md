# ADR 0023: Report-19 global-independence consumer

- Status: Accepted, consumer-only
- Date: 2026-08-21
- Contract: `strategy-research-global-independence-extension-v1`
- Verification: `strategy-research-global-independence-extension-verification-v1`
- Target: report schema 19 / `strategy-matrix-protocol-v8`

## Context

Report 18 verifies preregistered strata one dimension at a time. A three-cluster
cycle can pass every dimension while every cluster pair shares a parent stratum
in at least one dimension. Treating those three clusters as independent votes
would therefore overstate evidence even though report 18 is internally valid.

## Decision

Add a verifier-only report-19 extension. It must independently verify the
embedded report-18 extension using a caller-supplied base report hash and
caller-supplied registry bindings. For each report-18 entry it then verifies an
exactly rebuilt `strategy-correlation-preregistered-strata-gate-v2` document
against the embedded source preregistration, complete-link gate, strata
registration, and strata gate.

Contract validity and evidence outcome remain separate. A valid global gate
with `status=BLOCK` produces report-19 verification `status=PASS` and
`decision=BLOCK`. Any source drift, identity drift, semantic reseal, hash drift,
or nested authority escalation makes the report-19 contract itself BLOCK.

The extension is research-only. It has no builder, sole writer, persistence,
pointer mutation, scheduler, paper authority, live authority, or current
activation path.

## Consumer-first activation order

1. Preserve the synthetic three-dimension cycle as a regression fixture.
2. Activate only the report-19 verifier and adversarial contract tests.
3. Preregister protocol-v8 separately, including the exact report-19 schema and
   global-independence policy hashes.
4. Add formal persistence and a sole writer only after independent review.
5. Consider any `current` cutover only after those prerequisites; this ADR does
   not authorize that cutover.

## Consequences

Report 18 remains readable and valid for its declared scope, but it cannot prove
cross-dimension independence. Report 19 can consume that evidence without
silently upgrading it. Backtests, simulations, and natural-forward observations
remain research evidence, not profitability proof or trading permission.
