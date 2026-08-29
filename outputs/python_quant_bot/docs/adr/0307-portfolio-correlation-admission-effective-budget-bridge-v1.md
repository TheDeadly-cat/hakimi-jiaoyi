# ADR 0307: Admission-budget structural bridge v1

## Status

Accepted as an isolated, unmounted, research-only presentation candidate.

## Context

ADR 0306 provides an exact cross-runtime envelope for the ADR 0305 binding.
The remaining presentation problem is not another data table. A consumer must
show that correlation topology and effective-bet exposure are independent
load-bearing decisions, that both depend on one shared source binding, and that
no local PASS grants permission.

Reusing the ADR 0303 correlation drafting table would blur the difference
between universe matching and portfolio exposure. Editing ADR 0303 would also
invalidate its frozen source and consumer-registration hashes.

## Visual direction

The component uses a structural-inspection bridge metaphor.

- ADMISSION TOPOLOGY is the left pier.
- EFFECTIVE BUDGET is the right pier.
- SHARED SOURCE BINDING is the center span lock.
- The seven binding tiers form an inspection truss.
- SOURCE, GAP, MATURITY, PERMISSION form the governance deck below.
- PERMISSION remains a separate locked footer.

The palette uses paper, ink, steel blue, inspection orange, and survey yellow.
It intentionally avoids green success semantics. Typography combines a
high-contrast editorial title, condensed geometric body, and monospaced
inspection labels.

The distinctive signature is a three-part pier-span-pier structure rather than
cards that could be mistaken for independent approvals.

## Decision

Add a UMD/CommonJS pure presentation module and isolated stylesheet.

The module:

- accepts only the ADR 0306 envelope;
- calls the ADR 0306 frozen payload extractor internally;
- returns a deeply frozen view model;
- returns an escaped markup string;
- does not accept a naked view model as trusted source input;
- does not expose blocker text, source documents, positions, symbols, strategy
  identifiers, or full hashes;
- shows only short binding and proposal hashes;
- distinguishes local alignment, topology block, exposure block, source block,
  and source unknown;
- always ends with PERMISSION UNAUTHORIZED.

The stylesheet:

- is isolated under .hakimi-admission-budget-bridge-v1;
- has no import, URL, root, html, or body selector;
- includes compact and narrow responsive layouts;
- includes a reduced-motion guard;
- does not modify the protected host stylesheet.

## State language

- LOCAL ALIGNMENT means both local research decisions pass on one exact source
  chain.
- TOPOLOGY BLOCK means admission v2 blocks.
- EXPOSURE BLOCK means effective-budget v3 blocks.
- SOURCE BLOCK means an exact or shared-source tier blocks.
- SOURCE UNKNOWN means the delivery envelope cannot support a conclusion.
- UNAUTHORIZED means no current, paper, live, render, mount, or execution
  authority.

No READY label or profitability language is allowed.

## Non-goals

- No app.js or index.html import.
- No stylesheet link.
- No DOM mount or render call.
- No route, endpoint, or payload provider.
- No browser or service launch.
- No current writer, scheduler, paper, live, or order path.
- No backtest, blind test, or profitability claim.
- No change to the natural-forward evidence chain.
- No pack-v5 compatibility promotion.
- No pointer-v2 field, hash, or publication change.

## Activation boundary

A future consumer-registration contract may pin this JavaScript source,
stylesheet, Node contract, ADR, and ADR 0306 adapter registration. It remains a
separate decision from host registration, browser review, mounting, or current
activation.
