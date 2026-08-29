# ADR 0019: Report18 strata consumer-first extension

## Status

Accepted as a verifier-only extension. No report builder, writer, protocol-v7
registration, or current migration is implemented.

## Gap

A valid report17 complete-link extension can bind and rebuild gate-v2 without
containing preregistered parent strata, a hierarchy registry asset, or a BOUND
registry assessment. Report17 therefore cannot prove that apparent independent
cluster votes were compressed through an ex-ante classification source.

## Decision

Add strategy-research-preregistered-strata-extension-v1 targeting report schema
18 and strategy-matrix-protocol-v7. Every entry must map exactly to one verified
report17 entry and carry the same source preregistration and complete-link gate,
plus a verified strata registration, strata gate, registry asset, and registry
binding assessment.

Registry expectations are caller inputs, not document claims. The verifier
requires an external selection cutoff, registry asset hash, and classification
source hash for every strategy/variant/lane identity. A re-sealed document
cannot replace those expectations.

Contract status and decision remain separate. A complete-link, strata, or
registry decision BLOCK is valid evidence when all nested documents rebuild
exactly. Contract PASS does not imply decision PASS.

## Boundary

The extension is consumer-only and verifier-only. Writer availability, current
admission, current writer activation, paper authorization, and live ordering
remain false. Protocol-v7 is only a target identifier until a separate protocol
registration is reviewed.

The report17 dependency and report18 consumer support both package imports from
the project root and services imports from the exchange_terminal working
directory. A subprocess regression test keeps both entry styles compatible.

## Next activation steps

1. Register protocol-v7 with report18 and registry-binding prerequisites.
2. Add a formal report writer only after a real registry asset is independently
   approved and persisted.
3. Add a redacted public migration projection.
4. Mount frontend evidence only through a versioned application data route.
5. Review current migration independently.
