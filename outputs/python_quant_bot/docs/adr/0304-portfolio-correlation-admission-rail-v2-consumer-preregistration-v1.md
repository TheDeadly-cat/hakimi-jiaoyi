# ADR 0304: Portfolio correlation admission rail v2 consumer preregistration v1

## Status

Accepted as an isolated, unmounted, research-only contract.

## Context

ADR 0302 preregisters the Python and JavaScript in-memory delivery adapters.
ADR 0303 adds a pure presentation rail for the correlation admission v2
envelope. ADR 0302 deliberately leaves the presentation rail, stylesheet,
payload source, host slot, route, render path, and UI mount absent.

Mounting ADR 0303 directly would skip the consumer-first activation order. A
compatible-looking file could drift in its source hash, export order, stage
order, tier order, CSS namespace, or predecessor contract while still being
loaded by an eager host integration.

## Decision

Add a versioned Python preregistration contract before any host integration.
The contract pins:

- the exact ADR 0302 adapter registration hash;
- the delivery envelope schema and static fingerprint;
- the rail schema and static fingerprint;
- the two callable exports and their order;
- SOURCE, GAP, MATURITY, PERMISSION order;
- the seven admission tiers and their order;
- the isolated CSS namespace;
- the implementation, stylesheet, Node contract, and ADR 0303 SHA-256 values;
- the renderer input as the exact delivery envelope rather than a view model;
- the terminal permission state as UNAUTHORIZED.

The candidate manifest contains paths, hashes, contract metadata, and negative
authority facts. It does not contain source bytes, delivery envelopes, strategy
identifiers, symbol lists, DOM state, browser state, or runtime observations.

The binding output is hash-only. A local PASS means only that the exact
preregistration, candidate manifest, and ADR 0302 adapter registration agree.
Its overall status remains BLOCKED and all host, render, mount, current, paper,
live, and execution permissions remain false.

Malformed or non-strict JSON inputs become UNKNOWN. Correctly resealed but
unexpected documents become BLOCK. Extra fields are drift rather than forward
compatibility.

## Consumer-first activation order

1. Consumer preregistration.
2. Independent source hash measurement.
3. Hash-only candidate binding.
4. Separate host registration review.
5. Separate isolated mount review.
6. Separate current-writer review.

No later item is implied by an earlier PASS. In particular, this ADR does not
authorize item 4, 5, or 6.

## Adversarial contract

The synthetic contract covers:

- malformed preregistration, candidate manifest, and adapter registration;
- correctly resealed preregistration drift;
- implementation hash and CSS namespace drift;
- export, stage, and tier order drift;
- correctly resealed ADR 0302 host-plan drift;
- extra manifest fields;
- correctly resealed binding authority escalation;
- cyclic inputs and container subclasses;
- permanent current, paper, live, browser, DOM, render, and mount locks.

## Non-goals

- No source-file reader or runtime hash scanner.
- No import into app.js or index.html.
- No stylesheet registration.
- No endpoint, route, or payload-source registration.
- No DOM access, render call, browser launch, or visual claim.
- No current writer, scheduler, paper, live, or order path.
- No profitability claim.
- No change to the natural-forward evidence chain.
- No pack-v5 compatibility promotion.
- No pointer-v2 field, hash, or publication change.

## Activation acceptance boundary

A future host-registration proposal must consume an independently measured
candidate manifest and an exact PASS binding. It must define a new versioned
host slot, preserve SOURCE to GAP to MATURITY to PERMISSION, retain UNKNOWN on
missing or invalid input, and receive separate authorization and adversarial
review. This ADR alone cannot activate or mount the rail.
