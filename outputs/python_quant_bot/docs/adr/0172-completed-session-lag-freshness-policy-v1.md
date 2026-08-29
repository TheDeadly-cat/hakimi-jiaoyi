# ADR0172: Preregistered completed-session lag freshness policy v1

## Status

Accepted as an inactive, research-only candidate. It is not connected to the
shadow service, risk service, server, UI, engine, current evidence, paper, or
live paths.

## Gap proof

ADR0171 can return `PASS` for a native cutoff of `2026-12-19` while a synthetic
consumer assumption of `2027-01-31` is not an input to its builder. ADR0171
correctly reports `freshness_policy_defined=false` and
`freshness_evaluated=false`; therefore native cutoff integrity is not a
freshness gate.

Existing research currentness facts calculate calendar ages but explicitly do
not define thresholds. Provider-identity uniqueness/freshness contracts concern
signed replay checkpoints, not market-data sessions. Neither can close this
gap.

## Decision

Add two exact-rebuild contracts:

1. A registration pins the ADR0171 manifest hash, its inherited calendar
   registration/session-verification hashes, the registered calendar-ID set
   hash, a maximum completed-session lag, trusted-clock v2 quorum requirements,
   the calendar library version, and a declaration time before the frozen
   cutoff.
2. An evaluation verifies that registration, requires an exact trusted-clock v2
   quorum attestation, and uses the already pinned `exchange-calendars` runtime
   to find each registered calendar's latest session whose close is not after
   the attested reference time.

The lag is the maximum count of completed sessions strictly after the native
cutoff across all registered calendars. It is not elapsed UTC hours and does
not treat midnight session-label encoding as a session close.

The policy threshold is a native integer from zero through three. Evaluation is
bounded to 31 UTC calendar days from the cutoff before calendar lookup. A
cutoff that is not a registered session, is not yet completed at the reference
time, exceeds the horizon, or exceeds the preregistered session lag fails
closed.

## Reused boundary

ADR0172 does not create another calendar registration. It extracts the exact
calendar projection already consumed by ADR0171's verified
calendar/provider-composition context and pins its existing expected
registration hash. Raw calendar IDs are replaced by a set hash in registration
and by per-calendar hashes in evaluation output.

## Authority boundary

`PASS` means only that the local completed-session lag is within the
preregistered policy under an internally verified, dual-source clock
attestation. Public clock endpoints are not authenticated time authorities.
Therefore `external_clock_authority_authenticated`,
`freshness_externally_proven`, provider identity, shadow activation, runtime
activation, current admission, writer, migration, paper, and live permissions
remain false.

No prices, matrices, observation batches, clock endpoints, raw clock sources,
or raw calendar IDs are exposed. The natural-forward single-look chain and
pointer-v2 are unchanged.

## Consumer-first activation order

1. Keep registration and evaluation synthetic and inactive.
2. Authenticate external time-authority roles without changing this policy.
3. Bind the freshness evaluation to a versioned shadow-only adapter input.
4. Run independent adversarial review and accumulate natural shadow evidence.
5. Require a separate risk-service version switch and current migration
   decision. Paper/live remain unauthorized.

## Adversarial matrix

The targeted matrix covers zero-lag exact close, one-session boundary,
two-session stale rejection, pre-close reference time, bounded reference
horizon, single-source clock, legacy clock schema, clock tamper, calendar lookup
failure, retrospective policy declaration, bool/int aliases, excessive lag
thresholds, source/context/hash drift, exact-verifier tamper, redaction, and
permanent authority locks.

## Validation evidence

- Original calendar-registration hash replacement regression: 1/1 PASS.
- ADR0172 synthetic adversarial contract: 16/16 PASS.
- ADR0171, trusted-clock, calendar-session, composition, and shadow dependency
  matrix: 99/99 PASS.
- In-memory syntax compilation: 4/4 PASS.

These results are synthetic contract evidence only. They do not authenticate an
external time authority, prove real-market freshness or profitability, or grant
shadow, current, paper, or live permission.
