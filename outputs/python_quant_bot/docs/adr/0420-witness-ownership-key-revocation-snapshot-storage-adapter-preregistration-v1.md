# ADR0420: Witness Key-Revocation Snapshot Storage Adapter Preregistration v1

## Status

Accepted as an unmounted, research-only preregistration contract on 2026-08-24.

## Context

ADR0412 owns the witness ownership anti-replay state transition.  ADR0418 owns
the immutable revocation-snapshot manifest and current-head publication
semantics.  ADR0419 preregisters an external provider identity/source adapter.
None selects or verifies a storage domain for snapshot publication.

Other-domain persistence registrations cannot be reused because they bind
different replay assets and receipt semantics.  Reusing ADR0412 would also
collapse two aggregates: ownership consumption state and revocation snapshot
publication state.

## Decision

Add an exact storage-adapter preregistration builder/verifier with these rules:

1. Bind the ADR0419 identity/source registration hash, schema, implementation
   hash, ADR0418 stream, publication port hash, and consumer hash.
2. Declare an adapter by stable ID, static fingerprint, and implementation hash
   without importing or running it.
3. Store only hashes for the storage domain, immutable-content namespace, and
   current-head namespace.  Store no path, connection string, bucket, table,
   credential, or secret.
4. Fix backend-neutral semantics to content-addressed no-clobber publication,
   conditional compare-and-swap head update, one exact post-success current-head
   read, and no automatic retry or reissue.
5. Allow one declared backend kind per record: local filesystem, transactional
   database, or conditional object store.  The backend kind changes only one
   additional evidence requirement and grants no capability.
6. Require distinct semantic hashes and distinct durability, crash-recovery,
   and concurrency-control protocol IDs.
7. Keep thirteen common and one backend-specific evidence classes explicitly
   `UNOBSERVED`.
8. Keep runtime observation, implementation reproduction, namespace
   confinement, immutability, atomic CAS, durability, restart reads,
   rollback/equivocation detection, publication authority, current-chain
   activation, paper authority, and live authority false.

## Required evidence

Common requirements cover implementation reproducibility, storage-domain
ownership, namespace confinement, no-clobber collision behavior, strict bounded
reads, single-winner CAS, conflict without retry, three crash windows, restart
read consistency, rollback/equivocation detection, and an independent observer.

Backend-specific requirements cover Windows/reparse and same-volume semantics,
database isolation/unique constraints, or object-store conditional generation
and read consistency.  They are requirements only, not observed evidence.

## Consumer-first activation order

1. Keep this registration unmounted and use only synthetic hashes.
2. Define a versioned persistence evidence contract bound to this registration.
3. Select one real backend only after its owner, domain, namespace, recovery
   semantics, and isolated test boundary are explicitly authorized.
4. Implement the adapter and run crash/restart and concurrent CAS tests in an
   isolated location, never against project runtime state.
5. Obtain independent observer evidence before any current-consumer decision.

## Consequences

ADR0420 closes the storage preregistration-shape gap.  It does not create a
storage adapter and proves no atomicity, durability, restart consistency, or
external persistence.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
