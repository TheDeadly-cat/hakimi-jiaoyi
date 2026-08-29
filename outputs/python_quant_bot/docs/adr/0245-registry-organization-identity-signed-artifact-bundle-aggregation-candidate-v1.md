# ADR 0245: Registry organization identity signed artifact bundle aggregation candidate v1

## Status

Accepted as a blocked, synthetic local six-artifact cryptographic candidate.

## Context

ADR0243 verifies one evidence payload, artifact hash, Ed25519 public-key hash,
and detached signature. ADR0244 seals the Python exact-verifier result for the
six-reference ADR0242 bundle. Neither contract proves that all six referenced
artifacts were verified together against the same normalized reference set.

A consumer must re-run each ADR0243 verifier and bind all results to the
ADR0244 reference-set hash. It must not infer signer-role identity, source
trust, evidence semantics, revocation truth, or organization identity from
cryptographic validity.

## Decision

Add an unmounted Node aggregation candidate that requires:

1. one exact sealed ADR0244 PASS envelope;
2. exactly one item for each of the six evidence kinds;
3. a normalized reference-set hash matching the ADR0244 envelope;
4. subject registry id and public-key hash matching the envelope;
5. all references fresh at the envelope reference time;
6. six distinct signer roles;
7. six distinct signer public keys;
8. six distinct artifact hashes;
9. all six ADR0243 candidates and exact verifiers passing locally.

The aggregator re-runs each signature verification. It does not trust caller
supplied verification documents. Its output carries one hash-only receipt per
evidence kind and never embeds payload, public-key, signature, or private-key
material.

Local CRYPTOGRAPHIC_BINDING_PASS means only that six canonical payloads match
their references and detached signatures under six distinct Ed25519 public
keys. The aggregation document remains BLOCKED. Its exact verifier may return
PASS only for an exact local cryptographic pass.

The ADR0244 envelope is strict-canonical sealed but not process-authenticated.
The aggregator therefore records python_process_authenticated false even when
the envelope shape and seal are exact. It independently rechecks reference-set
binding, subject binding, freshness, uniqueness, and all signatures.

Evidence-body semantics, signer-role identity, external source trust,
revocation content, Python process authenticity, and registry organization
identity remain false. Every admission, presentation, runtime, writer, paper,
and live authority remains false.

## Consumer-first order

1. ADR0241 intake preregistration;
2. ADR0242 structure, binding, and freshness evaluation;
3. ADR0243 single signed-artifact candidate;
4. ADR0244 sealed Python exact-verification envelope;
5. ADR0245 six signed-artifact aggregation candidate;
6. independently governed signer-role and external-source evidence;
7. per-schema evidence-body semantic validators;
8. process-authenticated cross-runtime receipt;
9. organization-identity decision contract;
10. separately authorized adapter and runtime activation.

ADR0245 is not connected to current, HTTP, UI, registration-v8, pointer-v2, or
the natural-forward evidence chain.

## Adversarial matrix

- a real Python ADR0244 envelope and six Python-created Ed25519 signatures
  aggregate in Node;
- one signature, public key, or resigned payload substitution blocks;
- missing and duplicate kinds are rejected before aggregation;
- reference-set and subject substitution blocks even when the changed artifact
  verifies locally;
- independent freshness checks block a forged fresh-status envelope;
- resealed envelope promotion is rejected;
- an exact one-signature failure stays BLOCK/BLOCKED;
- aggregate promotion tampering becomes BLOCK/UNKNOWN;
- output contains no payload, public key, signature, or private key;
- all identity and authority fields remain false.

## Consequences

- The six required evidence references now have an executable aggregate local
  cryptographic gate rather than six independent-looking claims.
- A valid aggregate is not source legitimacy, signer identity, evidence
  semantics, revocation truth, process authentication, organization identity,
  strategy quality, profitability, or trading authority.
- Existing identity, intake, evaluator, envelope, current, HTTP, UI,
  registration-v8, pointer-v2, and natural-forward artifacts remain unchanged.
- No credential, endpoint, runtime asset, database, cache, log, service,
  browser, scheduler, market task, backtest, blind test, paper order, or live
  order is used.
