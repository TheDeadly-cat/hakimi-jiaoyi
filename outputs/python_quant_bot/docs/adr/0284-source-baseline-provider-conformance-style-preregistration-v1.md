# ADR0284: Source-Baseline Provider-Conformance Style Preregistration v1

## Status

Accepted as a machine-readable, isolated, unmounted stylesheet candidate.

## Context

ADR0282 supplies a neutral card renderer. ADR0283 registers its JavaScript and
canonical dependency but deliberately leaves stylesheet, app importer, and HTML
template null. The protected shared stylesheet cannot be changed or silently
reused for this source-specific consumer.

The subject is an external anti-replay provider-conformance gap. The audience is
a research-terminal operator. The card has one job: separate bound source,
open gaps, preregistered-but-not-run maturity, and locked permission at a glance.

## Design plan

Visual direction: **cold audit film**. The candidate uses a pale mineral surface,
oxide-black text, oxidized teal for locally bound traces, amber for unresolved
gaps, rust for permission locks, and blue-grey rules. It avoids the familiar
dark trading terminal, neon green, purple gradient, rounded dashboard tile, and
generic warm editorial defaults.

Typography has three roles:

- display: condensed industrial lettering for title and bounded counts;
- body: restrained humanist sans for explanations;
- utility: monospace for stages, hashes, states, and blocker identifiers.

The signature element is a four-stage calibration spine. Its color sequence
encodes the actual contract, not decoration: trace, gap, not-run maturity, lock.

Desktop structure:

```text
+-------------------------------------------------------------+
| SOURCE BASELINE / PROVIDER CONFORMANCE   NOT RUN / BLOCKED |
| External anti-replay conformance gap                       |
| 06 SOURCE | 14 REQUIRED | 00 RUN | 00 PASS | 07 OPEN      |
| SOURCE ===== GAP ===== MATURITY ===== PERMISSION            |
| OPEN GAP REGISTER        01 ... 07                          |
| PROVIDER / WRITER / ROUTE / UI / CURRENT / PAPER / LIVE    |
+-------------------------------------------------------------+
```

Compact layouts turn the calibration spine vertical and collapse the gap
register to one column. Motion is limited to a short stage reveal and is only
selectable under a future explicit `data-mount-state="mounted"`; reduced-motion
users receive no animation.

## Self-critique and revision

The first obvious direction was a dark execution terminal with bright status
accents. It was rejected because it is generic, biases the product toward live
trading, and can make a blocked evidence card look operational. The revised
light instrument-sheet treatment spends visual emphasis only on the calibration
spine and keeps every other surface quiet.

## Decision

Add a UMD/CommonJS style-preregistration module that seals the brief, six-color
palette, three typography roles, geometry, selector namespace, breakpoints,
mounted-only motion, asset plan, facts, and locked authority.

Add a new isolated stylesheet implementing that contract under the exclusive
`.sb-conformance-card` namespace. It does not import fonts, images, the shared
stylesheet, or external URLs. It defines desktop, compact, narrow, and reduced-
motion behavior. No existing stylesheet is modified.

The preregistration leaves the candidate stylesheet hash null. A later
registration version must independently pin the final stylesheet and contract
hashes before any app binding is considered.

## Consumer-first activation order

1. Keep ADR0281 producer preregistration frozen.
2. Keep ADR0282 card and ADR0283 asset registration frozen.
3. Validate this isolated style contract and candidate without a browser.
4. Create a future registration version that pins both new asset hashes.
5. Preregister app load order, route, and mount separately.
6. Execute browser and visual review only after explicit authorization.

No step automatically promotes the next one.

## Non-claims

Static CSS contract checks are not browser rendering or visual validation. This
candidate is not imported, routed, mounted, browser-executed, visually reviewed,
or admitted to current evidence. It does not call a provider, mutate runtime
state, authorize paper or live activity, prove market validity, demonstrate
strategy performance, or prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
