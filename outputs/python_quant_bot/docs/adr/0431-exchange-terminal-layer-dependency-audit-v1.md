# ADR0431: Exchange terminal layer-dependency audit v1

## Status

Accepted as a pure static architecture audit. The current graph is explicitly
BLOCKED_PARTIAL_LAYERING. This ADR does not move modules, install compatibility
shims, activate runtime behavior, or claim that the architecture migration is
complete.

## Context

The exchange terminal now contains domain, application, infrastructure, and
interfaces packages. Existing research-only and legacy-CLI contracts verify
capability locks, health behavior, synthetic fallback restrictions, and
side-effect-free listing. They do not verify dependency direction between the
new packages.

A scoped AST audit of the current source graph found:

- no module-level dependency cycle;
- domain has no outward dependency on application, infrastructure, or
  interfaces;
- application does not depend on infrastructure;
- application imports interfaces modules;
- interfaces modules also import application modules; and
- the interfaces package therefore mixes inward port definitions with outward
  delivery adapters and handoffs.

No module cycle does not prove that package roles are closed.

## Decision

Add a pure AST dependency auditor. The service accepts only a bounded native
mapping from canonical module name to source text. It performs no filesystem
enumeration and executes no imported module. The targeted contract supplies
only the four explicit source directories.

The audit reports:

- source-set hash and per-layer module counts;
- unique cross-layer dependency edge counts;
- bidirectional package pairs;
- module-level strongly connected components;
- dynamic-import presence;
- the observed interfaces port/delivery role mix;
- violations and a minimum cleanup slice; and
- permanently locked architecture, host, current, writer, paper, and live
  authority.

The current tree must return BLOCKED_PARTIAL_LAYERING with:

- APPLICATION_INTERFACES_PACKAGE_BIDIRECTIONAL;
- INTERFACES_PACKAGE_MIXES_PORT_AND_DELIVERY_ROLES; and
- PORT_DELIVERY_NAMESPACE_SPLIT_NOT_COMPLETED.

Its no-cycle, inward-domain, and application/infrastructure separation facts
remain visible rather than being discarded.

## Minimum cleanup slice

1. Classify every interfaces module as port, delivery adapter, or support.
2. Create an explicit application-owned port namespace.
3. Migrate application imports from interfaces to the port namespace.
4. Keep delivery adapters depending inward on application.
5. Add only temporary, hash-pinned compatibility shims for existing consumers.
6. Remove shims only after consumer-first migration evidence.

This ADR records the slice but does not perform it. Moving all modules at once
would create a high-risk compatibility rewrite and could overwrite current
working-tree changes.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Current four-layer graph | blocked partial layering |
| Current graph module cycles | none |
| Clean inward graph | conforming |
| Bidirectional package roles without module cycle | blocked |
| Cross-layer module cycle | blocked |
| Domain outward dependency | blocked |
| Application to infrastructure dependency | blocked |
| Dynamic import | blocked as unaudited |
| Non-native source map | UNKNOWN |
| Syntax error | UNKNOWN |
| Resealed migration-complete promotion | verifier rejects |
| Repeated evaluation | deterministic |
| Raw source text | not embedded |

## Consumer-first continuation

1. Keep the current package graph operational and the audit blocked.
2. Preregister the module-role classification and exact source preimages.
3. Introduce the application-owned port namespace without deleting old paths.
4. Migrate one consumer family at a time.
5. Verify import compatibility and side-effect boundaries after each family.
6. Remove compatibility shims only through a separate decision.
7. Re-evaluate architecture completion only when package bidirectionality is
   absent and all migration evidence is current.

No step authorizes or automatically performs the next step.

## Evidence and permission boundary

This ADR uses static source parsing only. It does not read runtime state, import
the audited modules, start a service or browser, mutate a database or cache, run
a backtest, or start a trading task. Architecture-test evidence does not prove
strategy performance, profitability, release authority, or paper/live
permission.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
