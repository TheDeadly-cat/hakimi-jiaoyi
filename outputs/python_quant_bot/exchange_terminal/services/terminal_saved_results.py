"""Resolve current-workspace saved identities before descriptive comparison.

Only the original native or accepted frozen verifier may produce an envelope.
Client-supplied reports, paths and integrity assertions are never accepted.
"""
from copy import deepcopy
import re

from .terminal_result_comparison import compare_saved_results


def verified_saved_result(service, reference):
    if type(reference) is not dict or set(reference) != {"kind", "id"}:
        raise ValueError("saved_result_reference_required")
    kind, identity = reference["kind"], reference["id"]
    if type(identity) is not str:
        raise ValueError("saved_result_id_required")
    if kind == "terminal_run" and re.fullmatch(r"[0-9a-f]{64}", identity):
        # read() resolves the immutable report ID and checks started/task/input
        # bindings. It does not invoke the research runner or repair old bytes.
        report = service.read("terminal_runs", identity)
        if report.get("status") != "COMPLETED":
            raise ValueError("saved_result_not_completed")
        return {"verification_status": "VERIFIED_RECORD", "id": identity,
                "report": deepcopy(report)}
    if kind == "core_run" and re.fullmatch(r"[0-9a-f]{24}", identity):
        from hakimi_terminal_research.offline_app import verify_run
        path = service._safe(service.core._lookup("runs", identity))
        service.core._guard_tree(path)
        manifest, report, snapshot = verify_run(path)
        return {"verification_status": "VERIFIED_RECORD", "id": identity,
                "manifest": deepcopy(manifest), "report": deepcopy(report),
                "snapshot": deepcopy(snapshot.document)}
    raise ValueError("saved_result_reference_invalid")


def compare_saved_references(service, request):
    if type(request) is not dict or set(request) != {"references"}:
        raise ValueError("saved_comparison_references_required")
    references = request["references"]
    if type(references) is not list or not 2 <= len(references) <= 10:
        raise ValueError("saved_comparison_requires_two_to_ten")
    return compare_saved_results([verified_saved_result(service, item) for item in references])


def resolve_execution_research(service, reference):
    """Bind an offline plan to saved evidence, never client form assumptions."""
    envelope = verified_saved_result(service, reference)
    report = envelope["report"]
    assumptions, display = {}, {}
    if reference["kind"] == "terminal_run":
        task = service._task_record(report["task_id"])
        # Validate the complete family journal before promising ownership across
        # versions; matching a family string alone is insufficient.
        family = service._family(task["family_id"])
        if task["version"] > family["version"]:
            raise ValueError("execution_research_family_version_uncommitted")
        selected = service._task_record(family["task_id"])
        while selected["id"] != task["id"]:
            if not selected.get("parent_task_id"):
                raise ValueError("execution_research_not_in_verified_family")
            selected = service._task_record(selected["parent_task_id"], family_id=task["family_id"])
        config, inputs = report["configuration"], report["input_summary"]
        meta = inputs.get("meta") or {}
        binding = dict(engine_id=report["engine_id"], strategy_id=report["strategy_id"],
            strategy_params=deepcopy(config["strategy_params"]), task_id=report["task_id"],
            task_version=report["version"], input_id=config["input_id"], report_id=report["id"],
            report_hash=report["id"], risk=deepcopy(config["risk"]), costs=deepcopy(config["costs"]))
        owner = "family:" + task["family_id"]
        security = meta.get("security") or {}
        display = {key: value for key, value in {
            "symbol": inputs.get("symbol"), "security_id": meta.get("security_id", security.get("security_id")),
            "currency": meta.get("currency", security.get("currency")), "asset_class": meta.get("asset_class")
        }.items() if type(value) is str and value}
        candidates = {"fill_model": config.get("execution_model"), "quantity_policy": config.get("quantity_policy")}
    else:
        manifest, snapshot = envelope["manifest"], envelope["snapshot"]
        spec = report["spec"]
        task = manifest["task"]
        binding = dict(engine_id="research.accepted-equity", strategy_id=task["strategy"],
            strategy_params=deepcopy(spec["strategy"]["params"]), task_id=manifest["task_id"],
            task_version=task.get("management", {}).get("revision") or manifest["task_id"],
            input_id=snapshot["snapshot_id"], report_id=manifest["run_id"], report_hash=report["report_hash"],
            risk=deepcopy(spec["risk"]), costs={key: spec[key] for key in ("fee_rate", "slippage_pct") if key in spec},
            source_hash=manifest["runtime"]["source_identity"]["content_sha256"])
        # A verified immutable task does not by itself prove current managed
        # family continuity, so do not combine ownership across core versions.
        owner = "task:" + manifest["task_id"]
        display = {key: snapshot["security"][key] for key in ("symbol", "security_id", "currency")
                   if type(snapshot["security"].get(key)) is str and snapshot["security"][key]}
        if snapshot.get("market") == "us_equity":
            display["asset_class"] = "US_EQUITY"
        candidates = {"fill_model": report.get("result", {}).get("execution_model"),
                      "quantity_policy": spec.get("quantity_policy")}
    if display.get("security_id"):
        binding["security_id"] = display["security_id"]
    binding.update(schema_version="hakimi-offline-research-binding-v1", status="COMPLETED")
    assumptions = {key: value for key, value in candidates.items() if type(value) is str and value}
    return {"binding": binding, "owner_id": owner, "display": display, "assumptions": assumptions}
