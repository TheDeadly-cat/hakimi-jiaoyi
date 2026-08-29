# ADR 0063: Factor calibration replay report consumer

- Status: Accepted for an unmounted research candidate
- Date: 2026-08-23
- Scope: Read-only consumption of G0 calibration replay receipts

## Context

G0 can exactly replay the beta declaration in an F0-v1 residualization registration from a separately sealed calibration-only observation set. A pure synthetic MATCH receipt proves the supplied rows reproduce the declared betas, but it still carries three blockers:

- `EXTERNAL_CALIBRATION_TIMING_UNATTESTED`;
- `REGISTRATION_CALIBRATION_RECEIPT_NOT_G0_BOUND`;
- `CALIBRATION_REPLAY_NOT_ACTIVATED`.

The declared calibration receipt hash inside registration v1 is provenance, not the G0 receipt hash. Reinterpreting it or switching to a registration v2 would silently change a frozen contract. Existing F0-v2, F1, F4, F5, runtime, and mounted UI paths have no G0 consumer.

## Decision

Add a versioned, unmounted G1 report consumer:

- schema: `strategy-correlation-cross-lag-factor-calibration-report-consumer-verification-v1`;
- static fingerprint: `20260823-cross-lag-factor-calibration-report-consumer-1`;
- exact source: G0 replay schema/fingerprint v1 only;
- verification: invoke the official G0 verifier with complete registration, calibration observations, and expected hashes;
- output: aggregate calibration summary, provenance hashes, fixed states, blockers, and locked authority;
- sealing: strict canonical JSON with `verification_hash`.

G1 does not recompute OLS, inspect private rows independently, mutate F0/G0, or create registration v2.

## State machine

| Source | Report | Gap | Maturity | Permission |
| --- | --- | --- | --- | --- |
| Verified G0 MATCH | `OBSERVED_CALIBRATION_MATCH` | mathematical replay matched; timing unattested | source candidate maturity | `LOCKED` |
| Verified G0 BLOCK | `OBSERVED_CALIBRATION_BLOCK` | calibration replay mismatch | source candidate maturity | `LOCKED` |
| Missing | `UNKNOWN` | `G0_CALIBRATION_REPLAY_MISSING` | `UNKNOWN` | `LOCKED` |
| Unsupported | `UNKNOWN` | `G0_CALIBRATION_REPLAY_UNSUPPORTED` | `UNKNOWN` | `LOCKED` |
| Invalid | `UNKNOWN` | `G0_CALIBRATION_REPLAY_INVALID` | `UNKNOWN` | `LOCKED` |

For an OBSERVED source, every G0 blocker remains in order and G1 appends `FACTOR_CALIBRATION_REPORT_NOT_ACTIVATED`. MATCH can set only the mathematical replay fact. External timing, formal registration binding, current admission, paper authorization, live permission, and profitability claims remain false.

## Privacy boundary

The projection may expose observation/date/count/tolerance/error aggregates and strict source/ledger hashes. It must not expose calibration rows, identity order, identity returns, factor values, factor identity/source, or beta values.

## Consumer-first activation order

1. G0 calibration replay remains an unmounted source candidate.
2. G1 verifies and projects G0 without mounting or activation.
3. A later presentation envelope may consume exact G1 only under a new version.
4. Any registration v2 requires a separate ADR and must not reinterpret registration v1.
5. No step automatically switches current, rewrites pointer-v2, or reissues evidence.

## Adversarial matrix

Coverage includes MATCH, BLOCK monotonicity, missing, unsupported, invalid, expected-hash substitution, broken and coherently resealed source tamper, registration/calibration substitution, aggregate-only privacy, blocker preservation, timing/binding non-upgrade, authority aliases, non-native containers, non-finite values, resealed report tamper, deterministic UNKNOWN closure, and denied external state.

## Safety and compatibility

The natural-forward single-look chain is unchanged. Legacy pack-v5 public reads remain UNKNOWN, pointer-v2 fields/hash and no-auto-reissue behavior remain unchanged, paper/live remain unauthorized, live remains permanently locked, and no calibration, simulation, backtest, or forward result is profitability proof.
