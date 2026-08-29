# ADR 0316: Portfolio Correlation Admission Effective-Budget Python Provider Binding v1

- Status: Accepted as an internal-only blocked binding
- Date: 2026-08-24
- Scope: Pure synthetic, explicit in-memory research calls

## Context

ADR0314 preregistered a Python provider candidate but kept its active import,
provider registration, and bound flag empty.  ADR0315 then registered the exact
consumer assets without loading them.  The next consumer-first step is a real
Python provider binding.  A second descriptive registration would not close the
gap because no exact document could resolve the ADR0311 callable.

Directly mounting the callable in `server.py` would skip the provider boundary,
mix provider resolution with HTTP policy, and make an internal research function
look externally authorized.  The provider binding must therefore be usable in
memory while remaining absent from the application and HTTP host.

## Decision

Add `portfolio-correlation-admission-effective-budget-python-provider-binding-v1`
with one nondefault registry entry.  The binding:

- verifies the exact ADR0314 host-binding preregistration;
- verifies the exact ADR0315 consumer static-asset registration;
- pins the ADR0311 module, callable, verifier, input mode, output schema, adapter
  registration, consumer preregistration, and Python consumer contract hashes;
- returns the ADR0311 callable only after a single safe snapshot of an exact
  ADR0316 binding document;
- permits explicit in-memory synthetic research resolution only;
- has no implicit default provider and accepts no external request authority;
- does not invoke the callable while the binding document is built.

The fixed contract hashes are:

- host Python provider candidate hash:
  `7afe9f01f2eef2ac20d39900d1c4102bd46b0f1eb1325dabdb41f6b012b460c6`
- callable identity hash:
  `79b2eed39d69bf89cf599951e302e75dd40cfcf2f935d9bbe8e1f535c3f8e2ce`
- registry hash:
  `1e2eb0bb8ad241b8b8c9c50299a58cbf17cea166ef33a59e3fa34aed4a359db2`
- provider binding hash:
  `d9b36dc1dce884333a985ff0a64e71359dea7adf128431ef12c407eab1466060`

## State and authority

The binding state is
`PYTHON_PROVIDER_BOUND_INTERNAL_ONLY_HTTP_APP_HOST_CURRENT_UNBOUND` and the
overall status remains `BLOCKED`.  Only these capabilities are true:

- exact in-memory provider resolution;
- explicit synthetic research invocation.

External requests, HTTP projection, application import, routes, endpoints,
runtime asset loading, browser execution, DOM mount, current admission, writer,
paper, and live authority remain false.

## Adversarial requirements

| Mutation or action | Required result |
| --- | --- |
| Build binding document | Provider is not invoked |
| Exact binding resolution | Exact ADR0311 callable is returned |
| Exact synthetic source chain | Existing KNOWN result and hash are preserved |
| Callable identity drift | No provider is returned |
| Registry default promotion | No provider is returned |
| Host or HTTP binding injection | No provider is returned |
| Authority promotion | No provider is returned |
| Unknown field or cyclic input | Fail closed |
| Second-read hash swap | One snapshot prevents the swap |

## Next activation order

1. Verify ADR0314, ADR0315, and ADR0316 exactly.
2. Resolve ADR0316 only for explicit synthetic research calls.
3. Design a read-only HTTP projection in a separate version.
4. Keep application import and host loading in a later separate version.
5. Require authorized browser review before any route or mount.
6. Consider current only through a separate explicit decision.

## Non-authority

The synthetic KNOWN call proves only that the existing exact source chain can be
reached through the provider boundary.  It is not a profitability result, does
not run a backtest or trading task, and grants no paper or live permission.  This
ADR does not alter the natural-forward single-look chain, legacy pack-v5 UNKNOWN
behavior, or pointer-v2.
