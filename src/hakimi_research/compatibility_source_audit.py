"""Pure AST contract for the historical quant_bot compatibility package."""

from __future__ import annotations

import ast
from typing import Any

from hakimi_research.experiment_manifest import canonical_payload_hash


QUANT_BOT_COMPATIBILITY_AUDIT_SCHEMA_VERSION = (
    "quant-bot-compatibility-package-audit-v1"
)
QUANT_BOT_EXPECTED_MODULES = (
    ("quant_bot.__init__", None),
    ("quant_bot.backtest", "hakimi_research.backtest"),
    ("quant_bot.config", "hakimi_research.config"),
    ("quant_bot.data", "hakimi_research.data"),
    ("quant_bot.execution", "hakimi_research.execution"),
    ("quant_bot.experiment_manifest", "hakimi_research.experiment_manifest"),
    ("quant_bot.indicators", "hakimi_research.indicators"),
    ("quant_bot.logging_setup", "hakimi_research.logging_setup"),
    ("quant_bot.models", "hakimi_research.models"),
    ("quant_bot.reporting", "hakimi_research.reporting"),
    ("quant_bot.risk", "hakimi_research.risk"),
    ("quant_bot.strategies.__init__", "hakimi_research.strategies"),
    ("quant_bot.strategies.base", "hakimi_research.strategies.base"),
    ("quant_bot.strategies.templates", "hakimi_research.strategies.templates"),
)
QUANT_BOT_COMPATIBILITY_AUTHORITY_LOCK = {
    "formal_implementation_in_outputs": False,
    "runtime_activation": False,
    "parameter_optimization": False,
    "paper": False,
    "live": False,
    "order": False,
}


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return {
        **document,
        "audit_hash": canonical_payload_hash(document),
    }


def _unknown(reason: str) -> dict[str, Any]:
    return _seal({
        "schema_version": QUANT_BOT_COMPATIBILITY_AUDIT_SCHEMA_VERSION,
        "status": "UNKNOWN",
        "decision": "SOURCE_MAPPING_NOT_VERIFIED",
        "source_set_hash": None,
        "module_count": None,
        "module_records": [],
        "facts": {
            "native_source_mapping_verified": False,
            "module_set_exact": False,
            "all_modules_ast_parsed": False,
            "definitions_absent": False,
            "canonical_import_targets_exact": False,
            "dynamic_code_absent": False,
            "compatibility_statements_only": False,
            "raw_source_embedded": False,
            "filesystem_io_performed": False,
            "runtime_import_execution_performed": False,
            "formal_implementation_absent": False,
        },
        "violations": [reason],
        "authority": dict(QUANT_BOT_COMPATIBILITY_AUTHORITY_LOCK),
    })


def _snapshot_sources(module_sources: Any) -> dict[str, str] | None:
    if type(module_sources) is not dict:
        return None
    snapshot: dict[str, str] = {}
    for module, source in module_sources.items():
        if (
            type(module) is not str
            or type(source) is not str
            or not source
            or len(source) > 1_000_000
            or module in snapshot
        ):
            return None
        snapshot[module] = source
    return snapshot


def _is_safe_all_assignment(node: ast.Assign) -> bool:
    if (
        len(node.targets) != 1
        or not isinstance(node.targets[0], ast.Name)
        or node.targets[0].id != "__all__"
        or not isinstance(node.value, (ast.List, ast.Tuple))
    ):
        return False
    return all(
        isinstance(item, ast.Constant) and type(item.value) is str
        for item in node.value.elts
    )


def _is_activation_call(node: ast.Expr) -> bool:
    call = node.value
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "activate_canonical_source"
        and not call.args
        and not call.keywords
    )


def _module_record(
    module: str,
    source: str,
    expected_target: str | None,
) -> tuple[dict[str, Any], list[str]]:
    violations: list[str] = []
    try:
        tree = ast.parse(source, filename=module)
    except (SyntaxError, ValueError, TypeError):
        return ({
            "module": module,
            "expected_canonical_target": expected_target,
            "source_hash": canonical_payload_hash(source),
            "ast_parsed": False,
            "definitions_absent": False,
            "canonical_import_target_exact": False,
            "dynamic_code_absent": False,
            "compatibility_statements_only": False,
        }, [f"{module}:AST_PARSE_FAILED"])

    definition_nodes = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Lambda,
    )
    definitions_absent = not any(
        isinstance(node, definition_nodes)
        for node in ast.walk(tree)
    )
    dynamic_code_absent = True
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in {
            "exec", "eval", "compile", "__import__",
        }:
            dynamic_code_absent = False
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
        ):
            dynamic_code_absent = False

    canonical_imports: list[str] = []
    import_shapes_safe = True
    statements_safe = True
    for node in tree.body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and type(node.value.value) is str
        ):
            continue
        if isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level != 0:
                import_shapes_safe = False
            elif target.startswith("hakimi_research"):
                canonical_imports.append(target)
            elif target == "_canonical_source":
                if [alias.name for alias in node.names] != ["activate_canonical_source"]:
                    import_shapes_safe = False
            else:
                import_shapes_safe = False
            continue
        if isinstance(node, ast.Assign) and _is_safe_all_assignment(node):
            continue
        if isinstance(node, ast.Expr) and _is_activation_call(node):
            continue
        statements_safe = False

    expected_imports = [] if expected_target is None else [expected_target]
    canonical_import_target_exact = (
        import_shapes_safe and canonical_imports == expected_imports
    )
    compatibility_statements_only = statements_safe and import_shapes_safe
    if not definitions_absent:
        violations.append(f"{module}:FORMAL_DEFINITION_PRESENT")
    if not canonical_import_target_exact:
        violations.append(f"{module}:CANONICAL_IMPORT_TARGET_INVALID")
    if not dynamic_code_absent:
        violations.append(f"{module}:DYNAMIC_CODE_PRESENT")
    if not compatibility_statements_only:
        violations.append(f"{module}:NON_COMPATIBILITY_STATEMENT_PRESENT")
    return ({
        "module": module,
        "expected_canonical_target": expected_target,
        "source_hash": canonical_payload_hash(source),
        "ast_parsed": True,
        "definitions_absent": definitions_absent,
        "canonical_import_target_exact": canonical_import_target_exact,
        "dynamic_code_absent": dynamic_code_absent,
        "compatibility_statements_only": compatibility_statements_only,
    }, violations)


def evaluate_quant_bot_compatibility_package(
    module_sources: Any,
) -> dict[str, Any]:
    """Audit explicit sources without filesystem access or import execution."""

    sources = _snapshot_sources(module_sources)
    if sources is None:
        return _unknown("MODULE_SOURCE_SET_NOT_NATIVE")
    expected = dict(QUANT_BOT_EXPECTED_MODULES)
    module_set_exact = set(sources) == set(expected)
    violations: list[str] = []
    if not module_set_exact:
        violations.append("MODULE_SET_MISMATCH")
    records: list[dict[str, Any]] = []
    for module in sorted(set(sources).intersection(expected)):
        record, module_violations = _module_record(
            module,
            sources[module],
            expected[module],
        )
        records.append(record)
        violations.extend(module_violations)
    violations = sorted(set(violations))
    facts = {
        "native_source_mapping_verified": True,
        "module_set_exact": module_set_exact,
        "all_modules_ast_parsed": (
            len(records) == len(expected)
            and all(record["ast_parsed"] for record in records)
        ),
        "definitions_absent": (
            len(records) == len(expected)
            and all(record["definitions_absent"] for record in records)
        ),
        "canonical_import_targets_exact": (
            len(records) == len(expected)
            and all(record["canonical_import_target_exact"] for record in records)
        ),
        "dynamic_code_absent": (
            len(records) == len(expected)
            and all(record["dynamic_code_absent"] for record in records)
        ),
        "compatibility_statements_only": (
            len(records) == len(expected)
            and all(record["compatibility_statements_only"] for record in records)
        ),
        "raw_source_embedded": False,
        "filesystem_io_performed": False,
        "runtime_import_execution_performed": False,
        "formal_implementation_absent": not violations,
    }
    document = {
        "schema_version": QUANT_BOT_COMPATIBILITY_AUDIT_SCHEMA_VERSION,
        "status": "PASS" if not violations else "BLOCK",
        "decision": (
            "COMPATIBILITY_REEXPORT_PACKAGE_ONLY"
            if not violations
            else "FORMAL_SOURCE_BOUNDARY_REQUIRES_CLEANUP"
        ),
        "source_set_hash": canonical_payload_hash(sources),
        "module_count": len(sources),
        "module_records": records,
        "facts": facts,
        "violations": violations,
        "authority": dict(QUANT_BOT_COMPATIBILITY_AUTHORITY_LOCK),
    }
    return _seal(document)


def verify_quant_bot_compatibility_package(
    document: Any,
    module_sources: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = evaluate_quant_bot_compatibility_package(module_sources)
    except Exception:
        return False
    return document == expected


__all__ = [
    "QUANT_BOT_COMPATIBILITY_AUDIT_SCHEMA_VERSION",
    "QUANT_BOT_COMPATIBILITY_AUTHORITY_LOCK",
    "QUANT_BOT_EXPECTED_MODULES",
    "evaluate_quant_bot_compatibility_package",
    "verify_quant_bot_compatibility_package",
]
