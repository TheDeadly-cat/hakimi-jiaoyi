# ADR0109: Provider-identity uniqueness/freshness longitudinal coverage v1

## Status

Accepted as an inactive, fail-closed research contract. It is not connected to current evidence, UI, server, engine, CLI, paper, or live paths.

## Context

ADR0108 verifies detached, signed complete-scan cardinality and time-window claims for one checkpoint while leaving external trust, actual uniqueness, freshness, and replay absence false. A single checkpoint cannot show whether the same signed claim remains stable as the append-only registry grows.

Adding another external attestation would only move the trust assumption. The locally provable next step is a preregistered longitudinal consumer that reruns ADR0108 over an exact bounded checkpoint sequence.

## Decision

Register a closed tree-size window with at least three evaluations, a fixed assertion digest and leaf index, a fixed ADR0108 registration receipt, a checkpoint step of one, and a maximum claimed reference-time gap.

The evaluator must:

1. Reverify every ADR0108 evaluation from its full inputs.
2. Require every tree size in the preregistered closed range with no missing or extra item.
3. Require each next `previous_segment` to equal the prior `current_segment` and its lineage previous-binding hash to equal the prior current-binding hash.
4. Keep registry, assertion digest, leaf index, occurrence provider, time authority, and source registration stable.
5. Require unique evaluation, checkpoint, and occurrence-receipt hashes.
6. Require strictly increasing scan and reference-time claims with preregistered maximum reference gaps.
7. Reject any source result that promotes uniqueness, freshness, replay absence, complete history, or authority.

## Authority boundary

The highest state is `CONTIGUOUS_SIGNED_SINGLE_OCCURRENCE_CLAIM_PREFIX_VERIFIED_EXTERNAL_TRUST_UNPROVEN`.

This state proves an exact, bounded, locally supplied prefix of internally consistent signed claims. It does not prove the external occurrence index was complete, either witness was authoritative, the reference times were correct, checkpoints outside the window were covered, future replay is absent, or the assertion is globally unique or fresh. All truth-bearing and trading authority fields remain false.

## Activation order

1. Keep the consumer inactive and use pure synthetic supplied sequences only.
2. Accumulate multiple independent bounded windows without switching current evidence.
3. Define external provider conformance and key-governance evidence separately.
4. Require an independent coverage/trust audit and an explicit migration decision before any successor field can become truth-bearing.

## Validation evidence (2026-10-03)

- Targeted longitudinal coverage contract: 37/37 PASS.
- Independent real three-checkpoint public-API chain: 29/29 PASS. Every replay, persistence, binding, lineage, and ADR0108 evaluation was reverified before coverage evaluation.
- Adversarial matrix: missing checkpoints, tree-size skips, assertion drift, reference-gap excess, valid segment forks, source truth promotion, and registration tampering all fail closed.
- Cross-lag factor calibration family: 884/884 PASS across 44 modules.
- In-memory syntax compilation: 2/2 PASS.
- Lean validation: 19 checks listed; dry-run planned 19, executed 0, runtime mutations false, paper false, live false.
- Explicit active-source references: 0.

The strongest state remains `CONTIGUOUS_SIGNED_SINGLE_OCCURRENCE_CLAIM_PREFIX_VERIFIED_EXTERNAL_TRUST_UNPROVEN`. The verified range was tree-size 1 through 3 with a maximum observed claimed reference-time gap of 100 ms. This bounded synthetic prefix does not make uniqueness, freshness, replay absence, complete history, external trust, or any authority field true.