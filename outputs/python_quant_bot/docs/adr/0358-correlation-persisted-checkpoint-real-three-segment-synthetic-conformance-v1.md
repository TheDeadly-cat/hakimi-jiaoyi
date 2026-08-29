# ADR0358: Persisted-checkpoint real three-segment synthetic conformance v1

## Status

Accepted as a test-only, no-I/O conformance fixture. It is not a production source, storage adapter, scheduler, current-evidence consumer, paper path, or live path.

## Context

ADR0357 requires at least three ADR0356 lineage documents. Its first independent matrix reverified two real ADR0356 documents but used a controlled source-verifier replacement for the third synthetic extension. That proved the history consumer in isolation, but not a complete three-document source composition.

The reviewed ADR0356 test extension was intentionally one-shot and fixed to a four-leaf Merkle tree. Reinvoking it cannot produce tree size five. A genuine third document additionally requires a five-leaf root, tree-four to tree-five consistency proof, two lifecycle-receipt inclusion proofs, a common previous-checkpoint commitment across windows, signed replay checkpoints and occurrence audits, a rebuilt common-view preregistration, signed persistence write/reopen receipts, and a strictly later persistence asset inside the registered source reference window.

## Decision

Add a reusable integration fixture under `tests/` that constructs the complete synthetic chain with existing public builders and real local test keys:

1. Reuse the reviewed tree-three ADR0356 anchor and tree-four extension.
2. Build tree five as `node(tree_four_root, new_leaf)`.
3. Verify the one-node tree-four to tree-five consistency proof and both three-node inclusion proofs before assembling documents.
4. Pin one common previous tree-four checkpoint commitment across both windows so the ADR0352 common-view contract remains exact.
5. Rebuild and verify both signed lifecycle replay gates and the ADR0352 preregistration/source gate.
6. Build a tree-five persistence asset at `02:51Z`, after the tree-four asset at `02:46Z`, with signed write and reopen receipts at `02:54Z` and `02:57Z` inside the source reference window.
7. Reverify the ADR0354 receipt state, ADR0355 source binding, and ADR0356 tree-five lineage document.
8. Submit all three ADR0356 documents to ADR0357 without patching or replacing either the ADR0356 verifier or ADR0357 source-consumer verifier.

## Evidence boundary

The fixture proves a deterministic, locally supplied, pure-synthetic tree `3 -> 4 -> 5` composition under an explicit fixture lifecycle. It performs no filesystem persistence, database access, runtime mutation, service start, scheduling, market-data read, or trading action.

This is not an all-source-unmocked chain. The inherited provider-attestation fixture keeps exactly three upstream synthetic seams active while the documents are built and reverified: correlation-matrix replay verification, calendar-session verification, and provider-identity assertion verification. Their targets are enumerated by the fixture and asserted by contract. ADR0356 and ADR0357 verifiers themselves are not patched or replaced. Cleanup ends all three seams after the integration class completes.

The three source documents remain synthetic and unmounted. This does not prove external replay-registry authority, external occurrence-auditor authority, external persistence-provider authority, actual write/reopen durability, crash recovery, complete history outside the registered prefix, correct external time, profitability, paper permission, or live permission.

## Compatibility

No production module or frontend file is changed. ADR0357 schema, contract hash, static fingerprint, and authority boundary remain unchanged. The natural-forward public evidence chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 contract, and neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` UI remain unchanged.
