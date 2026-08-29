# ADR0410: Shared strict Ed25519 public parsing contract v1

Date: 2026-08-24

Status: Accepted as an internal refactor contract

## Context

The unmounted v7-v10 provenance consumers each independently implemented canonical base64 decoding and canonical DER Ed25519 SubjectPublicKeyInfo parsing. A current-state bytecode/constant audit found one semantic fingerprint for each helper across all four modules, meaning four copies represented one security boundary. Keeping identical parsers duplicated increases future drift risk: one version could later accept whitespace, noncanonical padding, a non-Ed25519 key, or noncanonical DER while another remains strict.

The witness anti-replay and latestness facts remain false. This refactor must not be used to imply progress on real checkpoint ownership or source truth.

## Decision

Add `strict_ed25519_public_contract_v1.py` with two versioned public functions:

1. `decode_canonical_base64_v1` accepts only nonempty canonical base64 and rejects invalid characters, whitespace, and noncanonical encodings.
2. `load_canonical_ed25519_public_key_v1` accepts only nonempty bytes containing canonical DER SubjectPublicKeyInfo for an Ed25519 public key.

v7-v10 import these functions under their existing private helper names. Their schemas, static fingerprints, signature domains, digest message formats, decisions, hashes, blockers, limitations, and authority structures are not redesigned.

## Invariants

- Base64 must round-trip through strict decoding and canonical re-encoding.
- SPKI must parse as Ed25519 and serialize byte-for-byte to the supplied DER.
- Empty values, non-string base64, malformed DER, trailing DER bytes, and non-Ed25519 keys are rejected.
- The shared production module contains no private key, signing operation, clock, filesystem, network, database, cache, log, runtime, scheduler, or writer access.
- v7-v10 retain local-only semantics and public `admission_status=BLOCKED`.
- No `current`, pointer, public evidence-chain, paper, or live behavior changes.

## Validation scope

- Dedicated adversarial tests cover canonical and malformed base64/SPKI inputs.
- Existing v7-v10 tests prove compatibility at each signed provenance layer.
- The complete v1-v10 plus application-binding matrix checks predecessor behavior.
- Source hashes change because imports and duplicate helpers change; historical ADR hashes remain historical evidence and are not rewritten.

## Consequences and non-claims

This reduces one duplicated security boundary to one versioned implementation. It does not consolidate schema-specific provider, claim, receipt, evidence, quorum, or authority logic, because those contracts have materially different fields and failure semantics. It also does not prove witness anti-replay ownership, latest checkpoint, source identity, CAS, durability, clock/snapshot/broker truth, execution, profitability, runtime integration, migration safety, writer authorization, paper authorization, or live authorization.

The natural-forward public chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 is not reissued.
