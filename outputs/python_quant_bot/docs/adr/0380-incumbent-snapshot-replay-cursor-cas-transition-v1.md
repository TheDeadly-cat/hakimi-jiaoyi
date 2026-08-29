# ADR0380: Incumbent Snapshot Replay Cursor CAS Transition v1

## Status

Accepted as an unmounted, pure-synthetic, research-only candidate protocol.

## Context

ADR0379 can prove that a supplied incumbent snapshot attestation is fresh and
unseen relative to a supplied replay cursor. It intentionally never mutates the
cursor. Two evaluations against the same cursor can therefore return the same
candidate, and neither evaluation proves that another consumer did not win a
concurrent update.

ADR0276 already defines the project's fail-closed CAS semantics for a nonce
registry. Its state cannot be reused directly here: the nonce registry sequence
equals its unique replay-key count, while an incumbent snapshot cursor tracks an
upstream sequence that can advance by a policy-bounded jump. Conflating these
invariants would create a false compatibility contract.

## Decision

Add a domain-isolated CAS transition protocol with three bounded documents:

- a hash-bound transition intent produced only from an exact ADR0379 fresh,
  unreplayed candidate;
- a deterministic synthetic transition receipt;
- an immutable returned cursor paired with that receipt.

The intent binds the stream, projection preregistration, ADR0379 result
fingerprint, candidate attestation, expected cursor, expected high-water state,
request nonce, and proposed cursor hash.

Simulation checks outcomes in this order:

1. candidate attestation already consumed: `ALREADY_CONSUMED`, `BLOCK`;
2. candidate sequence not above observed high-water:
   `SNAPSHOT_SEQUENCE_NOT_ABOVE_OBSERVED_HIGH_WATER`, `BLOCK`;
3. observed cursor differs from the expected cursor:
   `COMPARE_AND_SWAP_CONFLICT`, `UNKNOWN`;
4. exact expected cursor:
   `ADVANCED_IN_RETURNED_CURSOR`, `UNKNOWN`.

The successful path returns a new immutable cursor with the candidate
attestation added to the canonical consumed set. It does not mutate either
input cursor. Repeating the simulation against the same old cursor produces the
same returned cursor and receipt, so every receipt fixes these fields to false:

- `input_cursor_mutation_performed`;
- `atomic_storage_commit_verified`;
- `durable_commit_verified`;
- `linearizable_read_verified`.

No outcome has `gate_status=PASS` or trading permission.

## Consumer-first activation order

1. Keep this protocol unmounted and synthetic.
2. Add a separate hash-only public projection and exact consumer contract.
3. Define a replay-cursor provider port with one atomic CAS operation.
4. Require authenticated provider authority, durable commit evidence, and
   linearizable read evidence.
5. Add a later receipt version that consumes provider evidence without
   upgrading legacy synthetic receipts.
6. Review current-chain activation and neutral UI presentation separately.

## Adversarial matrix

- exact expected cursor returns an immutable candidate cursor, still UNKNOWN;
- sequential duplicate blocks before stale-head conflict evaluation;
- nonmonotonic unseen sequence blocks;
- changed cursor with a still-fresh candidate returns CAS conflict;
- two simulations from the same old cursor are equal and prove no atomicity;
- tampered intent, cursor, attestation, or expected hash is rejected;
- an ADR0379 blocked or UNKNOWN result cannot produce an intent;
- changing the request nonce changes the intent but not the proposed cursor;
- no storage commit API is exposed.

## Non-claims

This protocol does not read or write a database, cache, file, runtime registry,
service, browser, scheduler, or market-data source. It does not prove atomic
storage execution, durability, linearizability, provider identity, real
holdings, wall-clock freshness, session freshness, strategy performance,
profitability, paper authority, or live authority.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. pointer-v2 is unchanged and is
not reissued by this protocol.
