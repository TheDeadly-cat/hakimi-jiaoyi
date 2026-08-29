# ADR0357: Correlation multi-window persisted-checkpoint lineage history coverage gate v1

## Status

Accepted as a synthetic, unmounted, consumer-first research contract. It is not connected to current evidence, UI, server, engine, CLI, storage, scheduler, paper, or live paths.

## Context

ADR0356 verifies one persisted-checkpoint lineage segment in either `REGISTERED_SOURCE_PIN` or `PREVIOUS_PERSISTED_ASSET` mode. Both modes deliberately leave `complete_persisted_checkpoint_history_verified=false`. Two locally valid endpoint documents therefore cannot prove that an expected intermediate persisted checkpoint was supplied.

ADR0109 already defines the general safety pattern for a preregistered bounded longitudinal prefix: at least three evaluations, a closed checkpoint range, exact segment handoffs, stable identities, unique hashes, and bounded claimed times. Its source schema is deliberately pinned to ADR0108 assertion evidence. A synthetic public-API probe confirmed that replacing that source schema with ADR0356 returns `UNKNOWN registration_source_evaluation_schema_invalid`, so direct reuse would create compatibility drift rather than a valid composition.

## Decision

Add an ADR0356-specific registration and consumer gate.

Registration pins:

1. The exact ADR0356 schema, static fingerprint, and implementation SHA-256.
2. An already observed anchor gate hash, anchor asset hash, and anchor checkpoint tree size.
3. A future closed checkpoint range containing at least three total segments with step one.
4. Study, ordered-window, replay-registry, and persistence-configuration identities.
5. A claimed registration time, future coverage interval, and maximum future asset-time gap.

Evaluation must:

1. Reverify every ADR0356 document from its complete supplied current/previous segment inputs and expected gate hash.
2. Require the registered anchor first and `PREVIOUS_PERSISTED_ASSET` mode thereafter.
3. Require each previous segment to equal the prior current segment and each previous asset hash to equal the prior current asset hash.
4. Require every checkpoint tree size in the registered closed range with no missing, duplicate, or extra item.
5. Keep registered study, window order, replay registry, namespace, persistence configuration, and ADR0355 source pin stable.
6. Require the anchor claimed asset time not to follow registration and all future claimed asset times to be strictly increasing inside the preregistered interval with the registered maximum gap.
7. Reject source authority, complete-history promotion, non-synthetic evidence, or runtime mutation claims.

## Authority boundary

The highest state is `PASS_PREREGISTERED_BOUNDED_PERSISTED_CHECKPOINT_HISTORY_COVERAGE`.

This proves only that a locally supplied synthetic sequence covers one preregistered bounded prefix under the pinned ADR0356 verifier. It does not prove checkpoints outside the registered range, complete persisted history, external persistence-provider authority, actual storage I/O, crash/reopen durability, an authoritative future pin, correct external time, profitability, or trading permission.

All writer, current-pointer, paper, live, complete-history, persistence-authority, and profitability fields remain false. UNKNOWN output is redacted and never includes lineage items, segments, or checkpoint assets.

## Consumer-first activation order

1. Keep the registration and gate unmounted and use supplied synthetic objects only.
2. Accumulate independent preregistered windows without switching current evidence or pointer-v2.
3. Define external persistence-provider authority and durable storage conformance separately.
4. Require an independent coverage audit and an explicit migration decision before any successor field can become truth-bearing.

## Compatibility

The public natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 fields and hash contract are unchanged and no pointer is reissued. The neutral UI remains `SOURCE -> GAP -> MATURITY -> PERMISSION`.
