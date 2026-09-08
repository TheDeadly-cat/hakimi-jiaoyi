# Review closeout: current build and research use

Input: the user-supplied review of `2cbccfdcb46c05ce4427f39fec541f7e77a0c6ee`,
read on 2026-09-05. This is the acceptance checklist, not a completion claim.
The existing offline CLI remains the baseline; existing source, raw inputs,
reports and historical references are preserved.

| Stage | Required result | Evidence required for completion |
|---|---|---|
| A | Old-position opening protection precedes pending orders; known opening target precedes ambiguous intrabar events; explicit reentry rule | Both review counterexamples reproduced then corrected; accounting, fees, partial fills and first equity contracts pass; versioned execution semantics |
| B | Exact accepted wheel is downloadable with redacted identity, dependencies, acceptance, scope and checksums | Successful current-SHA Windows/Ubuntu CI, downloaded artifacts independently verified and installed outside checkout; main gate policy read back from GitHub |
| C | Same original snapshot and all original 16 specs rerun under current wheel, then independently replayed | Report/ledger/summary verification; original files unchanged; cross-version orders, fills, equity and metric comparison; sanitized review package |
| D | Fixed Cash, full Buy-and-Hold, 25% initial Buy-and-Hold control, Dual MA and RSI over declared historical windows and costs | Plan fixed before outcomes; actual admitted source coverage; all240 planned cells retained; failures, return concentration, exposure and cost sensitivity explained; no blind/confirmation claim for viewed history |
| E | Frozen no-order forward observations with input/output/source/time identities | Immutable records; source-plan mismatch rejection; timing and backfill labels; reproducible signal records; explicit local deployment state |
| F | Measured full pipeline and concise read-only result view | Import/verification/execution/serialization/save/replay timings with scope; output linked to data/spec/result identities; no unmeasured optimization claims |

## Repository policy

`main-branch-protection.json` declares the GitHub-hosted policy: PR changes,
strict up-to-date `Research required gate` from GitHub Actions App15368,
administrator enforcement, no force pushes/deletions, resolved conversations.
The owner retains the merge decision; no number of outside reviewers is imposed
on this personal repository. Readiness for review does not execute a merge.
Policy behavior is documented by [GitHub](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

## Research boundaries

BTC-USDT spot, completed1h candles only. Source capture is explicit public GET;
research and replay are offline. No account, key, order, leverage, new market,
parameter search, AI decision path or desktop rewrite is part of this closeout.
Research observations are descriptive; 2026-08 was already viewed. The long-range
plan is checked against actual source coverage, never populated with synthetic
or silently interpolated substitutes.
