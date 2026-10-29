"""Read package identity bound by the private bootstrap; never import a broker.

The bootstrap is the only production caller of the private installation hook.
This is an in-process trusted-code contract, not protection against arbitrary
Python execution. Renderer data and environment variables cannot install it.
Each load checks current manifest and complete related filesystem membership;
it is neither SDK compatibility evidence nor permission to connect or trade.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from threading import RLock

from . import terminal_broker_execution_plan as plan


SCHEMA = "hakimi-broker-package-load-v1"
LOADER_PATH = "components/terminal/exchange_terminal/services/terminal_broker_package_loader.py"
ADAPTER_ROOT = "components/terminal/exchange_terminal/adapters"
DESCRIPTORS = {
    "OFFICIAL_SIMULATION": ADAPTER_ROOT + "/futu-us-equity-simulate-v1.json",
    "LIVE_CANDIDATE": ADAPTER_ROOT + "/futu-us-equity-real-v1.json",
}
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_DESCRIPTOR_BYTES = 256 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_RELATED_BYTES = 64 * 1024 * 1024
MAX_RELATED_FILES = 2048
MAX_RELATED_ENTRIES = 4096
CONTRACT_FILES = frozenset({LOADER_PATH, "resources/app/terminal-bootstrap.py",
    "components/terminal/exchange_terminal/services/terminal_broker_execution_plan.py"})
_lock = RLock()
_anchor = None
_anchor_invalid = False


class PackageLoaderError(ValueError):
    def __init__(self, code, reason):
        self.code, self.reason = code, reason
        super().__init__(code + ":" + reason)


def _require(value, reason):
    if not value:
        raise PackageLoaderError("PACKAGE_CHANGED", reason)


def _same_path(left, right):
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _plain_path(path):
    """Check every existing ancestor before any traversal or open."""
    for part in (path, *path.parents):
        if os.path.lexists(part):
            info = part.lstat()
            _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                     "reparse_path_rejected")
    _require(_same_path(path.resolve(), path.absolute()), "physical_path_alias_rejected")


def _bound(root, relative):
    plan._path(relative)
    path = root.joinpath(*relative.split("/"))
    _plain_path(path)
    _require(path.is_relative_to(root), "package_path_escape")
    return path


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink


def _read(root, relative, limit=MAX_FILE_BYTES, *, signatures=None):
    path = _bound(root, relative)
    before = path.lstat()
    _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "regular_unaliased_file_required")
    _require(0 <= before.st_size <= limit, "file_size_exceeded")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        _require(_signature(before) == _signature(opened), "file_replaced_before_read")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    _plain_path(path)
    _require(len(data) <= limit and _signature(before) == _signature(after) == _signature(path.lstat())
             and len(data) == after.st_size, "file_changed_during_read")
    if signatures is not None:
        signature = _signature(after)
        _require(relative not in signatures or signatures[relative] == signature, "file_changed_between_reads")
        signatures[relative] = signature
    return data


def _manifest(raw):
    value = plan._json_document(raw, MAX_MANIFEST_BYTES)
    core = {key: item for key, item in value.items() if key != "bundle_id"}
    expected = sha256(json.dumps(core, ensure_ascii=False, allow_nan=False,
                                sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    _require(value.get("schema_version") == "hakimi-original-terminal-v1" and value.get("bundle_id") == expected,
             "manifest_identity_invalid")
    files = value.get("files")
    _require(type(files) is dict and 0 < len(files) <= 50000, "manifest_files_invalid")
    seen = set()
    for name, digest in files.items():
        plan._path(name); plan._hash(digest)
        _require(name.casefold() not in seen, "case_aliased_manifest_path")
        seen.add(name.casefold())
    return value


@dataclass(frozen=True)
class _PackageAnchor:
    root: str
    manifest_bytes: bytes
    directory_identities: tuple


def _install_bootstrap_anchor(root, manifest_bytes):
    """Private: called last by initialize after its same-verify/private-path checks."""
    global _anchor
    root = Path(root).absolute()
    with _lock:
        if _anchor_invalid:
            raise PackageLoaderError("BOOTSTRAP_ANCHOR_INVALID", "initialization_previously_failed")
        try:
            _plain_path(root)
            manifest = _manifest(manifest_bytes)
            _require(_read(root, "terminal-manifest.json", MAX_MANIFEST_BYTES) == manifest_bytes,
                     "manifest_changed_since_bootstrap_verification")
            fresh = _PackageAnchor(str(root), bytes(manifest_bytes), _directory_identities(root, manifest))
            if _anchor is not None and _anchor != fresh:
                raise PackageLoaderError("BOOTSTRAP_ANCHOR_INVALID", "package_rebinding_rejected")
            _anchor = fresh
        except PackageLoaderError:
            raise
        except (OSError, ValueError, TypeError) as error:
            raise PackageLoaderError("BOOTSTRAP_ANCHOR_INVALID", "invalid_verified_package") from error


def _invalidate_bootstrap_anchor():
    global _anchor_invalid
    with _lock:
        # Never turn a failed initialized package into unbound repository mode.
        _anchor_invalid = True


@dataclass(frozen=True)
class BrokerRuntimeLoad:
    status: str
    mode: str
    runtime_identity: plan.VerifiedRuntimeIdentity | None

    def as_dict(self):
        identity = self.runtime_identity.as_dict() if self.runtime_identity else None
        gaps = (["PACKAGE_NOT_ANCHORED"] if identity is None else
                (["SDK_NOT_PACKAGED"] if identity["sdk"] is None else []) +
                (["APPLICATION_ADAPTER_NOT_PACKAGED"] if identity["adapter"] is None else []))
        return {"schema_version": SCHEMA, "status": self.status, "mode": self.mode,
                "package": identity["package"] if identity else None,
                "sdk": identity["sdk"] if identity else None,
                "adapter": identity["adapter"] if identity else None,
                "missing_capabilities": gaps, "runtime_compatibility": "NOT_VERIFIED",
                "fresh_check_scope": "MANIFEST_SDK_ADAPTER_AND_LOADER_CONTRACT_FILES",
                "identity_match_only": True, "permissions": dict(plan.PERMISSIONS)}


def _subtree(root, relative, files):
    prefix = relative + "/"
    expected = {name for name in files if name.startswith(prefix)}
    expected_dirs = set()
    for name in expected:
        parts = name.split("/")
        for end in range(len(relative.split("/")), len(parts)):
            expected_dirs.add("/".join(parts[:end]))
    folder = _bound(root, relative)
    actual, directories, pending, entries = set(), set(), [folder] if folder.exists() else [], 0
    while pending:
        directory = pending.pop()
        _plain_path(directory)
        _require(directory.is_dir(), "related_directory_required")
        directories.add(directory.relative_to(root).as_posix())
        for child in directory.iterdir():
            entries += 1
            _require(entries <= MAX_RELATED_ENTRIES, "related_entry_limit_exceeded")
            _plain_path(child)
            info = child.lstat()
            if stat.S_ISDIR(info.st_mode):
                pending.append(child)
            else:
                _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "related_nonregular_or_aliased_file")
                actual.add(child.relative_to(root).as_posix())
    _require(actual == expected and directories == expected_dirs, "related_membership_changed:" + relative)
    return actual


def _related_files(root, manifest):
    files = manifest["files"]
    sdk_parent = plan.SDK_ROOT.rstrip("/")
    site = _bound(root, sdk_parent)
    expected = {name[len(plan.SDK_ROOT):].split("/")[0] for name in files if name.startswith(plan.SDK_ROOT)
                and (name[len(plan.SDK_ROOT):].split("/")[0].casefold() == "futu" or
                     name[len(plan.SDK_ROOT):].split("/")[0].casefold().startswith("futu_api-"))}
    wheels = manifest.get("dependency_wheels")
    _require(type(wheels) is list and len(wheels) <= 1000 and all(type(item) is dict for item in wheels),
             "dependency_inventory_invalid")
    declared = [item for item in wheels if item.get("name") == "futu-api"]
    _require(len(declared) <= 1, "ambiguous_sdk_dependency")
    allowed = set()
    if declared:
        version = declared[0].get("version")
        _require(type(version) is str and re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", version), "sdk_version_invalid")
        allowed = {"futu", "futu_api-" + version + ".dist-info"}
    _require(expected == allowed, "manifest_sdk_family_does_not_match_declared_version")
    actual = set()
    if site.exists():
        _require(site.is_dir(), "sdk_parent_not_directory")
        for index, child in enumerate(site.iterdir()):
            _require(index < MAX_RELATED_ENTRIES, "sdk_parent_entry_limit_exceeded")
            name = child.name.casefold()
            if name == "futu" or name.startswith("futu_api-"):
                _plain_path(child)
                actual.add(child.name)
    _require(actual == expected, "sdk_family_membership_changed")
    names = _subtree(root, ADAPTER_ROOT, files)
    for name in sorted(expected):
        _require(name == "futu" or name.endswith(".dist-info"), "sdk_family_name_invalid")
        names |= _subtree(root, sdk_parent + "/" + name, files)
    _require(len(names) <= MAX_RELATED_FILES, "related_file_limit_exceeded")
    return names


def _descriptor_sources(root, manifest, relative, *, signatures=None):
    raw = _read(root, relative, MAX_DESCRIPTOR_BYTES, signatures=signatures)
    _require(sha256(raw).hexdigest() == manifest["files"].get(relative), "adapter_descriptor_hash_changed")
    descriptor = plan._json_document(raw, MAX_DESCRIPTOR_BYTES)
    sources = descriptor.get("source_files")
    _require(type(sources) is dict and 0 < len(sources) <= 100, "adapter_source_inventory_invalid")
    for name in sources:
        plan._path(name)
        _require(name.startswith("components/terminal/exchange_terminal/") and name in manifest["files"],
                 "adapter_source_outside_manifest")
    return raw, set(sources)


def _directory_identities(root, manifest):
    names = _related_files(root, manifest) | CONTRACT_FILES
    for descriptor in DESCRIPTORS.values():
        if descriptor in manifest["files"]:
            _, sources = _descriptor_sources(root, manifest, descriptor)
            names |= sources
    directories = {""}
    for name in names:
        parts = name.split("/")
        directories.update("/".join(parts[:end]) for end in range(1, len(parts)))
    result = []
    for name in sorted(directories):
        path = _bound(root, name) if name else root
        _plain_path(path)
        info = path.lstat()
        _require(stat.S_ISDIR(info.st_mode), "related_directory_required")
        result.append((name, info.st_dev, info.st_ino))
    return tuple(result)


def _check_directories(root, identities):
    for name, device, inode in identities:
        path = _bound(root, name) if name else root
        _plain_path(path)
        info = path.lstat()
        _require(stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == (device, inode),
                 "anchored_directory_replaced:" + name)


def load_broker_runtime_identity(mode):
    """Fresh, bounded read from the startup anchor; never an SDK import or query."""
    if type(mode) is not str or mode not in DESCRIPTORS:
        raise PackageLoaderError("MODE_INVALID", "explicit_broker_mode_required")
    with _lock:
        if _anchor_invalid:
            raise PackageLoaderError("BOOTSTRAP_ANCHOR_INVALID", "initialization_failed")
        if _anchor is None:
            return BrokerRuntimeLoad("NOT_PACKAGED", mode, None)
        anchor = _anchor
        try:
            root = Path(anchor.root)
            _plain_path(root)
            _check_directories(root, anchor.directory_identities)
            signatures = {}
            raw = _read(root, "terminal-manifest.json", MAX_MANIFEST_BYTES, signatures=signatures)
            _require(raw == anchor.manifest_bytes, "manifest_changed_since_startup")
            manifest = _manifest(raw)
            names = _related_files(root, manifest)
            descriptor_path = DESCRIPTORS[mode]
            descriptor_raw = None
            if descriptor_path in manifest["files"]:
                descriptor_raw, sources = _descriptor_sources(root, manifest, descriptor_path, signatures=signatures)
                names |= sources
            # The bootstrap/loader and plan contract are related inputs too.
            names |= CONTRACT_FILES
            _require(len(names) <= MAX_RELATED_FILES, "related_file_limit_exceeded")
            observed, total = {}, 0
            for name in sorted(names):
                content = _read(root, name, signatures=signatures)
                total += len(content)
                _require(total <= MAX_RELATED_BYTES, "related_byte_limit_exceeded")
                observed[name] = sha256(content).hexdigest()
                _require(observed[name] == manifest["files"].get(name), "related_file_hash_changed:" + name)
            _require(_read(root, "terminal-manifest.json", MAX_MANIFEST_BYTES, signatures=signatures) == raw, "manifest_changed_during_load")
            _require(_related_files(root, manifest) <= names, "related_membership_changed_during_load")
            _check_directories(root, anchor.directory_identities)
            for name, signature in signatures.items():
                _require(_signature(_bound(root, name).lstat()) == signature, "file_changed_across_load:" + name)
            identity = plan.verify_runtime_identity(manifest_bytes=raw, expected_manifest_sha256=sha256(raw).hexdigest(),
                observed_file_sha256=observed, mode=mode, adapter_path=descriptor_path if descriptor_raw is not None else None,
                adapter_descriptor_bytes=descriptor_raw)
            return BrokerRuntimeLoad("PACKAGED_IDENTITY_MATCHED", mode, identity)
        except PackageLoaderError:
            raise
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise PackageLoaderError("PACKAGE_CHANGED", str(error)) from error
