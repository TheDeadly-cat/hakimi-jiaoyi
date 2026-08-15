from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import stat
from typing import Any
import unicodedata
import uuid

from .strict_json_artifact import (
    StrictJsonArtifactError,
    StrictJsonDuplicateKeyError,
    StrictJsonRootTypeError,
    parse_strict_json_object,
)


IMMUTABLE_ARTIFACT_BUNDLE_MANIFEST_SCHEMA_VERSION = "immutable-artifact-bundle-manifest-v1"
DEFAULT_BUNDLE_MANIFEST_FILE = "manifest.json"
DEFAULT_MAX_BUNDLE_MANIFEST_BYTES = 256 * 1024
DEFAULT_MAX_BUNDLE_MEMBER_COUNT = 32
DEFAULT_MAX_BUNDLE_MEMBER_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_BUNDLE_TOTAL_BYTES = 64 * 1024 * 1024

_MANIFEST_STATUS = "IMMUTABLE_BUNDLE_READY"
_MANIFEST_FIELDS = {
    "schema_version",
    "status",
    "member_count",
    "total_member_bytes",
    "members",
    "bindings",
    "bundle_hash",
}
_MEMBER_FIELDS = {"role", "file", "size", "sha256"}
_WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"/\\|?*')
_WINDOWS_RESERVED_BASENAMES = {
    "aux",
    "clock$",
    "con",
    "conin$",
    "conout$",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
_WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


class ArtifactBundleError(ValueError):
    """A fail-closed bundle boundary error with a stable, path-free blocker."""

    def __init__(self, blocker: str) -> None:
        super().__init__(blocker)
        self.blocker = blocker


class ArtifactBundleByteLimitExceeded(ArtifactBundleError):
    pass


def _strict_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ArtifactBundleError("artifact_bundle_json_contract_invalid") from exc


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def bundle_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    """Return the one accepted durable JSON representation for a bundle manifest."""

    try:
        return (
            json.dumps(
                dict(manifest),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ArtifactBundleError("artifact_bundle_manifest_json_invalid") from exc


def windows_safe_basename_identity(value: Any) -> str | None:
    """Return the NFKC/casefold Windows identity for one exact safe basename.

    Non-canonical Unicode is rejected rather than silently rewritten. This makes
    manifest identity stable across case-insensitive Windows filesystems and
    case-sensitive test or archive filesystems.
    """

    if not isinstance(value, str) or not value:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    if normalized != value:
        return None
    if value in {".", ".."} or value != value.rstrip(" ."):
        return None
    if any(character in _WINDOWS_FORBIDDEN_CHARACTERS for character in value):
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    if "\x00" in value:
        return None
    windows_path = PureWindowsPath(value)
    if windows_path.is_absolute() or windows_path.drive or windows_path.root:
        return None
    if Path(value).name != value:
        return None
    # Windows component length is measured in UTF-16 code units.
    if len(value.encode("utf-16-le")) // 2 > 255:
        return None
    identity = normalized.casefold()
    device_name = identity.split(".", 1)[0]
    if device_name in _WINDOWS_RESERVED_BASENAMES:
        return None
    return identity


def validate_exact_basenames(
    names: Sequence[Any],
    *,
    reserved_names: Sequence[Any] = (),
) -> dict[str, Any]:
    blockers: list[str] = []
    identities: list[str] = []
    reserved_identities: set[str] = set()
    for reserved in reserved_names:
        identity = windows_safe_basename_identity(reserved)
        if identity is None:
            blockers.append("artifact_bundle_reserved_basename_invalid")
        else:
            reserved_identities.add(identity)
    for name in names:
        identity = windows_safe_basename_identity(name)
        if identity is None:
            blockers.append("artifact_bundle_member_basename_invalid")
            continue
        if identity in reserved_identities:
            blockers.append("artifact_bundle_member_basename_reserved")
        identities.append(identity)
    if len(identities) != len(set(identities)):
        blockers.append("artifact_bundle_member_basename_duplicate")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "identities": identities,
    }


def _path_is_link_or_reparse(path: Path, path_stat: os.stat_result | None = None) -> bool:
    try:
        current = path_stat if path_stat is not None else path.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(current.st_mode):
        return True
    if int(getattr(current, "st_file_attributes", 0)) & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            if is_junction():
                return True
        except OSError:
            return True
    return False


def _require_plain_directory(path: Path) -> os.stat_result:
    try:
        current = path.lstat()
    except OSError as exc:
        raise ArtifactBundleError("artifact_bundle_directory_unavailable") from exc
    if _path_is_link_or_reparse(path, current):
        raise ArtifactBundleError("artifact_bundle_directory_link_or_reparse_forbidden")
    if not stat.S_ISDIR(current.st_mode):
        raise ArtifactBundleError("artifact_bundle_directory_not_directory")
    return current


def read_bounded_artifact(
    path: Path | str,
    *,
    byte_limit: int,
    size_limit_blocker: str = "artifact_bundle_member_size_limit_exceeded",
) -> bytes:
    """Read at most ``byte_limit + 1`` bytes and reject links/reparse points.

    ``O_NOFOLLOW`` is used where the host exposes it. Windows reparse points are
    rejected through ``st_file_attributes`` and ``Path.is_junction`` where the
    running Python exposes them. Ancestor reparse points and hard-link aliases
    cannot be ruled out portably; callers must bind the returned exact bytes by
    size and digest.
    """

    if isinstance(byte_limit, bool) or not isinstance(byte_limit, int) or byte_limit < 0:
        raise ValueError("byte_limit must be a non-negative integer")
    artifact = Path(path)
    try:
        before = artifact.lstat()
    except OSError as exc:
        raise ArtifactBundleError("artifact_bundle_member_unavailable") from exc
    if _path_is_link_or_reparse(artifact, before):
        raise ArtifactBundleError("artifact_bundle_member_link_or_reparse_forbidden")
    if not stat.S_ISREG(before.st_mode):
        raise ArtifactBundleError("artifact_bundle_member_not_regular_file")

    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    descriptor: int | None = None
    try:
        descriptor = os.open(artifact, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ArtifactBundleError("artifact_bundle_member_not_regular_file")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ArtifactBundleError("artifact_bundle_member_identity_changed")
        remaining = byte_limit + 1
        chunks: list[bytes] = []
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after_open = os.fstat(descriptor)
    except ArtifactBundleError:
        raise
    except OSError as exc:
        raise ArtifactBundleError("artifact_bundle_member_unavailable") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)

    try:
        after_path = artifact.lstat()
    except OSError as exc:
        raise ArtifactBundleError("artifact_bundle_member_identity_changed") from exc
    if _path_is_link_or_reparse(artifact, after_path):
        raise ArtifactBundleError("artifact_bundle_member_link_or_reparse_forbidden")
    if (before.st_dev, before.st_ino) != (after_path.st_dev, after_path.st_ino):
        raise ArtifactBundleError("artifact_bundle_member_identity_changed")
    if (
        before.st_size != after_open.st_size
        or before.st_mtime_ns != after_open.st_mtime_ns
    ):
        raise ArtifactBundleError("artifact_bundle_member_changed_during_read")
    if len(raw) > byte_limit:
        raise ArtifactBundleByteLimitExceeded(size_limit_blocker)
    return raw


def _normalise_members(
    members: Mapping[str, bytes | bytearray | memoryview],
    *,
    member_roles: Mapping[str, str] | None,
    manifest_file: str,
) -> tuple[dict[str, bytes], dict[str, str]]:
    if not isinstance(members, Mapping) or not members:
        raise ArtifactBundleError("artifact_bundle_members_missing")
    names = list(members.keys())
    name_verification = validate_exact_basenames(names, reserved_names=(manifest_file,))
    if name_verification.get("status") != "PASS":
        raise ArtifactBundleError(str(name_verification["blockers"][0]))
    normalised: dict[str, bytes] = {}
    for name, raw in members.items():
        if not isinstance(raw, (bytes, bytearray, memoryview)):
            raise ArtifactBundleError("artifact_bundle_member_bytes_invalid")
        normalised[str(name)] = bytes(raw)

    if member_roles is None:
        roles = {name: "ARTIFACT" for name in normalised}
    else:
        if not isinstance(member_roles, Mapping) or set(member_roles) != set(normalised):
            raise ArtifactBundleError("artifact_bundle_member_role_inventory_invalid")
        roles = {}
        for name, raw_role in member_roles.items():
            if not isinstance(raw_role, str) or not raw_role or len(raw_role) > 128:
                raise ArtifactBundleError("artifact_bundle_member_role_invalid")
            if unicodedata.normalize("NFKC", raw_role) != raw_role:
                raise ArtifactBundleError("artifact_bundle_member_role_invalid")
            if any(ord(character) < 32 or ord(character) == 127 for character in raw_role):
                raise ArtifactBundleError("artifact_bundle_member_role_invalid")
            roles[str(name)] = raw_role
    return normalised, roles


def build_content_addressed_bundle_manifest(
    members: Mapping[str, bytes | bytearray | memoryview],
    *,
    member_roles: Mapping[str, str] | None = None,
    bindings: Mapping[str, Any] | None = None,
    manifest_file: str = DEFAULT_BUNDLE_MANIFEST_FILE,
    max_member_count: int = DEFAULT_MAX_BUNDLE_MEMBER_COUNT,
    max_member_bytes: int = DEFAULT_MAX_BUNDLE_MEMBER_BYTES,
    max_total_bytes: int = DEFAULT_MAX_BUNDLE_TOTAL_BYTES,
) -> dict[str, Any]:
    if windows_safe_basename_identity(manifest_file) is None:
        raise ArtifactBundleError("artifact_bundle_manifest_basename_invalid")
    for value, blocker in (
        (max_member_count, "artifact_bundle_member_count_limit_invalid"),
        (max_member_bytes, "artifact_bundle_member_size_limit_invalid"),
        (max_total_bytes, "artifact_bundle_total_size_limit_invalid"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ArtifactBundleError(blocker)
    normalised, roles = _normalise_members(
        members,
        member_roles=member_roles,
        manifest_file=manifest_file,
    )
    if len(normalised) > max_member_count:
        raise ArtifactBundleError("artifact_bundle_member_count_limit_exceeded")
    total_size = sum(len(raw) for raw in normalised.values())
    if any(len(raw) > max_member_bytes for raw in normalised.values()):
        raise ArtifactBundleByteLimitExceeded("artifact_bundle_member_size_limit_exceeded")
    if total_size > max_total_bytes:
        raise ArtifactBundleByteLimitExceeded("artifact_bundle_total_size_limit_exceeded")
    safe_bindings = dict(bindings or {}) if isinstance(bindings or {}, Mapping) else None
    if safe_bindings is None:
        raise ArtifactBundleError("artifact_bundle_bindings_invalid")
    # Validate bindings before any filesystem mutation and detach them from caller state.
    try:
        safe_bindings = json.loads(_canonical_json_bytes(safe_bindings).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ArtifactBundleError("artifact_bundle_bindings_invalid") from exc

    records = [
        {
            "role": roles[name],
            "file": name,
            "size": len(normalised[name]),
            "sha256": hashlib.sha256(normalised[name]).hexdigest(),
        }
        for name in sorted(normalised, key=lambda item: (windows_safe_basename_identity(item), item))
    ]
    content: dict[str, Any] = {
        "schema_version": IMMUTABLE_ARTIFACT_BUNDLE_MANIFEST_SCHEMA_VERSION,
        "status": _MANIFEST_STATUS,
        "member_count": len(records),
        "total_member_bytes": total_size,
        "members": records,
        "bindings": safe_bindings,
    }
    return {**content, "bundle_hash": _canonical_hash(content)}


def verify_content_addressed_bundle_manifest(
    manifest: Mapping[str, Any] | None,
    *,
    manifest_file: str = DEFAULT_BUNDLE_MANIFEST_FILE,
    max_member_count: int = DEFAULT_MAX_BUNDLE_MEMBER_COUNT,
    max_member_bytes: int = DEFAULT_MAX_BUNDLE_MEMBER_BYTES,
    max_total_bytes: int = DEFAULT_MAX_BUNDLE_TOTAL_BYTES,
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = dict(manifest or {}) if isinstance(manifest, Mapping) else {}
    if not isinstance(manifest, Mapping):
        blockers.append("artifact_bundle_manifest_not_object")
    if set(payload) != _MANIFEST_FIELDS:
        blockers.append("artifact_bundle_manifest_field_contract_invalid")
    if payload.get("schema_version") != IMMUTABLE_ARTIFACT_BUNDLE_MANIFEST_SCHEMA_VERSION:
        blockers.append("artifact_bundle_manifest_schema_invalid")
    if payload.get("status") != _MANIFEST_STATUS:
        blockers.append("artifact_bundle_manifest_status_invalid")
    if windows_safe_basename_identity(manifest_file) is None:
        blockers.append("artifact_bundle_manifest_basename_invalid")

    records_value = payload.get("members")
    records = list(records_value) if isinstance(records_value, list) else []
    if not isinstance(records_value, list) or not records:
        blockers.append("artifact_bundle_member_inventory_missing")
    if len(records) > max_member_count:
        blockers.append("artifact_bundle_member_count_limit_exceeded")
    names: list[str] = []
    declared_total = 0
    clean_records: list[dict[str, Any]] = []
    for raw_record in records:
        record = dict(raw_record or {}) if isinstance(raw_record, Mapping) else {}
        if set(record) != _MEMBER_FIELDS:
            blockers.append("artifact_bundle_member_field_contract_invalid")
        name = record.get("file")
        names.append(name if isinstance(name, str) else "")
        role = record.get("role")
        if (
            not isinstance(role, str)
            or not role
            or len(role) > 128
            or unicodedata.normalize("NFKC", role) != role
            or any(ord(character) < 32 or ord(character) == 127 for character in role)
        ):
            blockers.append("artifact_bundle_member_role_invalid")
        size = _strict_nonnegative_int(record.get("size"))
        if size is None:
            blockers.append("artifact_bundle_member_size_invalid")
            size = 0
        elif size > max_member_bytes:
            blockers.append("artifact_bundle_member_size_limit_exceeded")
        declared_total += size
        if not _is_sha256(record.get("sha256")):
            blockers.append("artifact_bundle_member_sha256_invalid")
        clean_records.append(record)

    name_verification = validate_exact_basenames(names, reserved_names=(manifest_file,))
    blockers.extend(name_verification.get("blockers") or [])
    sorted_records = sorted(
        clean_records,
        key=lambda item: (
            windows_safe_basename_identity(item.get("file")) or "",
            str(item.get("file") or ""),
        ),
    )
    if clean_records != sorted_records:
        blockers.append("artifact_bundle_member_inventory_not_canonical")
    member_count = _strict_nonnegative_int(payload.get("member_count"))
    if member_count != len(records):
        blockers.append("artifact_bundle_member_count_mismatch")
    total_member_bytes = _strict_nonnegative_int(payload.get("total_member_bytes"))
    if total_member_bytes != declared_total:
        blockers.append("artifact_bundle_total_size_mismatch")
    if declared_total > max_total_bytes:
        blockers.append("artifact_bundle_total_size_limit_exceeded")
    if not isinstance(payload.get("bindings"), Mapping):
        blockers.append("artifact_bundle_bindings_invalid")

    declared_hash = payload.get("bundle_hash")
    content = dict(payload)
    content.pop("bundle_hash", None)
    try:
        computed_hash = _canonical_hash(content)
    except ArtifactBundleError:
        computed_hash = ""
        blockers.append("artifact_bundle_manifest_json_invalid")
    if not _is_sha256(declared_hash) or declared_hash != computed_hash:
        blockers.append("artifact_bundle_hash_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "bundle_hash": str(declared_hash or ""),
        "member_count": len(records),
        "total_member_bytes": declared_total,
        "member_records": clean_records,
    }


def _json_object_without_duplicate_keys(raw: bytes) -> dict[str, Any]:
    try:
        return parse_strict_json_object(raw)
    except StrictJsonDuplicateKeyError as exc:
        raise ArtifactBundleError(
            "artifact_bundle_manifest_duplicate_json_key"
        ) from exc
    except StrictJsonRootTypeError as exc:
        raise ArtifactBundleError("artifact_bundle_manifest_not_object") from exc
    except StrictJsonArtifactError as exc:
        raise ArtifactBundleError("artifact_bundle_manifest_json_invalid") from exc


def _scan_flat_bundle_directory(
    bundle_dir: Path,
    *,
    max_member_count: int,
) -> tuple[list[str], list[str]]:
    names: list[str] = []
    blockers: list[str] = []
    try:
        with os.scandir(bundle_dir) as entries:
            for entry in entries:
                names.append(entry.name)
                if len(names) > max_member_count + 1:
                    blockers.append("artifact_bundle_inventory_count_limit_exceeded")
                    break
                try:
                    entry_stat = entry.stat(follow_symlinks=False)
                except OSError:
                    blockers.append("artifact_bundle_inventory_entry_unavailable")
                    continue
                entry_path = bundle_dir / entry.name
                if _path_is_link_or_reparse(entry_path, entry_stat):
                    blockers.append("artifact_bundle_inventory_link_or_reparse_forbidden")
                elif not stat.S_ISREG(entry_stat.st_mode):
                    blockers.append("artifact_bundle_inventory_not_flat")
    except OSError:
        blockers.append("artifact_bundle_inventory_unavailable")
    name_check = validate_exact_basenames(names)
    blockers.extend(name_check.get("blockers") or [])
    return names, list(dict.fromkeys(blockers))


def read_immutable_artifact_bundle(
    bundle_dir: Path | str,
    *,
    manifest_file: str = DEFAULT_BUNDLE_MANIFEST_FILE,
    expected_bundle_hash: str | None = None,
    expected_manifest_sha256: str | None = None,
    max_manifest_bytes: int = DEFAULT_MAX_BUNDLE_MANIFEST_BYTES,
    max_member_count: int = DEFAULT_MAX_BUNDLE_MEMBER_COUNT,
    max_member_bytes: int = DEFAULT_MAX_BUNDLE_MEMBER_BYTES,
    max_total_bytes: int = DEFAULT_MAX_BUNDLE_TOTAL_BYTES,
) -> dict[str, Any]:
    try:
        if windows_safe_basename_identity(manifest_file) is None:
            raise ArtifactBundleError("artifact_bundle_manifest_basename_invalid")
        directory = Path(bundle_dir)
        _require_plain_directory(directory)
        actual_names, inventory_blockers = _scan_flat_bundle_directory(
            directory,
            max_member_count=max_member_count,
        )
        if inventory_blockers:
            return {"status": "BLOCK", "blockers": inventory_blockers, "members": {}}
        manifest_raw = read_bounded_artifact(
            directory / manifest_file,
            byte_limit=max_manifest_bytes,
            size_limit_blocker="artifact_bundle_manifest_size_limit_exceeded",
        )
        manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
        if expected_manifest_sha256 is not None and manifest_sha256 != expected_manifest_sha256:
            raise ArtifactBundleError("artifact_bundle_manifest_sha256_mismatch")
        manifest = _json_object_without_duplicate_keys(manifest_raw)
        if bundle_manifest_bytes(manifest) != manifest_raw:
            raise ArtifactBundleError("artifact_bundle_manifest_serialization_noncanonical")
        verification = verify_content_addressed_bundle_manifest(
            manifest,
            manifest_file=manifest_file,
            max_member_count=max_member_count,
            max_member_bytes=max_member_bytes,
            max_total_bytes=max_total_bytes,
        )
        if verification.get("status") != "PASS":
            return {
                "status": "BLOCK",
                "blockers": list(verification.get("blockers") or []),
                "manifest": manifest,
                "manifest_file_sha256": manifest_sha256,
                "members": {},
            }
        bundle_hash = str(manifest.get("bundle_hash") or "")
        if expected_bundle_hash is not None and bundle_hash != expected_bundle_hash:
            raise ArtifactBundleError("artifact_bundle_expected_hash_mismatch")
        expected_names = [manifest_file] + [
            str(record.get("file") or "")
            for record in verification.get("member_records") or []
        ]
        if actual_names != expected_names and set(actual_names) != set(expected_names):
            raise ArtifactBundleError("artifact_bundle_inventory_mismatch")
        # The set comparison above is sufficient for ordering-independent filesystems;
        # exact spelling and case are preserved by the set and basename validation.
        if set(actual_names) != set(expected_names):
            raise ArtifactBundleError("artifact_bundle_inventory_mismatch")

        member_payloads: dict[str, bytes] = {}
        actual_total = 0
        for record in verification.get("member_records") or []:
            name = str(record.get("file") or "")
            raw = read_bounded_artifact(
                directory / name,
                byte_limit=max_member_bytes,
                size_limit_blocker="artifact_bundle_member_size_limit_exceeded",
            )
            actual_total += len(raw)
            if actual_total > max_total_bytes:
                raise ArtifactBundleByteLimitExceeded(
                    "artifact_bundle_total_size_limit_exceeded"
                )
            if len(raw) != record.get("size"):
                raise ArtifactBundleError("artifact_bundle_member_size_mismatch")
            if hashlib.sha256(raw).hexdigest() != record.get("sha256"):
                raise ArtifactBundleError("artifact_bundle_member_sha256_mismatch")
            member_payloads[name] = raw
        if actual_total != manifest.get("total_member_bytes"):
            raise ArtifactBundleError("artifact_bundle_total_size_mismatch")
        return {
            "status": "PASS",
            "blockers": [],
            "bundle_hash": bundle_hash,
            "manifest": manifest,
            "manifest_file_sha256": manifest_sha256,
            "member_count": len(member_payloads),
            "total_member_bytes": actual_total,
            "members": member_payloads,
        }
    except ArtifactBundleError as exc:
        return {"status": "BLOCK", "blockers": [exc.blocker], "members": {}}
    except Exception:
        return {
            "status": "BLOCK",
            "blockers": ["artifact_bundle_read_unexpected_error"],
            "members": {},
        }


def _write_fsynced_file(path: Path, raw: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory_best_effort(path: Path) -> str:
    """Best-effort directory fsync; Windows commonly does not expose it to Python."""

    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | int(getattr(os, "O_DIRECTORY", 0)))
        os.fsync(descriptor)
        return "PASS"
    except OSError:
        return "UNSUPPORTED"
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _entry_exists(path: Path) -> bool:
    return os.path.lexists(path)


def _publication_receipt(
    status: str,
    *,
    blockers: Sequence[str],
    published: bool,
    bundle_dir: Path,
    manifest: Mapping[str, Any],
    manifest_raw: bytes,
    manifest_file: str = DEFAULT_BUNDLE_MANIFEST_FILE,
    directory_fsync_status: str = "NOT_ATTEMPTED",
) -> dict[str, Any]:
    return {
        "status": status,
        "blockers": list(dict.fromkeys(str(item) for item in blockers if item)),
        "published": published,
        "bundle_dir": str(bundle_dir),
        "bundle_name": bundle_dir.name,
        "bundle_hash": str(manifest.get("bundle_hash") or ""),
        "manifest_file": manifest_file,
        "manifest_file_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "member_count": int(manifest.get("member_count") or 0),
        "total_member_bytes": int(manifest.get("total_member_bytes") or 0),
        "directory_fsync_status": directory_fsync_status,
    }


def publish_immutable_artifact_bundle(
    parent_dir: Path | str,
    members: Mapping[str, bytes | bytearray | memoryview],
    *,
    member_roles: Mapping[str, str] | None = None,
    bindings: Mapping[str, Any] | None = None,
    bundle_name_prefix: str = "immutable-artifact-bundle",
    manifest_file: str = DEFAULT_BUNDLE_MANIFEST_FILE,
    max_manifest_bytes: int = DEFAULT_MAX_BUNDLE_MANIFEST_BYTES,
    max_member_count: int = DEFAULT_MAX_BUNDLE_MEMBER_COUNT,
    max_member_bytes: int = DEFAULT_MAX_BUNDLE_MEMBER_BYTES,
    max_total_bytes: int = DEFAULT_MAX_BUNDLE_TOTAL_BYTES,
    failure_blocker: str = "artifact_bundle_publication_failed",
) -> dict[str, Any]:
    """Publish a flat content-addressed bundle without replacing valid content.

    The pending directory is a UUID sibling of the final directory, every member
    is fsynced, the manifest is written last, and the verified pending directory
    is renamed into place. Concurrent publishers using this helper cannot replace
    a completed non-empty destination. Python has no portable ``RENAME_NOREPLACE``
    for directories, so a hostile process racing an empty destination directory
    remains outside the portable guarantee; post-publication exact verification
    still fails closed.
    """

    empty_manifest: dict[str, Any] = {}
    empty_raw = b""
    final_bundle = Path(parent_dir) / "unplanned-bundle"
    try:
        if windows_safe_basename_identity(bundle_name_prefix) is None:
            raise ArtifactBundleError("artifact_bundle_name_prefix_invalid")
        if windows_safe_basename_identity(manifest_file) is None:
            raise ArtifactBundleError("artifact_bundle_manifest_basename_invalid")
        manifest = build_content_addressed_bundle_manifest(
            members,
            member_roles=member_roles,
            bindings=bindings,
            manifest_file=manifest_file,
            max_member_count=max_member_count,
            max_member_bytes=max_member_bytes,
            max_total_bytes=max_total_bytes,
        )
        manifest_raw = bundle_manifest_bytes(manifest)
        if len(manifest_raw) > max_manifest_bytes:
            raise ArtifactBundleByteLimitExceeded(
                "artifact_bundle_manifest_size_limit_exceeded"
            )
        normalised, _roles = _normalise_members(
            members,
            member_roles=member_roles,
            manifest_file=manifest_file,
        )
        raw_parent = Path(parent_dir)
        if _entry_exists(raw_parent) and _path_is_link_or_reparse(raw_parent):
            raise ArtifactBundleError("artifact_bundle_parent_link_or_reparse_forbidden")
        raw_parent.mkdir(parents=True, exist_ok=True)
        parent = raw_parent.resolve()
        _require_plain_directory(parent)
        final_name = f"{bundle_name_prefix}-{manifest['bundle_hash']}"
        if windows_safe_basename_identity(final_name) is None:
            raise ArtifactBundleError("artifact_bundle_final_basename_invalid")
        final_bundle = parent / final_name
    except ArtifactBundleError as exc:
        return _publication_receipt(
            "BLOCK",
            blockers=[exc.blocker],
            published=False,
            bundle_dir=final_bundle,
            manifest=locals().get("manifest", empty_manifest),
            manifest_raw=locals().get("manifest_raw", empty_raw),
            manifest_file=manifest_file,
        )
    except Exception:
        return _publication_receipt(
            "BLOCK",
            blockers=[failure_blocker],
            published=False,
            bundle_dir=final_bundle,
            manifest=locals().get("manifest", empty_manifest),
            manifest_raw=locals().get("manifest_raw", empty_raw),
            manifest_file=manifest_file,
        )

    def existing_receipt() -> dict[str, Any]:
        existing = read_immutable_artifact_bundle(
            final_bundle,
            manifest_file=manifest_file,
            expected_bundle_hash=str(manifest["bundle_hash"]),
            expected_manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            max_manifest_bytes=max_manifest_bytes,
            max_member_count=max_member_count,
            max_member_bytes=max_member_bytes,
            max_total_bytes=max_total_bytes,
        )
        identical = (
            existing.get("status") == "PASS"
            and existing.get("manifest") == manifest
            and existing.get("members") == normalised
        )
        return _publication_receipt(
            "EXISTING_IDENTICAL" if identical else "BLOCK",
            blockers=[] if identical else [f"{failure_blocker}:target_conflict"],
            published=False,
            bundle_dir=final_bundle,
            manifest=manifest,
            manifest_raw=manifest_raw,
            manifest_file=manifest_file,
        )

    if _entry_exists(final_bundle):
        return existing_receipt()

    pending = parent / f".pending-{uuid.uuid4().hex}"
    result: dict[str, Any] | None = None
    renamed = False
    cleanup_failed = False
    try:
        pending.mkdir(exist_ok=False)
        for record in manifest["members"]:
            name = str(record["file"])
            _write_fsynced_file(pending / name, normalised[name])
        # Manifest is deliberately the final file written into the pending tree.
        _write_fsynced_file(pending / manifest_file, manifest_raw)
        _fsync_directory_best_effort(pending)
        staged = read_immutable_artifact_bundle(
            pending,
            manifest_file=manifest_file,
            expected_bundle_hash=str(manifest["bundle_hash"]),
            expected_manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            max_manifest_bytes=max_manifest_bytes,
            max_member_count=max_member_count,
            max_member_bytes=max_member_bytes,
            max_total_bytes=max_total_bytes,
        )
        if staged.get("status") != "PASS" or staged.get("members") != normalised:
            result = _publication_receipt(
                "BLOCK",
                blockers=["artifact_bundle_staged_verification_blocked"],
                published=False,
                bundle_dir=final_bundle,
                manifest=manifest,
                manifest_raw=manifest_raw,
                manifest_file=manifest_file,
            )
        else:
            try:
                pending.rename(final_bundle)
                renamed = True
            except OSError:
                if _entry_exists(final_bundle):
                    result = existing_receipt()
                else:
                    result = _publication_receipt(
                        "BLOCK",
                        blockers=["artifact_bundle_atomic_rename_failed"],
                        published=False,
                        bundle_dir=final_bundle,
                        manifest=manifest,
                        manifest_raw=manifest_raw,
                        manifest_file=manifest_file,
                    )
            if renamed:
                directory_fsync_status = _fsync_directory_best_effort(parent)
                persisted = read_immutable_artifact_bundle(
                    final_bundle,
                    manifest_file=manifest_file,
                    expected_bundle_hash=str(manifest["bundle_hash"]),
                    expected_manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
                    max_manifest_bytes=max_manifest_bytes,
                    max_member_count=max_member_count,
                    max_member_bytes=max_member_bytes,
                    max_total_bytes=max_total_bytes,
                )
                if persisted.get("status") != "PASS" or persisted.get("members") != normalised:
                    result = _publication_receipt(
                        "BLOCK",
                        blockers=["artifact_bundle_post_publish_verification_blocked"],
                        published=False,
                        bundle_dir=final_bundle,
                        manifest=manifest,
                        manifest_raw=manifest_raw,
                        manifest_file=manifest_file,
                        directory_fsync_status=directory_fsync_status,
                    )
                else:
                    result = _publication_receipt(
                        "PUBLISHED",
                        blockers=[],
                        published=True,
                        bundle_dir=final_bundle,
                        manifest=manifest,
                        manifest_raw=manifest_raw,
                        manifest_file=manifest_file,
                        directory_fsync_status=directory_fsync_status,
                    )
    except Exception:
        result = _publication_receipt(
            "BLOCK",
            blockers=[failure_blocker],
            published=False,
            bundle_dir=final_bundle,
            manifest=manifest,
            manifest_raw=manifest_raw,
            manifest_file=manifest_file,
        )
    finally:
        if _entry_exists(pending):
            try:
                shutil.rmtree(pending)
            except OSError:
                cleanup_failed = True

    if cleanup_failed:
        return _publication_receipt(
            "BLOCK",
            blockers=["artifact_bundle_temporary_cleanup_failed"],
            published=False,
            bundle_dir=final_bundle,
            manifest=manifest,
            manifest_raw=manifest_raw,
            manifest_file=manifest_file,
        )
    return result or _publication_receipt(
        "BLOCK",
        blockers=[failure_blocker],
        published=False,
        bundle_dir=final_bundle,
        manifest=manifest,
        manifest_raw=manifest_raw,
        manifest_file=manifest_file,
    )
