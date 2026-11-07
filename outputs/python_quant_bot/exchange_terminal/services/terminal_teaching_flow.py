"""Explicit preparation of one existing fictional input, without a task or run."""
from copy import deepcopy
import base64
from importlib.resources import files
import re


SCHEMA = "terminal-teaching-input-v1"
STRATEGY = "price.dual_ma@1"
PARAMS = {"fast_window": 2, "slow_window": 4, "position_pct": .25,
          "stop_loss_pct": .03, "take_profit_pct": .06}
PERMISSIONS = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
_ID = re.compile(r"[a-f0-9]{24}\Z")


def _require(value, reason):
    if not value:
        raise ValueError("teaching_input_" + reason)


def _view_matches(view, snapshot):
    return (type(view) is dict and type(view.get("id")) is str and _ID.fullmatch(view["id"])
            and view.get("kind") == "PRICE_SNAPSHOT" and view.get("input_id") == snapshot["snapshot_id"]
            and view.get("evidence_kind") == "SYNTHETIC_TEST" and view.get("security") == snapshot["security"]
            and view.get("sessions") == len(snapshot["sessions"])
            and view.get("coverage_start") == snapshot["sessions"][0]["date"]
            and view.get("coverage_end") == snapshot["sessions"][-1]["date"]
            and (view.get("status") == "READY" or view.get("status") == "OFFLINE_INPUT_RETAINED"
                 and view.get("admission_status") == "READY"))


def prepare_teaching_input(service, payload):
    """Use the accepted importer; a caller must explicitly choose and save a task.

    The surrounding durable job owns submission/unknown-outcome handling. This
    helper never retries, repairs a workspace, runs a strategy, or follows a
    client-provided source path. A repeated completed request reuses a verified
    existing input identity and leaves its original file bytes untouched.
    """
    _require(type(payload) is dict and not payload, "empty_payload_required")
    from hakimi_terminal_research.documents import canonical_bytes, parse_document
    from hakimi_terminal_research.equity_dataset import build_equity_snapshot

    resources = files("hakimi_terminal_research").joinpath("resources")
    raw_csv = resources.joinpath("trade-demo.csv").read_bytes()
    declaration = parse_document(resources.joinpath("trade-demo-import.json").read_bytes())
    snapshot = build_equity_snapshot(raw_csv, declaration).document
    _require(snapshot["evidence_kind"] == "SYNTHETIC_TEST"
             and snapshot["security"]["security_id"] == "SYNTHETIC:RESEARCH:TEST"
             and snapshot["security"]["symbol"] == "TEST"
             and snapshot["security"]["currency"] == "USD"
             and len(snapshot["sessions"]) == 22
             and snapshot["research_admission"]["allowed"] is True
             and snapshot["research_admission"]["synthetic_only"] is True, "fixed_fixture_identity_mismatch")
    with service._lock:
        service._safe(service.workspace)
        inventory = service.core.read("inputs")
        _require(type(inventory) is dict and type(inventory.get("items")) is list, "inventory_not_available")
        existing = sorted((row for row in inventory["items"] if type(row) is dict
                           and row.get("input_id") == snapshot["snapshot_id"]), key=lambda row: str(row.get("id", "")))
        reused = bool(existing)
        if existing:
            # Re-read the exact opaque ID through the core's guarded lookup.
            _require(_view_matches(existing[0], snapshot), "existing_identity_mismatch")
            view = service.core.read("inputs", existing[0]["id"])
            _require(_view_matches(view, snapshot), "existing_input_changed")
        else:
            # An incomplete index cannot establish that there is no existing
            # counterpart. Preserve its diagnostics instead of creating a copy.
            _require(not inventory.get("warnings"), "inventory_incomplete_review_existing_records")
            view = service.core.mutate("import_document", {
                "filename": "fictional-teaching-price-snapshot.json",
                "document_base64": base64.b64encode(canonical_bytes(snapshot)).decode("ascii"),
            })
            _require(_view_matches(view, snapshot), "import_receipt_identity_mismatch")
    return {
        "schema_version": SCHEMA, "status": "READY", "input_id": view["id"],
        "snapshot_id": snapshot["snapshot_id"], "input": deepcopy(view), "reused": reused,
        "evidence_kind": "SYNTHETIC_TEST", "currency": snapshot["security"]["currency"], "sessions": 22,
        "strategy_key": STRATEGY, "params": dict(PARAMS),
        "teaching_parameters_only": True, "standard_defaults_changed": False,
        "source_truth_verified": False, "new_tasks": 0, "new_economic_runs": 0,
        "permissions": dict(PERMISSIONS),
        "next_step": "选择策略与本金，核对教学设置后明确保存一个任务；保存不会运行研究。",
        "limitations": ["固定虚构教学资料，不是真实行情或策略表现。", "教学均线2/4只用于这次体验，不改变标准策略默认值。"],
    }
