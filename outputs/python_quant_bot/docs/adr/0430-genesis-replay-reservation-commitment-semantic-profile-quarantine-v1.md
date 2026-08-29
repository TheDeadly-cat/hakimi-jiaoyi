# ADR0430: Genesis commitment semantic-profile quarantine v1

## Status

Accepted as an unmounted, fail-closed semantic quarantine. It does not resolve
the ADR0402 ambiguity, select a profile, install a commitment, activate current,
or authorize provider registration or trading.

## Context

ADR0402 produces an exact blocked genesis commitment whose binding includes
expected_out_of_band_genesis_commitment_hash. The source contract verifies that
the hash participates in the deterministic commitment, but its name does not
uniquely establish what external artifact the hash commits to.

Two materially different interpretations remain possible:

1. A pre-ceremony authorization-manifest anchor.
2. A post-derivation genesis-commitment match target.

Selecting either interpretation changes ceremony ordering, domain separation,
who can authorize the value, and what evidence can prove a match. Inferring a
meaning from the field name would create an unreviewed compatibility path.

## Decision

Add a semantic-profile quarantine that exact-verifies the complete ADR0402
commitment call chain, then preserves the ambiguous hash as an opaque value.

The quarantine:

- lists both candidate profiles with selected=false;
- sets profile_state to UNRESOLVED;
- exposes no profile-selection parameter;
- preserves all nine ADR0402 source blockers;
- adds ambiguity, preregistration, selection, selection-commitment, and domain-
  separation blockers;
- binds the ADR0402 implementation hash and a bounded set of source hashes;
- embeds no source commitment, evidence, signatures, keys, topology, or plan;
- keeps every profile, installation, provider, runtime, current, writer, paper,
  and live authority false; and
- returns BLOCK / DO_NOT_INTERPRET_OR_ACTIVATE even when ADR0402 is exact.

Invalid or non-native source commitments produce a sealed UNKNOWN quarantine
with the same locked decision and authority.

## Required future profile decision

A future version may proceed only after one profile is explicitly chosen and
preregistered with:

- an unambiguous profile identifier;
- a domain-separated profile-selection commitment;
- the authority allowed to issue that commitment;
- ceremony ordering and freshness rules;
- external artifact schema and exact hash field;
- signature, key-lifecycle, and anti-replay requirements;
- rollback and installation semantics; and
- migration behavior for every existing ADR0402 document.

No default profile and no compatibility alias are permitted.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR0402 commitment | BLOCK quarantine |
| Either candidate profile | listed, not selected |
| Opaque hash | preserved without interpretation |
| ADR0402 blockers | preserved exactly |
| Resealed profile selection or authority | verifier rejects |
| Tampered source commitment | UNKNOWN quarantine |
| Invalid expected source hash | UNKNOWN quarantine |
| Non-native or cyclic quarantine | verifier rejects |
| Extra compatibility field | verifier rejects |
| Raw source, signature, key, topology, or plan | absent |
| Repeated evaluation | deterministic and input-immutable |

## Consumer-first continuation

1. Keep ADR0402 unchanged and ADR0430 unmounted.
2. Obtain user direction on the intended semantic profile.
3. Preregister exactly one profile and its domain-separated selection
   commitment.
4. Independently review ceremony ordering, authority, signature, replay,
   installation, and migration semantics.
5. Add a profile-specific verifier without compatibility aliases.
6. Keep provider registration, runtime integration, current activation, writer,
   paper, and live authority behind separate decisions.

No step authorizes or automatically performs the next step.

## Evidence and permission boundary

This ADR performs only pure synthetic contract evaluation. It does not read or
write runtime state, contact an external provider, use a system clock, persist a
reservation, install a commitment, execute a browser, run a backtest, or start a
trading task. It does not prove strategy performance or profitability.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
