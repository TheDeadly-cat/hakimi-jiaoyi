# ADR 0042: Temporal report21 public projection and unmounted lockboard

Date: 2026-08-21

## Status

Accepted as a redacted read-only projection and unmounted visual asset.

## Context

Report21 and protocol-v10 are verifier-only contracts. Exposing their nested reports,
bindings, hashes, identities, correlations, intervals, or returns would weaken the
public evidence boundary. Treating preregistration or a consumer PASS as activation
would be materially misleading.

## Decision

Add one exact public projection with four ordered sections: SOURCE, GAP, MATURITY,
and PERMISSION. It distinguishes a missing report21 contract from an invalid supplied
contract, and distinguishes a verified PASS from a verified BLOCK. Even a verified
PASS is labelled unbound because no formal registration-to-report binding exists.

Add an unmounted lockboard component. Its signature is a three-aperture register for
the preregistered 20-return windows. The apertures communicate frozen boundaries only;
they never expose or imply per-window performance. A seven-stop migration rail ends at
formal binding, writer, and current locks.

## Consequences

- All hashes, reports, external bindings, identities, values, and profitability metrics
  remain redacted.
- Invalid source, contract, type, fingerprint, or authority input renders UNKNOWN.
- NOT_SUPPLIED remains distinct from UNKNOWN.
- PASS, BLOCK, UNBOUND, MISSING, and LOCKED remain distinct and never become READY.
- The component has no DOM discovery or automatic mount behavior and is absent from
  the main application source.
- No endpoint, writer, pointer, current route, paper authority, live authority, or
  execution path is added.
