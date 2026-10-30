"""Resolve current-workspace saved identities before descriptive comparison.

Only the original native or accepted frozen verifier may produce an envelope.
Client-supplied reports, paths and integrity assertions are never accepted.
"""
from copy import deepcopy
from hashlib import sha256
import json
import re

from .terminal_result_comparison import compare_saved_results


RECORDED_SOURCE_SCHEMA = "hakimi-saved-native-source-v1"
RECORDED_EVIDENCE_SCHEMA = "hakimi-saved-research-classification-v1"
SOURCE_DIGEST_RULE = "ASCII_SORTED_COMPACT_JSON_SOURCE_FILES_V1"


def _recorded_digest(value):
    return sha256(json.dumps(value, ensure_ascii=True, allow_nan=False,
                             sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()


def _recorded_seal(value):
    return {**value, "id": _recorded_digest(value)}


def _recorded_evidence_decision(facts):
    """Interpret saved classification fields, never a security symbol or label.

    A recorded authentication claim is still not external execution admission.
    Known synthetic research is permanently offline for this exact evidence.
    """
    synthetic, unauthenticated, authenticated = False, False, False

    def inspect(key, value):
        nonlocal synthetic, unauthenticated, authenticated
        leaf = key.rsplit(".", 1)[-1]
        if leaf in {"synthetic_only", "qa_test"} and value is True:
            synthetic = True
        if leaf in {"data_kind", "evidence_kind"} and type(value) is str:
            tag = value.upper()
            synthetic |= tag in {"QA", "QA_TEST"} or tag.startswith(("SYNTHETIC", "QA_"))
        if leaf == "source_authenticated" and type(value) is bool:
            authenticated |= value
            unauthenticated |= not value
        if leaf in {"data_kind", "evidence_kind", "evidence_status", "truth_status", "status"} and type(value) is str:
            unauthenticated |= "UNVERIFIED" in value.upper()
        if type(value) is dict:
            for name, item in value.items():
                inspect(str(name), item)

    for fact in facts:
        inspect(fact["path"], fact["value"])
    status = ("SYNTHETIC_OFFLINE_ONLY" if synthetic else "UNVERIFIED_RESEARCH" if unauthenticated
              else "RECORDED_AUTHENTICATION_REQUIRES_ADMISSION" if authenticated else "UNKNOWN")
    return {"status": status, "external_research_eligible": False if synthetic else None,
            "external_admission_required": True, "offline_only": synthetic,
            "admission_cannot_override_synthetic": synthetic}


def _recorded_classification(envelope, reference, binding):
    paths = ("report.data_kind", "report.evidence_kind", "report.evidence_status", "report.quality",
             "report.input_summary.data_kind", "report.input_summary.evidence_kind", "report.input_summary.quality",
             "report.input_summary.meta.data_kind", "report.input_summary.meta.evidence_kind",
             "report.input_summary.meta.qa_test", "report.input_summary.meta.synthetic_only",
             "report.input_summary.meta.source_authenticated", "report.input_summary.meta.source_authentication",
             "report.input_summary.meta.core_research_admission", "report.input_summary.meta.daily_research_admission",
             "report.input_summary.meta.price_source.truth_status", "report.dataset.data_kind", "report.dataset.evidence_kind",
             "snapshot.data_kind", "snapshot.evidence_kind", "snapshot.research_admission", "snapshot.source_authentication")
    facts = []
    for path in paths:
        item, found = envelope, True
        for name in path.split("."):
            if type(item) is not dict or name not in item:
                found = False
                break
            item = item[name]
        if found:
            facts.append({"path": path, "value": deepcopy(item)})
    return _recorded_seal({"schema_version": RECORDED_EVIDENCE_SCHEMA,
        "reference": deepcopy(reference), "task_id": binding["task_id"], "input_id": binding["input_id"],
        "report_hash": binding["report_hash"], "engine_id": binding["engine_id"],
        "facts": facts, "decision": _recorded_evidence_decision(facts)})


def _recorded_native_source(task, report, reference, binding):
    sources, fingerprint = task.get("engine_source_identity"), task.get("fingerprint")
    if (type(sources) is not dict or not 0 < len(sources) <= 32
            or any(type(name) is not str or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}\.py", name) is None
                   or type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None
                   for name, value in sources.items())
            or type(fingerprint) is not str or re.fullmatch(r"[a-f0-9]{64}", fingerprint) is None):
        raise ValueError("saved_native_source_identity_missing_or_invalid")
    config = report["configuration"]
    if (_recorded_digest(config.get("engine_source_identity")) != _recorded_digest(sources)
            or config.get("fingerprint") != fingerprint):
        raise ValueError("saved_native_source_identity_conflict")
    return _recorded_seal({"schema_version": RECORDED_SOURCE_SCHEMA,
        "reference": deepcopy(reference), "task_id": binding["task_id"], "input_id": binding["input_id"],
        "report_hash": binding["report_hash"], "engine_id": binding["engine_id"],
        "source_files": deepcopy(sources), "fingerprint": fingerprint,
        "digest_rule": SOURCE_DIGEST_RULE, "content_sha256": _recorded_digest(sources)})


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


def resolve_execution_research(service, reference, *, include_recorded_source=False):
    """Bind an offline plan to saved evidence, never client form assumptions."""
    if type(include_recorded_source) is not bool:
        raise ValueError("recorded_source_opt_in_boolean_required")
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
    resolved = {"binding": binding, "owner_id": owner, "display": display, "assumptions": assumptions}
    # Opt-in sidecars preserve the historical binding and candidate projection
    # byte-for-byte. Default callers retain their exact existing field contract.
    if include_recorded_source:
        if reference["kind"] == "terminal_run":
            resolved["recorded_source_identity"] = _recorded_native_source(task, report, reference, binding)
        resolved["recorded_evidence_classification"] = _recorded_classification(envelope, reference, binding)
    return resolved
