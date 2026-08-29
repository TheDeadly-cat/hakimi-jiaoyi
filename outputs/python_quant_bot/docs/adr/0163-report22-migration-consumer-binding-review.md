# ADR 0163: report22 migration consumer-binding review

- Status: Accepted
- Date: 2026-08-22
- Scope: Sealed static consumer-binding review

## Context

ADR 0162 established executable Python-to-Node evidence for the report22 migration
HTTP response and lockboard. The blocked mount preregistration still needs a
durable record that identifies exactly which consumer sources and executable test
definitions were reviewed. Historical test totals must not become embedded mount
authority.

## Decision

Add a deterministic, no-argument review-v1 artifact. It pins SHA-256 values for
the Python HTTP candidate, public projection, mount preregistration-v1, Node
lockboard and Node HTTP binding. It separately pins the Node binding test,
presentation suite-v15 and Python cross-runtime test source files.

The review records a five-case state matrix, Python-compatible canonical hash
contract, fixed SOURCE/GAP/MATURITY/PERMISSION order, CommonJS and browser-global
VM contract availability, verified-payload-only behavior and UNKNOWN fallback.
Test execution results and historical totals are explicitly not embedded.

Status is `CANDIDATE_BOUND_NOT_MOUNTED`. Static consumer review is complete, while
actual HTTP transport, DOM mounting, browser-process visual review and runtime
asset review remain false. Mount preregistration-v1 remains immutable and BLOCKED;
this artifact does not rewrite its consumer-review field.

## Consequences

The consumer binding now has a sealed source and evidence-definition identity for
a future successor mount decision. It does not prove live transport or visual
behavior, register a route, start a service/browser, execute migration, change
current/single-look/pointer, or grant paper/live and profitability authority.
