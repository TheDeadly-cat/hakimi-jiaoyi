# ADR0386: Replay Cursor Provider Signed Registration Candidate v1

## Status

Accepted as an unmounted, synthetic signed-registration candidate and redacted
verification contract.

## Context

ADR0385 preregisters a provider identity claim, Ed25519 public-key SPKI hash,
implementation claim, capabilities, and external conformance plan. It does not
prove that the corresponding private key signed anything or that a provider
exists.

## Decision

Add three sealed internal documents:

- provider registration claim bound to ADR0385, challenge hash, and registration
  nonce hash;
- signed registration candidate carrying canonical DER-SPKI public key and
  Ed25519 signature;
- redacted verification evidence.

The signature message is the raw 32 bytes represented by the exact claim SHA-256
digest. The claim includes a fixed signature domain and exact ADR0385 identity,
protocol, implementation, challenge, nonce, authority lock, and blockers.

Valid verification can establish only that a signature from the preregistered
public key verifies over that exact claim. Evidence may set
`preregistered_key_signature_verified=true` and
`provider_key_possession_observed=true`. It must keep provider organization
identity, key-control continuity, provider implementation, external conformance,
challenge source authority, challenge freshness, replay consumption, provider
registration, atomicity, durability, linearizability, writer permission, paper
authority, and live authority false.

Raw public key and signature are excluded from verification evidence. Repeating
the same evaluation is deterministic and explicitly does not consume replay.

## Consumer-first activation order

1. Keep claim, signed candidate, and evidence unmounted.
2. Preregister a trusted challenge issuer and challenge-consumption protocol.
3. Define key rotation and provider organization-identity evidence.
4. Bind a signed provider-registration receipt to an authorized external
   provider endpoint without storing secrets in this project.
5. Execute ADR0385 external conformance cases with an independent observer.
6. Review current/HTTP activation separately; synthetic candidates remain
   permanently non-promotable.

## Adversarial matrix

- exact claim is deterministic and operationally BLOCKED;
- valid preregistered signature is observed without registration authority;
- wrong key can verify its own signature but fails preregistered-key binding;
- tampered signature fails verification;
- coherently resealed and re-signed semantic promotion fails exact claim rebuild;
- signed-document tamper or schema alias fails exact verification;
- evidence mutation fails exact rebuild;
- raw key and signature remain redacted;
- challenge/nonce drift changes the claim hash;
- exact replay is deterministic and remains unconsumed;
- preregistration/implementation drift cannot build a claim;
- invalid base64, key type, or signature length is rejected;
- production code has no private-key, I/O, storage, route, or runtime operation.

## Non-claims

Test keys are generated only in memory. Production code does not generate, read,
or persist private keys. No endpoint, provider, external runtime, network,
storage, database, cache, service, browser, scheduler, market data, or holdings
are accessed. This work does not prove identity, durable key control, challenge
freshness, replay consumption, provider registration, external atomicity,
profitability, paper authority, or live authority.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. pointer-v2 remains unchanged
and is not reissued.
