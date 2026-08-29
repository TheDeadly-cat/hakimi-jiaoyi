# ADR 0012: Protocol-v6 complete-link registration

Status: Preregistration implemented; formal registry and report writer unavailable

## Context

The schema17 complete-link consumer exists, but a future writer must not choose its own topology threshold, overlap rule, source schemas, or migration prerequisites. Existing protocol registration v3 targets protocol-v5 and report schema16 and must remain replayable.

## Decision

Add `strategy-correlation-protocol-registration-v4` targeting protocol-v6 and report schema17. It embeds and independently verifies the existing multiplicity protocol registration v3, then freezes the complete-link topology policy, gate-v2 and audit schemas, schema17 extension contract, and base schema16 hash-binding requirement.

Writer activation requires independent schema16 verification, base-report hash binding, complete-link gate-v2 rebuild, a formal protocol-v6 registry, and schema17 sole-writer migration tests.

The registration is preregistration only. It reports formal registry binding, writer availability, current admission, current writer activation, paper authorization, and live authority as false.

## Consequences

- A future schema17 writer cannot silently lower the 0.75 threshold or 40-observation overlap floor.
- Protocol-v5/report16 remains immutable and replayable.
- Protocol-v6 cannot skip the multiplicity family and protocol-v3 lineage.
- No report writer, current switch, profitability claim, or execution authority is introduced.
