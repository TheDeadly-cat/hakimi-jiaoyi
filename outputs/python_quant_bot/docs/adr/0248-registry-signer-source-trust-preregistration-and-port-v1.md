# ADR 0248: Registry signer source-trust preregistration and port v1

## Status

Accepted as an inactive, blocked, source-free contract. It is not connected to
current evidence, UI, server, engine, CLI, paper, live, or runtime paths.

## Context

ADR0241 preregisters six organization-identity evidence kinds and signer roles.
ADR0242 evaluates reference structure, binding, role/key separation, and
freshness. ADR0243 through ADR0245 can prove local Ed25519 possession over exact
artifacts. None proves that a signer key is controlled by its declared role or
that the source which supplied that role binding is independently trusted.

The older provider-identity chain cannot close this gap. ADR0111 explicitly
states that its conformance and governance auditors are not externally trusted
by this repository. ADR0112 adds role manifests and reproducibility, while
ADR0113 adds artifact transparency and availability. Those are useful upstream
artifacts, not external trust roots. Treating their local signatures as source
trust would only move the unverified assumption.

No external authority registry, trust anchor, source adapter, revocation source,
credential, endpoint, payload, or trusted time is authorized in this slice.

## Decision

Add immutable `registry-signer-source-trust-record-v1`. One record binds exactly
one of ADR0241's six evidence kinds and signer roles to:

1. subject registry id and public-key hash;
2. evidence signer public-key hash;
3. a role-specific external authority namespace, role, key, and statement hash;
4. a trust-anchor id and hash;
5. source-adapter id and implementation hash;
6. policy id and version;
7. revocation-source id and snapshot hash;
8. bounded issuance and expiry times under lowercase Ed25519.

The interface rejects schema, role, algorithm, hash, and time aliases. Subject,
authority, anchor, adapter, and revocation namespaces must be structurally
distinct. Subject, evidence-signer, and authority key hashes must also be
distinct. These checks prevent direct self-attestation but do not claim
governance independence.

Add a runtime-checkable source port that exposes only adapter identity, protocol
version, and retrieval of immutable records. Structural Protocol conformance is
not evidence of source trust.

Add a source-free preregistration consumer that exactly rebuilds ADR0241 intake
and preregisters six role-specific source-trust requirements. It accepts no
records, endpoints, payloads, signatures, trust booleans, anchors, or adapter
implementations. All record, adapter, anchor, and external-authority counts stay
zero. Every permission and identity conclusion stays false. Exact verifier PASS
means only that the blocked preregistration was reproduced exactly.

## Consumer-first activation order

1. exact ADR0241 intake, ADR0242 structure/freshness, and ADR0245 signatures;
2. this source-trust record shape, port, and source-free preregistration;
3. separately authorized precommitment of six authority namespaces, keys,
   trust anchors, source adapters, policies, and revocation sources;
4. independently governed adapter implementations and offline conformance;
5. source-record retrieval with trusted reference time and revocation checks;
6. payload semantics and role-control verification;
7. organization identity decision;
8. separate registration, receipt, route, mount, current, and activation review.

No later step may infer source trust from a local signature PASS, distinct names,
distinct hashes, or structural port conformance.

## Adversarial matrix

- evidence-kind/signer-role and evidence-kind/authority-role aliases fail;
- subject/authority/anchor/adapter/revocation namespace collisions fail;
- subject/evidence-signer/authority key collisions fail;
- schema, algorithm, hash, boolean-as-time, and validity aliases fail;
- identity substitution and predecessor-hash drift fail exact rebuild;
- resealed record-count, observed-state, trust, signer identity, organization
  identity, writer authority, role collision, separation weakening, and port
  alias promotions become `BLOCK/UNKNOWN`;
- a structurally matching synthetic port returns zero records and grants no
  authority.

## Consequences

- The missing signer-role/source-trust boundary is explicit and versioned.
- Local governance, provenance, transparency, and signature results remain
  upstream evidence rather than self-authorizing trust roots.
- No infrastructure adapter, trust anchor, external source, or runtime path is
  introduced.
- Current artifacts, registration-v9, suite-v19, pointer-v2, UI, and the natural
  forward evidence chain remain unchanged and unmounted.
- This contract is not external trust, organization identity, trusted time,
  profitability, current admission, runtime activation, paper/live authority,
  route, mount, migration, receipt, or writer authority.
