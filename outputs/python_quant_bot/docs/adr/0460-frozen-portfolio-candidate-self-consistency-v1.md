# ADR 0460: Frozen portfolio candidate self-consistency v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Frozen development candidate construction and verification

## Context

The v6 verifier checked the outer candidate hash and several governance
contracts, but it did not rebuild all facts available inside the candidate. A
valid synthetic candidate remained `PASS` after each of the following changes
was applied and the unkeyed outer hash was recomputed:

- replacement of the universe contract with an empty object;
- replacement of the temporal exposure audit hash with an invalid value;
- divergence of `candidate_id` from the frozen spec;
- removal of `research_report_hash`.

## Decision

Upgrade new frozen candidates to `frozen-portfolio-candidate-v7` and add
`frozen-portfolio-candidate-self-consistency-v1`:

1. Candidate, spec, dataset, and report anchor fields must have canonical,
   non-empty identities where the frozen object carries an anchor.
2. `candidate_id` must equal the identifier derived from the frozen spec.
3. The embedded universe contract is reverified by its formal verifier.
4. The temporal exposure audit hash is recomputed from its embedded payload.
5. Non-object candidate inputs return a structured `BLOCK` rather than raising.

The contract proves internal consistency, not cryptographic authenticity. A
coherent replacement with newly valid upstream objects still requires external
experiment, file-hash, completion, and activation bindings.

Consumers import the candidate schema through the shared constant; no external
hard-coded v6 consumer was found. Existing v6 artifacts are not rewritten.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Valid v7 synthetic candidate | PASS, research-only |
| Empty resealed universe contract | BLOCK from universe verifier |
| Invalid resealed temporal audit hash | BLOCK from hash recomputation |
| Resealed candidate/spec ID mismatch | BLOCK |
| Missing report hash at build or verify | BLOCK |
| Non-object candidate | Structured BLOCK without exception |

## Boundaries

- Tests use only synthetic reports and isolated temporary source files.
- No candidate is activated and no formal report directory is read.
- No backtest, market task, service, browser, scheduler, runtime database, paper
  order, or live order is started.
- Paper/live remain unauthorized, and the public evidence chain is unchanged.
