# ADR 0085: Factor Calibration Precommit Report Consumer v7

- Date: 2026-09-13
- Status: Accepted for local research, unmounted

## Context

Precommit gate v7 adds a verified finite-horizon omnibus guard over lags 4, 5,
and 6. Report consumer v6 only understands the lag-1-through-lag-3 precommit
surface. Treating that older report as sufficient would hide an omnibus block
while preserving a locally positive consumer state.

## Decision

Add a versioned report consumer v7 that fully re-verifies both report consumer
v6 and precommit gate v7 against one complete synthetic source context.

The consumer returns VERIFIED_LOCAL_BINDING only when report consumer v6 is
VERIFIED_LOCAL_BINDING and precommit gate v7 has the finite-horizon positive
decision. A verified block from either source is monotone and maps to
VERIFIED_BLOCK. Missing, unsupported, invalid, incompatible, or cross-hash
drift maps to UNKNOWN.

The public projection contains only:

- source decisions, verification states, and bound hashes;
- protocol metadata inherited from report consumer v6;
- aggregate lag coverage 1 through 6 and omnibus band 4 through 6;
- one omnibus quadratic-energy ceiling and one observed aggregate;
- fold and unstable-identity counts;
- explicit blockers, facts, and locked authority.

Rows, returns, beta values, residual values, per-lag values, identities, and
private fold ledgers remain outside the public contract.

## Consequences

- The known synthetic distributed-lag path can keep consumer v6 locally
  positive while consumer v7 correctly reports VERIFIED_BLOCK.
- The layer is consumer-first and remains unmounted. No presentation envelope,
  current pointer, scheduler, paper path, or live path consumes it.
- This contract is research evidence only. It is not profitability evidence or
  trading authorization.
