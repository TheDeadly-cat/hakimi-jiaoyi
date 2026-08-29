# ADR 0105: Replay checkpoint persistence receipt verifier v1

## Status

Accepted as an inactive, synthetic-only candidate verifier. It performs no I/O
and is not connected to a provider, runtime store, database, `current`, paper,
or live paths.

## Context

ADR 0104 preregisters write/reopen evidence but intentionally observes no
receipts. A future durable pin requires evidence that exactly one sealed asset
was written and independently reopened in a distinct session without drift.

## Decision

Add a pure verifier for a sealed checkpoint asset and two Ed25519-signed provider
receipts. It verifies:

- the exact ADR 0104 persistence registration;
- persistence public-key hash binding and key role;
- checkpoint asset canonical seal and replay-registry identity;
- write and reopen signatures using schema-domain-separated canonical JSON;
- exact asset and record hash replay;
- record cardinality exactly one in both receipts;
- distinct write and reopen session IDs;
- asset-created <= written < reopened ordering;
- reopen binding to the exact signed write receipt hash.

The highest state is
`WRITE_REOPEN_SIGNATURES_SESSION_SEPARATION_AND_RECORD_REPLAY_VERIFIED_EXTERNAL_DURABILITY_UNPROVEN`.
This proves a local cryptographic receipt contract only. Signed provider claims
do not independently prove storage durability, provider trust, or external time.
The source replay-verifier receipt hash remains opaque and is not promoted.

The static fingerprint is
`20260929-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-receipt-verifier-1`.

## Fail-closed boundary

Shape drift, extra fields, seal drift, wrong provider/adapter/key roles,
noncanonical public keys or signatures, signature failure, asset/record drift,
duplicate sessions, cardinality drift, timestamp reversal, source-write drift,
and bool/int output aliases fail to `UNKNOWN`.

All authority fields remain false, including durable write/reopen,
authoritative pin, replay registry checked, replay absence, uniqueness, identity,
admission, selection, paper, and live authority.

## Activation order

1. Adversarially validate this synthetic consumer.
2. Bind its opaque source hash to a verified ADR 0103 evaluation in a separate
   composition contract.
3. Establish independent persistence-provider trust and external durability.
4. Only then consider a persisted asset as a future pin candidate.
5. Keep uniqueness/freshness and `current` integration separate and later.

## Consequences

No provider or durable storage is implemented. This is not profitability or
trading evidence.

## Validation

- Targeted synthetic verifier tests: 28/28.
- Independent signed write/reopen matrix: 18/18.
- Factor-calibration family: 760/760.
- In-memory compile: 2/2.
- Lean list/dry-run: planned 19, executed 0, runtime mutations false.
- Active integration references: 0.

These checks prove only local signature, session, cardinality, and record-replay
logic. They do not prove external provider trust, real durability, external time,
source replay-evaluation validity, uniqueness, freshness, profitability, or
trading authorization.