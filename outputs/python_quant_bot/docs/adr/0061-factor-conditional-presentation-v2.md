# ADR 0061: Factor-Conditional Presentation v2

## Status

Accepted for an unmounted candidate. This decision versions the Python
presentation envelope and the detached evidence card. It does not mount either
artifact in the application, add a route, or authorize current/paper/live use.

## Context

F2 consumes the frozen F1-v1 receipt. A synthetic replay produced a VERIFIED,
OBSERVED F2 envelope whose complete key set contained no F3 gate hash, F4
verification hash, family registration hash, global test count, global decision,
or aggregate view summaries. F2 is correct for its historical source and must
remain frozen.

F4 now provides a strict aggregate report that composes F1 and F3. Presenting
that report through F2 would either discard the global family or silently change
the meaning of an existing schema. A versioned F5 boundary is required.

## Decision

Create these detached candidate contracts:

- envelope schema: `strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v2`
- envelope fingerprint: `20260822-cross-lag-factor-conditional-presentation-envelope-2`
- model schema: `strategy-correlation-cross-lag-factor-conditional-presentation-model-v2`
- presentation fingerprint: `20260822-cross-lag-factor-conditional-f5-unmounted-presentation-1`
- presentation status: `UNMOUNTED_CANDIDATE`

The Python envelope must replay F4 through the full F4 verifier. It receives F4,
F1, F3, family registration, F0, strata, raw rows, residual rows,
residualization registration, factor observations, and every expected hash used
by F4. The envelope never treats a sealed F4 document as self-authenticating.

## Envelope states

- `VERIFIED`: F4 exactly replays. The envelope carries a deep copy of the F4
  aggregate report and its F1/F3 provenance hashes.
- `NOT_SUPPLIED`: no F4 report was supplied.
- `UNSUPPORTED`: the report schema or fingerprint is not F4-v2.
- `INVALID`: shape, expected hash, exact replay, or strict JSON verification
  failed.

A VERIFIED envelope may still carry an F4 `source_state=UNKNOWN`. VERIFIED means
the UNKNOWN closure replayed exactly; it does not convert UNKNOWN to evidence.

## Browser model

The JavaScript model must verify the Python `envelope_hash` using strict
canonical JSON and SHA-256 before reading the report. It must reject:

- wrong schema or fingerprint;
- tampered or non-finite envelopes;
- unverified report states presented as evidence;
- unlocked authority;
- identity-level or private-ledger fields;
- reordered or missing SOURCE -> GAP -> MATURITY -> PERMISSION axes.

The card exports factory functions only. It performs no DOM query, mount,
network call, storage access, timer, or global application mutation on import.

## Visual direction

The detached card uses a warm neutral evidence-atlas surface with graphite type,
muted mineral accents, a four-axis evidence rail, compact family metrics, paired
RAW/RESIDUAL rows, provenance hashes, and explicit blockers. The layout must be
responsive and provide reduced-motion behavior.

The copy remains neutral:

- SOURCE identifies verified artifact lineage.
- GAP reports the global family decision without claiming independence.
- MATURITY states candidate and timing limitations.
- PERMISSION states research-only and no execution authority.

No READY, profitability, recommendation, buy/sell, or execution language is
permitted.

## Security and privacy

- DOM rendering uses `textContent`, never untrusted `innerHTML`.
- Identity-level lag rows and private recalculation-ledger content are forbidden.
- Hashes may be visually shortened, but the full value remains in safe title or
  data attributes.
- No automatic mount or browser side effect is allowed.
- The component is scoped under one F5 class namespace.

## Adversarial matrix

1. VERIFIED pass-family envelope;
2. VERIFIED blocked-family envelope;
3. VERIFIED exact UNKNOWN closure;
4. missing F4 -> NOT_SUPPLIED;
5. F1/F2 source -> UNSUPPORTED;
6. F4 expected-hash mismatch -> INVALID;
7. F4 coherent reseal -> INVALID;
8. F1/F3/source-context substitution -> INVALID;
9. residual removal/duplicate/reorder/extension -> INVALID;
10. envelope metric/report/authority reseal -> reject;
11. mapping subclass -> INVALID;
12. non-finite source -> INVALID;
13. aggregate-only projection;
14. permanently locked authority;
15. deterministic closed states;
16. denied Python I/O/time/randomness;
17. Python-to-Node hash parity;
18. JS tamper after sealing;
19. JS authority alias/unlock;
20. JS identity/private-ledger injection;
21. detached import with no DOM;
22. safe text rendering of hostile strings;
23. responsive and reduced-motion CSS;
24. forbidden READY/profit/execution copy scan.

## Activation order

1. Python envelope and contracts.
2. Detached JS model/card and scoped CSS.
3. Independent Python-to-Node parity review.
4. Research lean list/dry-run integration.
5. Baseline documentation.
6. Any application mount requires a separate ADR and current-evidence audit.

## Invariants

- F1-v1, F2, F3, and F4 remain unchanged.
- No app, HTML, server, Electron, scheduler, or current pointer references F5.
- The natural-forward single-look chain remains unchanged.
- Legacy pack-v5 public reads remain UNKNOWN.
- Pointer-v2 remains field/hash compatible and is not reissued.
- Synthetic and backtest evidence does not prove profitability.
- Paper and live remain unauthorized; live remains hard locked.

## F5 implementation closure: detached envelope and evidence atlas

The Python envelope v2, detached JavaScript model/card, scoped CSS, and their contracts are implemented without changing F2 or any mount point. The envelope fully replays F4 and distinguishes VERIFIED, NOT_SUPPLIED, UNSUPPORTED, and INVALID. A VERIFIED exact F4 UNKNOWN remains UNKNOWN.

The browser model recomputes the Python `envelope_hash` with strict canonical JSON and SHA-256 before reading the report. It rejects authority aliases/unlocks, identity-level fields, private-ledger fields, malformed view summaries, and tampering after sealing. Import is DOM-free; card creation requires an explicit document and writes untrusted values through `textContent` only.

Visual implementation uses a warm neutral evidence-atlas surface, graphite typography, mineral status accents, a SOURCE -> GAP -> MATURITY -> PERMISSION rail, global-family metrics, RAW/RESIDUAL rows, blockers, provenance tokens, two responsive breakpoints, staggered reveal, and reduced-motion closure. It remains detached and has no browser screenshot or mounted-runtime evidence.

Validation evidence:

- Python envelope targeted contracts: `16/16 PASS`
- Node syntax checks: `2/2 PASS`
- detached Node model/card/CSS contracts: `16/16 PASS`
- actual Python-to-Node PASS/BLOCK/UNKNOWN hash and state parity: PASS
- F1/F2/F3/F4/F5 combination matrix: `173/173 PASS`
- fixed activation-source files scanned: `20`; F5 references: `0`

The research lean plan now includes the F5 Python test/syntax target and a separate F5 Node check. No fresh execution, mount, browser, service, route, scheduler, pointer, paper task, or live task is authorized.
