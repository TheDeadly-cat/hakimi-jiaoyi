# ADR 0030: Redacted public calibration rail for cluster stability

- Status: Accepted for standalone consumer-only presentation
- Date: 2026-08-21

## Context

The within-cluster stability gate can be contract-valid with either a PASS or BLOCK evidence decision. Exposing the gate document directly would reveal research identities, topology, hashes, correlation values, and interval values, while presenting only PASS/BLOCK could blur contract validity, evidence maturity, and execution authority.

## Decision

Add `strategy-correlation-cluster-stability-public-summary-v1`, rebuilt from the full external verifier inputs. The projection exposes only fixed SOURCE, GAP, MATURITY, and PERMISSION labels. It redacts all identities, hashes, correlations, intervals, returns, rankings, and profitability metrics. A valid BLOCK remains observed BLOCK evidence; malformed, mismatched, resealed, or authority-escalated inputs become UNKNOWN.

Add a standalone calibration-rail presenter with static fingerprint `20260821-within-cluster-stability-calibration-rail-1`. The rail distinguishes uncertainty evidence, complete-link topology, adjusted interval evidence, the consumer gate, missing report integration, and locked current activation. It is responsive, reduced-motion aware, dependency-free, and not mounted in the application.

## Consequences

The UI can explain the statistical gap without disclosing research internals or implying profitability. There is still no report integration, writer, persistence, current cutover, paper authorization, or live authority. Browser and rendered-device QA remain outside this slice because no browser or service startup was authorized.
