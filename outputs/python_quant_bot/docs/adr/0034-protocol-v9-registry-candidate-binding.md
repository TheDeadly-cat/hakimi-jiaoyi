# ADR 0034: Protocol-v9 registry candidate and external binding

- Status: Accepted for candidate-only implementation
- Date: 2026-08-21

## Context

Registration-v7 preregisters report20 and its stability policy but contains no protocol-v9 registry asset or binding hash. A registration document cannot self-authenticate an external governance snapshot, and a candidate must remain distinct from formal registry activation.

## Decision

Add pure `strategy-correlation-cluster-stability-registry-asset-v1` and `strategy-correlation-cluster-stability-registry-binding-assessment-v1` contracts. The asset binds registration-v7, the cluster-stability policy, report20, stability schemas, an external registry source hash, and effective/frozen timestamps. Its status is always `FROZEN_CANDIDATE`.

The assessment requires caller-supplied expected asset, source, registration, and policy hashes plus an evidence cutoff. Candidate binding succeeds only when the asset and protocol independently verify, all hashes bind, report20/stability schemas match, and effective/frozen dates precede evidence. Success is named `CANDIDATE_BOUND`; formal registry remains unbound.

## Consequences

No file, database, network, service, pointer, writer, or formal registry is created. Candidate evidence can satisfy only a future externally verified prerequisite. Formal registry activation, current admission, paper authorization, and live authority remain false.
