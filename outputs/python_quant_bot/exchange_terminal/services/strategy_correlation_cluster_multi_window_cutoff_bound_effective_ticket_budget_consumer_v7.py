from __future__ import annotations

from typing import Any

from .strategy_correlation_cluster_multi_window_market_data_common_cutoff_gate_v6 import (
    GATE_SCHEMA_VERSION as COMMON_CUTOFF_GATE_V6_SCHEMA_VERSION,
    PREREGISTRATION_SCHEMA_VERSION as COMMON_CUTOFF_PREREGISTRATION_V6_SCHEMA_VERSION,
    verify_market_data_common_cutoff_gate_v6,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-cutoff-bound-effective-ticket-"
    "budget-preregistration-v7"
)
COMPONENT_DERIVATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-conservative-component-"
    "derivation-v1"
)
CONSUMER_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-cutoff-bound-effective-ticket-"
    "budget-consumer-v7"
)
CONSUMER_VERIFICATION_SCHEMA_VERSION = f"{CONSUMER_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-correlation-cluster-cutoff-bound-effective-ticket-budget-v7-lock-1"
)
CLUSTER_MERGE_RULE = "ANY_WINDOW_COCLUSTER_EDGE_CONNECTED_COMPONENTS"
REQUIRED_WINDOW_IDS = ("short", "anchor", "long")
MAX_MONEY_MINOR_UNITS = 9_999_999_999_999_999

_CUTOFF_CONTEXT_KEYS = frozenset(
    {
        "common_cutoff_preregistration",
        "adapter_v5_document",
        "adapter_v5_context",
        "expected_common_cutoff_preregistration_v6_hash",
    }
)


class CutoffBoundEffectiveTicketBudgetContractError(ValueError):
    pass


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _identifier(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 160
        or any(character.isspace() for character in value)
    ):
        raise CutoffBoundEffectiveTicketBudgetContractError(f"{field}_invalid")
    return value


def _native_int(
    value: Any,
    field: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise CutoffBoundEffectiveTicketBudgetContractError(f"{field}_invalid")
    return value


def _validated_symbols(value: Any) -> list[str]:
    if (
        type(value) is not list
        or len(value) < 2
        or any(
            type(item) is not str
            or not item
            or item != item.strip().upper()
            for item in value
        )
        or value != sorted(set(value))
    ):
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "expected_symbols_invalid"
        )
    return list(value)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "consumer_only": True,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _check(name: str, ok: bool, passed: str, failed: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "blocking": True,
        "detail": passed if ok else failed,
    }


def build_cutoff_bound_effective_ticket_budget_preregistration_v7(
    *,
    expected_symbols: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    expected_common_cutoff_preregistration_v6_hash: Any,
    max_effective_ticket_count: Any,
    max_cluster_gross_bps: Any,
    required_window_ids: Any,
    cluster_merge_rule: Any,
) -> dict[str, Any]:
    symbols = _validated_symbols(expected_symbols)
    clean_strategy_id = _identifier(strategy_id, "strategy_id")
    clean_variant_id = _identifier(variant_id, "variant_id")
    clean_lane = _identifier(lane, "lane")
    if not strict_sha256(expected_common_cutoff_preregistration_v6_hash):
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "expected_common_cutoff_preregistration_v6_hash_invalid"
        )
    ticket_limit = _native_int(
        max_effective_ticket_count,
        "max_effective_ticket_count",
        minimum=1,
        maximum=len(symbols),
    )
    gross_limit = _native_int(
        max_cluster_gross_bps,
        "max_cluster_gross_bps",
        minimum=1,
        maximum=10_000,
    )
    if (
        type(required_window_ids) is not list
        or required_window_ids != list(REQUIRED_WINDOW_IDS)
    ):
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "required_window_ids_invalid"
        )
    if cluster_merge_rule != CLUSTER_MERGE_RULE:
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "cluster_merge_rule_invalid"
        )
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_RESEARCH_ONLY",
        "source": {
            "common_cutoff_preregistration_v6_hash": (
                expected_common_cutoff_preregistration_v6_hash
            ),
        },
        "scope": {
            "symbols": symbols,
            "strategy_id": clean_strategy_id,
            "variant_id": clean_variant_id,
            "lane": clean_lane,
        },
        "policy": {
            "required_window_ids": list(REQUIRED_WINDOW_IDS),
            "cluster_merge_rule": CLUSTER_MERGE_RULE,
            "max_effective_ticket_count": ticket_limit,
            "max_cluster_gross_bps": gross_limit,
            "money_unit": "CALLER_DEFINED_INTEGER_MINOR_UNIT",
            "gross_bps_rounding": "CEILING",
            "proposal_action": "ADD_GROSS_EXPOSURE",
        },
        "facts": {
            "multi_window_cluster_merge_policy_defined": True,
            "effective_ticket_budget_defined": True,
            "cluster_gross_budget_defined": True,
            "budget_evaluated": False,
            "latest_effective_bet_budget_v11_bound": False,
            "runtime_consumer_bound": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        document,
        "budget_preregistration_v7_hash",
    )


def verify_cutoff_bound_effective_ticket_budget_preregistration_v7(
    document: Any,
    *,
    expected_budget_preregistration_v7_hash: Any,
) -> dict[str, Any]:
    exact = False
    if (
        type(document) is dict
        and strict_sha256(expected_budget_preregistration_v7_hash)
        and document.get("budget_preregistration_v7_hash")
        == expected_budget_preregistration_v7_hash
    ):
        try:
            scope = _dict(document.get("scope"))
            policy = _dict(document.get("policy"))
            source = _dict(document.get("source"))
            rebuilt = build_cutoff_bound_effective_ticket_budget_preregistration_v7(
                expected_symbols=scope.get("symbols"),
                strategy_id=scope.get("strategy_id"),
                variant_id=scope.get("variant_id"),
                lane=scope.get("lane"),
                expected_common_cutoff_preregistration_v6_hash=source.get(
                    "common_cutoff_preregistration_v6_hash"
                ),
                max_effective_ticket_count=policy.get(
                    "max_effective_ticket_count"
                ),
                max_cluster_gross_bps=policy.get("max_cluster_gross_bps"),
                required_window_ids=policy.get("required_window_ids"),
                cluster_merge_rule=policy.get("cluster_merge_rule"),
            )
            exact = strict_json_contract_equal(document, rebuilt)
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            exact = False
    return {
        "schema_version": f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1",
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["budget_preregistration_v7_mismatch"],
        "preregistration_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def derive_conservative_multi_window_components_v1(
    window_inputs: Any,
    symbols: Any,
    required_window_ids: Any,
) -> dict[str, Any]:
    clean_symbols = _validated_symbols(symbols)
    if (
        type(required_window_ids) is not list
        or required_window_ids != list(REQUIRED_WINDOW_IDS)
        or type(window_inputs) is not dict
        or set(window_inputs) != set(REQUIRED_WINDOW_IDS)
    ):
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "window_input_scope_invalid"
        )

    parent = {symbol: symbol for symbol in clean_symbols}

    def find(symbol: str) -> str:
        root = symbol
        while parent[root] != root:
            root = parent[root]
        while parent[symbol] != symbol:
            next_symbol = parent[symbol]
            parent[symbol] = root
            symbol = next_symbol
        return root

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        first, second = sorted((left_root, right_root))
        parent[second] = first

    window_summaries: list[dict[str, Any]] = []
    for window_id in REQUIRED_WINDOW_IDS:
        entry = _dict(window_inputs.get(window_id))
        gate = _dict(entry.get("gate"))
        clusters = _list(gate.get("cluster_results"))
        if (
            gate.get("status") != "PASS"
            or gate.get("decision")
            != "PASS_DYNAMIC_WINDOW_INDEPENDENT_TICKET_RESEARCH_GATE"
            or not strict_sha256(gate.get("gate_v2_hash"))
            or not clusters
        ):
            raise CutoffBoundEffectiveTicketBudgetContractError(
                f"{window_id}_gate_invalid"
            )
        cluster_ids: list[str] = []
        covered_symbols: list[str] = []
        for cluster in clusters:
            if (
                type(cluster) is not dict
                or set(cluster)
                != {
                    "cluster_id",
                    "effective_vote_count",
                    "member_outcomes",
                    "status",
                }
                or cluster.get("status") != "PASS"
                or type(cluster.get("effective_vote_count")) is not int
                or cluster.get("effective_vote_count") != 1
            ):
                raise CutoffBoundEffectiveTicketBudgetContractError(
                    f"{window_id}_cluster_invalid"
                )
            cluster_id = _identifier(cluster.get("cluster_id"), "cluster_id")
            members_raw = _list(cluster.get("member_outcomes"))
            members: list[str] = []
            for outcome in members_raw:
                if (
                    type(outcome) is not dict
                    or set(outcome) != {"status", "symbol"}
                    or outcome.get("status") != "PASS"
                    or outcome.get("symbol") not in clean_symbols
                ):
                    raise CutoffBoundEffectiveTicketBudgetContractError(
                        f"{window_id}_member_outcome_invalid"
                    )
                members.append(outcome["symbol"])
            if not members or members != sorted(set(members)):
                raise CutoffBoundEffectiveTicketBudgetContractError(
                    f"{window_id}_cluster_members_invalid"
                )
            cluster_ids.append(cluster_id)
            covered_symbols.extend(members)
            for member in members[1:]:
                union(members[0], member)
        if (
            cluster_ids != sorted(set(cluster_ids))
            or sorted(covered_symbols) != clean_symbols
            or len(covered_symbols) != len(clean_symbols)
            or gate.get("raw_passing_symbol_ticket_count") != len(clean_symbols)
            or gate.get("effective_independent_ticket_count") != len(clusters)
            or gate.get("discounted_correlated_ticket_count")
            != len(clean_symbols) - len(clusters)
        ):
            raise CutoffBoundEffectiveTicketBudgetContractError(
                f"{window_id}_cluster_coverage_invalid"
            )
        window_summaries.append(
            {
                "window_id": window_id,
                "gate_v2_hash": gate["gate_v2_hash"],
                "cluster_count": len(clusters),
                "effective_independent_ticket_count": gate[
                    "effective_independent_ticket_count"
                ],
                "discounted_correlated_ticket_count": gate[
                    "discounted_correlated_ticket_count"
                ],
            }
        )

    grouped: dict[str, list[str]] = {}
    for symbol in clean_symbols:
        grouped.setdefault(find(symbol), []).append(symbol)
    member_groups = sorted(
        (sorted(members) for members in grouped.values()),
        key=lambda members: members[0],
    )
    components = [
        {
            "component_id": f"component-{index:03d}",
            "members": members,
            "member_count": len(members),
        }
        for index, members in enumerate(member_groups, start=1)
    ]
    document = {
        "schema_version": COMPONENT_DERIVATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "merge_rule": CLUSTER_MERGE_RULE,
        "symbols": clean_symbols,
        "window_summaries": window_summaries,
        "components": components,
        "effective_independent_ticket_count": len(components),
        "discounted_correlated_ticket_count": len(clean_symbols)
        - len(components),
        "facts": {
            "all_required_windows_consumed": True,
            "any_window_cocluster_edges_union_applied": True,
            "connected_components_recomputed": True,
            "single_window_independence_assumed": False,
            "raw_matrices_embedded": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "component_derivation_v1_hash")


def _verify_common_cutoff_gate_v6(
    document: Any,
    context: Any,
) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != COMMON_CUTOFF_GATE_V6_SCHEMA_VERSION
        or document.get("status") != "PASS"
        or type(context) is not dict
        or set(context) != _CUTOFF_CONTEXT_KEYS
    ):
        return False
    try:
        verification = verify_market_data_common_cutoff_gate_v6(
            document,
            context["common_cutoff_preregistration"],
            context["adapter_v5_document"],
            context["adapter_v5_context"],
            expected_common_cutoff_preregistration_v6_hash=context[
                "expected_common_cutoff_preregistration_v6_hash"
            ],
        )
    except (
        ArithmeticError,
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return False
    return bool(
        type(verification) is dict
        and verification.get("status") == "PASS"
        and verification.get("gate_exactly_verified") is True
        and verification.get("gate_decision")
        == "PASS_COMMON_NATIVE_CUTOFF_BOUND_RESEARCH_GATE_V6"
        and not _list(verification.get("blockers"))
    )


def _normalize_positions(value: Any, symbols: list[str]) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "positions_before_invalid"
        )
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if type(item) is not dict or set(item) != {
            "symbol",
            "notional_minor",
            "direction",
        }:
            raise CutoffBoundEffectiveTicketBudgetContractError(
                "position_shape_invalid"
            )
        symbol = item.get("symbol")
        if symbol not in symbols or symbol in seen:
            raise CutoffBoundEffectiveTicketBudgetContractError(
                "position_symbol_invalid"
            )
        notional = _native_int(
            item.get("notional_minor"),
            "position_notional_minor",
            minimum=1,
            maximum=MAX_MONEY_MINOR_UNITS,
        )
        direction = item.get("direction")
        if direction not in {"LONG", "SHORT"}:
            raise CutoffBoundEffectiveTicketBudgetContractError(
                "position_direction_invalid"
            )
        seen.add(symbol)
        normalized.append(
            {
                "symbol": symbol,
                "notional_minor": notional,
                "direction": direction,
            }
        )
    return sorted(normalized, key=lambda item: item["symbol"])


def _normalize_proposal(value: Any, symbols: list[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "symbol",
        "notional_minor",
        "direction",
    }:
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "proposal_shape_invalid"
        )
    symbol = value.get("symbol")
    if symbol not in symbols:
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "proposal_symbol_invalid"
        )
    notional = _native_int(
        value.get("notional_minor"),
        "proposal_notional_minor",
        minimum=1,
        maximum=MAX_MONEY_MINOR_UNITS,
    )
    direction = value.get("direction")
    if direction not in {"LONG", "SHORT"}:
        raise CutoffBoundEffectiveTicketBudgetContractError(
            "proposal_direction_invalid"
        )
    return {
        "symbol": symbol,
        "notional_minor": notional,
        "direction": direction,
    }


def evaluate_cutoff_bound_effective_ticket_budget_consumer_v7(
    budget_preregistration: Any,
    common_cutoff_gate_v6_document: Any,
    common_cutoff_gate_v6_context: Any,
    positions_before: Any,
    proposal: Any,
    *,
    equity_minor: Any,
    expected_budget_preregistration_v7_hash: Any,
) -> dict[str, Any]:
    preregistration_verification = (
        verify_cutoff_bound_effective_ticket_budget_preregistration_v7(
            budget_preregistration,
            expected_budget_preregistration_v7_hash=(
                expected_budget_preregistration_v7_hash
            ),
        )
    )
    preregistration_ok = preregistration_verification.get("status") == "PASS"
    cutoff_gate_ok = _verify_common_cutoff_gate_v6(
        common_cutoff_gate_v6_document,
        common_cutoff_gate_v6_context,
    )

    preregistration = _dict(budget_preregistration)
    scope = _dict(preregistration.get("scope"))
    policy = _dict(preregistration.get("policy"))
    source = _dict(preregistration.get("source"))
    symbols = _list(scope.get("symbols")) if preregistration_ok else []
    cutoff_preregistration = _dict(
        _dict(common_cutoff_gate_v6_context).get(
            "common_cutoff_preregistration"
        )
    )
    cutoff_expected = _dict(cutoff_preregistration.get("expected"))
    adapter_context = _dict(
        _dict(common_cutoff_gate_v6_context).get("adapter_v5_context")
    )
    source_identity_ok = bool(
        preregistration_ok
        and cutoff_gate_ok
        and cutoff_preregistration.get("schema_version")
        == COMMON_CUTOFF_PREREGISTRATION_V6_SCHEMA_VERSION
        and cutoff_preregistration.get(
            "common_cutoff_preregistration_v6_hash"
        )
        == source.get("common_cutoff_preregistration_v6_hash")
        == _dict(common_cutoff_gate_v6_context).get(
            "expected_common_cutoff_preregistration_v6_hash"
        )
        and cutoff_expected.get("symbols") == symbols
        and adapter_context.get("strategy_id") == scope.get("strategy_id")
        and adapter_context.get("variant_id") == scope.get("variant_id")
        and adapter_context.get("lane") == scope.get("lane")
    )

    component_derivation: dict[str, Any] = {}
    if source_identity_ok:
        try:
            component_derivation = derive_conservative_multi_window_components_v1(
                adapter_context.get("window_inputs"),
                symbols,
                policy.get("required_window_ids"),
            )
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            component_derivation = {}
    component_derivation_ok = bool(
        component_derivation.get("status") == "PASS"
        and component_derivation.get("merge_rule") == CLUSTER_MERGE_RULE
        and component_derivation.get("symbols") == symbols
        and strict_sha256(component_derivation.get("component_derivation_v1_hash"))
    )

    inputs_ok = False
    normalized_positions: list[dict[str, Any]] = []
    normalized_proposal: dict[str, Any] = {}
    clean_equity: int | None = None
    if preregistration_ok:
        try:
            normalized_positions = _normalize_positions(positions_before, symbols)
            normalized_proposal = _normalize_proposal(proposal, symbols)
            clean_equity = _native_int(
                equity_minor,
                "equity_minor",
                minimum=1,
                maximum=MAX_MONEY_MINOR_UNITS,
            )
            inputs_ok = True
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            inputs_ok = False

    component_summaries: list[dict[str, Any]] = []
    effective_before: int | None = None
    effective_after: int | None = None
    marginal_tickets: int | None = None
    proposal_component_id: str | None = None
    max_observed_gross_bps: int | None = None
    ticket_limit_ok = False
    cluster_gross_limit_ok = False
    proposal_scope_hash: str | None = None
    positions_before_hash: str | None = None
    proposal_hash: str | None = None

    if component_derivation_ok and inputs_ok and clean_equity is not None:
        components = _list(component_derivation.get("components"))
        component_by_symbol: dict[str, str] = {}
        members_by_component: dict[str, list[str]] = {}
        for component in components:
            component_id = _dict(component).get("component_id")
            members = _list(_dict(component).get("members"))
            if type(component_id) is not str:
                component_by_symbol = {}
                break
            members_by_component[component_id] = members
            for symbol in members:
                component_by_symbol[symbol] = component_id
        if set(component_by_symbol) == set(symbols):
            gross_by_component = {
                component_id: 0 for component_id in members_by_component
            }
            occupied_symbols_by_component = {
                component_id: set() for component_id in members_by_component
            }
            for position in normalized_positions:
                component_id = component_by_symbol[position["symbol"]]
                gross_by_component[component_id] += position["notional_minor"]
                occupied_symbols_by_component[component_id].add(position["symbol"])
            occupied_before = {
                component_id
                for component_id, gross in gross_by_component.items()
                if gross > 0
            }
            proposal_component_id = component_by_symbol[
                normalized_proposal["symbol"]
            ]
            gross_by_component[proposal_component_id] += normalized_proposal[
                "notional_minor"
            ]
            occupied_symbols_by_component[proposal_component_id].add(
                normalized_proposal["symbol"]
            )
            occupied_after = {
                component_id
                for component_id, gross in gross_by_component.items()
                if gross > 0
            }
            effective_before = len(occupied_before)
            effective_after = len(occupied_after)
            marginal_tickets = effective_after - effective_before
            observed_bps: list[int] = []
            for component_id in sorted(members_by_component):
                gross = gross_by_component[component_id]
                gross_bps = (
                    (gross * 10_000 + clean_equity - 1) // clean_equity
                    if gross > 0
                    else 0
                )
                observed_bps.append(gross_bps)
                component_summaries.append(
                    {
                        "component_id": component_id,
                        "members": members_by_component[component_id],
                        "gross_notional_minor_after": gross,
                        "gross_bps_after": gross_bps,
                        "occupied_symbol_count_after": len(
                            occupied_symbols_by_component[component_id]
                        ),
                        "includes_proposal": component_id
                        == proposal_component_id,
                    }
                )
            max_observed_gross_bps = max(observed_bps, default=0)
            ticket_limit_ok = bool(
                effective_after <= policy.get("max_effective_ticket_count")
            )
            cluster_gross_limit_ok = bool(
                max_observed_gross_bps <= policy.get("max_cluster_gross_bps")
            )
            positions_before_hash = strict_canonical_hash(normalized_positions)
            proposal_hash = strict_canonical_hash(normalized_proposal)
            proposal_scope_hash = strict_canonical_hash(
                {
                    "equity_minor": clean_equity,
                    "positions_before_hash": positions_before_hash,
                    "proposal_hash": proposal_hash,
                    "budget_preregistration_v7_hash": preregistration.get(
                        "budget_preregistration_v7_hash"
                    ),
                    "common_cutoff_gate_v6_hash": _dict(
                        common_cutoff_gate_v6_document
                    ).get("common_cutoff_gate_v6_hash"),
                }
            )

    checks = [
        _check(
            "budget_preregistration_v7_exact",
            preregistration_ok,
            "Effective-ticket budget preregistration exactly verifies.",
            "Effective-ticket budget preregistration is invalid or mismatched.",
        ),
        _check(
            "common_cutoff_gate_v6_exact_pass",
            cutoff_gate_ok,
            "Common-cutoff gate v6 exactly verifies with PASS status.",
            "Common-cutoff gate v6 is invalid, UNKNOWN, or mismatched.",
        ),
        _check(
            "strategy_universe_source_identity_exact",
            source_identity_ok,
            "Strategy identity and symbol universe match cutoff evidence.",
            "Strategy identity or symbol universe differs from cutoff evidence.",
        ),
        _check(
            "conservative_multi_window_components_exact",
            component_derivation_ok,
            "Conservative any-window components were exactly recomputed.",
            "Multi-window component derivation is invalid or incomplete.",
        ),
        _check(
            "portfolio_proposal_inputs_exact",
            inputs_ok,
            "Integer portfolio and proposal inputs are exact.",
            "Portfolio, proposal, or equity input is invalid.",
        ),
        _check(
            "effective_ticket_limit",
            ticket_limit_ok,
            "Effective ticket count remains within preregistered limit.",
            "Effective ticket count exceeds preregistered limit.",
        ),
        _check(
            "cluster_gross_limit",
            cluster_gross_limit_ok,
            "Every conservative component remains within gross-bps limit.",
            "At least one conservative component exceeds gross-bps limit.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    source_and_input_ok = bool(
        preregistration_ok
        and cutoff_gate_ok
        and source_identity_ok
        and component_derivation_ok
        and inputs_ok
    )
    if not source_and_input_ok:
        status = "UNKNOWN"
        budget_status = "NOT_EVALUATED"
    elif ticket_limit_ok and cluster_gross_limit_ok:
        status = "PASS"
        budget_status = "PASS"
    else:
        status = "BLOCK"
        budget_status = "BLOCK"
    if not preregistration_ok or not cutoff_gate_ok or not source_identity_ok:
        first_blocking_tier = "SOURCE"
    elif not component_derivation_ok:
        first_blocking_tier = "CLUSTER_COMPONENTS"
    elif not inputs_ok:
        first_blocking_tier = "PORTFOLIO_INPUT"
    elif not ticket_limit_ok:
        first_blocking_tier = "EFFECTIVE_TICKET_LIMIT"
    elif not cluster_gross_limit_ok:
        first_blocking_tier = "CLUSTER_GROSS_LIMIT"
    else:
        first_blocking_tier = None

    adapter_v5_document = _dict(
        _dict(common_cutoff_gate_v6_context).get("adapter_v5_document")
    )
    consumer_document = _dict(adapter_context.get("consumer_document"))
    document = {
        "schema_version": CONSUMER_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "budget_status": budget_status,
        "admission_status": "BLOCKED",
        "decision": (
            "PASS_CUTOFF_BOUND_EFFECTIVE_TICKET_RESEARCH_BUDGET_V7"
            if status == "PASS"
            else (
                "BLOCK_CUTOFF_BOUND_EFFECTIVE_TICKET_RESEARCH_BUDGET_V7"
                if status == "BLOCK"
                else "UNKNOWN_CUTOFF_BOUND_EFFECTIVE_TICKET_BUDGET_UNVERIFIED"
            )
        ),
        "first_blocking_tier": first_blocking_tier,
        "source": {
            "budget_preregistration_v7_hash": (
                preregistration.get("budget_preregistration_v7_hash")
                if preregistration_ok
                else None
            ),
            "common_cutoff_preregistration_v6_hash": (
                source.get("common_cutoff_preregistration_v6_hash")
                if source_identity_ok
                else None
            ),
            "common_cutoff_gate_v6_hash": (
                _dict(common_cutoff_gate_v6_document).get(
                    "common_cutoff_gate_v6_hash"
                )
                if cutoff_gate_ok
                else None
            ),
            "adapter_v5_hash": (
                adapter_v5_document.get("adapter_v5_hash")
                if cutoff_gate_ok
                else None
            ),
            "consumer_v3_hash": (
                consumer_document.get("consumer_v3_hash")
                if cutoff_gate_ok
                else None
            ),
            "component_derivation_v1_hash": component_derivation.get(
                "component_derivation_v1_hash"
            ),
            "positions_before_hash": positions_before_hash,
            "proposal_hash": proposal_hash,
            "proposal_scope_hash": proposal_scope_hash,
        },
        "policy": {
            "cluster_merge_rule": policy.get("cluster_merge_rule"),
            "required_window_ids": _list(policy.get("required_window_ids")),
            "max_effective_ticket_count": policy.get(
                "max_effective_ticket_count"
            ),
            "max_cluster_gross_bps": policy.get("max_cluster_gross_bps"),
            "gross_bps_rounding": "CEILING",
            "money_unit": "CALLER_DEFINED_INTEGER_MINOR_UNIT",
        },
        "budget_summary": {
            "effective_ticket_count_before": effective_before,
            "effective_ticket_count_after": effective_after,
            "marginal_effective_ticket_count": marginal_tickets,
            "proposal_component_id": proposal_component_id,
            "max_observed_cluster_gross_bps": max_observed_gross_bps,
            "component_count": (
                component_derivation.get("effective_independent_ticket_count")
                if component_derivation_ok
                else None
            ),
        },
        "component_summaries": component_summaries,
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "common_cutoff_gate_v6_bound": cutoff_gate_ok,
            "all_required_windows_consumed": component_derivation_ok,
            "any_window_cocluster_union_applied": component_derivation_ok,
            "correlated_symbols_share_one_effective_ticket": (
                component_derivation_ok
            ),
            "proposal_reuses_occupied_component": marginal_tickets == 0,
            "cluster_gross_accumulates_correlated_symbols": (
                component_derivation_ok and inputs_ok
            ),
            "direction_netting_applied": False,
            "latest_effective_bet_budget_v11_bound": False,
            "portfolio_positions_embedded": False,
            "raw_market_rows_embedded": False,
            "runtime_consumer_bound": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "budget_consumer_v7_hash")


def verify_cutoff_bound_effective_ticket_budget_consumer_v7(
    document: Any,
    budget_preregistration: Any,
    common_cutoff_gate_v6_document: Any,
    common_cutoff_gate_v6_context: Any,
    positions_before: Any,
    proposal: Any,
    *,
    equity_minor: Any,
    expected_budget_preregistration_v7_hash: Any,
) -> dict[str, Any]:
    expected = evaluate_cutoff_bound_effective_ticket_budget_consumer_v7(
        budget_preregistration,
        common_cutoff_gate_v6_document,
        common_cutoff_gate_v6_context,
        positions_before,
        proposal,
        equity_minor=equity_minor,
        expected_budget_preregistration_v7_hash=(
            expected_budget_preregistration_v7_hash
        ),
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": CONSUMER_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["budget_consumer_v7_exact_rebuild_mismatch"],
        "consumer_status": expected["status"] if exact else "UNKNOWN",
        "budget_status": expected["budget_status"] if exact else "UNKNOWN",
        "admission_status": "BLOCKED",
        "consumer_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "CLUSTER_MERGE_RULE",
    "COMPONENT_DERIVATION_SCHEMA_VERSION",
    "CONSUMER_SCHEMA_VERSION",
    "CONSUMER_VERIFICATION_SCHEMA_VERSION",
    "CutoffBoundEffectiveTicketBudgetContractError",
    "PREREGISTRATION_SCHEMA_VERSION",
    "REQUIRED_WINDOW_IDS",
    "STATIC_FINGERPRINT",
    "build_cutoff_bound_effective_ticket_budget_preregistration_v7",
    "derive_conservative_multi_window_components_v1",
    "evaluate_cutoff_bound_effective_ticket_budget_consumer_v7",
    "verify_cutoff_bound_effective_ticket_budget_consumer_v7",
    "verify_cutoff_bound_effective_ticket_budget_preregistration_v7",
]
