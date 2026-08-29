# ADR 0354: Multi-window lifecycle-replay checkpoint persistence receipt verifier v1

- Status: Accepted as an unmounted synthetic research verifier
- Date: 2026-08-24

## Context

ADR0353 preregisters a future checkpoint-asset, write-receipt, and reopen-
receipt contract for one exact ADR0352 common replay view. It deliberately
reports `write_receipt_observed=false` and `reopen_receipt_observed=false`.
Registration alone cannot prove that a supplied asset was written once and
reopened in a different session without record drift.

ADR0105 provides the relevant provider-identity persistence pattern, but its
asset schema and source receipt are bound to a different trust domain. ADR0354
uses the same separation principles under the lifecycle-replay common-view
schemas fixed by ADR0353.

## Decision

Add a pure ADR0354 verifier with five versioned operations:

- build one sealed common-view checkpoint asset;
- build an unsigned write receipt;
- assemble a write receipt from a supplied Ed25519 signature;
- build an unsigned reopen receipt bound to the write receipt;
- assemble and evaluate the supplied write/reopen evidence.

The evaluator exactly rebuilds ADR0353, checks the persistence public-key hash,
rebuilds the asset from the preregistered checkpoint root/tree and source
hashes, verifies both domain-separated Ed25519 signatures, and requires:

- one native-integer record in each receipt;
- exact canonical asset record-hash replay;
- distinct strict write and reopen session IDs;
- reopen binding to the exact signed write-receipt hash;
- checkpoint issue <= asset creation <= write < reopen <= source reference;
- write delay, reopen delay, and minimum reopen separation within ADR0353
  policy.

The production module accepts only the registered public key. It performs no
write, reopen, filesystem, database, cache, network, or provider operation.
Raw public keys, signatures, and the asset document are not emitted by the
evaluation.

## Claim calibration

The highest state is
`WRITE_REOPEN_SIGNATURES_SESSION_SEPARATION_AND_RECORD_REPLAY_VERIFIED_EXTERNAL_DURABILITY_UNPROVEN`.

It proves local cryptographic verification of supplied receipts, exact record
replay, session separation, and internally consistent timing. It does not prove
external persistence-provider authority, real storage durability, external
time, authoritative future pinning, ADR0352 evaluation source binding,
checkpoint lineage, split-view absence, global lifecycle-receipt uniqueness,
future replay absence, profitability, or trading authorization.

## Consumer-first activation order

1. Keep ADR0354 synthetic and unmounted.
2. Add a composition gate that exactly rebuilds ADR0352 and ADR0354 and binds
   the asset source hash to the verified common-view evaluation.
3. Bind the asset's previous hash to registered genesis or one exact previous
   persisted asset.
4. Accumulate bounded longitudinal checkpoint coverage and detect rollback.
5. Establish independent provider trust and durable publication separately.
6. Bind ADR0176 content-issuance replay before any ADR0346 consumer successor.
7. Require explicit current migration and never auto-reissue pointer-v2.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact asset plus valid write/reopen signatures | local `PASS` |
| ADR0353 registration or asset drift | `UNKNOWN` |
| Wrong expected asset/receipt hash | `UNKNOWN` |
| Wrong write or reopen signing key | `UNKNOWN` |
| Duplicate session ID | `UNKNOWN` |
| Bool/duplicate record count or record-hash drift | `UNKNOWN` |
| Reopen source-write hash drift | `UNKNOWN` |
| Timestamp reversal or delay-policy breach | `UNKNOWN` |
| Resealed authority promotion | verification failure |
| Raw public key, signature, or asset in output | rejected |

## Boundary

Validation uses only synthetic in-memory keys, signatures, hashes, timestamps,
assets, and receipts. This ADR changes no existing service, report, writer,
server, engine, CLI, frontend, current pointer, natural-forward artifact,
legacy pack-v5 behavior, or pointer-v2 contract. It starts no historical-data
task, backtest, service, browser, scheduler, database, cache, log, broker,
paper, or live path.
