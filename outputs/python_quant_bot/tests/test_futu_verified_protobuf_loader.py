"""Synthetic source/manifest fixtures only; never import Futu or protobuf.

Actual private-interpreter/generated-class compatibility is a separate bounded
probe. These tests do not substitute a mock success for that installed path.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_verified_protobuf_loader as loader
from exchange_terminal.services import terminal_broker_execution_plan as contract


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def synthetic_manifest():
    blobs = {
        loader.SITE + "futu/__init__.py": b"# SYNTHETIC TEST ONLY, never imported\n",
        loader.SITE + "futu_api-10.7.6708.dist-info/METADATA": b"synthetic SDK metadata\n",
        loader.SITE + "google/protobuf/__init__.py": b"# synthetic protobuf source\n",
        loader.SITE + "protobuf-7.35.1.dist-info/METADATA": b"synthetic protobuf metadata\n",
    }
    return {"schema_version": "hakimi-original-terminal-v1", "version": "0.0.0.synthetic",
        "source_provenance": {"development_probe": False, "git": {"commit": "1" * 40, "status": "CLEAN"}},
        "files": {name: sha256(raw).hexdigest() for name, raw in blobs.items()},
        "dependency_wheels": [
            {"name": "futu-api", "version": loader.PINNED_SDK_VERSION,
             "filename": "futu_api-10.7.6708-py3-none-any.whl", "sha256": loader.PINNED_WHEEL_SHA256},
            {"name": "protobuf", "version": loader.PROTOBUF_VERSION,
             "filename": "synthetic-protobuf.whl", "sha256": loader.PROTOBUF_WHEEL_SHA256}]}


def manifest_inputs(manifest=None):
    manifest = deepcopy(manifest if manifest is not None else synthetic_manifest())
    manifest.pop("bundle_id", None)
    manifest["bundle_id"] = sha256(encoded(manifest)).hexdigest()
    raw = encoded(manifest)
    expected = sha256(raw).hexdigest()
    runtime = contract.verify_runtime_identity(manifest_bytes=raw, expected_manifest_sha256=expected,
        observed_file_sha256=manifest["files"], mode="OFFICIAL_SIMULATION")
    return raw, expected, runtime


def flags(**changes):
    result = dict(isolated=1, no_site=1, ignore_environment=1, dont_write_bytecode=1)
    result.update(changes)
    return SimpleNamespace(**result)


class PureRejectionTests(unittest.TestCase):
    def reject(self, code, callback):
        with self.assertRaises(loader.ProtobufLoaderError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)

    def test_normal_process_refuses_before_file_io(self):
        with patch.object(loader.sys, "flags", flags(isolated=0)), patch.object(Path, "open", side_effect=AssertionError("no IO")):
            self.reject("PRIVATE_ISOLATED_WORKER_REQUIRED", lambda: loader.load_verified_protobuf(
                package_root="not-read", expected_manifest_sha256="0" * 64, runtime_identity={}))

    def test_all_private_flags_are_required(self):
        for name in ("isolated", "no_site", "ignore_environment", "dont_write_bytecode"):
            with self.subTest(name=name), patch.object(loader.sys, "flags", flags(**{name: 0})), \
                    patch.object(loader.sys, "dont_write_bytecode", True):
                self.reject("PRIVATE_ISOLATED_WORKER_REQUIRED", loader._private_process)

    def test_runtime_bytecode_setting_cannot_override_invocation_requirement(self):
        with patch.object(loader.sys, "flags", flags()), patch.object(loader.sys, "dont_write_bytecode", False):
            self.reject("PRIVATE_ISOLATED_WORKER_REQUIRED", loader._private_process)

    def test_protobuf_environment_override_refused_without_revealing_value(self):
        with patch.object(loader.sys, "flags", flags()), patch.object(loader.sys, "dont_write_bytecode", True), \
                patch.dict(os.environ, {"PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "secret-value"}, clear=True):
            self.reject("PROTOBUF_ENVIRONMENT_OVERRIDE_REJECTED", loader._private_process)

    def test_renderer_dict_is_not_typed_runtime_even_under_private_flags(self):
        with patch.object(loader, "_private_process"), patch.object(Path, "open", side_effect=AssertionError("no IO")):
            self.reject("TRUSTED_RUNTIME_IDENTITY_REQUIRED", lambda: loader.load_verified_protobuf(
                package_root="not-read", expected_manifest_sha256="0" * 64, runtime_identity={"trusted": True}))

    def test_second_attempt_rejected_before_paths_even_after_previous_failure(self):
        _, expected, runtime = manifest_inputs()
        with patch.object(loader, "_private_process"), patch.object(loader, "_attempted", True), \
                patch.object(Path, "open", side_effect=AssertionError("no IO")):
            self.reject("NEW_PRIVATE_WORKER_REQUIRED", lambda: loader.load_verified_protobuf(
                package_root="not-read", expected_manifest_sha256=expected, runtime_identity=runtime))

    def test_cold_cache_rejects_sdk_google_pb_and_namespace_without_deleting(self):
        for name in ("futu", "futu.common", "google", "google.protobuf.descriptor_pool", "Common_pb2",
                     "other.Common_pb2", "_hakimi_verified_futu_pb_old"):
            modules = {"sys": sys, name: object()}
            original = dict(modules)
            with self.subTest(name=name):
                self.reject("MODULE_CACHE_NOT_COLD", lambda: loader._cold_modules(modules))
                self.assertEqual(modules, original)
        loader._cold_modules({"json": json, "google_tools": object()})

    def test_valid_pure_manifest_preserves_sdk_and_permission_boundary(self):
        args = manifest_inputs()
        with patch.object(Path, "open", side_effect=AssertionError("pure manifest validation")):
            manifest, runtime = loader._manifest(*args)
        self.assertEqual(manifest["bundle_id"], runtime["package"]["bundle_id"])
        self.assertEqual(runtime["sdk"]["runtime_compatibility"], "NOT_VERIFIED")
        self.assertIsNone(runtime["adapter"])
        self.assertEqual(len(runtime["permissions"]), 9)
        self.assertFalse(any(runtime["permissions"].values()))

    def test_manifest_bytes_and_expected_identity_must_match_typed_runtime(self):
        raw, expected, runtime = manifest_inputs()
        self.reject("MANIFEST_IDENTITY_MISMATCH", lambda: loader._manifest(raw + b" ", expected, runtime))
        self.reject("MANIFEST_IDENTITY_MISMATCH", lambda: loader._manifest(raw, "0" * 64, runtime))
        self.reject("TRUSTED_RUNTIME_IDENTITY_REQUIRED", lambda: loader._manifest(raw, expected, runtime.as_dict()))

    def test_bundle_digest_cannot_be_merely_self_reported(self):
        raw, _, _ = manifest_inputs()
        manifest = json.loads(raw); manifest["bundle_id"] = "b" * 64
        raw = encoded(manifest); expected = sha256(raw).hexdigest()
        runtime = contract.verify_runtime_identity(manifest_bytes=raw, expected_manifest_sha256=expected,
            observed_file_sha256=manifest["files"], mode="OFFICIAL_SIMULATION")
        self.reject("PACKAGE_IDENTITY_MISMATCH", lambda: loader._manifest(raw, expected, runtime))

    def test_both_locked_dependency_hashes_and_versions_are_required(self):
        for index, key, value in ((0, "sha256", "a" * 64), (1, "sha256", "b" * 64), (1, "version", "7.35.2")):
            manifest = synthetic_manifest(); manifest["dependency_wheels"][index][key] = value
            with self.subTest(index=index, key=key):
                args = manifest_inputs(manifest)
                self.reject("PINNED_DEPENDENCY_REQUIRED", lambda: loader._manifest(*args))

    def test_duplicate_protobuf_declaration_and_second_metadata_version_rejected(self):
        manifest = synthetic_manifest(); manifest["dependency_wheels"].append(deepcopy(manifest["dependency_wheels"][1]))
        self.reject("PINNED_DEPENDENCY_REQUIRED", lambda: loader._manifest(*manifest_inputs(manifest)))
        for extra in ("protobuf-6.0.dist-info/METADATA", "futu_api-10.0.dist-info/METADATA"):
            manifest = synthetic_manifest(); manifest["files"][loader.SITE + extra] = "a" * 64
            with self.subTest(extra=extra):
                self.reject("DEPENDENCY_METADATA_AMBIGUOUS", lambda: loader._manifest(*manifest_inputs(manifest)))

    def test_missing_protobuf_sources_rejected(self):
        manifest = synthetic_manifest(); manifest["files"].pop(loader.SITE + "google/protobuf/__init__.py")
        self.reject("PROTOBUF_INVENTORY_MISSING", lambda: loader._manifest(*manifest_inputs(manifest)))

    def test_generated_absolute_dependencies_and_descriptor_literal_are_parsed_without_exec(self):
        source = b"from google.protobuf import descriptor_pool\nimport Common_pb2 as common\nDESCRIPTOR=descriptor_pool.Default().AddSerializedFile(b'fixture')\nraise AssertionError('do not execute')\n"
        self.assertEqual(loader._pb_source(source, "Fixture_pb2"), (("Common_pb2",), b"fixture"))

    def test_generated_external_relative_and_dynamic_descriptor_imports_refused(self):
        for source in (b"import futu\n", b"import socket\n", b"from . import Common_pb2\n"):
            with self.subTest(source=source):
                self.reject("GENERATED_IMPORT_OUTSIDE_PROTOBUF", lambda: loader._pb_source(source, "Fixture_pb2"))
        for source in (b"x.AddSerializedFile('not bytes')", b"x.AddSerializedFile(b'a');x.AddSerializedFile(b'b')"):
            self.reject("DESCRIPTOR_LITERAL_REQUIRED", lambda: loader._pb_source(source, "Fixture_pb2"))
        self.reject("GENERATED_SOURCE_INVALID", lambda: loader._pb_source(b"x", "../Fixture_pb2"))

    def test_finder_has_no_sys_path_or_sdk_fallback(self):
        files = SimpleNamespace(root=Path("synthetic-package"), manifest={"files": {}})
        finder = loader._Finder(files, {})
        with patch.object(importlib.machinery.PathFinder, "find_spec", side_effect=AssertionError("no global fallback")):
            self.reject("SDK_IMPORT_FORBIDDEN", lambda: finder.find_spec("futu.common"))
            self.reject("PROTOBUF_IMPORT_OUTSIDE_CLOSURE", lambda: finder.find_spec("Missing_pb2"))
            self.reject("PROTOBUF_IMPORT_OUTSIDE_CLOSURE", lambda: finder.find_spec("google.other"))
            with self.assertRaises(ModuleNotFoundError):
                finder.find_spec("unmanifested_module")

    def test_manifest_ambiguity_rejected_and_pyc_never_selected(self):
        stem = loader.SITE + "google/protobuf/fixture"
        files = SimpleNamespace(root=Path("synthetic-package"), manifest={"files": {stem + ".pyc": "0" * 64}})
        finder = loader._Finder(files, {})
        with self.assertRaises(ModuleNotFoundError):
            finder.find_spec("google.protobuf.fixture")
        files.manifest["files"].update({stem + ".py": "0" * 64, stem + "/__init__.py": "0" * 64})
        self.reject("AMBIGUOUS_MANIFEST_MODULE", lambda: finder.find_spec("google.protobuf.fixture"))

    def test_result_private_factory_and_returned_maps_are_immutable(self):
        self.reject("PROTOBUF_PRIVATE_FACTORY_REQUIRED", lambda: loader.VerifiedProtobufBindings({}, {}, b"{}", lambda: None, object()))
        # Private factory exercise only: never represented as a real loaded SDK.
        result = loader.VerifiedProtobufBindings({1001: object()}, {}, b'{"synthetic":true}', lambda: None, loader._TOKEN)
        with self.assertRaises(TypeError):
            result.request_classes[1002] = object()
        with self.assertRaises(FrozenInstanceError):
            result._data = b"{}"
        result.as_dict()["synthetic"] = False
        self.assertTrue(result.verify_current()["synthetic"])


class TempSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-protobuf-loader-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def files(self, values):
        for relative, raw in values.items():
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return loader._Files(self.root, b"{}", {"files": {name: sha256(raw).hexdigest() for name, raw in values.items()}})

    def test_manifest_initial_read_is_regular_bounded_and_stable(self):
        path = self.root / "terminal-manifest.json"; path.write_bytes(b"{}")
        self.assertEqual(loader._initial_manifest(path), b"{}")
        path.write_bytes(b"")
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "REGULAR_BOUNDED_MANIFEST_REQUIRED"):
            loader._initial_manifest(path)

    def test_source_hash_mismatch_and_equal_size_restored_time_are_rejected(self):
        files = self.files({"fixture.py": b"x=1\n"})
        path = self.root / "fixture.py"; before = path.stat()
        self.assertEqual(files.read("fixture.py"), b"x=1\n")
        path.write_bytes(b"x=2\n"); os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "FILE_HASH_MISMATCH"):
            files.read("fixture.py")

    def test_cross_file_stability_rejects_earlier_source_change(self):
        files = self.files({"first.py": b"x=1", "last.py": b"y=1"})
        files.read("first.py"); files.read("last.py")
        (self.root / "first.py").write_bytes(b"changed-size")
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "FILE_CHANGED_DURING_LOAD"):
            files.stable()

    def test_related_membership_addition_rejected(self):
        files = self.files({"family/a.py": b"x=1"})
        files.members("family/")
        (self.root / "family/extra.py").write_bytes(b"x=2")
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "RELATED_MEMBERSHIP_CHANGED"):
            files.stable()

    def test_hardlink_and_lexical_alias_rejected(self):
        files = self.files({"fixture.py": b"x=1"})
        os.link(self.root / "fixture.py", self.root / "other.py")
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "REGULAR_BOUNDED_FILE_REQUIRED"):
            files.read("fixture.py")
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "PHYSICAL_PATH_ALIAS"):
            loader._plain(self.root / "alias" / ".." / "fixture.py")

    def test_source_loader_compiles_verified_bytes_ignoring_poison_bytecode(self):
        files = self.files({"fixture.py": b"value='verified synthetic source'\n"})
        (self.root / "fixture.pyc").write_bytes(b"untrusted bytecode must never be read")
        owner = SimpleNamespace(files=files, loaded={}, origins={})
        source = loader._Source(owner, "fixture.py")
        spec = importlib.util.spec_from_file_location("synthetic_fixture", self.root / "fixture.py", loader=source)
        module = importlib.util.module_from_spec(spec); source.exec_module(module)
        self.assertEqual(module.value, "verified synthetic source")
        self.assertEqual(set(files.identities), {"fixture.py"})
        self.assertIs(owner.loaded["synthetic_fixture"], module)


if __name__ == "__main__":
    unittest.main()
