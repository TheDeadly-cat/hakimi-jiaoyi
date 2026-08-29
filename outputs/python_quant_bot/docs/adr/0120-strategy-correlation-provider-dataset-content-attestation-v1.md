# ADR 0120: Strategy correlation provider dataset-content attestation v1

## Status

Accepted as an inactive, fail-closed research candidate. It adds a distinct provider dataset-signing key role and signed content-binding claim above ADR0119. It does not activate data admission, current writers, reports, paper, or live paths.

## Context

ADR0119 binds every dataset data/manifest hash into one composition root and aligns local source labels with a provider identity assertion. It explicitly does not prove that the provider issued or signed those dataset hashes.

A synthetic audit changed all local dataset data hashes and rebuilt valid ADR0119 compositions. Both the original and alternate compositions passed, both retained `dataset_content_attested_by_provider=false`, and neither contained a signature, public key, or dataset-attestation input. Identity-registry and timestamp-adapter signatures cannot safely substitute for a provider dataset-content key because they represent different roles and messages.

## Decision

Add three consumer-first contracts:

1. Register one `PROVIDER_DATASET_CONTENT_ATTESTATION` Ed25519 public key against the ADR0119 composition and provider-identity lineage.
2. Require that key to differ from both the identity-registry signing key and timestamp-adapter signing key extracted from the reverified source contexts.
3. Bind key ID, public-key hash, provider-ID hash, provider identity verification/document hashes, dataset count/root, validity claims, algorithm, encoding, and message format in a sealed registration.
4. Generate an unsigned canonical receipt without accepting or storing a private key.
5. Sign the strict-canonical SHA-256 digest externally and assemble the receipt from the detached signature bytes.
6. Verify Ed25519 signature, canonical content hash, signature hash, attestation hash, expected registration/attestation pins, validity claims, and all ADR0119/replay/input/common-support/dataset lineage.
7. Redact public key and signature bytes from the verification output.
8. Keep external provider key control, external provider data issuance, replay-registry coverage, observation admission, profitability, paper, and live false.

The receipt uses `ED25519`, `RFC8785_JCS_UTF8`, and `STRICT_CANONICAL_SHA256_DIGEST_V1`. Its scope is `ALL_COMPOSED_DATASET_DATA_AND_MANIFEST_HASHES`.

## Proof boundary

A passing result proves that a signature under the separately registered dataset key covers the exact ADR0119 dataset binding and source lineage. The registration itself is local evidence. It does not prove external provider control of that key, external provider issuance of the bytes, identity-registry or calendar governance, authoritative time, replay absence, robustness, or profitability.

## Consumer-first activation order

1. Keep ADR0120 synthetic-only and detached.
2. Add external key-custody, rotation, revocation, and provider key-binding governance evidence.
3. Add replay-registry and durable receipt evidence.
4. Add a neutral report/presentation consumer only after those layers are reviewed.
5. Require a separate migration ADR before observation admission or current activation.

No secret, market data, K-line task, backtest, browser, service, scheduler, report writer, paper path, or live path is used.

## Validation plan

- Test role separation, strict key/base64 grammar, registration/time pins, canonical unsigned content, signature verification, source drift, dataset drift, authority locks, redaction, deterministic seals, and tamper rejection.
- Run an independent real-source composition with actual calendar/provider verifiers and fresh in-memory synthetic signing keys.
- Confirm active consumers remain unreferenced and all permissions remain false.

## Validation evidence

1. The targeted ADR0120 contract passes 22/22, and the service and test compile in memory 2/2.
2. An independent real-source public-API matrix passes 20/20. It rebuilds ADR0119 through the actual calendar and provider verifiers, each invoked 14 times, then uses a fresh in-memory dataset key for detached signing.
3. The matrix rejects registry-key role collision, wrong signing key, public-key substitution, coherently resealed signature drift, registration/attestation pin drift, out-of-window issuance, dataset drift, composition drift, and output drift.
4. The directly related anchor-signature/provider-identity/ADR0119/ADR0120 family passes 90/90 across four TestCase classes.
5. The research lean profile lists and dry-runs 15 grouped checks. ADR0120 TestCase and service source each occur once; planned is 15, while executed, completed, and reused are zero. Runtime mutation, paper, and live flags are false.
6. Eight explicit active entrypoints contain zero registration, receipt, verification schema, fingerprint, state, key-role, or module references.

Implementation fingerprints:

- Static fingerprint: `20260822-strategy-correlation-provider-dataset-content-attestation-1`.
- Service SHA-256: `91DCAD9660F379C47C2E912BDA5032CBABC72DC5AF8C42ECE2EA3BEDE19BC654`.
- Test SHA-256: `FBDDDA303CC19BC64A96067A80EEF31D24E51EA03EBCB2A92A4D9B055A1E763F`.

No private key is accepted by the production service. The broader provider-history family is outside this slice and was not rerun. The current natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 fields, hash contract, and no-auto-reissue behavior remain unchanged.
