# ADR 0113: Provider identity artifact transparency and availability v1

## Status

Accepted as an inactive, fail-closed research contract. It is not connected to current evidence, UI, server, engine, CLI, paper, or live paths.

## Context

ADR0112 binds finite requirement and vector roots plus two signed runner result transcripts. It does not receive the detached artifact bytes, prove that catalog records are present in a transparency log, or bind independent retrieval claims. A pure synthetic ADR0112 call reached its strongest state while nine artifact-content, checkpoint, proof, and observer dimensions remained outside its thirteen evaluation parameters.

The existing assertion replay contract already defines domain-separated binary Merkle inclusion and consistency algorithms. Those proofs are tied to assertion receipts and cannot establish availability of ADR0112 artifacts. Local artifact I/O and implementation manifests likewise provide no external publication or retrieval semantics.

## Decision

Add an inactive registration and evaluation consumer using the existing inclusion/consistency algorithm shape with artifact-specific empty, leaf, node, and checkpoint domains.

The registration pins:

1. Exact ADR0112 registration and evaluation receipt hashes and source fingerprint.
2. Distinct transparency-log, observer-A, and observer-B entities, keys, organizations, control groups, ownership-disclosure hashes, and observer run IDs.
3. A canonical artifact catalog root, exact artifact count and total byte count, per-artifact size bound, content encoding, and content hash policy.
4. A pinned transparency checkpoint root and tree size, artifact-specific Merkle domains, checkpoint signature domain, observer signature domains, and bounded evidence times.
5. The strict canonical hash of the complete normalized registration.

The evaluation:

1. Reruns ADR0112 and rejects any role collision between its six roles and the three new roles.
2. Validates a sorted exact artifact catalog and requires every supplied base64url payload to match the catalog content hash and size. Payload bytes are not projected into output evidence.
3. Verifies the transparency-log checkpoint signature, every artifact-record inclusion proof, and consistency from the preregistered pinned checkpoint.
4. Verifies two separately keyed observer receipts. Each observer must report every catalog artifact in canonical order with matching locator commitment, content hash, size, successful retrieval, and bounded timestamps.
5. Requires both observer result-transcript roots to agree while signed receipts remain distinct.

The highest state is `LOCAL_ARTIFACT_CONTENT_AND_SIGNED_TRANSPARENCY_INCLUSION_DUAL_RETRIEVAL_CLAIMS_VERIFIED_EXTERNAL_LOG_TRUST_UNPROVEN`.

## Proof boundary

Payload validation proves only that the bytes were supplied to this local evaluation. A signed checkpoint and valid proofs do not establish external log governance, public visibility, or long-term persistence. Observer signatures prove only that preregistered keys signed internally consistent retrieval claims; they do not prove the observers are trustworthy, geographically independent, or actually performed network retrieval. Locator commitments intentionally do not expose URLs.

Therefore external log trust, public artifact availability, external persistence, external time truth, actual auditor independence, true suite completeness, profitability, observation admission, promotion, paper permission, and live permission remain false or unproven.

## Validation evidence

1. The targeted synthetic contract passes 41/41 and both the service and test compile in memory.
2. An independent component matrix passes 26/26: one complete positive chain, registration-receipt tampering, twenty-two artifact/log/observer/source adversarial cases, and an assertion that the immediate ADR0112 public verifier was exercised. The immediate verifier was called 43 times.
3. The positive component path runs the real ADR0112 verifier and isolates only ADR0112's older ADR0111 test-fixture boundary. This is stronger than mocking ADR0112 directly, but it is not a claim that the complete historical ancestor chain was reproduced end to end.
4. The explicit factor-calibration family passes 1043/1043 across 48 TestCase classes, including ADR0113 exactly once.
5. The authoritative current research lean profile lists and dry-runs 14 grouped checks. ADR0113's test and service each occur once; executed, completed, and reused counts are zero; runtime mutation, paper, and live flags are false.
6. Eight named active entrypoints contain zero ADR0113 module, schema, or strongest-state references. The consumer remains inactive.

Implementation fingerprints:

- Service SHA-256: `A09D300C0AF3C436902DBFA3A981BD1874FE799AFE164B3F3E09F5236BDE4B04`.
- Test SHA-256: `C698459C4BE4C00A4FC461CC9669DBB9AC91306365B9DF1BDF18D949E716BDFC`.
- Lean manifest SHA-256: `D368977636667949496551E7B4DDC73C5BCB1A32D9F3D4113F2B81D59E485281`.
- Lean plan hash: `a9c7fe0a76f79820f28b6cecdc8afa8235a6ad9fac3803d122baaa04d70605b1`.

## Consumer-first activation order

1. Keep this consumer inactive and use only pure synthetic in-memory payloads, checkpoints, proofs, and receipts.
2. Publish immutable content-addressed artifacts without changing this consumer.
3. Establish an externally governed transparency log and independently operated availability observers.
4. Verify non-genesis checkpoint consistency and repeated retrieval over time with detached evidence.
5. Review external trust, persistence, and public accessibility separately.
6. Require a new migration ADR and explicit authorization before any current consumer or authority field can change.

No backtest, market data, runtime state, filesystem artifact read, network request, service, browser, scheduler, paper path, or live path is used.
