# ADR0483: Execution-authority single-pass equivalence v1

Date: 2026-08-25

## Status

Accepted for the shared fail-closed authority scanner. This is an internal
performance change, not a new authority contract or evidence-chain version.

## Context

Profiling the pure-synthetic replay-cursor fixture chain attributed about
12.46 million calls to `authority_violations`. The scanner recursively entered
the public function for every scalar, allocated and extended an empty list for
each leaf, and repeatedly normalized common field names. A deterministic
1,200-row, 40-scan pre-change benchmark had a five-round median of `0.436001s`.

The scanner is a permission boundary. Performance work is acceptable only if
it preserves exact traversal order, reported paths, Unicode NFKC/case-folding,
localized aliases, custom paths, container support, and the rule that only the
native singleton `False` is non-violating.

## Decision

1. Accumulate violations into one closure-owned list instead of recursively
   allocating one list per value.
2. Recurse only into `Mapping`, `list`, and `tuple` containers. Scalars cannot
   contain nested authority claims and no longer receive a no-op function call.
3. Cache canonicalization by the already-converted text value with a bounded
   `4096`-entry LRU. Conversion happens before the cache, preserving unhashable
   input support and observing the current text of mutable/custom objects.
4. Keep the public names, inputs, output type, ordering, aliases, and consumers
   unchanged. No compatibility route or version activation is required.

## Consumer-first acceptance

The shared scanner remains the sole consumer entry point. Acceptance requires:

- direct scanner and sanitizer contracts;
- the mandatory `live_authorized` alias contract;
- an independent historical-reference implementation over adversarial aliases,
  non-string keys, scalar roots, unhashable canonicalization inputs, mutable text,
  nested mappings/lists/tuples, and a deterministic synthetic corpus;
- the replay-cursor fixture setup benchmark, because it exposed the hotspot;
- unchanged protected frontend fingerprints.

## Safety boundaries

This work reads no market, runtime, database, cache, log, credential, paper, or
live state. Passing synthetic equivalence and timing checks does not establish
profitability, strategy maturity, paper authorization, or live authorization.
The current single-look evidence chain, legacy pack-v5 UNKNOWN behavior, and
pointer-v2 no-reissue contract are unchanged.
