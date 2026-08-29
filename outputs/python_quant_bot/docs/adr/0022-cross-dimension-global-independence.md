# ADR 0022: Cross-dimension global independence

## Status

Accepted as a consumer-only audit and gate. It does not replace the existing
strata gate-v1, report18, protocol-v7, or any current writer.

## Gap

The preregistered strata gate evaluates every dimension independently. A
synthetic three-cluster example passed all three dimensions while every cluster
pair shared a parent stratum in one dimension. No pair was globally independent,
yet the gate reported PASS.

## Decision

Add strategy-correlation-strata-global-independence-audit-v1 and
strategy-correlation-preregistered-strata-gate-v2.

Two clusters conflict when they share a parent stratum in any preregistered
dimension. The audit builds the union conflict graph and computes an exact
maximum pairwise-independent cluster set for both all registered clusters and
passing clusters. The vote gate uses the registered independent capacity as the
fixed denominator, requires at least two globally independent passing votes,
and preserves the fixed 60 percent fraction.

Exact search is limited to 24 clusters and 250,000 search nodes. Exceeding
either limit blocks the audit. No approximate capacity is reported or used.

The gate independently rebuilds the source preregistration, strata
registration, complete-link gate, and base strata gate. It preserves monotonic
BLOCK evidence and seals the conflict graph, capacities, witnesses, and search
facts with strict canonical hashes.

## Boundary

The new gate is consumer-only and requires a new report schema. Writer
implementation, current admission, current writer activation, paper
authorization, and live ordering remain false. Exact synthetic evidence is not
profitability evidence or trading authority.

## Next activation steps

1. Add a report19 consumer for global-independence gate-v2.
2. Register protocol-v8 only after the report19 consumer is independently
   verified.
3. Add a redacted public projection without cluster identities.
4. Consider a writer only after a real registry asset and formal persistence
   exist.
5. Review current migration independently.
