from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Callable

from .event_replay import EventReplayService
from hakimi_research.research_execution_rehearsal import ResearchExecutionRehearsalSimulator
from .portfolio_risk import evaluate_portfolio_risk
from .risk_service import RiskService, build_risk_snapshot


PORTFOLIO_EXECUTION_REHEARSAL_SCHEMA_VERSION = "portfolio-internal-execution-rehearsal-v1"
SUPPORTED_FEE_RATE = 0.0005


def _research_rehearsal_authorization(risk_result: dict[str, object]) -> dict[str, object]:
    if type(risk_result) is not dict:
        return {
            "allowed": False,
            "blockers": ["risk_result_exact_dict_required"],
            "research_rehearsal_allowed": False,
            "mode": "RESEARCH_REHEARSAL",
            "paper_order_allowed": False,
            "live_order_allowed": False,
            "order_entry_allowed": False,
        }
    raw_blockers = risk_result.get("blockers", [])
    blockers = list(raw_blockers) if type(raw_blockers) is list and all(type(item) is str for item in raw_blockers) else ["risk_result_blockers_exact_list_required"]
    allowed = risk_result.get("allowed") is True and not blockers
    result = dict(risk_result)
    result.update(
        {
            "allowed": allowed,
            "blockers": blockers,
            "research_rehearsal_allowed": allowed,
            "mode": "RESEARCH_REHEARSAL",
            "paper_order_allowed": False,
            "live_order_allowed": False,
            "order_entry_allowed": False,
        }
    )
    return result

def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def _is_finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _is_sha256(value: Any) -> bool:
    clean = str(value or "").lower()
    return len(clean) == 64 and all(character in "0123456789abcdef" for character in clean)


def _check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "status": "PASS" if ok else "BLOCK", "ok": bool(ok), "detail": detail})


def _audit_query(events: list[dict[str, Any]]) -> Callable[..., list[dict[str, Any]]]:
    def query(
        *,
        limit: int = 120,
        event_type: str = "",
        run_id: str = "",
        symbol: str = "",
        signal_id: str = "",
        order_id: str = "",
        request_id: str = "",
        snapshot_id: str = "",
    ) -> list[dict[str, Any]]:
        rows = events
        filters = {
            "type": event_type,
            "run_id": run_id,
            "symbol": str(symbol or "").upper(),
            "signal_id": signal_id,
            "order_id": order_id,
            "request_id": request_id,
            "snapshot_id": snapshot_id,
        }
        for key, expected in filters.items():
            if expected:
                rows = [row for row in rows if str(row.get(key) or "") == expected]
        safe_limit = max(1, min(int(limit or 120), 5000))
        return deepcopy(rows[-safe_limit:])

    return query


def _apply_corporate_action(
    action: dict[str, Any],
    *,
    positions: dict[str, float],
    cash_state: dict[str, float],
) -> dict[str, Any]:
    action_type = str(action.get("action_type") or "")
    symbol = str(action.get("symbol") or "").upper()
    before = positions.get(symbol, 0.0)
    ok = True
    detail = action_type or "UNKNOWN"
    if action_type == "SPLIT_QUANTITY_ADJUSTMENT":
        expected_before = _number(action.get("quantity_before"), before)
        after = max(_number(action.get("quantity_after")), 0.0)
        ok = abs(before - expected_before) <= max(1e-7, abs(expected_before) * 1e-7)
        positions[symbol] = after
        detail = f"{symbol} {before:.10f} -> {after:.10f}"
    elif action_type == "DIVIDEND_RECEIVABLE_ACCRUED":
        amount = max(_number(action.get("amount")), 0.0)
        cash_state["receivable"] += amount
        detail = f"{symbol} receivable +{amount:.6f}"
    elif action_type == "DIVIDEND_CASH_SETTLED":
        amount = max(_number(action.get("amount")), 0.0)
        cash_state["cash"] += amount
        cash_state["receivable"] = max(cash_state["receivable"] - amount, 0.0)
        detail = f"{symbol} cash +{amount:.6f}"
    elif action_type == "DELISTING_CASH_SETTLEMENT":
        quantity = max(_number(action.get("quantity")), 0.0)
        amount = max(_number(action.get("amount")), 0.0)
        ok = abs(before - quantity) <= max(1e-7, abs(quantity) * 1e-7)
        positions[symbol] = 0.0
        cash_state["cash"] += amount
        detail = f"{symbol} settled {quantity:.10f} for {amount:.6f}"
    else:
        ok = False
        detail = f"unsupported corporate action: {action_type or '--'}"
    return {"ok": ok, "type": action_type, "symbol": symbol, "detail": detail}


def run_portfolio_execution_rehearsal(
    backtest: dict[str, Any],
    *,
    stage: str,
    correlations: dict[str, Any] | None = None,
    clusters: dict[str, str] | None = None,
    generated_at: int = 0,
) -> dict[str, Any]:
    """Replay recorded fills through the production risk and paper lifecycle services in memory."""

    payload = dict(backtest or {})
    run_spec = dict(payload.get("run_spec") or {})
    manifest = dict(payload.get("dataset_manifest") or {})
    source_orders = [dict(row) for row in payload.get("orders") or [] if isinstance(row, dict)]
    corporate_actions = [
        dict(row) for row in payload.get("corporate_action_events") or [] if isinstance(row, dict)
    ]
    source_run_hash = str(payload.get("run_hash") or "")
    dataset_hash = str(manifest.get("data_hash") or run_spec.get("dataset_hash") or "")
    raw_initial_cash = payload.get("initial_cash") if payload.get("initial_cash") is not None else run_spec.get("initial_cash")
    raw_fee_rate = run_spec.get("fee_rate")
    initial_cash = _number(raw_initial_cash, -1.0)
    fee_rate = _number(raw_fee_rate, -1.0)
    correlation_matrix = dict(correlations or {})
    cluster_map = {str(symbol).upper(): str(cluster or symbol).upper() for symbol, cluster in dict(clusters or {}).items()}
    run_id = f"internal-rehearsal-{str(stage or 'stage').lower()}-{source_run_hash[:12]}"
    checks: list[dict[str, Any]] = []

    _check(checks, "source_backtest_passed", payload.get("ok") is True, f"ok={payload.get('ok')!r}")
    _check(
        checks,
        "source_has_no_execution_authority",
        payload.get("research_only") is True
        and payload.get("paper_authorized") is False
        and payload.get("live_order_allowed") is False,
        "源报告必须保持仅研究、无模拟盘或实盘授权",
    )
    _check(checks, "source_run_hash", _is_sha256(source_run_hash), f"run_hash={source_run_hash or '--'}")
    _check(checks, "dataset_hash", _is_sha256(dataset_hash), f"dataset_hash={dataset_hash or '--'}")
    _check(checks, "initial_cash", initial_cash > 0, f"initial_cash={initial_cash:.2f}")
    _check(
        checks,
        "research_execution_rehearsal_fee_contract",
        abs(fee_rate - SUPPORTED_FEE_RATE) <= 1e-12,
        f"backtest_fee_rate={fee_rate:.8f} / executor_fee_rate={SUPPORTED_FEE_RATE:.8f}",
    )
    _check(
        checks,
        "source_order_count",
        type(payload.get("order_event_count")) is int
        and len(source_orders) == payload.get("order_event_count")
        and bool(source_orders),
        f"orders={len(source_orders)} / declared={payload.get('order_event_count')!r}",
    )
    numeric_contract_ok = all(
        _is_finite_number(value)
        for value in (
            raw_initial_cash,
            raw_fee_rate,
            payload.get("final_equity"),
            payload.get("turnover"),
            payload.get("total_fees"),
            payload.get("dividend_receivable"),
        )
    ) and all(
        _is_finite_number(order.get(key))
        for order in source_orders
        for key in ("quantity", "price", "fee")
    )
    _check(checks, "source_numeric_contract", numeric_contract_ok, "finite non-boolean numbers required")
    order_symbols = {str(order.get("symbol") or "").upper() for order in source_orders}
    _check(
        checks,
        "correlation_contract",
        str(correlation_matrix.get("status") or "") == "PASS"
        and isinstance(correlation_matrix.get("pairs"), dict),
        f"status={correlation_matrix.get('status') or '--'}",
    )
    missing_clusters = sorted(symbol for symbol in order_symbols if symbol and symbol not in cluster_map)
    _check(checks, "cluster_contract", not missing_clusters, f"missing={','.join(missing_clusters) or '--'}")
    if any(not item["ok"] for item in checks):
        result = {
            "schema_version": PORTFOLIO_EXECUTION_REHEARSAL_SCHEMA_VERSION,
            "status": "BLOCK",
            "stage": stage,
            "source_run_hash": source_run_hash,
            "dataset_hash": dataset_hash,
            "checks": checks,
            "order_evidence": [],
            "isolated_in_memory": True,
            "network_accessed": False,
            "production_runtime_mutated": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        result["rehearsal_hash"] = _canonical_hash(result)
        result["generated_at"] = int(generated_at or 0)
        return result

    clock = [1_800_000_000_000]
    cash_state = {"cash": initial_cash, "receivable": 0.0}
    positions: dict[str, float] = {}
    marks: dict[str, float] = {}
    current: dict[str, Any] = {"symbol": "", "price": 0.0, "quantity": 0.0, "regime": {}}
    audit_events: list[dict[str, Any]] = []
    stored_orders: dict[str, dict[str, Any]] = {}
    minimum_cash = initial_cash

    def snapshot_provider(price: float) -> dict[str, Any]:
        symbol = current["symbol"]
        if symbol and price > 0:
            marks[symbol] = price
        position_value = sum(quantity * marks.get(item, 0.0) for item, quantity in positions.items())
        symbol_position_value = positions.get(symbol, 0.0) * marks.get(symbol, 0.0)
        equity = cash_state["cash"] + cash_state["receivable"] + position_value
        return build_risk_snapshot(
            {
                "symbol": symbol,
                "equity": equity,
                "cash": cash_state["cash"],
                "available_cash": cash_state["cash"],
                "drawdown_pct": 0.0,
                "max_drawdown_pct": 100.0,
                "position_value": symbol_position_value,
                "gross_position_value": position_value,
                "leverage": 1.0,
                "position_side": "LONG" if positions.get(symbol, 0.0) > 1e-12 else "FLAT",
                "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            clock[0],
        )

    def write_order(order: dict[str, Any]) -> None:
        stored_orders[str(order.get("order_id") or "")] = deepcopy(order)

    def load_idempotency(key: str) -> dict[str, Any] | None:
        return next(
            (deepcopy(order) for order in stored_orders.values() if str(order.get("idempotency_key") or "") == key),
            None,
        )

    risk_service = RiskService(
        snapshot_provider=snapshot_provider,
        now_ms=lambda: clock[0],
        audit_writer=lambda event: audit_events.append(deepcopy(event)),
        portfolio_context_provider=lambda risk, symbol, side, notional, _price, context: evaluate_portfolio_risk(
            equity=_number((risk.get("paper") or {}).get("equity")),
            positions=[
                {
                    "symbol": held_symbol,
                    "notional": quantity * marks.get(held_symbol, 0.0),
                    "direction": "LONG",
                    "cluster": cluster_map.get(held_symbol, held_symbol),
                }
                for held_symbol, quantity in positions.items()
                if quantity > 1e-12
            ],
            proposed_symbol=symbol,
            proposed_notional=notional,
            proposed_direction="LONG",
            proposed_cluster=cluster_map.get(symbol, symbol),
            risk_increasing=str(side or "").upper() == "BUY" and context.get("reduce_only") is not True,
            correlations=correlation_matrix,
            regime=dict(current.get("regime") or {}),
        ),
    )
    executor = ResearchExecutionRehearsalSimulator(
        now_ms=lambda: clock[0],
        audit_writer=lambda event: audit_events.append(deepcopy(event)),
        book_reader=lambda _symbol, _side: [[current["price"], current["quantity"] * 1.000001]],
        funding_rate_reader=lambda _symbol: 0.0,
        order_writer=write_order,
        idempotency_loader=load_idempotency,
        max_orders=max(100, len(source_orders) + 10),
        instance_nonce=hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16],
    )

    timeline: list[tuple[str, int, int, dict[str, Any]]] = []
    timeline.extend(
        (str(action.get("date") or ""), 0, index, action)
        for index, action in enumerate(corporate_actions)
    )
    timeline.extend(
        (str(order.get("date") or ""), 1, index, order)
        for index, order in enumerate(source_orders)
    )
    timeline.sort(key=lambda item: (item[0], item[1], item[2]))
    order_evidence: list[dict[str, Any]] = []
    action_evidence: list[dict[str, Any]] = []
    fee_total = 0.0
    turnover = 0.0
    risk_pass_count = 0
    lifecycle_fill_count = 0
    idempotency_checks: list[bool] = []
    decision_regimes = {
        str(decision.get("signal_date") or ""): dict(decision.get("regime") or {})
        for decision in payload.get("decisions") or []
        if isinstance(decision, dict) and decision.get("reason") == "relative_strength_rebalance"
    }

    for timeline_index, (_event_date, priority, source_index, row) in enumerate(timeline):
        clock[0] = 1_800_000_000_000 + timeline_index * 100
        if priority == 0:
            action_evidence.append(
                _apply_corporate_action(row, positions=positions, cash_state=cash_state)
            )
            minimum_cash = min(minimum_cash, cash_state["cash"])
            continue

        symbol = str(row.get("symbol") or "").upper()
        side = str(row.get("side") or "").upper()
        expected_quantity = max(_number(row.get("quantity")), 0.0)
        expected_price = max(_number(row.get("price")), 0.0)
        expected_notional = expected_quantity * expected_price
        expected_fee = max(_number(row.get("fee")), 0.0)
        current.update({
            "symbol": symbol,
            "price": expected_price,
            "quantity": expected_quantity,
            "regime": decision_regimes.get(str(row.get("signal_date") or ""), {}),
        })
        marks[symbol] = expected_price
        snapshot_id = f"snapshot-{source_run_hash[:12]}-{source_index:04d}"
        signal_id = f"signal-{source_run_hash[:12]}-{source_index:04d}"
        idempotency_key = f"{run_id}:{source_index:04d}:{symbol}:{side}"
        audit_events.append({
            "type": "market_snapshot",
            "snapshot_id": snapshot_id,
            "run_id": run_id,
            "symbol": symbol,
            "last": expected_price,
            "quality": {
                "status": "HISTORICAL_READY",
                "historical": True,
                "attested": True,
                "data_hash": dataset_hash,
            },
        })
        context = {
            "source": "internal_backtest_rehearsal",
            "strategy_id": "causal_relative_strength",
            "run_id": run_id,
            "signal_id": signal_id,
            "signal_created_at": clock[0],
            "signal_action": side,
            "signal_reason": str(row.get("reason") or "historical_replay"),
            "market_snapshot_id": snapshot_id,
            "idempotency_key": idempotency_key,
            "order_type": "MARKET",
            "limit_price": 0.0,
            "direction_mode": "LONG_ONLY",
            "reduce_only": side == "SELL",
            "data_status": "HISTORICAL_READY",
            "data_quality": {
                "status": "HISTORICAL_READY",
                "historical": True,
                "attested": True,
                "realtime": False,
                "fallback": False,
                "quarantined": False,
                "can_simulate": True,
                "can_increase_risk": False,
                "blocking_reasons": [],
                "data_hash": dataset_hash,
            },
        }
        risk = risk_service.evaluate(
            symbol=symbol,
            side=side,
            mode="SIMULATION",
            notional=expected_notional,
            price=expected_price,
            context=context,
        )
        risk_pass_count += int(risk.get("allowed") is True)
        portfolio_gate = dict((risk.get("context") or {}).get("portfolio_risk") or {})
        submit_args = {
            "symbol": symbol,
            "side": side,
            "order_type": "MARKET",
            "mark_price": expected_price,
            "notional": expected_notional,
            "risk_result": _research_rehearsal_authorization(risk),
            "context": context,
        }
        report = executor.submit(**submit_args)
        lifecycle_filled = risk.get("allowed") is True and report.get("lifecycle_state") == "FILLED"
        lifecycle_fill_count += int(lifecycle_filled)
        actual_quantity = max(_number(report.get("filled_qty")), 0.0)
        actual_price = max(_number(report.get("avg_price")), 0.0)
        actual_fee = max(_number(report.get("fee")), 0.0)
        quantity_tolerance = max(1e-7, expected_quantity * 1e-7)
        quantity_match = abs(actual_quantity - expected_quantity) <= quantity_tolerance
        price_match = abs(actual_price - expected_price) <= max(1e-7, expected_price * 1e-8)
        fee_match = abs(actual_fee - expected_fee) <= 0.02
        settlement_ok = lifecycle_filled and quantity_match and price_match and fee_match
        settlement_reason = ""
        if settlement_ok and side == "BUY":
            cost = actual_quantity * actual_price + actual_fee
            if cost > cash_state["cash"] + 0.02:
                settlement_ok = False
                settlement_reason = "insufficient_rehearsal_cash"
            else:
                cash_state["cash"] -= cost
                positions[symbol] = positions.get(symbol, 0.0) + actual_quantity
        elif settlement_ok and side == "SELL":
            held = positions.get(symbol, 0.0)
            if actual_quantity > held + quantity_tolerance:
                settlement_ok = False
                settlement_reason = "rehearsal_sell_exceeds_position"
            else:
                cash_state["cash"] += actual_quantity * actual_price - actual_fee
                remaining = max(held - actual_quantity, 0.0)
                if remaining <= 1e-12:
                    positions.pop(symbol, None)
                else:
                    positions[symbol] = remaining
        elif settlement_ok:
            settlement_ok = False
            settlement_reason = f"unsupported_side:{side or '--'}"
        if settlement_ok:
            fee_total += actual_fee
            turnover += actual_quantity * actual_price
        minimum_cash = min(minimum_cash, cash_state["cash"])

        if source_index == 0 and lifecycle_filled:
            replay = executor.submit(**submit_args)
            conflict = executor.submit(**{**submit_args, "notional": expected_notional + max(expected_price, 1.0)})
            idempotency_checks.extend([
                replay.get("idempotent_replay") is True and replay.get("order_id") == report.get("order_id"),
                conflict.get("idempotency_conflict") is True and executor.snapshot().get("order_count") == 1,
            ])

        order_evidence.append({
            "index": source_index,
            "signal_date": str(row.get("signal_date") or ""),
            "date": str(row.get("date") or ""),
            "symbol": symbol,
            "side": side,
            "risk_status": risk.get("status"),
            "portfolio_risk_status": portfolio_gate.get("status"),
            "portfolio_risk_failed_checks": [
                str(check.get("name") or "")
                for check in portfolio_gate.get("checks") or []
                if check.get("blocking") and not check.get("ok")
            ],
            "order_id": report.get("order_id"),
            "lifecycle_state": report.get("lifecycle_state"),
            "expected_quantity": round(expected_quantity, 10),
            "actual_quantity": round(actual_quantity, 10),
            "expected_price": round(expected_price, 8),
            "actual_price": round(actual_price, 8),
            "expected_fee": round(expected_fee, 6),
            "actual_fee": round(actual_fee, 6),
            "settlement_status": "PASS" if settlement_ok else "BLOCK",
            "settlement_reason": settlement_reason,
        })

    replay_service = EventReplayService(
        now_ms=lambda: clock[0] + 1,
        audit_query=_audit_query(audit_events),
        order_loader=lambda order_id: deepcopy(stored_orders.get(order_id)),
        run_order_loader=lambda requested_run_id, limit: [
            deepcopy(order)
            for order in list(stored_orders.values())[-max(1, min(int(limit or 500), 2000)):]
            if str(order.get("run_id") or "") == requested_run_id
        ],
    )
    lineage = replay_service.replay_run(run_id, max(len(source_orders), 1))
    expected_positions = dict(payload.get("final_positions") or {})
    quantity_deltas: dict[str, float] = {}
    for symbol in sorted(set(positions) | set(expected_positions)):
        expected_quantity = _number((expected_positions.get(symbol) or {}).get("quantity"))
        quantity_deltas[symbol] = positions.get(symbol, 0.0) - expected_quantity
    position_match = all(abs(delta) <= max(1e-6, abs(delta) * 1e-6) for delta in quantity_deltas.values())
    expected_market_value = sum(_number(item.get("market_value")) for item in expected_positions.values())
    expected_receivable = _number(payload.get("dividend_receivable"))
    reported_final_equity = _number(payload.get("final_equity"))
    expected_final_cash = reported_final_equity - expected_market_value - expected_receivable
    reconstructed_equity = cash_state["cash"] + expected_market_value + cash_state["receivable"]
    cash_tolerance = max(1.0, initial_cash * 0.00001)
    turnover_tolerance = max(1.0, abs(_number(payload.get("turnover"))) * 0.00001)

    _check(
        checks,
        "historical_risk_gateway",
        risk_pass_count == len(source_orders),
        f"risk_pass={risk_pass_count}/{len(source_orders)}",
    )
    portfolio_pass_count = sum(
        item.get("portfolio_risk_status") == "PASS" for item in order_evidence
    )
    _check(
        checks,
        "portfolio_risk_gateway",
        portfolio_pass_count == len(source_orders),
        f"portfolio_pass={portfolio_pass_count}/{len(source_orders)}",
    )
    _check(
        checks,
        "research_rehearsal_lifecycle",
        lifecycle_fill_count == len(source_orders),
        f"filled={lifecycle_fill_count}/{len(source_orders)}",
    )
    _check(
        checks,
        "fill_settlement",
        all(item["settlement_status"] == "PASS" for item in order_evidence),
        f"settled={sum(item['settlement_status'] == 'PASS' for item in order_evidence)}/{len(order_evidence)}",
    )
    _check(checks, "idempotency", bool(idempotency_checks) and all(idempotency_checks), f"checks={idempotency_checks}")
    _check(
        checks,
        "event_lineage_replay",
        lineage.get("status") == "PASS" and int(lineage.get("passed_count") or 0) == len(source_orders),
        f"status={lineage.get('status')} / passed={lineage.get('passed_count')}/{len(source_orders)}",
    )
    _check(checks, "corporate_action_replay", all(item["ok"] for item in action_evidence), f"events={len(action_evidence)}")
    _check(checks, "position_reconciliation", position_match, f"quantity_deltas={quantity_deltas}")
    _check(
        checks,
        "cash_reconciliation",
        abs(cash_state["cash"] - expected_final_cash) <= cash_tolerance,
        f"replayed={cash_state['cash']:.6f} / expected={expected_final_cash:.6f} / tolerance={cash_tolerance:.6f}",
    )
    _check(
        checks,
        "equity_reconciliation",
        abs(reconstructed_equity - reported_final_equity) <= cash_tolerance,
        f"replayed={reconstructed_equity:.6f} / reported={reported_final_equity:.6f}",
    )
    _check(
        checks,
        "fee_reconciliation",
        abs(fee_total - _number(payload.get("total_fees"))) <= 0.05,
        f"replayed={fee_total:.6f} / reported={_number(payload.get('total_fees')):.6f}",
    )
    _check(
        checks,
        "turnover_reconciliation",
        abs(turnover - _number(payload.get("turnover"))) <= turnover_tolerance,
        f"replayed={turnover:.6f} / reported={_number(payload.get('turnover')):.6f}",
    )
    _check(checks, "cash_never_negative", minimum_cash >= -0.02, f"minimum_cash={minimum_cash:.6f}")

    passed = all(item["ok"] for item in checks)
    result = {
        "schema_version": PORTFOLIO_EXECUTION_REHEARSAL_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "stage": str(stage or ""),
        "run_id": run_id,
        "source_run_hash": source_run_hash,
        "dataset_hash": dataset_hash,
        "order_count": len(source_orders),
        "risk_pass_count": risk_pass_count,
        "portfolio_risk_pass_count": portfolio_pass_count,
        "lifecycle_fill_count": lifecycle_fill_count,
        "lineage_pass_count": int(lineage.get("passed_count") or 0),
        "audit_event_count": len(audit_events),
        "corporate_action_event_count": len(action_evidence),
        "final_cash": round(cash_state["cash"], 6),
        "expected_final_cash": round(expected_final_cash, 6),
        "reconstructed_equity": round(reconstructed_equity, 6),
        "reported_final_equity": round(reported_final_equity, 6),
        "minimum_cash": round(minimum_cash, 6),
        "fees_replayed": round(fee_total, 6),
        "turnover_replayed": round(turnover, 6),
        "checks": checks,
        "order_evidence": order_evidence,
        "corporate_action_evidence": action_evidence,
        "lineage_replay_hash": str(lineage.get("replay_hash") or ""),
        "isolated_in_memory": True,
        "network_accessed": False,
        "production_runtime_mutated": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result["rehearsal_hash"] = _canonical_hash(result)
    result["generated_at"] = int(generated_at or 0)
    return result


def run_research_report_execution_rehearsal(
    research_report: dict[str, Any],
    *,
    stages: tuple[str, ...] = ("validation", "test", "full"),
    generated_at: int = 0,
) -> dict[str, Any]:
    source = dict(research_report or {})
    correlations = dict(source.get("correlation_matrix") or {})
    clusters = dict((source.get("spec") or {}).get("clusters") or {})
    stage_reports: dict[str, dict[str, Any]] = {}
    determinism: dict[str, dict[str, Any]] = {}
    for stage in stages:
        first = run_portfolio_execution_rehearsal(
            dict(source.get(stage) or {}),
            stage=stage,
            correlations=correlations,
            clusters=clusters,
            generated_at=generated_at,
        )
        second = run_portfolio_execution_rehearsal(
            dict(source.get(stage) or {}),
            stage=stage,
            correlations=correlations,
            clusters=clusters,
            generated_at=generated_at + 1 if generated_at else 1,
        )
        deterministic = str(first.get("rehearsal_hash") or "") == str(second.get("rehearsal_hash") or "")
        stage_reports[stage] = first
        determinism[stage] = {
            "status": "PASS" if deterministic else "BLOCK",
            "first_hash": first.get("rehearsal_hash"),
            "second_hash": second.get("rehearsal_hash"),
        }
    checks = {
        "source_report_research_only": source.get("research_only") is True
        and source.get("paper_authorized") is False
        and source.get("live_order_allowed") is False,
        "all_stage_rehearsals_pass": bool(stage_reports)
        and all(report.get("status") == "PASS" for report in stage_reports.values()),
        "all_stage_rehearsals_deterministic": bool(determinism)
        and all(item.get("status") == "PASS" for item in determinism.values()),
    }
    result = {
        "schema_version": PORTFOLIO_EXECUTION_REHEARSAL_SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "source_batch_run_hash": str(source.get("batch_run_hash") or ""),
        "source_candidate_hash": str((source.get("frozen_candidate") or {}).get("candidate_hash") or ""),
        "checks": checks,
        "determinism": determinism,
        "stages": stage_reports,
        "stage_summary": {
            stage: {
                "status": report.get("status"),
                "order_count": report.get("order_count"),
                "risk_pass_count": report.get("risk_pass_count"),
                "portfolio_risk_pass_count": report.get("portfolio_risk_pass_count"),
                "lifecycle_fill_count": report.get("lifecycle_fill_count"),
                "lineage_pass_count": report.get("lineage_pass_count"),
                "rehearsal_hash": report.get("rehearsal_hash"),
            }
            for stage, report in stage_reports.items()
        },
        "interpretation": "内部执行链工程验收，不构成新的未见样本、收益证明或模拟盘授权。",
        "isolated_in_memory": True,
        "network_accessed": False,
        "production_runtime_mutated": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    logical_report = deepcopy(result)
    for stage_report in logical_report["stages"].values():
        stage_report.pop("generated_at", None)
    result["report_hash"] = _canonical_hash(logical_report)
    result["generated_at"] = int(generated_at or 0)
    return result
