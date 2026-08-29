"""Pure AST audit for exchange_terminal layer dependency direction.

The auditor consumes an explicit in-memory module-to-source mapping. It performs
no filesystem or import execution. A cycle-free graph can still be blocked when
one package mixes inward ports with outward delivery adapters.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "exchange-terminal-layer-dependency-audit-v1"
STATIC_FINGERPRINT = (
    "20260824-exchange-terminal-layer-dependency-audit-v1-"
    "pure-ast-partial-layering-lock-1"
)
LAYERS = ("domain", "application", "infrastructure", "interfaces")
STATUS_CONFORMING = "CONFORMING_STATIC_GRAPH"
STATUS_BLOCKED = "BLOCKED_PARTIAL_LAYERING"

MINIMUM_PORT_DELIVERY_CLEANUP_SLICE = (
    "CLASSIFY_INTERFACES_MODULES_AS_PORT_DELIVERY_OR_SUPPORT",
    "CREATE_EXPLICIT_APPLICATION_PORT_NAMESPACE",
    "MIGRATE_APPLICATION_IMPORTS_TO_PORT_NAMESPACE",
    "KEEP_DELIVERY_ADAPTERS_DEPENDING_INWARD",
    "ADD_TEMPORARY_HASH_PINNED_COMPATIBILITY_SHIMS",
    "REMOVE_SHIMS_ONLY_AFTER_CONSUMER_MIGRATION",
)

_MODULE_RE = re.compile(
    r"^exchange_terminal\.(domain|application|infrastructure|interfaces)"
    r"\.[a-z_][a-z0-9_]*$"
)
_MAX_MODULES = 512
_MAX_SOURCE_LENGTH = 1_000_000
_MAX_TOTAL_SOURCE_LENGTH = 16_000_000
_AUTHORITY_KEYS = (
    "architecture_migration_complete_allowed",
    "compatibility_shim_removal_allowed",
    "current_admission_allowed",
    "host_activation_allowed",
    "live_order_allowed",
    "paper_authorized",
    "runtime_mutation_allowed",
    "writer_allowed",
)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _snapshot_sources(module_sources: Any) -> dict[str, str] | None:
    if type(module_sources) is not dict:
        return None
    if not 1 <= len(module_sources) <= _MAX_MODULES:
        return None
    snapshot: dict[str, str] = {}
    total = 0
    for module, source in module_sources.items():
        if (
            type(module) is not str
            or _MODULE_RE.fullmatch(module) is None
            or type(source) is not str
            or len(source) > _MAX_SOURCE_LENGTH
        ):
            return None
        total += len(source)
        if total > _MAX_TOTAL_SOURCE_LENGTH or module in snapshot:
            return None
        snapshot[module] = source
    return snapshot


def _resolve_import_from(
    source_module: str,
    node: ast.ImportFrom,
) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = source_module.split(".")[:-1]
    keep = len(package_parts) - (node.level - 1)
    if keep < 0:
        return ""
    parts = package_parts[:keep]
    if node.module:
        parts.extend(node.module.split("."))
    return ".".join(parts)


def _module_imports(
    module: str,
    tree: ast.AST,
    known_modules: set[str],
) -> tuple[set[str], bool]:
    targets: set[str] = set()
    dynamic_import_present = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in known_modules:
                    targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_import_from(module, node)
            if base in known_modules:
                targets.add(base)
            for alias in node.names:
                candidate = base + "." + alias.name if base else alias.name
                if candidate in known_modules:
                    targets.add(candidate)
        elif isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name) and function.id == "__import__":
                dynamic_import_present = True
            if (
                isinstance(function, ast.Attribute)
                and function.attr == "import_module"
                and isinstance(function.value, ast.Name)
                and function.value.id == "importlib"
            ):
                dynamic_import_present = True
    return targets, dynamic_import_present


def _strongly_connected_components(
    modules: set[str],
    edges: dict[str, set[str]],
) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low_links: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(module: str) -> None:
        nonlocal index
        indices[module] = index
        low_links[module] = index
        index += 1
        stack.append(module)
        on_stack.add(module)
        for target in sorted(edges.get(module, set())):
            if target not in indices:
                visit(target)
                low_links[module] = min(low_links[module], low_links[target])
            elif target in on_stack:
                low_links[module] = min(low_links[module], indices[target])
        if low_links[module] != indices[module]:
            return
        component: list[str] = []
        while True:
            current = stack.pop()
            on_stack.remove(current)
            component.append(current)
            if current == module:
                break
        if len(component) > 1 or module in edges.get(module, set()):
            components.append(sorted(component))

    for module in sorted(modules):
        if module not in indices:
            visit(module)
    return sorted(components)


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "decision": "DEPENDENCY_AUDIT_INPUT_NOT_VERIFIED",
        "source_set_hash": None,
        "module_counts": {layer: None for layer in LAYERS},
        "cross_layer_edge_counts": {},
        "bidirectional_layer_pairs": [],
        "module_cycles": [],
        "role_observation": {
            "interfaces_contains_inward_ports": False,
            "interfaces_contains_outward_delivery_adapters": False,
            "interfaces_package_role_mixed": False,
        },
        "minimum_cleanup_slice": [],
        "facts": {
            "native_source_mapping_verified": False,
            "all_modules_ast_parsed": False,
            "dynamic_imports_absent": False,
            "module_cycle_detected": False,
            "package_level_bidirectional_dependency_detected": False,
            "domain_inward_only": False,
            "application_infrastructure_separated": False,
            "raw_source_embedded": False,
            "filesystem_io_performed": False,
            "runtime_import_execution_performed": False,
            "architecture_migration_complete": False,
        },
        "violations": [reason],
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "layer_dependency_audit_hash")


def evaluate_exchange_terminal_layer_dependency_audit_v1(
    module_sources: Any,
) -> dict[str, Any]:
    sources = _snapshot_sources(module_sources)
    if sources is None:
        return _unknown("MODULE_SOURCE_SET_NOT_BOUNDED_NATIVE_MAPPING")

    trees: dict[str, ast.AST] = {}
    try:
        for module, source in sources.items():
            trees[module] = ast.parse(source, filename=module)
    except (SyntaxError, ValueError, TypeError):
        return _unknown("MODULE_SOURCE_AST_PARSE_FAILED")

    known_modules = set(sources)
    edges: dict[str, set[str]] = {}
    dynamic_modules: list[str] = []
    for module, tree in trees.items():
        targets, dynamic = _module_imports(module, tree, known_modules)
        edges[module] = targets
        if dynamic:
            dynamic_modules.append(module)

    module_counts = {
        layer: sum(
            module.startswith("exchange_terminal." + layer + ".")
            for module in known_modules
        )
        for layer in LAYERS
    }
    cross_edges: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for source, targets in edges.items():
        source_layer = source.split(".")[1]
        for target in targets:
            target_layer = target.split(".")[1]
            if source_layer != target_layer:
                cross_edges[(source_layer, target_layer)].add((source, target))
    edge_counts = {
        source + "->" + target: len(pairs)
        for (source, target), pairs in sorted(cross_edges.items())
    }

    bidirectional_pairs: list[str] = []
    for left_index, left in enumerate(LAYERS):
        for right in LAYERS[left_index + 1 :]:
            if cross_edges.get((left, right)) and cross_edges.get((right, left)):
                bidirectional_pairs.append(left.upper() + "_" + right.upper())

    cycles = _strongly_connected_components(known_modules, edges)
    violations: list[str] = []
    if any(source == "domain" for source, _target in cross_edges):
        violations.append("DOMAIN_DEPENDS_ON_OUTER_LAYER")
    if cross_edges.get(("application", "infrastructure")):
        violations.append("APPLICATION_DEPENDS_ON_INFRASTRUCTURE")
    if cross_edges.get(("infrastructure", "interfaces")):
        violations.append("INFRASTRUCTURE_DEPENDS_ON_DELIVERY_INTERFACES")
    if cross_edges.get(("interfaces", "infrastructure")):
        violations.append("INTERFACES_DEPENDS_ON_INFRASTRUCTURE")
    if (
        cross_edges.get(("application", "interfaces"))
        and cross_edges.get(("interfaces", "application"))
    ):
        violations.extend(
            [
                "APPLICATION_INTERFACES_PACKAGE_BIDIRECTIONAL",
                "INTERFACES_PACKAGE_MIXES_PORT_AND_DELIVERY_ROLES",
                "PORT_DELIVERY_NAMESPACE_SPLIT_NOT_COMPLETED",
            ]
        )
    if cycles:
        violations.append("CROSS_LAYER_MODULE_CYCLE_DETECTED")
    if dynamic_modules:
        violations.append("DYNAMIC_IMPORT_PRESENT_UNAUDITED")
    violations = sorted(set(violations))

    mixed_interfaces = (
        bool(cross_edges.get(("application", "interfaces")))
        and bool(cross_edges.get(("interfaces", "application")))
    )
    conforming = not violations
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS_CONFORMING if conforming else STATUS_BLOCKED,
        "decision": (
            "STATIC_LAYER_DEPENDENCY_DIRECTION_CONFORMS"
            if conforming
            else "LAYER_ROLE_SEPARATION_REQUIRED"
        ),
        "source_set_hash": strict_canonical_hash(sources),
        "module_counts": module_counts,
        "cross_layer_edge_counts": edge_counts,
        "bidirectional_layer_pairs": bidirectional_pairs,
        "module_cycles": cycles,
        "role_observation": {
            "interfaces_contains_inward_ports": bool(
                cross_edges.get(("application", "interfaces"))
            ),
            "interfaces_contains_outward_delivery_adapters": bool(
                cross_edges.get(("interfaces", "application"))
            ),
            "interfaces_package_role_mixed": mixed_interfaces,
        },
        "minimum_cleanup_slice": (
            list(MINIMUM_PORT_DELIVERY_CLEANUP_SLICE)
            if mixed_interfaces
            else []
        ),
        "facts": {
            "native_source_mapping_verified": True,
            "all_modules_ast_parsed": True,
            "dynamic_imports_absent": not dynamic_modules,
            "module_cycle_detected": bool(cycles),
            "package_level_bidirectional_dependency_detected": bool(
                bidirectional_pairs
            ),
            "domain_inward_only": not any(
                source == "domain" for source, _target in cross_edges
            ),
            "application_infrastructure_separated": not bool(
                cross_edges.get(("application", "infrastructure"))
            ),
            "raw_source_embedded": False,
            "filesystem_io_performed": False,
            "runtime_import_execution_performed": False,
            "architecture_migration_complete": conforming,
        },
        "violations": violations,
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "layer_dependency_audit_hash")


def verify_exchange_terminal_layer_dependency_audit_v1(
    document: Any,
    module_sources: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        expected = evaluate_exchange_terminal_layer_dependency_audit_v1(
            module_sources
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "LAYERS",
    "MINIMUM_PORT_DELIVERY_CLEANUP_SLICE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS_BLOCKED",
    "STATUS_CONFORMING",
    "evaluate_exchange_terminal_layer_dependency_audit_v1",
    "verify_exchange_terminal_layer_dependency_audit_v1",
]
