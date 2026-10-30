"""Explicit allowlisted file-resolution fixtures; no real workspace mutations."""
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

if Path(__file__).with_name('terminal_workspace_history.py').is_file():
    spec = importlib.util.spec_from_file_location('exchange_terminal.services._workspace_history_msix_draft',
                                                  Path(__file__).with_name('terminal_workspace_history.py'))
    history = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(history)
else:
    from exchange_terminal.services import terminal_workspace_history as history


class MsixWorkspaceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='history-msix-mapping-qa-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.local = self.root / 'Local'
        self.trial = self.local / 'HakimiTradeTrial' / 'workspaces'
        self.package = self.local / 'Packages' / 'OpenAI.Codex_2p2nqsd0c76g0'
        self.resolve = Path.resolve

    def marker(self, name, *, physical_name=None, package=None):
        logical = self.trial / name
        physical = (package or self.package) / 'LocalCache' / 'Local' / 'HakimiTradeTrial' / 'workspaces' / (physical_name or name)
        value = {'schema_version': 'research-trial-workspace-v1', 'bundle_id': name + 'c' * 44}
        for folder in (logical, physical):
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'trial-workspace-identity.json').write_text(json.dumps(value), encoding='utf-8')
        return logical, physical

    def redirect(self, mappings):
        original = self.resolve
        normalized = {str(left.absolute()): right for left, right in mappings.items()}
        def resolve(path, *args, **kwargs):
            target = normalized.get(str(path.absolute()), path)
            return original(target, *args, **kwargs)
        return patch.object(Path, 'resolve', resolve)

    def reader(self, **options):
        return history.TerminalWorkspaceHistory(local_app_data=self.local,
            known_original_root=self.root / 'not-existing-original', **options)

    def identity(self):
        return {str(path.relative_to(self.root)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.root.rglob('*') if path.is_file()}

    def test_default_empty_allowlist_preserves_old_warning_and_never_probes_other_packages(self):
        logical, physical = self.marker('a' * 20)
        with self.redirect({logical / 'trial-workspace-identity.json': physical / 'trial-workspace-identity.json'}):
            before = self.identity()
            view = self.reader().list_workspaces()
            self.assertEqual(view['items'], [])
            self.assertTrue(any('history_path_outside_workspace' in item for item in view['warnings']))
            self.assertEqual(self.identity(), before)

    def test_two_generic_bundle_names_become_separate_physical_roots_without_merging(self):
        pairs = [self.marker(char * 20) for char in ('a', 'b')]
        for logical, _ in pairs:
            target = logical / 'runs' / 'logical-only' / 'started.json'
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({'run_id': 'logical-only-unknown'}), encoding='utf-8')
        redirects = {logical / 'trial-workspace-identity.json': physical / 'trial-workspace-identity.json'
                     for logical, physical in pairs}
        with self.redirect(redirects), patch.object(Path, 'mkdir', side_effect=AssertionError('No creation during reads')):
            reader = self.reader(msix_package_roots=(self.package,))
            before = self.identity()
            view = reader.list_workspaces()
            self.assertEqual(len(view['items']), 2)
            self.assertEqual({row['physical_root'] for row in view['items']}, {str(p) for _, p in pairs})
            self.assertEqual(len({row['id'] for row in view['items']}), 2)
            self.assertEqual(sum('history_path_outside_workspace' in item for item in view['warnings']), 2)
            for row in view['items']:
                self.assertIn('MSIX 物理只读', row['label'])
                self.assertTrue(row['read_only'])
                self.assertEqual(reader.list_records(row['id'], 'runs')['items'], [])
                self.assertEqual(reader.list_records(row['id'], 'tasks')['items'], [])
            self.assertEqual(self.identity(), before)

    def test_wrong_package_wrong_leaf_and_non_local_package_root_are_rejected(self):
        scenarios = [
            {'package': self.local / 'Packages' / 'Other.App_abcdefghijkl0'},
            {'physical_name': 'b' * 20},
            {'package': self.root / 'OutsidePackages' / 'OpenAI.Codex_2p2nqsd0c76g0'},
        ]
        for index, options in enumerate(scenarios):
            logical, physical = self.marker(str(index + 1) * 20, **options)
            with self.redirect({logical / 'trial-workspace-identity.json': physical / 'trial-workspace-identity.json'}):
                allowed = options.get('package', self.package) if index == 2 else self.package
                view = self.reader(msix_package_roots=(allowed,)).list_workspaces()
                self.assertFalse(any(row['physical_root'] == str(physical) for row in view['items']))
                self.assertTrue(any('msix_' in warning for warning in view['warnings']))

    def test_identity_marker_schema_bundle_length_and_prefix_must_match(self):
        logical, physical = self.marker('a' * 20)
        marker = physical / 'trial-workspace-identity.json'
        for value in ({'schema_version': 'other', 'bundle_id': 'a' * 64},
                      {'schema_version': 'research-trial-workspace-v1', 'bundle_id': 'b' * 64},
                      {'schema_version': 'research-trial-workspace-v1', 'bundle_id': 'a' * 20},
                      {'schema_version': 'research-trial-workspace-v1', 'bundle_id': 'a' * 64, 'extra': True}):
            marker.write_text(json.dumps(value), encoding='utf-8')
            with self.redirect({logical / marker.name: marker}):
                before = self.identity()
                view = self.reader(msix_package_roots=(self.package,)).list_workspaces()
                self.assertEqual(view['items'], [])
                self.assertTrue(any('marker_identity_mismatch' in warning for warning in view['warnings']))
                self.assertEqual(self.identity(), before)

    def test_current_logical_or_physical_workspace_is_excluded(self):
        logical, physical = self.marker('a' * 20)
        with self.redirect({logical / 'trial-workspace-identity.json': physical / 'trial-workspace-identity.json'}):
            for active in (logical, physical):
                with self.subTest(active=active):
                    self.assertEqual(self.reader(msix_package_roots=(self.package,), current_workspace=active).list_workspaces()['items'], [])

    def test_independent_explicit_physical_candidate_is_deduplicated_by_its_own_root(self):
        logical, physical = self.marker('a' * 20)
        with self.redirect({logical / 'trial-workspace-identity.json': physical / 'trial-workspace-identity.json'}):
            view = self.reader(msix_package_roots=(self.package,), extra_roots=(physical,)).list_workspaces()
            self.assertEqual(len(view['items']), 1)
            self.assertEqual(view['items'][0]['physical_root'], str(physical))

    def test_arbitrary_external_marker_is_not_read_and_safe_boundary_is_unchanged(self):
        logical, physical = self.marker('a' * 20)
        outside = self.root / 'other' / 'trial-workspace-identity.json'
        outside.parent.mkdir(); outside.write_text('{}', encoding='utf-8')
        real_document = history._document
        def document(root, path):
            self.assertNotEqual(path, outside)
            return real_document(root, path)
        with self.redirect({logical / 'trial-workspace-identity.json': outside}), patch.object(history, '_document', document):
            self.assertEqual(self.reader(msix_package_roots=(self.package,)).list_workspaces()['items'], [])
            with self.assertRaisesRegex(ValueError, 'history_path_outside_workspace'):
                history._safe(logical, logical / 'trial-workspace-identity.json')

    def test_reparse_physical_marker_is_rejected_before_document_read(self):
        logical, physical = self.marker('a' * 20)
        marker = physical / 'trial-workspace-identity.json'
        original_lstat = Path.lstat
        def lstat(path, *args, **kwargs):
            if path == marker:
                return types.SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
            return original_lstat(path, *args, **kwargs)
        with self.redirect({logical / marker.name: marker}), patch.object(Path, 'lstat', lstat):
            view = self.reader(msix_package_roots=(self.package,)).list_workspaces()
            self.assertEqual(view['items'], [])
            self.assertTrue(any('reparse' in warning for warning in view['warnings']))

    def test_nontrial_extra_root_cannot_gain_a_physical_alias(self):
        logical, physical = self.marker('a' * 20)
        arbitrary = self.root / 'arbitrary' / ('b' * 20)
        arbitrary.mkdir(parents=True)
        (arbitrary / 'trial-workspace-identity.json').write_text('{}', encoding='utf-8')
        with self.redirect({arbitrary / 'trial-workspace-identity.json': physical / 'trial-workspace-identity.json'}):
            view = self.reader(msix_package_roots=(self.package,), extra_roots=(arbitrary,)).list_workspaces()
            self.assertFalse(any(row['physical_root'] == str(physical) for row in view['items']))

    def test_selected_terminal_container_enables_only_its_exact_mapped_history(self):
        logical, physical = self.marker('a' * 20)
        workspace = self.package / 'LocalCache/Local/HakimiTradeTerminal/workspaces/current/runtime/research-workspace'
        workspace.mkdir(parents=True)
        roots = history.msix_history_roots_for_workspace(workspace, local_app_data=self.local)
        self.assertEqual(roots, (self.package,))
        with self.redirect({logical / 'trial-workspace-identity.json': physical / 'trial-workspace-identity.json'}):
            before = self.identity()
            reader = self.reader(current_workspace=workspace, msix_package_roots=roots)
            row, = reader.list_workspaces()['items']
            self.assertEqual(row['physical_root'], str(physical))
            self.assertEqual(reader.list_records(row['id'], 'tasks')['items'], [])
            self.assertEqual(reader.list_records(row['id'], 'runs')['items'], [])
            self.assertEqual(self.identity(), before)

    def test_unrelated_layouts_do_not_authorize_a_package_container(self):
        for path in (self.root / 'ordinary-workspace',
                     self.package / 'LocalCache/Local/OtherApp/workspaces/current/runtime/research-workspace',
                     self.package / 'LocalCache/Local/HakimiTradeTerminal/workspaces/current/runtime',
                     self.package / 'LocalCache/Local/HakimiTradeTerminal/workspaces/current/runtime/research-workspace/nested',
                     self.local / 'Packages/invalid-family/LocalCache/Local/HakimiTradeTerminal/workspaces/current/runtime/research-workspace'):
            path.mkdir(parents=True, exist_ok=True)
            self.assertEqual(history.msix_history_roots_for_workspace(path, local_app_data=self.local), ())
        missing = self.package / 'LocalCache/Local/HakimiTradeTerminal/workspaces/missing/runtime/research-workspace'
        self.assertEqual(history.msix_history_roots_for_workspace(missing, local_app_data=self.local), ())

    def test_other_user_and_reparse_workspace_cannot_authorize_history(self):
        workspace = self.package / 'LocalCache/Local/HakimiTradeTerminal/workspaces/current/runtime/research-workspace'
        workspace.mkdir(parents=True)
        another_local = self.root / 'AnotherUser/Local'
        (another_local / 'Packages').mkdir(parents=True)
        self.assertEqual(history.msix_history_roots_for_workspace(workspace, local_app_data=another_local), ())
        original_lstat = Path.lstat
        def lstat(path, *args, **kwargs):
            if path == workspace:
                return types.SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return original_lstat(path, *args, **kwargs)
        with patch.object(Path, 'lstat', lstat):
            self.assertEqual(history.msix_history_roots_for_workspace(workspace, local_app_data=self.local), ())


if __name__ == '__main__':
    unittest.main()
