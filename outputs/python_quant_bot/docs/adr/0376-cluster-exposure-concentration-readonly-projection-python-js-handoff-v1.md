# ADR 0376: Concentration Projection Python-to-JavaScript Handoff v1

- Status: implemented, additive, unmounted
- Date: 2026-08-24
- Scope: exact in-memory interface bridge
- Authority: none

## Decision

Add a dedicated ADR0375 handoff schema. The builder calls the full ADR0375
exact verifier with every upstream batch, projection, proposal, exposure-policy,
concentration-policy, hash, and context input. Only an exact result produces the
four-field presenter envelope.

The bridge does not reuse ADR0373 because absolute exposure and concentration
are separate public schemas. JSON cloning rejects NaN and unsupported values
and prevents aliasing. Wrong hashes, resealed authority changes, and envelope
mutation fail closed.

## Cross-language evidence

Python tests pass balanced, concentration-blocked, upstream-blocked, and unknown
envelopes through stdin to the actual ADR0377 Node presenter. No temporary file,
DOM, browser, service, route, or runtime loader is used.

## Authority boundary

The bridge is unmounted and has no file, network, Node, subprocess, storage,
HTTP, engine, pointer, scheduler, paper, or live operation. Presenter acceptance
proves schema interoperability only, not diversification, market validity,
rendered UI, profitability, or trading authorization.
