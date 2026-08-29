# ADR 0131: Strategy correlation return replay complete alias upstream contract v1

## Status

Accepted as a regression and evidence receipt. The production return-replay
implementation is unchanged. This decision does not activate a writer, register
a route, admit a current artifact, or authorize paper/live use.

Static fingerprint:
20260822-strategy-correlation-return-replay-complete-alias-contract-1

## Context

ADR 0130 observed 183 accepted bool/int aliases inside an uncertainty-audit
matrix when verify_correlation_matrix_replay was mocked to PASS. That result
demonstrates the audit builder's explicit reliance on its upstream verifier; it
does not prove that the real replay chain accepts those aliases.

The actual synthetic return-replay fixture contains five datasets with 61
completed rows each. Every attack changes one row from complete=True to
complete=1, then correctly reseals both the nested input_hash and outer
replay_hash before invoking the real verifier.

## Decision

Persist a regression contract covering all 305 completed rows. Require every
resealed alias attack to BLOCK with correlation_replay_input_invalid.

Pin the unchanged production source SHA-256:
E238A4B502892CD3EB91E2C10DC203C9618270F9BF578E7E8774CC66D231BB09

Do not add redundant strict equality to uncertainty or multiplicity builders.
Their source documents are accepted only after their declared upstream verifier
contracts succeed.

## Compatibility and authority

This receipt changes no schema, builder, verifier, hash algorithm, natural
forward evidence, legacy pack-v5 UNKNOWN behavior, pointer-v2 contract, current
admission, route registration, profitability claim, paper authorization, or
live authorization.
