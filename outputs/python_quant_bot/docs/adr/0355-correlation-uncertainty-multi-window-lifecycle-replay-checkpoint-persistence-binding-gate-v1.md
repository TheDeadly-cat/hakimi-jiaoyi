# ADR 0355: Multi-window lifecycle-replay checkpoint persistence binding gate v1

- Status: Accepted as an unmounted synthetic research composition
- Date: 2026-08-24

## Context

ADR0354 verifies supplied persistence receipts and a sealed asset but
intentionally keeps `source_replay_binding_gate_verified=false`. Its asset binds
an ADR0352 preregistration hash and common-view hash, not a reverified ADR0352
evaluation. The source could therefore remain opaque to a downstream consumer.

ADR0106 establishes the relevant composition pattern: both source and
persistence verifiers must be rerun from strict bundles, then the opaque asset
source hash must be cross-bound. Its provider-identity schemas cannot be reused
directly for lifecycle-replay common-view evidence.

## Decision

Add ADR0355 as a pure composition gate with two exact bundles:

- `source_inputs` contains the full ADR0352 invocation chain and every expected
  hash pin;
- `persistence_inputs` contains ADR0353 registration/configuration, ADR0354
  asset/write/reopen material, and every expected receipt hash.

ADR0355 accepts no caller-provided verification boolean. It:

1. Calls the ADR0352 public verifier from the complete source bundle.
2. Calls the ADR0354 public verifier using the same ADR0352 preregistration
   lineage from the source bundle.
3. Requires both source modules' positive local facts and negative external
   authority facts.
4. Binds ADR0352 output receipts to its preregistered common view.
5. Binds ADR0353 registration and the sealed asset to the exact ADR0352
   preregistration, common-view hash, checkpoint root/tree/issue time,
   reference time, and registry identity/namespace.
6. Binds ADR0354 evaluation evidence to the exact registration and asset hash.
7. Preserves an ADR0352 `BLOCK` after all persistence evidence is verified.

Only hashes, counts, and source identifiers are emitted. Raw input bundles,
assets, public keys, and signatures are not emitted.

## Claim calibration

A local ADR0355 `PASS` means one supplied asset and its cryptographically valid
write/reopen receipts are exactly bound to a fully reverified ADR0352 common-
view evaluation.

It does not prove external persistence-provider authority, actual I/O, real
durability, external time, authoritative future pinning, previous persisted-
asset lineage, complete history, longitudinal coverage, split-view absence,
global uniqueness, future replay absence, content-issuance replay,
profitability, or trading authorization.

## Consumer-first activation order

1. Keep ADR0355 synthetic and unmounted.
2. Bind the asset's previous hash to registered genesis or one exact previous
   ADR0355-bound asset.
3. Require strictly increasing checkpoint tree size and exact previous root.
4. Accumulate bounded longitudinal coverage and reject rollback or forks.
5. Establish independent persistence-provider trust and durable publication.
6. Bind ADR0176 content-issuance replay before any ADR0346 consumer successor.
7. Require explicit current migration and never auto-reissue pointer-v2.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR0352 plus exact ADR0354 evidence | local `PASS` |
| Missing or extra source/persistence bundle field | `UNKNOWN` |
| Source gate or persistence evaluation drift | `UNKNOWN` |
| ADR0352 preregistration splice | `UNKNOWN` |
| Asset common-view/root/tree/source drift | `UNKNOWN` |
| Upstream verifier accepts a source splice | local binding still returns `UNKNOWN` |
| ADR0352 is validly blocked | preserve `BLOCK` |
| Resealed authority promotion | verification failure |
| Raw bundles, asset, public key, or signature in output | rejected |

## Boundary

Validation uses only synthetic in-memory keys, signatures, hashes, timestamps,
assets, receipts, and upstream fixtures. This ADR performs no I/O and changes
no existing service, report, writer, server, engine, CLI, frontend, current
pointer, natural-forward artifact, legacy pack-v5 behavior, or pointer-v2
contract. It starts no historical-data task, backtest, service, browser,
scheduler, database, cache, log, broker, paper, or live path.
