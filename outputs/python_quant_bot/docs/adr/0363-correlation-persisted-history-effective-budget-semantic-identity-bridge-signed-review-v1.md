# ADR 0363: Correlation persisted-history/effective-budget semantic-identity bridge signed review v1

- Status: Accepted for synthetic research evidence only
- Date: 2026-08-24
- Scope: Unmounted, consumer-inactive correlation evidence

## Context

ADR 0362 exactly binds the bounded persisted-history coverage source to the
uncertainty/effective-budget source. It deliberately does not claim semantic
study-identity equivalence because the history and budget window-order hashes
are distinct.

The next missing prerequisite is not an automatic equivalence rule. It is a
reviewable, tamper-evident statement that binds both technical identities and
records a narrow human-review claim without turning that claim into truth or
authority.

## Decision

Add a versioned local Ed25519 signed-review contract with five stages:

1. Register a reviewer public-key hash while redacting raw reviewer and process
   identifiers and the public-key material from the registration artifact.
2. Reverify the exact ADR 0362 preregistration and build a bridge claim that
   binds its preregistration hash, binding-contract hashes, history study
   identity, both distinct window-order hashes, symbol order, and cluster
   partition.
3. Bind the claim, reviewer registration, and nonce hash into a strict canonical
   SHA256 unsigned attestation.
4. Attach an Ed25519 detached signature over the unsigned-attestation digest.
   The assembly API never accepts private-key material.
5. Reverify every source and signature link before emitting redacted public
   evidence.

The fixed relationship claim is:

`SAME_RESEARCH_INTENT_DISTINCT_TECHNICAL_WINDOW_IDENTITIES_REVIEW_CLAIM`

The highest evidence state is:

`SIGNED_SEMANTIC_IDENTITY_BRIDGE_CLAIM_VERIFIED_EXTERNAL_REVIEW_GOVERNANCE_UNPROVEN`

## Claim boundary

The positive state proves only that:

- the exact ADR 0362 source preregistration reverified;
- the signed claim binds the two distinct technical identity sets;
- the detached Ed25519 signature verifies against the registered public-key
  hash;
- claim, registration, nonce, signature, and source hashes are internally
  consistent;
- the public evidence redacts raw identifiers, nonce, rationale, public key,
  and signature.

It does not prove:

- real reviewer identity;
- reviewer independence;
- reviewer-registration governance;
- nonce uniqueness or durable replay prevention;
- semantic study-identity equivalence;
- effective-budget activation;
- runtime mounting, current admission, pointer writing, paper/live authority,
  profitability, or trading permission.

`semantic_study_identity_equivalence_verified` remains `false`.
`effective_budget_activation_allowed` remains `false`.

## Activation order

Consumer-first activation remains mandatory:

1. Verify the ADR 0362 source preregistration.
2. Verify reviewer-key registration.
3. Verify the exact bridge claim.
4. Verify nonce binding and detached signature.
5. Emit redacted signed-review evidence.
6. Keep every runtime and trading authority lock closed.

No current alias, pointer, HTTP registration, scheduler, runtime consumer, or UI
is changed by this ADR.

## Adversarial matrix

The synthetic contract tests cover:

- successful signature verification without semantic-equivalence promotion;
- exact binding of both distinct source identity sets;
- registration and public-evidence redaction;
- resealed signature tampering;
- resealed source-preregistration tampering;
- resealed relationship-claim promotion;
- nonce mismatch;
- resealed authority promotion;
- permanent paper/live/profitability/runtime locks.

## Consequences

ADR 0363 supplies a narrow governed-review prerequisite while remaining
fail-closed. A later ADR may define independent reviewer governance and durable
anti-replay storage, but it must not reinterpret this signed statement as
semantic equivalence or activation permission.
