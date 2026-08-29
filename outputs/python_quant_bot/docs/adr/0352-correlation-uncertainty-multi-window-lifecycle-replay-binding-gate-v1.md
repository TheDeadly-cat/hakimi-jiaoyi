# ADR 0352: Multi-window lifecycle-replay binding gate v1

- Status: Accepted as an unmounted synthetic research candidate
- Date: 2026-08-24

## Context

ADR0351 exactly binds every provider-attested observation window to one fresh
ADR0121 dataset-key lifecycle claim. A pure synthetic read-only call proves
that ADR0351 can return research-only `PASS` while
`lifecycle_receipt_replay_registry_checked=false`, with no replay evidence in
its output. A valid historical lifecycle signature therefore does not prove
that its governance receipt appears once in an append-only registry view.

ADR0122 already owns the detached lifecycle-replay semantics for one receipt.
It verifies a signed checkpoint, Merkle inclusion, append-only consistency
from a pinned checkpoint, a separately signed complete-scan claim, an
exactly-one-occurrence claim, and explicit freshness windows. Reimplementing
those checks in the multi-window gate would duplicate cryptographic ownership.

Calling ADR0122 independently for every window is still insufficient. A caller
could present each receipt under a different root, scan snapshot, reference
time, or registry identity and incorrectly treat those results as one common
replay view.

## Decision

Add ADR0352 as an unmounted post-gate adapter. Do not modify ADR0122, ADR0351,
ADR0346, or any active consumer.

ADR0352 preregisters one ordered ADR0122 binding per ADR0351 window and
requires all windows to share exactly one view:

- replay-registry identity, namespace, adapter identity, and registry key;
- occurrence-auditor identity and key;
- freshness policies and registration declaration time;
- pinned prior tree size/root/checkpoint commitment;
- successor tree size/root and checkpoint issue time;
- append-only consistency-proof hash;
- complete index-snapshot root, record count, scan range, scan completion,
  audit issue time, and reference time.

Each window keeps its own source lifecycle verification/receipt hash,
registration, checkpoint signature, inclusion proof, occurrence audit, and
leaf index. Lifecycle receipt hashes, ADR0122 registrations, checkpoint
receipts, occurrence audits, pins, and leaf indices must all be distinct. The
shared tree must be large enough to contain every preregistered window.

At evaluation ADR0352:

1. Exactly rebuilds ADR0351 and preserves its `BLOCK`.
2. Reconstructs the ADR0122 lifecycle context from the matching ADR0351 bundle.
3. Calls the ADR0122 public verifier for every preregistered window.
4. Requires ADR0122 positive signature, inclusion, consistency, complete-scan,
   exactly-one, source-binding, and freshness facts.
5. Cross-binds every replay registration, checkpoint, proof hash, occurrence
   audit, registry view, lifecycle receipt, and window identifier.
6. Requires shared replay/auditor keys to remain distinct from every window's
   dataset, governance, identity-registry, and timestamp-adapter keys.
7. Emits only redacted hashes, identifiers, counts, indices, and timestamps.

ADR0122 remains the sole owner of signature, Merkle, consistency, scan,
cardinality, and freshness semantics.

## Claim calibration

A local ADR0352 `PASS` means every ADR0351 lifecycle receipt has exact ADR0122
evidence under one preregistered registry root and complete-scan snapshot, with
one signed occurrence claim at a distinct leaf index.

It does not prove external replay-registry authority, external occurrence-
auditor authority, durable checkpoint publication, independent split-view
detection, complete real-world index history, global lifecycle-receipt
uniqueness, future replay absence, authoritative time, content-issuance replay
absence, market authenticity, statistical independence, profitability, or
trading authorization. The output deliberately keeps
`lifecycle_receipt_replay_registry_checked=false` and records the narrower
signed-evidence fact separately.

## Consumer-first activation order

1. Keep ADR0352 synthetic and unmounted.
2. Bind independently observed, durably published checkpoint consistency.
3. Accumulate longitudinal common-view checkpoints and detect rollback or
   split-view divergence.
4. Bind ADR0176 content-issuance replay evidence for every ADR0120 attestation.
5. Add a versioned ADR0346 successor requiring both replay layers as vetoes.
6. Add neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` presentation only
   after the consumer contract stabilizes.
7. Require separate explicit authorization for current migration and never
   auto-reissue pointer-v2.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Two distinct receipts under one root and scan snapshot | research-only `PASS` |
| Split root, scan snapshot, registry, policy, or reference time | preregistration rejected |
| Duplicate lifecycle receipt or leaf index | preregistration rejected |
| Missing or reordered replay bundle | `UNKNOWN` |
| Wrong registry/auditor signature or proof | `UNKNOWN` |
| Replay gate or lifecycle source splice | `UNKNOWN` |
| ADR0122 verifier accepts a missing required positive fact | local defense returns `UNKNOWN` |
| ADR0351 overlap chain is blocked | preserve `BLOCK` |
| Resealed authority promotion | verification failure |
| Raw public keys, signatures, or proofs in output | rejected |

## Boundary

Validation uses only synthetic in-memory dates, prices, lifecycle receipts,
Ed25519 keys, signatures, Merkle leaves, checkpoints, proofs, and scan claims.
The production module accepts no private key. This ADR starts no historical-
data task, backtest, service, browser, scheduler, database, cache, log, broker,
paper, or live path. It changes no report, writer, server, engine, CLI,
frontend, current pointer, natural-forward artifact, legacy pack-v5 behavior,
or pointer-v2 contract.
