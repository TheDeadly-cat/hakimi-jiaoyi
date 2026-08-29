# ADR 0018: Strata registry candidate and binding

## Status

Accepted as a consumer-first source contract and binding assessment. No real
classification asset is created by this decision.

## Gap

The strata registration can freeze a valid cluster partition without recording
where the classification came from, which source content was used, when the
classification became effective, or whether it was frozen before selection.
Self-consistent registration hashes therefore do not prove ex-ante provenance.

## Decision

Add strategy-correlation-strata-registry-asset-v1. A candidate asset requires an
explicit external classification source name, source version, lowercase SHA-256
content hash, effective date, UTC freeze timestamp, source preregistration hash,
and the canonical strata dimensions. Its methodology permanently states that
selection returns were not used and post-selection edits are not allowed.

Add strategy-correlation-strata-registry-binding-assessment-v1. Binding requires
independent verification of the registry asset and strata registration, caller-
supplied expected hashes for both the registry asset and classification source,
exact source-preregistration and dimension equality, and effective/frozen dates
strictly before the selection cutoff.

Centralize the stricter research evidence authority surface in
strict_research_authority. This wrapper preserves the existing execution-
authority aliases and adds native-false enforcement for current, writer, formal
registry, paper, and live fields.

## Boundary

The registry asset remains FROZEN_CANDIDATE and the assessment can report BOUND,
but formal registry activation, writer activation, current admission, paper
authorization, and live ordering remain false. Synthetic tests do not create or
approve a real classification source.

## Next activation steps

1. Supply an independently reviewed real classification snapshot and its
   content hash.
2. Persist that asset only through a separately reviewed formal registry path.
3. Require the BOUND assessment in the future report-schema consumer.
4. Add a writer only after the report schema and formal registry are frozen.
5. Review current migration independently.
