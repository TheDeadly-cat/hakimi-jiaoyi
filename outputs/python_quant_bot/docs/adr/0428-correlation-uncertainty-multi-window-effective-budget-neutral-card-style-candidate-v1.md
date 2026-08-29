# ADR0428: Correlation uncertainty effective-budget neutral card style candidate v1

## Status

Accepted as an unmounted stylesheet candidate with a static Node contract. It
is not imported by app.js or styles.css, loaded by a browser, mounted in the
DOM, or approved for host integration.

## Context

ADR0348 created a deterministic semantic card for the ADR0347 correlation
uncertainty and effective-budget projection. The card already distinguishes a
cross-cluster veto, reduction-only path, local research-budget observation,
downstream block, and unknown source while preserving the neutral
SOURCE -> GAP -> MATURITY -> PERMISSION order.

ADR0348 explicitly left production styling and browser review absent. The
static directory contains no stylesheet for its emitted class names. Modifying
the protected host stylesheet would combine visual design, asset registration,
browser execution, and mount authority in one change.

## Decision

Add a standalone stylesheet candidate for the existing ADR0348 markup. The
stylesheet is not imported. Every selector is scoped to the
.hakimi-uncertainty-budget-card-v1 namespace and its emitted descendants.

The visual direction extends the established evidence-card language:

- warm paper surfaces with a restrained technical grid;
- condensed display typography, editorial body typography, and monospaced
  evidence labels;
- cool teal for source, ochre for open gaps, blue-gray for maturity, and oxide
  brown for locked permission;
- explicit text states preserved in the markup so color is never the only cue;
- six bounded metrics, a four-stage rail, open-gap ledger, source receipt, and
  permission note with distinct spatial hierarchy; and
- one finite card entrance plus staggered stage disclosure, disabled under
  reduced-motion preferences.

The style supports desktop, container-constrained, and narrow layouts. It also
defines increased-contrast, forced-colors, and print fallbacks. It loads no
font, image, script, or remote resource.

## Static adversarial contract

The colocated Node contract pins the exact ADR0348 card implementation, test,
and decision hashes. It also pins the protected app.js,
evidence_presentation.js, and styles.css preimages and proves none references
the candidate stylesheet.

The contract verifies:

- every emitted card class has an explicit scoped style;
- no html, body, :root, universal host, or ID selector is introduced;
- design tokens, typography, layered background, responsive grids, four state
  treatments, reduced motion, forced colors, contrast, and print rules exist;
- animations are finite;
- pseudo-elements inject decoration only, never UI copy;
- no import, URL, executable CSS, fixed host overlay, unresolved template token,
  promotional wording, or sensitive locator exists; and
- brace structure is balanced.

## Consumer-first continuation

1. Keep the ADR0348 card and ADR0428 stylesheet unmounted.
2. Obtain independent semantic-markup, CSS-scope, disclosure, and contrast
   review.
3. Preregister the exact card and stylesheet hashes as one asset pair.
4. Define a separately preregistered host adapter and protected preimages.
5. Only with explicit authorization, load the pair in an isolated browser
   review environment.
6. Review desktop and mobile layout, native zoom, keyboard reading order,
   screen-reader output, contrast, forced colors, and reduced motion.
7. Keep production import, route, DOM mount, current, writer, paper, and live
   authority behind separate decisions.

No step authorizes or automatically performs the next step.

## Evidence and permission boundary

This ADR makes no browser, visual-quality, accessibility, market-validity,
strategy-performance, profitability, release, or trading-permission claim. No
service, browser, runtime asset, cache, database, log, scheduler, backtest, or
trading task is accessed or started.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
