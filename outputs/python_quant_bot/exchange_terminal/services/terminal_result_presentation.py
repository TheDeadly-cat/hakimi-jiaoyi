"""Present existing financial facts without modifying a saved core report."""
from copy import deepcopy

from .terminal_saved_results import verified_saved_result


def project_core_result_detail(detail, verified):
    """Join only the same verified report; missing facts remain absent."""
    if (type(detail) is not dict or type(verified) is not dict
            or verified.get("verification_status") != "VERIFIED_RECORD"
            or detail.get("id") != verified.get("id")):
        raise ValueError("core_result_presentation_verified_identity_required")
    manifest, report = verified.get("manifest", {}), verified.get("report", {})
    identities = detail.get("identities", {})
    expected = {"run_id": manifest.get("run_id"), "task_id": manifest.get("task_id"),
                "report_hash": report.get("report_hash")}
    if any(type(v) is not str or not v for v in expected.values()) or identities != expected:
        raise ValueError("core_result_presentation_report_changed")
    result = report.get("result", {})
    if type(result) is not dict or type(detail.get("summary")) is not dict:
        raise ValueError("core_result_presentation_saved_shape_invalid")
    out = deepcopy(detail)
    summary = out["summary"]
    fields = {key: result[key] for key in ("execution_model", "metric_semantics_version", "round_trip_count") if key in result}
    security = report.get("dataset", {}).get("security", {})
    if "currency" in security:
        fields["currency"] = security["currency"]
    for key, value in fields.items():
        if key in summary and summary[key] != value:
            raise ValueError("core_result_presentation_saved_fact_conflict:" + key)
        summary[key] = deepcopy(value)
    out["verification_status"] = "VERIFIED_RECORD"
    out["presentation_schema"] = "terminal-core-result-presentation-v1"
    return out


def core_result_detail(service, identity):
    detail = service.core.read("runs", identity)
    verified = verified_saved_result(service, {"kind": "core_run", "id": identity})
    return project_core_result_detail(detail, verified)


def present_core_run_completion(service, result):
    """An auxiliary read can never turn an already saved run into failure."""
    if type(result) is not dict or type(result.get("id")) is not str:
        return result
    try:
        verified = verified_saved_result(service, {"kind": "core_run", "id": result["id"]})
        return project_core_result_detail(result, verified)
    except Exception:
        out = deepcopy(result)
        out["presentation_warnings"] = [*(out.get("presentation_warnings") or []),
            "研究结果已保存；财务补充信息暂时未读全。可重新读取同一份报告，不要重复运行。"]
        return out
