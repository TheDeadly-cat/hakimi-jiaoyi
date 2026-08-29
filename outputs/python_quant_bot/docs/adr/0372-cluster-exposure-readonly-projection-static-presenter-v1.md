# ADR 0372: Cluster Exposure Read-only Projection Static Presenter v1

- Status: implemented, additive, unmounted
- Date: 2026-08-24
- Scope: pure static view-model and markup presenter
- Authority: none; paper and live remain unauthorized

## Context

ADR0371 provides a redacted, hash-bound cluster-exposure projection suitable
for a future public presentation boundary. Rendering it directly through a
generic object inspector would weaken the UI contract: unknown metrics could
leak, arbitrary blocker text could enter markup, neutral maturity stages could
be reordered, and an observed within-limit state could look like readiness.

The presenter must preserve the project's visual language while remaining
unmounted until a trustworthy exact-verification handoff exists.

## Decision

Add a pure JavaScript presenter and isolated stylesheet:

- `evidence_cluster_exposure_readonly_projection_v1.js`
- `evidence_cluster_exposure_readonly_projection_v1.css`

The presenter accepts only a strict verification-handoff envelope containing an
ADR0371 projection, its expected hash, and the exact verification status. It
validates the complete fixed schema, status-specific decision path, summary
shape, authority lock, facts, blocker order, and hash equality before producing
an immutable view model or escaped HTML string.

Invalid input produces a fixed `UNKNOWN` view model. No caller-controlled value
from an invalid envelope is reflected.

## Verification handoff boundary

The JavaScript presenter is not a cryptographic verifier. Hash equality in the
handoff envelope proves only that two supplied strings match. A future bridge
must first call the ADR0371 Python exact verifier and then construct the
versioned handoff envelope in the same trusted read-only boundary.

Until that bridge is separately specified and verified, the presenter remains
unmounted and cannot be used as evidence authority.

## Visual direction

The component uses the established ink, paper, tide, rust, and marker palette
with Fraunces, IBM Plex Sans Condensed, and IBM Plex Mono typography. Its visual
signature is a contour map where two proposal nodes flow into one cluster
exposure ring and a marked preregistered cap.

The status palette is neutral:

- unknown uses muted grey;
- limit breach uses rust;
- within-limit observation uses tide blue, not success green.

The governance rail remains exactly:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

The component always states that it is a static, non-live projection and that
it does not form an admission, position, signal, order, return, or profit
conclusion.

## Presenter invariants

1. Envelope and projection keys are exact; extra keys fail closed.
2. Projection and expected hashes are lowercase SHA-256 and equal.
3. ADR0371 schema, fingerprint, unmounted status, facts, and authority are exact.
4. Unknown metrics render only `--`.
5. Limit blockers are allowlisted and canonically ordered.
6. Static evidence blockers remain visible for every status.
7. Authority promotion or blocker injection returns the fixed unknown view.
8. All rendered values are HTML escaped.
9. View models and nested values are deeply frozen.
10. Production JavaScript has no DOM, network, storage, route, runtime loader,
    or pointer API.
11. CSS is scoped, responsive at 720 and 430 pixels, keyboard-focus visible,
    and reduced-motion aware.
12. Neither JavaScript nor CSS is referenced by the current `index.html`.

## Public copy

- `未核验`
- `预登记上限阻断`
- `结构内观察`
- `静态只读投影 · 非实时结果`
- `模拟未授权 · 实盘永久硬锁`
- `不构成准入、仓位、信号、订单或收益结论`

The presenter does not use `READY`.

## Consumer-first activation order

1. Keep the presenter and CSS unmounted.
2. Define a versioned Python-to-JavaScript verification-handoff bridge.
3. Prove the bridge calls ADR0371 exact verification and cannot set exact status
   from an unverified document.
4. Run Node contract checks for the bridge plus presenter.
5. Only then consider an explicit static mount ADR. No automatic current or
   public-reader activation is allowed.

## Non-goals

- No DOM mount or current-page modification.
- No browser or screenshot validation claim.
- No HTTP, artifact reader, engine, runtime, storage, scheduler, pointer,
  publication, paper, or live operation.
- No market data, backtest, return, or profitability claim.
- No natural-forward chain change.

## Evidence boundary

Node tests prove static parsing, fail-closed presentation, escaping, immutable
view models, stage order, styling contracts, and deliberate non-mounting only.
They do not prove rendered-browser appearance, accessibility technology
behavior, market validity, evidence maturity, profitability, or trading
authorization.
