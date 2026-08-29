# ADR 0014: Neutral complete-link migration ledger

Status: Public projection and standalone presenter implemented; application mount pending

## Context

Complete-link protocol registration is internal governance evidence. A public UI must not expose strategy identities, symbols, hashes, raw correlations, or interpret consumer readiness as profitability or execution readiness.

## Decision

Add a redacted public summary with the sequence SOURCE, GAP, MATURITY, PERMISSION. A verified registration-v4 projects an observed source, formal-registry-and-writer gap, consumer-only maturity, and research-only permission. Invalid input projects UNKNOWN and null policy values.

Add a standalone responsive ledger presenter and stylesheet using graphite, warm amber, and cool cyan, with reduced-motion support. A new Node suite wrapper runs the existing presentation suite before the ledger contract.

The component is not automatically mounted in the application. Browser and rendered visual QA remain pending explicit authorization.

## Consequences

- Public output contains no identities, hashes, raw registration, or return data.
- No READY, profitability, paper, or live implication is introduced.
- Existing presentation tests remain first in the wrapper and must continue to pass.
- UI integration can occur later without changing the public summary contract.
