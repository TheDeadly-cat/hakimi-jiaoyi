from __future__ import annotations

import math
from typing import Any


ORDER_TYPES = {"MARKET", "CURRENT", "LIMIT", "POST_ONLY", "IOC", "FOK", "OCO"}
PAPER_ORDER_SIDES = {"BUY", "SELL"}
POSITION_SIDES = {"FLAT", "LONG", "SHORT"}
PAPER_ORDER_STATES = {
    "CREATED",
    "RISK_CHECKED",
    "ACCEPTED",
    "WORKING",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCELLED",
    "REJECTED",
    "EXPIRED",
}
PAPER_TERMINAL_STATES = {"FILLED", "CANCELLED", "REJECTED", "EXPIRED"}
EXECUTION_REPORT_STATUSES = {
    "CREATED",
    "RISK_CHECKED",
    "ACCEPTED",
    "WORKING",
    "FILLED",
    "PARTIAL",
    "IOC_PARTIAL_CANCEL",
    "IOC_CANCELLED",
    "WAITING_LIMIT",
    "MAKER_WAIT",
    "CANCELLED",
    "REJECTED",
    "EXPIRED",
}
MAX_IDEMPOTENCY_KEY_LENGTH = 160
MAX_RISK_REQUEST_ID_LENGTH = 160

_ORDER_NONNEGATIVE_FIELDS = (
    "mark_price",
    "limit_price",
    "requested_notional",
    "requested_qty",
)
_REPORT_NONNEGATIVE_FIELDS = (
    "avg_price",
    "filled_qty",
    "filled_notional",
    "fee",
    "requested_notional",
    "requested_qty",
    "levels_used",
)
_REPORT_FINITE_FIELDS = (
    "slippage_pct",
    "funding_rate",
    "funding_estimate",
    "funding_charged",
)


def _finite_number(value: Any, error: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(error)
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(error) from None
    if not math.isfinite(parsed) or (nonnegative and parsed < 0):
        raise ValueError(error)
    return parsed


def _timestamp(value: Any, error: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(error)
    return value


def validate_paper_lifecycle_order(payload: Any) -> dict[str, Any]:
    """Validate the durable order contract before restore, replay, or settlement."""
    if not isinstance(payload, dict):
        raise ValueError("paper_order_contract_object_required")

    order_id = payload.get("order_id")
    account_id = payload.get("account_id")
    symbol = payload.get("symbol")
    side = payload.get("side")
    order_type = payload.get("order_type")
    state = payload.get("state")
    position_side_before = payload.get("position_side_before")
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("paper_order_contract_order_id_invalid")
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValueError("paper_order_contract_account_id_invalid")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("paper_order_contract_symbol_invalid")
    if not isinstance(side, str) or side.upper() not in PAPER_ORDER_SIDES:
        raise ValueError("paper_order_contract_side_invalid")
    if not isinstance(order_type, str) or order_type.upper() not in ORDER_TYPES:
        raise ValueError("paper_order_contract_order_type_invalid")
    if not isinstance(state, str) or state.upper() not in PAPER_ORDER_STATES:
        raise ValueError("paper_order_contract_state_invalid")
    if not isinstance(position_side_before, str) or position_side_before.upper() not in POSITION_SIDES:
        raise ValueError("paper_order_contract_position_side_before_invalid")
    clean_state = state.upper()

    for field in ("idempotency_key", "request_signature"):
        value = payload.get(field, "")
        if value is not None and not isinstance(value, str):
            raise ValueError(f"paper_order_contract_{field}_invalid")
    idempotency_key = str(payload.get("idempotency_key") or "")
    request_signature = str(payload.get("request_signature") or "")
    if len(idempotency_key) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise ValueError("paper_order_contract_idempotency_key_too_long")
    if idempotency_key and not request_signature:
        raise ValueError("paper_order_contract_request_signature_missing")
    risk_request_id = payload.get("risk_request_id")
    if (
        not isinstance(risk_request_id, str)
        or not risk_request_id.strip()
        or len(risk_request_id.strip()) > MAX_RISK_REQUEST_ID_LENGTH
    ):
        raise ValueError("paper_order_contract_risk_request_id_invalid")

    for field in ("reduce_only", "quantity_constrained"):
        if field not in payload or type(payload.get(field)) is not bool:
            raise ValueError(f"paper_order_contract_{field}_invalid")

    created_at = _timestamp(payload.get("created_at"), "paper_order_contract_created_at_invalid")
    updated_at = _timestamp(payload.get("updated_at"), "paper_order_contract_updated_at_invalid")
    if updated_at < created_at:
        raise ValueError("paper_order_contract_time_regression")

    for field in _ORDER_NONNEGATIVE_FIELDS:
        if field in payload:
            _finite_number(payload.get(field), f"paper_order_contract_{field}_invalid", nonnegative=True)
    requested_qty = _finite_number(
        payload.get("requested_qty", 0.0),
        "paper_order_contract_requested_qty_invalid",
        nonnegative=True,
    )
    requested_notional = _finite_number(
        payload.get("requested_notional", 0.0),
        "paper_order_contract_requested_notional_invalid",
        nonnegative=True,
    )
    mark_price = _finite_number(
        payload.get("mark_price", 0.0),
        "paper_order_contract_mark_price_invalid",
        nonnegative=True,
    )
    if payload.get("quantity_constrained") is not (requested_qty > 0):
        raise ValueError("paper_order_contract_quantity_semantics_invalid")
    if requested_notional <= 0 or mark_price <= 0:
        raise ValueError("paper_order_contract_request_budget_invalid")
    if requested_qty > 0:
        quantity_notional = requested_qty * mark_price
        request_tolerance = max(0.01, quantity_notional * 1e-8)
        if abs(requested_notional - quantity_notional) > request_tolerance:
            raise ValueError("paper_order_contract_requested_quantity_notional_mismatch")

    raw_transitions = payload.get("transitions")
    if not isinstance(raw_transitions, list) or not raw_transitions:
        raise ValueError("paper_order_contract_transitions_invalid")
    previous_time = 0
    for index, transition in enumerate(raw_transitions):
        if not isinstance(transition, dict):
            raise ValueError("paper_order_contract_transition_invalid")
        transition_state = transition.get("state")
        if not isinstance(transition_state, str) or transition_state.upper() not in PAPER_ORDER_STATES:
            raise ValueError("paper_order_contract_transition_state_invalid")
        occurred_at = _timestamp(
            transition.get("time"),
            "paper_order_contract_transition_time_invalid",
        )
        if occurred_at < previous_time:
            raise ValueError("paper_order_contract_transition_time_regression")
        if transition_state.upper() in PAPER_TERMINAL_STATES and index != len(raw_transitions) - 1:
            raise ValueError("paper_order_contract_transition_after_terminal")
        previous_time = occurred_at
    if str(raw_transitions[-1].get("state") or "").upper() != clean_state:
        raise ValueError("paper_order_contract_transition_state_mismatch")
    if previous_time > updated_at:
        raise ValueError("paper_order_contract_transition_after_update")

    report = payload.get("execution_report")
    if not isinstance(report, dict):
        raise ValueError("paper_order_contract_execution_report_invalid")
    report_status = report.get("status")
    if not isinstance(report_status, str) or report_status.upper() not in EXECUTION_REPORT_STATUSES:
        raise ValueError("paper_order_contract_execution_status_invalid")
    for field in ("quantity_constrained",):
        if field in report and type(report.get(field)) is not bool:
            raise ValueError(f"paper_order_contract_report_{field}_invalid")
    for field in _REPORT_NONNEGATIVE_FIELDS:
        if field in report:
            _finite_number(
                report.get(field),
                f"paper_order_contract_report_{field}_invalid",
                nonnegative=True,
            )
    for field in _REPORT_FINITE_FIELDS:
        if field in report:
            _finite_number(report.get(field), f"paper_order_contract_report_{field}_invalid")

    filled_qty = _finite_number(
        report.get("filled_qty", 0.0),
        "paper_order_contract_report_filled_qty_invalid",
        nonnegative=True,
    )
    avg_price = _finite_number(
        report.get("avg_price", 0.0),
        "paper_order_contract_report_avg_price_invalid",
        nonnegative=True,
    )
    filled_notional = _finite_number(
        report.get("filled_notional", 0.0),
        "paper_order_contract_report_filled_notional_invalid",
        nonnegative=True,
    )
    if filled_qty > 0 and (avg_price <= 0 or filled_notional <= 0):
        raise ValueError("paper_order_contract_fill_semantics_invalid")
    if filled_qty > 0:
        calculated_notional = filled_qty * avg_price
        notional_tolerance = max(0.05, calculated_notional * 1e-5)
        if abs(filled_notional - calculated_notional) > notional_tolerance:
            raise ValueError("paper_order_contract_fill_notional_mismatch")
    if "requested_qty" in report:
        report_requested_qty = _finite_number(
            report.get("requested_qty"),
            "paper_order_contract_report_requested_qty_invalid",
            nonnegative=True,
        )
        if abs(report_requested_qty - requested_qty) > 1e-8:
            raise ValueError("paper_order_contract_report_requested_qty_mismatch")
    if payload.get("quantity_constrained") is True:
        if filled_qty > requested_qty + 1e-8:
            raise ValueError("paper_order_contract_fill_quantity_exceeded")
        if clean_state == "FILLED" and abs(filled_qty - requested_qty) > 1e-8:
            raise ValueError("paper_order_contract_filled_quantity_incomplete")
    if filled_notional > requested_notional + 0.01:
        raise ValueError("paper_order_contract_fill_notional_exceeded")
    if clean_state == "FILLED" and (filled_qty <= 0 or report_status.upper() != "FILLED"):
        raise ValueError("paper_order_contract_filled_state_invalid")
    if clean_state in {"REJECTED", "EXPIRED"} and filled_qty > 0:
        raise ValueError("paper_order_contract_terminal_fill_invalid")
    fill_states = {"PARTIALLY_FILLED", "FILLED", "CANCELLED"}
    fill_statuses = {"FILLED", "PARTIAL", "IOC_PARTIAL_CANCEL"}
    if filled_qty > 0 and (clean_state not in fill_states or report_status.upper() not in fill_statuses):
        raise ValueError("paper_order_contract_fill_state_mismatch")
    if filled_qty <= 0 and report_status.upper() in fill_statuses:
        raise ValueError("paper_order_contract_report_fill_missing")
    if report_status.upper() == "FILLED" and clean_state != "FILLED":
        raise ValueError("paper_order_contract_report_state_mismatch")
    if "side" in report and str(report.get("side") or "").upper() != side.upper():
        raise ValueError("paper_order_contract_report_side_mismatch")
    if "order_type" in report and str(report.get("order_type") or "").upper() != order_type.upper():
        raise ValueError("paper_order_contract_report_order_type_mismatch")
    return payload
