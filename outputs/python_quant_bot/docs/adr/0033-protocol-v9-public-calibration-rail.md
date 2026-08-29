# ADR 0033: Protocol-v9 public calibration rail

- Status: Accepted for standalone migration presentation
- Date: 2026-08-21

## Context

The existing within-cluster calibration rail understands standalone gate PASS/BLOCK evidence but not registration-v7. A real protocol-v9 registration therefore degrades to UNKNOWN even though report20 and its policy are preregistered. Replacing the old summary would break gate-evidence replay, while displaying registration documents directly would expose hashes, nested source registrations, and research governance internals.

## Decision

Add `strategy-correlation-cluster-stability-protocol-migration-public-summary-v1` with static fingerprint `20260821-cluster-stability-protocol-v9-migration-rail-1`. It independently verifies registration-v7 and exposes only protocol/report targets, fixed source/gap/maturity/permission labels, and the writer-prerequisite count. Hashes, source registrations, registry identity, research identities, correlations, intervals, and returns remain redacted.

Extend the existing calibration rail backward-compatibly. Gate summaries still present PASS/BLOCK evidence. Protocol summaries present protocol-v9, report20 consumer, and stability policy as sealed, followed by missing formal registry, missing report20 writer, and locked current. Invalid, partial, type-aliased, authority-escalated, or fingerprint-drifted summaries render UNKNOWN.

## Consequences

The UI accurately reflects preregistration maturity without implying activation. The component remains standalone and unmounted, with no network, browser, service, writer, persistence, current cutover, paper authorization, or live authority.
