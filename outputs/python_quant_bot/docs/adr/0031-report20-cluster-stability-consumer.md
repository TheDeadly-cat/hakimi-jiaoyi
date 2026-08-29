# ADR 0031: Report20 verifier-only cluster stability extension

- Status: Accepted for consumer-first implementation
- Date: 2026-08-21

## Context

A fully verified report19 can produce decision PASS without containing any within-cluster stability evidence. The standalone stability gate closes the statistical point-estimate gap, but it is not yet part of the report chain. Report19 also retains only matrix hashes, so a later consumer cannot safely infer or reconstruct source uncertainty, the correlation matrix, or selection cells from the report document.

## Decision

Add verifier-only `strategy-research-cluster-stability-extension-v1`, targeting report20 and `strategy-matrix-protocol-v9`. It embeds and independently verifies report19, then requires exactly one stability gate for every report19 identity. The caller must separately provide the original base-report hash, the expected report19 extension hash, registry bindings, and a full external stability binding containing the source uncertainty audit, correlation matrix, selection cells, and expected stability-gate hash.

Contract verification remains separate from evidence decision. A valid stability BLOCK produces contract PASS with decision BLOCK. Missing, duplicate, mismatched, resealed, native-type-aliased, or authority-escalated evidence produces contract BLOCK. No source matrix or returns are copied into report20 entries.

## Consequences

The report chain can no longer treat report19 PASS as sufficient evidence of within-cluster stability. The extension is consumer-only and has no production builder, writer, persistence, pointer, current cutover, paper authorization, or live authority. Protocol-v9 preregistration remains a later consumer-first step.
