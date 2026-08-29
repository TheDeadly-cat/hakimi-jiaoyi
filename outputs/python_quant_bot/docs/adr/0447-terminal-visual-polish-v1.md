# ADR 0447: Terminal visual polish V1

## Status

Accepted on 2026-08-25.

## Context

The terminal already has a large, evidence-heavy information architecture and a
protected base stylesheet and JavaScript contract. Rewriting those assets would
mix visual work with mature evidence behavior and create unnecessary compatibility
risk. The page nevertheless benefits from a clearer reading hierarchy, stronger
keyboard focus, and a more deliberate narrow-screen layout.

## Decision

Add one independent stylesheet after the established style layers. The visual
direction is an evidence calibration bench rather than a promotional trading
screen:

- Existing Carbon, Slate, Cyan, Amber, Red, and Soft Ink tokens remain the color
  source across all current themes.
- Bahnschrift is used as the local display face, Aptos and Microsoft YaHei UI for
  body text, and Cascadia Mono for status and evidence identifiers. No external
  font or network dependency is introduced.
- A low-contrast measurement grid and a calibration-tick spine provide the single
  signature element. Large glow effects and speculative market decoration are
  intentionally excluded.
- The four evidence stages receive distinct but neutral accents. Green is not used
  to imply maturity, permission, profitability, or authorization.
- Keyboard focus, reduced-motion, forced-colors, 1180/760/500 pixel breakpoints,
  horizontal control overflow, and single-column dense grids are handled in the
  additive layer.

The HTML change is one stylesheet link. Existing CSS, JavaScript, element IDs,
copy, data attributes, and event bindings are untouched.

## Static contract

The dedicated Node contract proves that:

- the polish layer is linked exactly once and after both established stylesheets;
- all four protected frontend fingerprints remain exact;
- `SOURCE -> GAP -> MATURITY -> PERMISSION` stays in order;
- the explicit simulation-unavailable and live-hard-lock copy remains present;
- the stylesheet has no external imports or URLs;
- focus-visible, responsive, reduced-motion, and forced-colors contracts exist;
- CSS braces are balanced.

## Evidence boundary

Static checks prove source wiring and declared CSS contracts only. No browser was
started, so this ADR makes no rendered-layout, pixel, interaction, console, or
cross-browser claim. It does not change evidence authority, paper/live permission,
or profitability claims.
