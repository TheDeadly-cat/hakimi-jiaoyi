"""One-shot, private-worker loader for manifest-verified protobuf classes.

No SDK top-level import, connection, context, thread, subprocess or credential
lookup is provided. The worker/bootstrap supplies the trusted runtime identity
and expected manifest hash; this is not a renderer/HTTP API. The application
code invoking this module is trusted by that launcher. Only loaded local byte
identity is established, never broker compatibility, authorization or production
transport availability. An import failure taints this worker: start a new worker
instead of deleting or rebinding pre-existing modules/descriptors.
"""
import ast
from dataclasses import dataclass
from hashlib import sha256
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from threading import RLock
from types import MappingProxyType, ModuleType

from ..services import terminal_broker_execution_plan as contract
from ..services.terminal_broker_wire_profile import PINNED_SDK_VERSION, PINNED_WHEEL_SHA256


SCHEMA = "hakimi-verified-futu-protobuf-v1"
PROTOBUF_VERSION = "7.35.1"
PROTOBUF_WHEEL_SHA256 = "230a75ddfc2de4806e56696ce9640c1cdfdb6543b7cfce98d42a4c0a0e7bdb87"
RUNTIME = "runtime/python"
SITE = RUNTIME + "/Lib/site-packages/"
PB_ROOT = SITE + "futu/common/pb/"
PROTO_NAMES = MappingProxyType({1001: "InitConnect", 1002: "GetGlobalState", 2001: "Trd_GetAccList",
    2101: "Trd_GetFunds", 2102: "Trd_GetPositionList", 3202: "Qot_GetStaticInfo",
    3203: "Qot_GetSecuritySnapshot", 2202: "Trd_PlaceOrder", 2201: "Trd_GetOrderList",
    2205: "Trd_ModifyOrder", 2225: "Trd_GetOrderFee"})
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_MEMBERS = 4096
_TOKEN = object()
_lock = RLock()
_attempted = False


class ProtobufLoaderError(ValueError):
    def __init__(self, code, detail=""):
        self.code, self.detail = code, detail
        super().__init__(code + (":" + detail if detail else ""))


def _require(value, code, detail=""):
    if not value:
        raise ProtobufLoaderError(code, detail)


def _private_process():
    _require(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.ignore_environment == 1
             and sys.flags.dont_write_bytecode == 1 and sys.dont_write_bytecode is True,
             "PRIVATE_ISOLATED_WORKER_REQUIRED")
    _require(not any(key.startswith(("PROTOCOL_BUFFERS_", "PROTOBUF_")) for key in os.environ),
             "PROTOBUF_ENVIRONMENT_OVERRIDE_REJECTED")


def _cold_modules(modules):
    for name in modules:
        _require(not (name == "futu" or name.startswith("futu.") or name == "google"
                 or name.startswith("google.") or name.rsplit(".", 1)[-1].endswith("_pb2")
                 or name.startswith("_hakimi_verified_futu_pb_")), "MODULE_CACHE_NOT_COLD", name)


def _manifest(data, expected, runtime_identity):
    _require(type(runtime_identity) is contract.VerifiedRuntimeIdentity, "TRUSTED_RUNTIME_IDENTITY_REQUIRED")
    runtime = runtime_identity.as_dict()
    contract._hash(expected)
    _require(type(data) is bytes and sha256(data).hexdigest() == expected
             and runtime["package"]["manifest_sha256"] == expected, "MANIFEST_IDENTITY_MISMATCH")
    manifest = contract._json_document(data, 8 * 1024 * 1024)
    core = {key: value for key, value in manifest.items() if key != "bundle_id"}
    bundle = sha256(json.dumps(core, ensure_ascii=False, allow_nan=False,
                              sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    _require(manifest.get("schema_version") == "hakimi-original-terminal-v1"
             and manifest.get("bundle_id") == bundle == runtime["package"]["bundle_id"], "PACKAGE_IDENTITY_MISMATCH")
    files = manifest.get("files")
    _require(type(files) is dict and 0 < len(files) <= 50000, "MANIFEST_FILES_INVALID")
    names = set()
    for name, digest in files.items():
        contract._path(name); contract._hash(digest)
        _require(name.casefold() not in names, "MANIFEST_PATH_ALIAS")
        names.add(name.casefold())
    wheels = manifest.get("dependency_wheels")
    _require(type(wheels) is list and len(wheels) <= 1000 and all(type(row) is dict for row in wheels),
             "DEPENDENCY_DECLARATIONS_INVALID")
    for name, version, digest in (("futu-api", PINNED_SDK_VERSION, PINNED_WHEEL_SHA256),
                                  ("protobuf", PROTOBUF_VERSION, PROTOBUF_WHEEL_SHA256)):
        rows = [row for row in wheels if row.get("name") == name]
        _require(len(rows) == 1 and rows[0].get("version") == version and rows[0].get("sha256") == digest,
                 "PINNED_DEPENDENCY_REQUIRED", name)
    sdk = runtime["sdk"]
    _require(type(sdk) is dict and sdk.get("name") == "futu-api" and sdk.get("version") == PINNED_SDK_VERSION
             and sdk.get("wheel_sha256") == PINNED_WHEEL_SHA256, "PINNED_RUNTIME_SDK_REQUIRED")
    sdk_files = {name: digest for name, digest in files.items() if name.startswith(
        (SITE + "futu/", SITE + "futu_api-" + PINNED_SDK_VERSION + ".dist-info/"))}
    _require(sdk["installed_files_sha256"] == contract.digest(sdk_files)
             and sdk["installed_file_count"] == len(sdk_files), "RUNTIME_SDK_INVENTORY_MISMATCH")
    for family, allowed in (("protobuf-", "protobuf-" + PROTOBUF_VERSION + ".dist-info"),
                            ("futu_api-", "futu_api-" + PINNED_SDK_VERSION + ".dist-info")):
        found = {name[len(SITE):].split("/")[0] for name in files
                 if name.startswith(SITE + family) and ".dist-info/" in name}
        _require(found == {allowed}, "DEPENDENCY_METADATA_AMBIGUOUS", family)
    _require(SITE + "google/protobuf/__init__.py" in files and
             SITE + "protobuf-" + PROTOBUF_VERSION + ".dist-info/METADATA" in files, "PROTOBUF_INVENTORY_MISSING")
    return manifest, runtime


def _pb_source(data, name):
    _require(type(data) is bytes and len(data) <= 4 * 1024 * 1024
             and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*_pb2", name), "GENERATED_SOURCE_INVALID")
    tree = ast.parse(data, filename=name + ".py")
    dependencies, descriptors = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.endswith("_pb2") and "." not in alias.name:
                    dependencies.add(alias.name)
                else:
                    _require(alias.name.startswith("google.protobuf"), "GENERATED_IMPORT_OUTSIDE_PROTOBUF", alias.name)
        elif isinstance(node, ast.ImportFrom):
            _require(node.level == 0 and node.module and node.module.startswith("google.protobuf"),
                     "GENERATED_IMPORT_OUTSIDE_PROTOBUF", str(node.module))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "AddSerializedFile":
            _require(len(node.args) == 1, "DESCRIPTOR_LITERAL_REQUIRED")
            descriptors.append(ast.literal_eval(node.args[0]))
    _require(len(descriptors) == 1 and type(descriptors[0]) is bytes and descriptors[0], "DESCRIPTOR_LITERAL_REQUIRED")
    return tuple(sorted(dependencies)), descriptors[0]


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink


def _plain(path):
    for item in (path, *path.parents):
        if os.path.lexists(item):
            info = item.lstat()
            _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                     "REPARSE_PATH_REJECTED")
    _require(os.path.normcase(str(path.resolve())) == os.path.normcase(str(path.absolute())), "PHYSICAL_PATH_ALIAS")


def _initial_manifest(path):
    _plain(path)
    before = path.lstat()
    limit = 8 * 1024 * 1024
    _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= limit,
             "REGULAR_BOUNDED_MANIFEST_REQUIRED")
    with path.open("rb") as stream:
        _require(_signature(os.fstat(stream.fileno())) == _signature(before), "MANIFEST_REPLACED_BEFORE_READ")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    _require(_signature(before) == _signature(after) == _signature(path.lstat()) and len(data) == after.st_size,
             "MANIFEST_CHANGED_DURING_READ")
    return data


class _Files:
    def __init__(self, root, manifest_bytes, manifest):
        self.root, self.manifest_bytes, self.manifest = root, manifest_bytes, manifest
        self.signatures, self.directories, self.identities, self.total = {}, {}, {}, 0
        self.memberships = {}

    def path(self, relative):
        contract._path(relative)
        path = self.root.joinpath(*relative.split("/"))
        _plain(path)
        for directory in (self.root, *path.parents):
            if directory == self.root or directory.is_relative_to(self.root):
                info = directory.stat()
                identity = (info.st_dev, info.st_ino)
                _require(directory not in self.directories or self.directories[directory] == identity, "DIRECTORY_CHANGED")
                self.directories[directory] = identity
        return path

    def read(self, relative):
        expected = sha256(self.manifest_bytes).hexdigest() if relative == "terminal-manifest.json" else self.manifest["files"].get(relative)
        _require(expected is not None, "UNMANIFESTED_IMPORT", relative)
        path = self.path(relative)
        before = path.lstat()
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= MAX_FILE,
                 "REGULAR_BOUNDED_FILE_REQUIRED", relative)
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            _require(_signature(before) == _signature(opened), "FILE_REPLACED_BEFORE_READ")
            data = stream.read(MAX_FILE + 1)
            after = os.fstat(stream.fileno())
        signature = _signature(after)
        _require(_signature(before) == signature == _signature(path.lstat()) and len(data) == after.st_size,
                 "FILE_CHANGED_DURING_READ", relative)
        _require(relative not in self.signatures or self.signatures[relative] == signature,
                 "FILE_CHANGED_DURING_LOAD", relative)
        _require(sha256(data).hexdigest() == expected, "FILE_HASH_MISMATCH", relative)
        if relative not in self.signatures:
            self.total += len(data)
            _require(self.total <= MAX_TOTAL and len(self.signatures) < MAX_MEMBERS, "LOADER_RESOURCE_LIMIT")
        self.signatures[relative] = signature
        self.identities[relative] = {"sha256": expected, "bytes": len(data)}
        return data

    def members(self, prefix):
        directory = self.path(prefix.rstrip("/"))
        expected = {name for name in self.manifest["files"] if name.startswith(prefix)}
        actual, todo, count = set(), [directory], 0
        while todo:
            current = todo.pop()
            for entry in current.iterdir():
                count += 1
                _require(count <= MAX_MEMBERS, "LOADER_MEMBERSHIP_LIMIT")
                relative = entry.relative_to(self.root).as_posix()
                self.path(relative)
                if entry.is_dir():
                    todo.append(entry)
                else:
                    actual.add(relative)
        _require(actual == expected, "RELATED_MEMBERSHIP_CHANGED", prefix)
        self.memberships[prefix] = expected

    def stable(self):
        for directory, identity in tuple(self.directories.items()):
            _plain(directory)
            info = directory.stat()
            _require((info.st_dev, info.st_ino) == identity, "DIRECTORY_CHANGED")
        for relative, signature in tuple(self.signatures.items()):
            path = self.path(relative)
            _require(_signature(path.lstat()) == signature, "FILE_CHANGED_DURING_LOAD", relative)
        for prefix in tuple(self.memberships):
            self.members(prefix)


class _Source(importlib.abc.Loader):
    def __init__(self, owner, relative):
        self.owner, self.relative = owner, relative

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = self.owner.files.read(self.relative)
        origin = str(self.owner.files.root / self.relative)
        exec(compile(source, origin, "exec", dont_inherit=True), module.__dict__)
        self.owner.loaded[module.__name__] = module
        self.owner.origins[module.__name__] = origin


class _Extension(importlib.abc.Loader):
    def __init__(self, owner, name, relative):
        self.owner, self.relative = owner, relative
        self.delegate = importlib.machinery.ExtensionFileLoader(name, str(owner.files.root / relative))

    def create_module(self, spec):
        self.owner.files.read(self.relative)
        module = self.delegate.create_module(spec)
        self.owner.files.read(self.relative)
        return module

    def exec_module(self, module):
        self.delegate.exec_module(module)
        self.owner.files.read(self.relative)
        self.owner.loaded[module.__name__] = module
        self.owner.origins[module.__name__] = str(self.owner.files.root / self.relative)


class _Finder(importlib.abc.MetaPathFinder):
    def __init__(self, files, pb):
        self.files, self.pb, self.loaded, self.origins = files, pb, {}, {}

    def find_spec(self, fullname, path=None, target=None):
        _require(all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) for part in fullname.split(".")), "IMPORT_NAME_INVALID")
        _require(not (fullname == "futu" or fullname.startswith("futu.")), "SDK_IMPORT_FORBIDDEN")
        for importer in (importlib.machinery.BuiltinImporter, importlib.machinery.FrozenImporter):
            found = importer.find_spec(fullname)
            if found is not None:
                return found
        if fullname in self.pb:
            candidates = [PB_ROOT + fullname + ".py"]
        elif fullname in ("google", "google._upb"):
            spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = [str(self.files.root / (SITE + fullname.replace(".", "/")))]
            return spec
        elif fullname == "google.protobuf" or fullname.startswith(("google.protobuf.", "google._upb.")):
            stem = SITE + fullname.replace(".", "/")
            candidates = [stem + "/__init__.py", stem + ".py"] + [stem + suffix for suffix in importlib.machinery.EXTENSION_SUFFIXES]
        else:
            _require(not (fullname.startswith("google.") or fullname.rsplit(".", 1)[-1].endswith("_pb2")), "PROTOBUF_IMPORT_OUTSIDE_CLOSURE")
            stem = RUNTIME + "/Lib/" + fullname.replace(".", "/")
            candidates = [stem + "/__init__.py", stem + ".py"]
            if "." not in fullname:
                candidates += [RUNTIME + "/DLLs/" + fullname + suffix for suffix in importlib.machinery.EXTENSION_SUFFIXES]
                candidates += [RUNTIME + "/" + fullname + suffix for suffix in importlib.machinery.EXTENSION_SUFFIXES]
        available = [name for name in candidates if name in self.files.manifest["files"]]
        if not available:
            # Never fall through to another finder/global sys.path. Optional
            # protobuf backend imports can handle this normal ImportError.
            raise ModuleNotFoundError("verified worker import unavailable: " + fullname, name=fullname)
        _require(len(available) == 1, "AMBIGUOUS_MANIFEST_MODULE", fullname)
        relative = available[0]
        loader = _Source(self, relative) if relative.endswith(".py") else _Extension(self, fullname, relative)
        return importlib.util.spec_from_file_location(fullname, self.files.root / relative, loader=loader,
            submodule_search_locations=[str((self.files.root / relative).parent)] if relative.endswith("/__init__.py") else None)


@dataclass(frozen=True, init=False, slots=True)
class VerifiedProtobufBindings:
    request_classes: object
    response_classes: object
    _data: bytes
    _verify: object

    def __init__(self, requests, responses, data, verify, token):
        _require(token is _TOKEN, "PROTOBUF_PRIVATE_FACTORY_REQUIRED")
        object.__setattr__(self, "request_classes", MappingProxyType(dict(requests)))
        object.__setattr__(self, "response_classes", MappingProxyType(dict(responses)))
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_verify", verify)

    def as_dict(self):
        return json.loads(self._data)

    def verify_current(self):
        self._verify()
        return self.as_dict()


def _load_verified_protobuf(*, package_root, expected_manifest_sha256, runtime_identity):
    """Explicit trusted-worker call, once per fresh -I -S -B private process.

    The guard remains installed for this dedicated worker's lifetime. It never
    deletes/replaces pre-existing protobuf caches; a failed load requires a new
    worker. Application launcher source identity is a separate trust boundary.
    """
    global _attempted
    _private_process()  # Reject ordinary host/repository calls before file IO.
    _require(type(runtime_identity) is contract.VerifiedRuntimeIdentity, "TRUSTED_RUNTIME_IDENTITY_REQUIRED")
    with _lock:
        _require(not _attempted, "NEW_PRIVATE_WORKER_REQUIRED")
        _cold_modules(sys.modules)
        root = Path(package_root).absolute()
        _plain(root)
        root_info = root.stat()
        _require(stat.S_ISDIR(root_info.st_mode), "PACKAGE_DIRECTORY_REQUIRED")
        root_identity = (root_info.st_dev, root_info.st_ino)
        runtime_root = root / RUNTIME
        _require(os.path.normcase(str(Path(sys.executable).absolute())) == os.path.normcase(str(runtime_root / "python.exe")),
                 "PRIVATE_INTERPRETER_PATH_MISMATCH")
        _plain(Path(sys.executable))
        for entry in sys.path:
            _require(type(entry) is str and bool(entry) and Path(entry).is_absolute()
                     and (Path(entry) == root or Path(entry).is_relative_to(root)), "GLOBAL_IMPORT_PATH_REJECTED")
        path = root / "terminal-manifest.json"
        manifest_bytes = _initial_manifest(path)
        manifest, runtime = _manifest(manifest_bytes, expected_manifest_sha256, runtime_identity)
        files = _Files(root, manifest_bytes, manifest)
        files.directories[root] = root_identity
        files.read("terminal-manifest.json")
        for relative in (RUNTIME + "/python.exe", RUNTIME + "/python3.dll",
                         RUNTIME + "/python" + str(sys.version_info.major) + str(sys.version_info.minor) + ".dll"):
            files.read(relative)
        for relative in manifest["files"]:
            if relative.startswith(RUNTIME + "/vcruntime") and relative.endswith(".dll"):
                files.read(relative)
        for prefix in (PB_ROOT, SITE + "google/protobuf/", SITE + "google/_upb/",
                       SITE + "protobuf-" + PROTOBUF_VERSION + ".dist-info/"):
            files.members(prefix)
        for relative in manifest["files"]:
            if relative.startswith((SITE + "google/protobuf/", SITE + "google/_upb/",
                                    SITE + "protobuf-" + PROTOBUF_VERSION + ".dist-info/")):
                files.read(relative)
        # Verify already imported private-stdlib containers. Parent application
        # source injection, if any, is an explicit launcher/probe boundary; it
        # cannot supply protobuf, SDK or pb2 cached modules (checked above).
        for module in tuple(sys.modules.values()):
            origin = getattr(module, "__file__", None)
            if type(origin) is str and Path(origin).is_relative_to(runtime_root):
                files.read(Path(origin).relative_to(root).as_posix())
                cached = getattr(module, "__cached__", None)
                if type(cached) is str and Path(cached).exists():
                    _require(Path(cached).is_relative_to(root), "PRELOADED_BYTECODE_OUTSIDE_PACKAGE")
                    files.read(Path(cached).relative_to(root).as_posix())
        pending = [name + "_pb2" for name in PROTO_NAMES.values()]
        pb, descriptors = {}, {}
        while pending:
            name = pending.pop()
            if name in pb:
                continue
            _require(len(pb) < 512, "GENERATED_CLOSURE_TOO_LARGE")
            relative = PB_ROOT + name + ".py"
            dependencies, descriptor = _pb_source(files.read(relative), name)
            pb[name], descriptors[name] = relative, descriptor
            pending.extend(dependencies)
        finder = _Finder(files, pb)
        namespace_name = "_hakimi_verified_futu_pb_" + manifest["bundle_id"][:16]
        _attempted = True
        sys.meta_path.insert(0, finder)
        try:
            protobuf = importlib.import_module("google.protobuf")
            _require(protobuf.__version__ == PROTOBUF_VERSION, "LOADED_PROTOBUF_VERSION_MISMATCH")
            pool = importlib.import_module("google.protobuf.descriptor_pool").Default()
            for name in pb:
                try:
                    pool.FindFileByName(name[:-4] + ".proto")
                except KeyError:
                    pass
                else:
                    raise ProtobufLoaderError("DESCRIPTOR_CACHE_NOT_COLD", name)
            modules = {name: importlib.import_module(name) for name in sorted(pb)}
            namespace = ModuleType(namespace_name)
            namespace.__path__ = []
            namespace.__spec__ = importlib.machinery.ModuleSpec(namespace_name, loader=None, is_package=True)
            sys.modules[namespace_name] = namespace
            for name, module in modules.items():
                setattr(namespace, name, module)
                sys.modules[namespace_name + "." + name] = module
            requests, responses = {}, {}
            for proto, name in PROTO_NAMES.items():
                module = modules[name + "_pb2"]
                _require(module.Request.DESCRIPTOR.full_name == name + ".Request" and
                         module.Response.DESCRIPTOR.full_name == name + ".Response", "PROTOCOL_CLASS_IDENTITY_MISMATCH")
                requests[proto], responses[proto] = module.Request, module.Response
            namespaces = {name: (sys.modules[name], tuple(sys.modules[name].__path__))
                          for name in ("google", "google._upb", namespace_name) if name in sys.modules}

            def verify():
                _require(sys.meta_path and sys.meta_path[0] is finder and sys.modules.get(namespace_name) is namespace,
                         "IMPORT_GUARD_OR_NAMESPACE_CHANGED")
                for name, module in {**finder.loaded, **modules}.items():
                    _require(sys.modules.get(name) is module, "MODULE_CACHE_IDENTITY_CHANGED", name)
                    if name in finder.origins:
                        _require(getattr(module, "__file__", None) == finder.origins[name]
                                 and getattr(getattr(module, "__spec__", None), "origin", None) == finder.origins[name],
                                 "MODULE_CACHE_ORIGIN_CHANGED", name)
                for name, (module, paths) in namespaces.items():
                    _require(sys.modules.get(name) is module and tuple(module.__path__) == paths,
                             "NAMESPACE_CACHE_CHANGED", name)
                for name, module in modules.items():
                    _require(sys.modules.get(namespace_name + "." + name) is module
                             and getattr(namespace, name) is module
                             and module.DESCRIPTOR.serialized_pb == descriptors[name]
                             and pool.FindFileByName(name[:-4] + ".proto") is module.DESCRIPTOR,
                             "DESCRIPTOR_OR_ALIAS_CHANGED", name)
                for proto, name in PROTO_NAMES.items():
                    module = modules[name + "_pb2"]
                    _require(module.Request is requests[proto] and module.Response is responses[proto]
                             and pool.FindMessageTypeByName(name + ".Request") is requests[proto].DESCRIPTOR
                             and pool.FindMessageTypeByName(name + ".Response") is responses[proto].DESCRIPTOR,
                             "PROTOCOL_CLASS_CACHE_CHANGED")
                # A later explicit verify_current also catches equal-size edits
                # whose timestamps were restored. New imports never use pyc.
                for relative in tuple(files.signatures):
                    files.read(relative)
                files.stable()

            verify()
            body = {"schema_version": SCHEMA, "package_root": str(root), "package": runtime["package"],
                    "sdk": runtime["sdk"], "protobuf": {"version": PROTOBUF_VERSION, "wheel_sha256": PROTOBUF_WHEEL_SHA256},
                    "namespace": namespace_name, "loaded_files": files.identities,
                    "protocols": {str(proto): {"name": name, "request": name + ".Request", "response": name + ".Response"}
                                  for proto, name in PROTO_NAMES.items()},
                    "source_identity_only": True, "runtime_compatibility": "NOT_VERIFIED",
                    "production_transport_available": False, "permissions": dict(contract.PERMISSIONS)}
            body["id"] = contract.digest(body)
            return VerifiedProtobufBindings(requests, responses, contract.canonical_bytes(body), verify, _TOKEN)
        except ProtobufLoaderError:
            raise
        except Exception as error:
            raise ProtobufLoaderError("VERIFIED_PROTOBUF_IMPORT_FAILED", type(error).__name__) from error


def load_verified_protobuf(*, package_root, expected_manifest_sha256, runtime_identity):
    """Load once in the trusted isolated worker; return byte-source identity only.

    Hashes and package_root must come from the worker/bootstrap, never an HTTP
    payload. Failure does not delete existing modules or reset descriptor pools.
    """
    try:
        return _load_verified_protobuf(package_root=package_root,
                                      expected_manifest_sha256=expected_manifest_sha256,
                                      runtime_identity=runtime_identity)
    except ProtobufLoaderError:
        raise
    except (OSError, ValueError, TypeError, KeyError, SyntaxError) as error:
        raise ProtobufLoaderError("VERIFIED_PACKAGE_INPUT_REJECTED", type(error).__name__) from error
