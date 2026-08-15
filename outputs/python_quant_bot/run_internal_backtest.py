from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from exchange_terminal.services.portfolio_backtest_pack import (
    CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
    PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
    build_internal_backtest_bundle,
    build_internal_backtest_pack,
    verify_internal_backtest_bundle,
    verify_internal_backtest_pack,
)
from exchange_terminal.services.immutable_json_artifact import (
    json_artifact_bytes,
    publish_json_artifact_no_clobber,
)
from exchange_terminal.services.immutable_artifact_bundle import (
    DEFAULT_BUNDLE_MANIFEST_FILE,
    build_content_addressed_bundle_manifest,
    bundle_manifest_bytes,
    publish_immutable_artifact_bundle,
    read_bounded_artifact,
)
from exchange_terminal.services.portfolio_backtest_pack_pointer import (
    DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE,
    MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
    MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
    portfolio_backtest_bundle_manifest_bindings,
    portfolio_backtest_bundle_member_roles,
    portfolio_backtest_bundle_pointer_receipt_bindings,
    publish_portfolio_backtest_bundle_pointer,
    verify_persisted_portfolio_backtest_bundle_pointer,
)


PROJECT_ROOT = Path(__file__).resolve().parent
_CURRENT_BUNDLE_PACK_FILE = "pack.json"
_CURRENT_BUNDLE_NAME_PREFIX = "internal-portfolio-backtest-bundle"


def _scope() -> dict[str, bool]:
    return {
        "research_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps({**payload, **_scope()}, ensure_ascii=False, indent=2))


def _blocker(prefix: str, exc: BaseException) -> str:
    return f"{prefix}:{type(exc).__name__}"


def _external_output(report_dir: Path, raw_output: Path) -> tuple[Path | None, list[str]]:
    try:
        output = raw_output.resolve()
    except Exception as exc:
        return None, [_blocker("output_resolve_exception", exc)]
    try:
        output.relative_to(report_dir)
    except ValueError:
        pass
    else:
        return None, ["explicit_report_root_output_forbidden"]
    if output.name == DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE:
        return None, ["explicit_output_pointer_basename_forbidden"]
    return output, []


def _external_v4_export(report_dir: Path, output: Path, generated_at: int) -> int:
    try:
        pack = dict(
            build_internal_backtest_pack(
                report_dir,
                generated_at=generated_at,
                schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION,
            )
            or {}
        )
    except Exception as exc:
        _emit({
            "status": "BLOCK",
            "mode": "OFFLINE_EXPORT_LEGACY_V4",
            "error": "offline legacy v4 build raised",
            "build_blockers": [_blocker("pack_v4_build_exception", exc)],
            "output": str(output),
            "offline_export": True,
        })
        return 2
    try:
        verification = dict(verify_internal_backtest_pack(pack) or {})
    except Exception as exc:
        verification = {
            "status": "BLOCK",
            "blockers": [_blocker("pack_v4_verification_exception", exc)],
        }
    if (
        pack.get("schema_version") != PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION
        or verification.get("status") != "PASS"
    ):
        _emit({
            "status": "BLOCK",
            "mode": "OFFLINE_EXPORT_LEGACY_V4",
            "error": "offline legacy v4 verification blocked",
            "verification": str(verification.get("status") or "BLOCK"),
            "verification_blockers": list(verification.get("blockers") or []),
            "output": str(output),
            "offline_export": True,
        })
        return 2

    expected_raw = b""
    expected_sha256 = ""
    try:
        expected_raw = json_artifact_bytes(pack)
        expected_sha256 = hashlib.sha256(expected_raw).hexdigest()
        publication = dict(
            publish_json_artifact_no_clobber(
                output,
                pack,
                failure_blocker="offline_v4_pack_publication_failed",
            )
            or {}
        )
    except Exception as exc:
        publication = {
            "status": "BLOCK",
            "published": False,
            "blockers": [_blocker("offline_v4_pack_publication_exception", exc)],
        }
    persisted = (
        (
            publication.get("status") == "PUBLISHED"
            and publication.get("published") is True
            or publication.get("status") == "EXISTING_IDENTICAL"
            and publication.get("published") is False
        )
        and publication.get("path") == str(output)
        and publication.get("file_sha256") == expected_sha256
        and publication.get("byte_length") == len(expected_raw)
    )
    post_verification: dict[str, Any]
    if persisted:
        try:
            persisted_raw = read_bounded_artifact(
                output,
                byte_limit=MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
                size_limit_blocker="offline_v4_pack_size_limit_exceeded",
            )
            post_verification = dict(verify_internal_backtest_pack(pack) or {})
            persisted = (
                persisted_raw == expected_raw
                and pack.get("schema_version")
                == PORTFOLIO_INTERNAL_BACKTEST_PACK_V4_SCHEMA_VERSION
                and post_verification.get("status") == "PASS"
            )
        except Exception as exc:
            post_verification = {
                "status": "BLOCK",
                "blockers": [_blocker("offline_v4_post_publication_verification_exception", exc)],
            }
            persisted = False
    else:
        post_verification = {
            "status": "SKIPPED",
            "blockers": ["offline_v4_publication_receipt_invalid"],
        }
    candidate = pack.get("candidate") if isinstance(pack.get("candidate"), dict) else {}
    _emit({
        "status": pack.get("status") if persisted else "BLOCK",
        "mode": "OFFLINE_EXPORT_LEGACY_V4",
        "pack_schema_version": pack.get("schema_version"),
        "promotion_status": pack.get("promotion_status"),
        "candidate_hash": candidate.get("candidate_hash"),
        "pack_hash": pack.get("pack_hash"),
        "verification": verification.get("status"),
        "verification_blockers": list(verification.get("blockers") or []),
        "post_publication_verification": post_verification.get("status"),
        "post_publication_verification_blockers": list(
            post_verification.get("blockers") or []
        ),
        "blockers": list(pack.get("blockers") or []),
        "promotion_blockers": list(pack.get("promotion_blockers") or []),
        "output": str(output),
        "output_scope": "OFFLINE_EXPORT_LEGACY_V4",
        "offline_export": True,
        "artifact_publication": publication,
        "pointer_publication": {
            "status": "NOT_APPLICABLE",
            "published": False,
            "blockers": ["offline_export_never_updates_current_pointer"],
        },
    })
    succeeded = (
        persisted
        and pack.get("status") == "INTERNAL_BACKTEST_EVIDENCE_READY"
        and verification.get("status") == "PASS"
    )
    return 0 if succeeded else 2


def _current_v6_bundle(report_dir: Path, generated_at: int) -> int:
    try:
        build = dict(
            build_internal_backtest_bundle(report_dir, generated_at=generated_at) or {}
        )
        pack = dict(build.get("pack") or {})
        detached = list(build.get("detached_artifacts") or [])
    except Exception as exc:
        _emit({
            "status": "BLOCK",
            "mode": "CURRENT_REPORT_ROOT_V6_BUNDLE",
            "error": "current v6 bundle build raised",
            "build_blockers": [_blocker("bundle_v6_build_exception", exc)],
            "offline_export": False,
        })
        return 2
    try:
        verification = dict(verify_internal_backtest_bundle(pack, detached) or {})
    except Exception as exc:
        verification = {
            "status": "BLOCK",
            "artifact_contract_status": "BLOCK",
            "return_quality": {},
            "blockers": [_blocker("bundle_v6_verification_exception", exc)],
        }
    source_integrity_status = str(
        verification.get("return_quality_source_integrity_status") or "BLOCK"
    )
    numeric_claims_available = verification.get("numeric_claims_available") is True
    contract_ready = (
        pack.get("schema_version") == CURRENT_PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION
        and verification.get("artifact_contract_status") == "PASS"
    )
    semantic_ready = (
        contract_ready
        and verification.get("status") == "PASS"
        and source_integrity_status == "PASS"
        and numeric_claims_available
    )
    if not contract_ready:
        _emit({
            "status": "BLOCK",
            "mode": "CURRENT_REPORT_ROOT_V6_BUNDLE",
            "error": "current v6 bundle artifact contract blocked",
            "pack_schema_version": pack.get("schema_version"),
            "verification": str(verification.get("status") or "BLOCK"),
            "artifact_contract_status": str(
                verification.get("artifact_contract_status") or "BLOCK"
            ),
            "source_integrity_status": source_integrity_status,
            "numeric_claims_available": False,
            "verification_blockers": list(verification.get("blockers") or []),
            "blockers": list(pack.get("blockers") or []),
            "bundle_publication": {
                "status": "SKIPPED",
                "published": False,
                "blockers": ["bundle_artifact_contract_blocked"],
            },
            "pointer_publication": {
                "status": "SKIPPED",
                "published": False,
                "blockers": ["bundle_artifact_contract_blocked"],
            },
            "offline_export": False,
        })
        return 2

    material_blockers: list[str] = []
    try:
        pack_raw = json_artifact_bytes(pack)
        members: dict[str, bytes] = {_CURRENT_BUNDLE_PACK_FILE: pack_raw}
        detached_by_file: dict[str, dict[str, Any]] = {}
        for raw_item in detached:
            item = dict(raw_item or {}) if isinstance(raw_item, dict) else {}
            name = str(item.get("file") or "")
            raw = item.get("raw_bytes")
            if not name or name in members or not isinstance(raw, bytes):
                material_blockers.append("bundle_detached_artifact_material_invalid")
                continue
            members[name] = raw
            detached_by_file[name] = item
        roles = portfolio_backtest_bundle_member_roles(
            pack,
            pack_file=_CURRENT_BUNDLE_PACK_FILE,
        )
        bindings = portfolio_backtest_bundle_manifest_bindings(
            pack,
            pack_file=_CURRENT_BUNDLE_PACK_FILE,
        )
        if set(members) != set(roles) or len(detached_by_file) != 2:
            material_blockers.append("bundle_member_inventory_invalid")
        for name, item in detached_by_file.items():
            raw = members[name]
            if (
                item.get("byte_length") != len(raw)
                or item.get("sha256") != hashlib.sha256(raw).hexdigest()
                or item.get("role") != roles.get(name)
            ):
                material_blockers.append("bundle_detached_artifact_binding_invalid")
        expected_manifest = build_content_addressed_bundle_manifest(
            members,
            member_roles=roles,
            bindings=bindings,
            max_member_count=3,
            max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
            max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
        )
        expected_manifest_raw = bundle_manifest_bytes(expected_manifest)
    except Exception as exc:
        material_blockers.append(_blocker("bundle_material_exception", exc))
    if material_blockers:
        _emit({
            "status": "BLOCK",
            "mode": "CURRENT_REPORT_ROOT_V6_BUNDLE",
            "error": "current v6 bundle material invalid",
            "build_blockers": list(dict.fromkeys(material_blockers)),
            "bundle_publication": {
                "status": "SKIPPED",
                "published": False,
                "blockers": ["bundle_material_invalid"],
            },
            "pointer_publication": {
                "status": "SKIPPED",
                "published": False,
                "blockers": ["bundle_material_invalid"],
            },
            "offline_export": False,
        })
        return 2

    try:
        bundle_publication = dict(
            publish_immutable_artifact_bundle(
                report_dir,
                members,
                member_roles=roles,
                bindings=bindings,
                bundle_name_prefix=_CURRENT_BUNDLE_NAME_PREFIX,
                max_member_count=3,
                max_member_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_MEMBER_BYTES,
                max_total_bytes=MAX_PUBLIC_PORTFOLIO_BACKTEST_BUNDLE_TOTAL_BYTES,
                failure_blocker="backtest_bundle_publication_failed",
            )
            or {}
        )
    except Exception as exc:
        bundle_publication = {
            "status": "BLOCK",
            "published": False,
            "blockers": [_blocker("backtest_bundle_publication_exception", exc)],
        }
    expected_bundle_hash = str(expected_manifest.get("bundle_hash") or "")
    expected_manifest_file_sha256 = hashlib.sha256(expected_manifest_raw).hexdigest()
    expected_total_member_bytes = sum(len(raw) for raw in members.values())
    try:
        published_bundle_dir = Path(str(bundle_publication.get("bundle_dir") or "")).resolve()
        bundle_path_bound = (
            published_bundle_dir.parent == report_dir
            and published_bundle_dir.name
            == f"{_CURRENT_BUNDLE_NAME_PREFIX}-{expected_bundle_hash}"
            and bundle_publication.get("bundle_name") == published_bundle_dir.name
        )
    except Exception:
        bundle_path_bound = False
    bundle_persisted = (
        (
            bundle_publication.get("status") == "PUBLISHED"
            and bundle_publication.get("published") is True
            or bundle_publication.get("status") == "EXISTING_IDENTICAL"
            and bundle_publication.get("published") is False
        )
        and not list(bundle_publication.get("blockers") or [])
        and bundle_path_bound
        and bundle_publication.get("bundle_hash") == expected_bundle_hash
        and bundle_publication.get("manifest_file") == DEFAULT_BUNDLE_MANIFEST_FILE
        and bundle_publication.get("manifest_file_sha256")
        == expected_manifest_file_sha256
        and bundle_publication.get("member_count") == len(members)
        and bundle_publication.get("total_member_bytes")
        == expected_total_member_bytes
    )
    pack_file_sha256 = hashlib.sha256(pack_raw).hexdigest()
    expected_pointer_receipt = portfolio_backtest_bundle_pointer_receipt_bindings(
        bundle_dir_name=published_bundle_dir.name if bundle_path_bound else "",
        manifest_file_sha256=expected_manifest_file_sha256,
        bundle_hash=expected_bundle_hash,
        pack_file=_CURRENT_BUNDLE_PACK_FILE,
        pack_file_sha256=pack_file_sha256,
        pack=pack,
    )
    if bundle_persisted and semantic_ready:
        try:
            pointer_publication = dict(
                publish_portfolio_backtest_bundle_pointer(
                    report_dir,
                    str(bundle_publication.get("bundle_dir") or ""),
                    expected_bundle_hash=expected_bundle_hash,
                    expected_manifest_file_sha256=expected_manifest_file_sha256,
                    expected_pack_file_sha256=pack_file_sha256,
                    expected_pack_hash=str(pack.get("pack_hash") or ""),
                    expected_evidence_hash=str(pack.get("evidence_hash") or ""),
                    expected_pack_status=str(pack.get("status") or "UNKNOWN"),
                )
                or {}
            )
        except Exception as exc:
            pointer_publication = {
                "status": "BLOCK",
                "published": False,
                "blockers": [_blocker("bundle_pointer_publication_exception", exc)],
            }
    elif not bundle_persisted:
        pointer_publication = {
            "status": "SKIPPED",
            "published": False,
            "blockers": ["bundle_publication_blocked"],
        }
    else:
        pointer_publication = {
            "status": "SKIPPED",
            "published": False,
            "blockers": ["bundle_semantic_verification_blocked"],
        }
    pointer_satisfied = (
        pointer_publication.get("status") in {"PUBLISHED", "EXISTING_IDENTICAL"}
        and (
            pointer_publication.get("published") is True
            or pointer_publication.get("status") == "EXISTING_IDENTICAL"
        )
        and all(
            pointer_publication.get(field) == expected
            for field, expected in expected_pointer_receipt.items()
        )
    )
    if pointer_satisfied:
        try:
            persisted_pointer_verification = dict(
                verify_persisted_portfolio_backtest_bundle_pointer(
                    report_dir,
                    expected_bindings=expected_pointer_receipt,
                )
                or {}
            )
        except Exception as exc:
            persisted_pointer_verification = {
                "status": "BLOCK",
                "blockers": [_blocker("persisted_bundle_pointer_verification_exception", exc)],
            }
    else:
        persisted_pointer_verification = {
            "status": "SKIPPED",
            "blockers": ["bundle_pointer_receipt_invalid"],
        }
    pointer_persisted = (
        persisted_pointer_verification.get("status") == "PASS"
        and all(
            persisted_pointer_verification.get(field) == expected
            for field, expected in expected_pointer_receipt.items()
        )
    )
    succeeded = (
        pack.get("status") == "INTERNAL_BACKTEST_EVIDENCE_READY"
        and semantic_ready
        and bundle_persisted
        and pointer_satisfied
        and pointer_persisted
    )
    candidate = pack.get("candidate") if isinstance(pack.get("candidate"), dict) else {}
    _emit({
        "status": pack.get("status") if succeeded else "BLOCK",
        "mode": "CURRENT_REPORT_ROOT_V6_BUNDLE",
        "pack_schema_version": pack.get("schema_version"),
        "promotion_status": pack.get("promotion_status"),
        "candidate_hash": candidate.get("candidate_hash"),
        "pack_hash": pack.get("pack_hash"),
        "evidence_hash": pack.get("evidence_hash"),
        "verification": verification.get("status"),
        "artifact_contract_status": verification.get("artifact_contract_status"),
        "source_integrity_status": source_integrity_status,
        "numeric_claims_available": numeric_claims_available and semantic_ready,
        "verification_blockers": list(verification.get("blockers") or []),
        "blockers": list(pack.get("blockers") or []),
        "promotion_blockers": list(pack.get("promotion_blockers") or []),
        "forward_progress": pack.get("forward_progress"),
        "output": str(bundle_publication.get("bundle_dir") or ""),
        "output_scope": "CURRENT_REPORT_ROOT_V6_BUNDLE",
        "offline_export": False,
        "bundle_publication": bundle_publication,
        "pointer_publication": pointer_publication,
        "persisted_pointer_verification": persisted_pointer_verification,
    })
    return 0 if succeeded else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a read-only internal backtest evidence bundle for the active frozen portfolio "
            "candidate. This command performs no market fetch, parameter search, paper order, or live order."
        )
    )
    default_runtime = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
    parser.add_argument("--report-dir", type=Path, default=default_runtime / "reports")
    parser.add_argument(
        "--output",
        type=Path,
        help="External path for an explicit legacy-v4 offline export; report-root paths are forbidden.",
    )
    args = parser.parse_args()
    generated_at = int(time.time() * 1000)
    try:
        report_dir = args.report_dir.resolve()
    except Exception as exc:
        _emit({
            "status": "BLOCK",
            "error": "internal backtest report root planning failed",
            "planning_blockers": [_blocker("report_dir_resolve_exception", exc)],
        })
        return 2

    if args.output is not None:
        output, blockers = _external_output(report_dir, args.output)
        if blockers or output is None:
            _emit({
                "status": "BLOCK",
                "error": "explicit internal backtest output is not allowed",
                "planning_blockers": blockers or ["explicit_output_invalid"],
                "pointer_file": DEFAULT_PORTFOLIO_BACKTEST_PACK_POINTER_FILE,
                "offline_export": False,
            })
            return 2
        return _external_v4_export(report_dir, output, generated_at)
    return _current_v6_bundle(report_dir, generated_at)


if __name__ == "__main__":
    raise SystemExit(main())
