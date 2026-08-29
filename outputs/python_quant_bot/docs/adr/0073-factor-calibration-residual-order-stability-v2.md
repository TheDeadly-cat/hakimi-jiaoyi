# ADR 0073: Factor calibration residual-order stability v2

## Status

Candidate only. Unmounted and not current.

## Decision

Freeze K0 v1 and add a v2 verifier that evaluates lag 1 and lag 2 separately,
then takes the maximum absolute normalized residual-energy coupling. The
inclusive ceiling remains `0.8`. K0 v1, H0, replay, registration, observation,
and fold identities remain strictly bound.

## Motivation

A repeated `++--` residual pattern has lag-one coupling `0.111...` after signed
cancellation but lag-two coupling `1`. K0 v1 and precommit v4 therefore remain
locally positive despite deterministic periodic residual order.

## Limits

V2 closes only the preregistered lag-two bypass. It is not a white-noise test,
does not cover arbitrary lag order, and grants no profitability or execution
authority.
