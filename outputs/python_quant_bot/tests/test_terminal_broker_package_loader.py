"""New TEMP package bytes only; no installed package, SDK or account is opened."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_package_loader as loader

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("_test_broker_loader_bootstrap", ROOT / "tools/terminal_package_bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
SIM, REAL = "OFFICIAL_SIMULATION", "LIVE_CANDIDATE"
SDK = loader.plan.SDK_ROOT + "futu/__init__.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class BrokerPackageLoaderTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket.connect", "socket.socket.bind", "socket.getaddrinfo", "subprocess.Popen", "sqlite3.connect"):
            block = patch(target, side_effect=AssertionError("No external or database operation"))
            block.start(); self.addCleanup(block.stop)
        for module, name, value in ((loader, "_anchor", None), (loader, "_anchor_invalid", False),
                                    (bootstrap, "_VERIFIED_PACKAGE", None), (bootstrap, "_ACTIVATED_LOADER", None)):
            change = patch.object(module, name, value)
            change.start(); self.addCleanup(change.stop)

    def bundle(self, *, sdk=True, modes=(SIM,)):
        temporary = tempfile.TemporaryDirectory(prefix="broker-loader-中文 空格-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "纯合成程序 夹具"
        files = {
            loader.LOADER_PATH: Path(loader.__file__).read_bytes(),
            "resources/app/terminal-bootstrap.py": (ROOT / "tools/terminal_package_bootstrap.py").read_bytes(),
            "components/terminal/exchange_terminal/services/terminal_broker_execution_plan.py": b"# Synthetic plan file; presence is not an adapter.\n",
            "unrelated.bin": b"Synthetic unrelated package member.\n",
        }
        if sdk:
            files[SDK] = b"raise AssertionError('Synthetic SDK must never be imported')\n"
            files[loader.plan.SDK_ROOT + "futu_api-10.7.6708.dist-info/METADATA"] = b"Name: futu-api\nVersion: 10.7.6708\n"
        for mode in modes:
            entry = loader.ADAPTER_ROOT + "/" + ("simulate" if mode == SIM else "real") + ".py"
            files[entry] = b"raise AssertionError('Synthetic adapter must never be imported')\n"
            descriptor = dict(schema_version=loader.plan.ADAPTER_SCHEMA, adapter_id="SYNTHETIC_TEST_ONLY",
                mode=mode, sdk_environment=loader.plan.MODE_CONTRACTS[mode][0], contract_id=loader.plan.MODE_CONTRACTS[mode][1],
                sdk_name="futu-api", sdk_version="10.7.6708", market="US", asset_class="EQUITY", currency="USD",
                security_mapping="EXACT_SAVED_US_SYMBOL_V1", quantity_policy="WHOLE_SHARES", order_type="LIMIT",
                time_in_force="DAY", sides=["BUY", "SELL"], entrypoint={"path": entry, "function": "build_scoped_transport"},
                source_files={entry: sha256(files[entry]).hexdigest()})
            files[loader.DESCRIPTORS[mode]] = canonical(descriptor)
        for name, value in files.items():
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(value)
        core = dict(schema_version="hakimi-original-terminal-v1", version="0.0.0.synthetic", platform="win32-x64",
            scope="SYNTHETIC_TEST_FILES_NOT_AN_INSTALLATION", files={name: sha256(value).hexdigest() for name, value in files.items()},
            source_provenance={"development_probe": False, "git": {"status": "CLEAN", "commit": "a" * 40}},
            dependency_wheels=[{"name": "futu-api", "version": "10.7.6708", "filename": "futu_api-10.7.6708-py3-none-any.whl", "sha256": "b" * 64}] if sdk else [])
        raw = canonical({**core, "bundle_id": sha256(canonical(core)).hexdigest()}) + b"\n"
        (root / "terminal-manifest.json").write_bytes(raw)
        return root.resolve()

    def install_verified_fixture(self, root):
        # Real complete file verification, followed by the private trusted-code
        # handoff. Private interpreter flags are tested separately; this fixture
        # deliberately does not pretend its dummy files are a runnable package.
        manifest = bootstrap.verify(root)
        self.assertEqual(bootstrap._VERIFIED_PACKAGE[0], str(root.resolve()))
        loader._install_bootstrap_anchor(root, bootstrap._VERIFIED_PACKAGE[1])
        return manifest

    def expect_changed(self, root, mutate):
        mutate()
        with self.assertRaises(loader.PackageLoaderError) as caught:
            loader.load_broker_runtime_identity(SIM)
        self.assertEqual(caught.exception.code, "PACKAGE_CHANGED")
        self.assertIsNotNone(loader._anchor)

    def test_repository_mode_ignores_env_and_never_searches_for_a_package(self):
        with patch.dict(os.environ, HAKIMI_TERMINAL_PACKAGE_ID="a" * 64, HAKIMI_TERMINAL_PACKAGE_ROOT="C:/fake"), \
             patch.object(loader, "_read", side_effect=AssertionError("No package reads without anchor")):
            loaded = loader.load_broker_runtime_identity(SIM)
        self.assertEqual(loaded.status, "NOT_PACKAGED"); self.assertIsNone(loaded.runtime_identity)
        self.assertFalse(any(loaded.as_dict()["permissions"].values()))
        self.assertEqual(loaded.as_dict()["runtime_compatibility"], "NOT_VERIFIED")

    def test_real_temp_manifest_and_observed_files_produce_identity_only_without_import(self):
        root = self.bundle(); manifest = self.install_verified_fixture(root)
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
        with patch("builtins.__import__", wraps=__import__) as imported:
            value = loader.load_broker_runtime_identity(SIM)
        self.assertFalse(any(call.args[0] == "futu" or call.args[0].startswith("futu.") for call in imported.call_args_list))
        self.assertIs(type(value.runtime_identity), loader.plan.VerifiedRuntimeIdentity)
        public = value.as_dict(); self.assertEqual(public["package"]["bundle_id"], manifest["bundle_id"])
        self.assertEqual(public["sdk"]["version"], "10.7.6708"); self.assertIsNotNone(public["adapter"])
        self.assertEqual(public["runtime_compatibility"], "NOT_VERIFIED"); self.assertFalse(any(public["permissions"].values()))
        self.assertNotIn("root", public)
        self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()})

    def test_sdk_absence_and_plan_presence_do_not_fabricate_an_adapter(self):
        root = self.bundle(sdk=False, modes=()); self.install_verified_fixture(root)
        public = loader.load_broker_runtime_identity(SIM).as_dict()
        self.assertIsNone(public["sdk"]); self.assertIsNone(public["adapter"])
        self.assertEqual(public["missing_capabilities"], ["SDK_NOT_PACKAGED", "APPLICATION_ADAPTER_NOT_PACKAGED"])

    def test_modes_use_distinct_fixed_descriptor_paths_and_no_client_path(self):
        root = self.bundle(); self.install_verified_fixture(root)
        self.assertIsNotNone(loader.load_broker_runtime_identity(SIM).runtime_identity.as_dict()["adapter"])
        self.assertIsNone(loader.load_broker_runtime_identity(REAL).runtime_identity.as_dict()["adapter"])
        with self.assertRaises(loader.PackageLoaderError) as caught: loader.load_broker_runtime_identity("SIMULATE")
        self.assertEqual(caught.exception.code, "MODE_INVALID")
        with self.assertRaises(TypeError): loader.load_broker_runtime_identity(SIM, adapter_path="client.json")

    def test_manifest_even_whitespace_change_is_rejected_without_old_identity_fallback(self):
        root = self.bundle(); self.install_verified_fixture(root); old = loader.load_broker_runtime_identity(SIM)
        target = root / "terminal-manifest.json"
        self.expect_changed(root, lambda: target.write_bytes(target.read_bytes() + b" "))
        self.assertIsNotNone(old.runtime_identity)

    def test_changed_sdk_bytes_are_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        self.expect_changed(root, lambda: (root / SDK).write_bytes(b"changed"))

    def test_deleted_sdk_member_is_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        self.expect_changed(root, lambda: (root / SDK).unlink())

    def test_added_sdk_member_is_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        self.expect_changed(root, lambda: (root / loader.plan.SDK_ROOT / "futu/extra.py").write_bytes(b"not declared"))

    def test_added_sdk_version_directory_is_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        self.expect_changed(root, lambda: (root / loader.plan.SDK_ROOT / "futu_api-99.dist-info").mkdir())

    def test_added_empty_adapter_directory_is_not_adapter_absence(self):
        root = self.bundle(modes=()); self.install_verified_fixture(root)
        self.expect_changed(root, lambda: (root / loader.ADAPTER_ROOT).mkdir())

    def test_adapter_descriptor_and_source_changes_are_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        target = root / loader.DESCRIPTORS[SIM]; original = target.read_bytes()
        self.expect_changed(root, lambda: target.write_bytes(original + b" "))
        target.write_bytes(original)
        self.expect_changed(root, lambda: (root / loader.ADAPTER_ROOT / "simulate.py").write_bytes(b"changed"))

    def test_full_inventory_is_startup_only_and_each_load_rechecks_related_bytes(self):
        root = self.bundle(); self.install_verified_fixture(root)
        (root / "unrelated.bin").write_bytes(b"Not part of this bounded fresh check")
        with patch.object(loader, "_read", wraps=loader._read) as reads:
            loader.load_broker_runtime_identity(SIM)
        self.assertNotIn("unrelated.bin", [call.args[1] for call in reads.call_args_list])
        self.assertIn(SDK, [call.args[1] for call in reads.call_args_list])
        self.expect_changed(root, lambda: (root / SDK).write_bytes(b"changed on second load"))

    def test_hardlink_alias_is_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        os.link(root / SDK, root.parent / "other-hardlink.py")
        with self.assertRaisesRegex(loader.PackageLoaderError, "aliased"):
            loader.load_broker_runtime_identity(SIM)

    def test_real_directory_symlink_is_rejected(self):
        root = self.bundle(modes=()); self.install_verified_fixture(root)
        outside = root.parent / "external-adapters"; outside.mkdir()
        (root / loader.ADAPTER_ROOT).symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(loader.PackageLoaderError, "reparse"):
            loader.load_broker_runtime_identity(SIM)

    def test_related_and_descriptor_budgets_are_enforced(self):
        root = self.bundle(); self.install_verified_fixture(root)
        for constant, limit in (("MAX_RELATED_FILES", 2), ("MAX_RELATED_ENTRIES", 1),
                                ("MAX_RELATED_BYTES", 1), ("MAX_DESCRIPTOR_BYTES", 1)):
            with self.subTest(constant=constant), patch.object(loader, constant, limit), self.assertRaises(loader.PackageLoaderError):
                loader.load_broker_runtime_identity(SIM)
        with self.assertRaisesRegex(loader.PackageLoaderError, "size_exceeded"):
            loader._read(root, SDK, 1)

    def test_a_second_package_cannot_rebind_the_initialized_process(self):
        first = self.bundle(); self.install_verified_fixture(first)
        second = self.bundle(modes=()); bootstrap.verify(second)
        with self.assertRaises(loader.PackageLoaderError) as caught:
            loader._install_bootstrap_anchor(second, bootstrap._VERIFIED_PACKAGE[1])
        self.assertEqual(caught.exception.code, "BOOTSTRAP_ANCHOR_INVALID")
        self.assertEqual(loader._anchor.root, str(first.resolve()))

    def test_initialize_requires_same_verification_and_private_interpreter(self):
        root = self.bundle()
        with self.assertRaisesRegex(RuntimeError, "same_verification_required"):
            bootstrap.initialize(root, {})
        manifest = bootstrap.verify(root)
        with self.assertRaisesRegex(RuntimeError, "isolated_python_flags_required"):
            bootstrap.initialize(root, manifest)
        self.assertIsNone(loader._anchor)
        with self.assertRaisesRegex(RuntimeError, "same_verification_required"):
            bootstrap.initialize(root, {**manifest, "version": "forged"})

    def test_failed_initialization_cannot_leave_an_active_anchor_or_fall_back_to_repo(self):
        root = self.bundle(); manifest = self.install_verified_fixture(root)
        bootstrap._ACTIVATED_LOADER = loader
        with self.assertRaisesRegex(RuntimeError, "isolated_python_flags_required"):
            bootstrap.initialize(root, manifest)
        with self.assertRaises(loader.PackageLoaderError) as caught: loader.load_broker_runtime_identity(SIM)
        self.assertEqual(caught.exception.code, "BOOTSTRAP_ANCHOR_INVALID")

    def test_earlier_sdk_and_first_descriptor_reads_are_rechecked_after_later_reads(self):
        root = self.bundle(); self.install_verified_fixture(root)
        read = loader._read
        for target, trigger in ((SDK, "METADATA"), (loader.DESCRIPTORS[SIM], "futu/__init__.py")):
            original = (root / target).read_bytes(); changed = []
            def hooked(package, name, *args, **kwargs):
                value = read(package, name, *args, **kwargs)
                if name.endswith(trigger) and not changed:
                    (root / target).write_bytes(original + b"\n# changed after its successful read\n")
                    changed.append(target)
                return value
            with self.subTest(target=target), patch.object(loader, "_read", side_effect=hooked):
                with self.assertRaisesRegex(loader.PackageLoaderError, "file_changed_across_load"):
                    loader.load_broker_runtime_identity(SIM)
            self.assertEqual(changed, [target]); (root / target).write_bytes(original)

    def test_same_path_sdk_directory_replacement_is_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        target = root / loader.plan.SDK_ROOT / "futu"
        old = target.with_name("futu-retained-original")
        self.assertTrue(old.is_relative_to(root)); target.rename(old); shutil.copytree(old, target)
        with self.assertRaisesRegex(loader.PackageLoaderError, "anchored_directory_replaced"):
            loader.load_broker_runtime_identity(SIM)

    def test_same_path_package_root_replacement_is_rejected(self):
        root = self.bundle(); self.install_verified_fixture(root)
        old = root.with_name(root.name + "-retained-original")
        self.assertEqual(old.parent, root.parent); root.rename(old); shutil.copytree(old, root)
        with self.assertRaisesRegex(loader.PackageLoaderError, "anchored_directory_replaced"):
            loader.load_broker_runtime_identity(SIM)

    def test_initial_second_sdk_dist_info_cannot_hide_in_a_valid_manifest(self):
        root = self.bundle()
        name = loader.plan.SDK_ROOT + "futu_api-99.dist-info/METADATA"
        target = root / name; target.parent.mkdir(); target.write_bytes(b"second synthetic distribution")
        path = root / "terminal-manifest.json"; manifest = json.loads(path.read_bytes())
        manifest["files"][name] = sha256(target.read_bytes()).hexdigest()
        core = {key: value for key, value in manifest.items() if key != "bundle_id"}
        path.write_bytes(canonical({**core, "bundle_id": sha256(canonical(core)).hexdigest()}))
        bootstrap.verify(root)
        with self.assertRaisesRegex(loader.PackageLoaderError, "declared_version"):
            loader._install_bootstrap_anchor(root, bootstrap._VERIFIED_PACKAGE[1])
        self.assertIsNone(loader._anchor)

    def test_bootstrap_import_requires_exact_verified_loader_path_and_bytes(self):
        root = self.bundle(); manifest = bootstrap.verify(root)
        imported = SimpleNamespace(__file__=str(root / "outside.py"), _install_bootstrap_anchor=lambda *args: self.fail("must not install"))
        with patch.object(bootstrap.importlib, "import_module", return_value=imported):
            with self.assertRaisesRegex(RuntimeError, "loader_import_shadowed"):
                bootstrap._activate_verified_loader(root, manifest)
        self.assertIsNone(loader._anchor)
        (root / loader.LOADER_PATH).write_bytes(b"changed before import")
        with patch.object(bootstrap.importlib, "import_module", side_effect=AssertionError("Changed loader must not import")):
            with self.assertRaisesRegex(RuntimeError, "loader_bytes_changed"):
                bootstrap._activate_verified_loader(root, manifest)

    def test_bootstrap_activation_uses_same_verify_raw_bytes_not_env_claims(self):
        root = self.bundle(); manifest = bootstrap.verify(root)
        imported = SimpleNamespace(__file__=str(root / loader.LOADER_PATH), _install_bootstrap_anchor=loader._install_bootstrap_anchor)
        with patch.object(bootstrap.importlib, "import_module", return_value=imported), \
             patch.dict(os.environ, HAKIMI_TERMINAL_PACKAGE_ID="forged"):
            bootstrap._activate_verified_loader(root, manifest)
        self.assertEqual(loader._anchor.manifest_bytes, bootstrap._VERIFIED_PACKAGE[1])
        self.assertEqual(loader.load_broker_runtime_identity(SIM).as_dict()["package"]["bundle_id"], manifest["bundle_id"])


if __name__ == "__main__":
    unittest.main()
