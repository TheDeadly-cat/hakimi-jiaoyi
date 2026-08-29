# ADR 0020: Protocol-v7 strata registration

## Status

Accepted as a preregistered consumer protocol. No formal registry, report
writer, protocol current migration, paper authority, or live authority exists.

## Gap

Protocol-v6 freezes complete-link gate-v2 and report17 but does not require
preregistered parent strata, a hierarchy registry asset, BOUND external hashes,
or report18 verification. A report18 consumer without a matching protocol
registration would leave those requirements outside the preregistered protocol.

## Decision

Add strategy-correlation-protocol-registration-v5 targeting
strategy-matrix-protocol-v7 and report schema 18. It embeds and exactly rebuilds
a verified registration-v4 source for protocol-v6.

Its strategy-correlation-strata-policy-v1 freezes the report18 extension and
verification schemas, strata registration and gate schemas, registry asset and
binding schemas, independent report17 verification, source and strata exact
rebuilds, external registry-asset and classification-source hashes, selection
cutoff binding, a real registry asset requirement, and sole-writer migration
tests.

## Boundary

The registration status remains PREREGISTERED. The report18 consumer and
candidate registry contracts may be available, but formal_registry_bound,
writer_available, formal registry activation, current admission, paper
authorization, and live ordering remain false.

Protocol modules retain their existing project-root package import convention.
This decision does not broaden script-style import compatibility through the
older multiplicity and protocol-binding chain.

## Next activation steps

1. Add a registry-binding public migration projection for protocol-v7.
2. Supply and independently approve a real hierarchy classification asset.
3. Implement a report18 writer only after formal asset persistence and
   sole-writer migration tests exist.
4. Review current migration independently.
