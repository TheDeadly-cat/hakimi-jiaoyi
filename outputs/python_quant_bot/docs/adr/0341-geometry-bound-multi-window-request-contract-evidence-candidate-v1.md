# ADR 0341: Geometry-bound multi-window request-contract evidence candidate v1

- Status: Accepted as synthetic, unregistered request-content evidence only
- Date: 2026-08-24
- Scope: canonical request-content hashing before security-receipt semantics
- Decision authority: none for ADR0334 semantics, transport parsing, authentication, HTTP mounting, current, paper, or live

## Context

ADR0339 request-scope evidence accepts a structurally valid `request_contract_hash`. ADR0340 internally creates an exact ADR0337 request-role mapping, but the current chain has no evidence candidate that derives the scope hash from that actual mapping.

Porting the older security-receipt semantic gate directly would therefore compare authentication, CSRF, and origin evidence against a caller-supplied opaque hash. That would preserve the exact gap that ADR0325 closed in the older portfolio chain.

The current internal candidate request has three fields: its schema version, an ADR0334 evaluation, and the expected ADR0334 evaluation hash. Unlike the older fixed two-field projection request, valid ADR0334 evaluations can neutrally vary across `PASS`, `BLOCK`, and `UNKNOWN`, so one global known request hash is inappropriate.

## Decision

Add a dynamic, versioned request-contract evidence candidate with these rules:

1. Accept only an exact ordered three-field request mapping matching the ADR0337 request-role contract.
2. Snapshot only exact JSON trees and reject cycles, non-finite values, non-string object keys, and requests above 1,000,000 canonical bytes.
3. Require the ADR0334 evaluation's exact 19-field order, frozen schema, contract hash, static fingerprint, neutral authority, and unmounted synthetic state.
4. Recompute the ADR0334 evaluation hash from its first 18 fields and require it to equal both embedded hash references.
5. Preserve exact `PASS`, `BLOCK`, and `UNKNOWN` evaluation status without promotion.
6. Derive a request-payload hash and a method/route/schema/evaluation-bound request-contract hash. No request hash is accepted from the caller.
7. Embed the bounded request snapshot only inside this in-memory evidence candidate. Logging and response embedding are forbidden.
8. Exact verification rebuilds the complete candidate and rejects top-level, request, evaluation, or contract-payload field-order drift.

## Frozen contract

- Request-evidence contract hash: `0d0046487ff4fab91d2be6e7dc1e2da0d352560aabc16250009809164341725a`
- ADR0334 evaluation field-order hash: `104f7e26f5ca98f8a3a8c6bd6a25e568dee4dcb3c37c743494664e7c7b68a793`
- Request-contract payload field-order hash: `6845f7bfb8bfd07f21dad53d3f2d0580c4303a2920aed0d4462fd2cb27799a7e`
- ADR0337 request-role hash: `2d6ad49ff964471733c26c428a8450757d4e00c3f1f268510fd950d31a8d1928`
- ADR0334 binding contract hash: `32edce4777fa90cdc1c79536ea3187133775a368e0e1e401db9f82c165122e47`
- Method: `POST`
- Proposed route: `/api/research/strategy-correlation-clusters/geometry-budget-multi-window-presentation-v9`
- Maximum canonical request size: 1,000,000 bytes
- Static fingerprint: `20260824-strategy-correlation-matrix-geometry-budget-multi-window-presentation-request-contract-evidence-candidate-v1-synthetic-unregistered-lock-1`

## Integrity versus semantics

This candidate proves that one request snapshot is internally consistent with its canonical hashes. It does not have ADR0334 verification contexts and cannot prove that a rehashed evaluation came from the trusted ADR0334 producer. A caller can still alter non-authority semantics and recompute hashes; the evidence remains explicitly non-authoritative.

The next security gate must require all of the following simultaneously:

1. Exact ADR0341 request evidence.
2. Scope `request_contract_hash` equality with the ADR0341 derived hash.
3. Exact ADR0340 production receipt and ADR0339 context-creation receipt.
4. ADR0341 evaluation hash equality with ADR0340's exact-verified evaluation hash.
5. Registered host-owned security receipt providers before any semantic success state exists.

## Adversarial matrix

| Threat | Required result |
| --- | --- |
| Missing, extra, or reordered request role | Reject |
| Wrong request schema | Reject |
| ADR0334 evaluation or expected-hash mismatch | Reject |
| Rehashed paper/live/current promotion | Reject |
| Rehashed non-authority semantic change | Integrity evidence may exist, but semantic authority remains false |
| Exact neutral `BLOCK` or `UNKNOWN` evaluation | Preserve without promotion |
| Non-JSON, cyclic, non-finite, or oversized request | Reject |
| Candidate or nested field-order/hash tamper | Exact verification fails |
| Scope built with unrelated caller hash | Future cross-binding gate must reject |
| Logging, response embedding, HTTP/current/paper/live inference | Explicitly forbidden |

## Remaining blockers

- The evidence is not yet required by ADR0339 or ADR0340 call signatures.
- External HTTP-body parsing and transport ownership remain unregistered.
- ADR0334 source semantics require ADR0340 production-receipt cross-binding.
- Authentication, CSRF, origin, request-scope, and generation-ID producers remain unregistered.
- No lifecycle owner, trusted provider, handler, or route is bound.
- No runtime, database, cache, filesystem, network, scheduler, browser, or trading access is introduced.
- Natural-forward evidence, legacy pack-v5 public UNKNOWN behavior, and pointer-v2 remain unchanged.
- No profitability claim and no paper/live authority are created.
