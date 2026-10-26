"""Small synthetic archives exercise packaging; no real runtime or engine starts."""
from copy import deepcopy
import base64
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import build_windows_trial as trial
REAL_PROVENANCE = trial.packaging_provenance
spec = importlib.util.spec_from_file_location('trial_acceptance_fixture', Path(__file__).with_name('test_release_wheel_bundle.py'))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def wheel(path, members):
    members = dict(members)
    metadata = next(name for name in members if name.endswith('.dist-info/METADATA'))
    record = metadata.rsplit('/', 1)[0] + '/RECORD'
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    for name, raw in sorted(members.items()):
        raw = raw.encode() if isinstance(raw, str) else raw
        members[name] = raw
        writer.writerow([name, 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(trial.sha(raw))).decode().rstrip('='), len(raw)])
    writer.writerow([record, '', ''])
    members[record] = stream.getvalue().encode()
    with zipfile.ZipFile(path, 'w') as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)


class WindowsTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hakimi-trial-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt = fixtures.fixture(self.root)
        package = Path(self.receipt['wheel'])
        with zipfile.ZipFile(package) as archive:
            contents = {name: archive.read(name) for name in archive.namelist()}
        wheel(package, contents)
        self.receipt['wheel_sha256'] = trial.sha(package.read_bytes())
        self.wheels = self.root/'wheelhouse'; self.wheels.mkdir()
        wheel(self.wheels/'sample-1.0-py3-none-any.whl', {'sample/__init__.py': b'pass\n',
            'sample-1.0.dist-info/METADATA': b'Name: sample\nVersion: 1.0\n',
            'sample-1.0.dist-info/LICENSE': b'Synthetic fixture license notice, not executed.\n'})
        self.python = self.root/'python.zip'; self.electron = self.root/'electron.zip'
        with zipfile.ZipFile(self.python, 'w') as archive:
            for name in ['python.exe','python314.dll','LICENSE.txt','vcruntime140.dll']:
                archive.writestr(name, b'FAKE_BYTES_NOT_EXECUTED')
            archive.writestr('__install__.json', json.dumps(dict(**{'sort-version':'3.14.6'},url=trial.RUNTIMES['python']['url'])))
        with zipfile.ZipFile(self.electron, 'w') as archive:
            for name in ['electron.exe','LICENSE','LICENSES.chromium.html']:
                archive.writestr(name, b'FAKE_BYTES_NOT_EXECUTED')
            archive.writestr('version', '31.7.7')
        runtime_lock = deepcopy(trial.RUNTIMES)
        runtime_lock['python']['sha256'] = trial.sha(self.python.read_bytes())
        runtime_lock['electron']['sha256'] = trial.sha(self.electron.read_bytes())
        self.lock = patch.object(trial, 'RUNTIMES', runtime_lock)
        self.lock.start(); self.addCleanup(self.lock.stop)
        self.output = self.root/'trial.0.2.1'
        source=self.receipt['installed_runtime']['source_identity'];env=self.receipt['installed_runtime']['environment_verified']
        self.actual=dict(version='0.2.1',source_status='BUILD_VERIFIED',source_sha256=source['content_sha256'],
            build_receipt=source['build_receipt'],environment_status='VERIFIED',lock_sha256=env['lock_sha256'],
            python=str(self.output/'runtime/python/python.exe'),package_directory=str(self.output/'runtime/python/Lib/site-packages/hakimi_research'),
            isolated_venv=False,package_inside_venv=True,python_version='3.14.6',
            python_prefix=str(self.output/'runtime/python'),python_base_prefix=str(self.output/'runtime/python'),
            import_search_paths=[str(self.output/'runtime/python/Lib'),str(self.output/'runtime/python/Lib/site-packages')])
        self.probe_patch=patch.object(trial,'probe_installation',return_value=self.actual)
        self.probe=self.probe_patch.start();self.addCleanup(self.probe_patch.stop)
        provenance=dict(scope='SYNTHETIC_GIT_FIXTURE',files_sha256={
            'outputs/hakimi_trade_electron/'+name:trial.sha((ROOT/'outputs/hakimi_trade_electron'/name).read_bytes()) for name in trial.APP_FILES})
        self.provenance_patch=patch.object(trial,'packaging_provenance',return_value=provenance)
        self.provenance_patch.start();self.addCleanup(self.provenance_patch.stop)

    def build(self):
        return trial.build(self.receipt,self.python,self.electron,self.wheels,self.output)

    def test_offline_bundle_has_relative_runtime_complete_inventory_and_accepted_bytes(self):
        original=Path(self.receipt['wheel']).read_bytes()
        result=self.build()
        self.assertEqual(result['new_economic_runs'],0)
        self.assertEqual(result['clean_windows_acceptance'],'NOT_PERFORMED')
        self.assertTrue(Path(str(self.output)+'.zip').is_file())
        manifest=json.loads((self.output/'trial-manifest.json').read_bytes())
        self.assertEqual(manifest['python'],'runtime/python/python.exe')
        self.assertEqual((self.output/'accepted-wheel'/Path(self.receipt['wheel']).name).read_bytes(),original)
        self.assertEqual(Path(self.receipt['wheel']).read_bytes(),original)
        raw=(self.output/'trial-manifest.json').read_text()
        self.assertNotIn(str(self.root),raw);self.assertNotIn('PRIVATE_',raw)
        notices=json.loads((self.output/'THIRD-PARTY-NOTICES.json').read_bytes())
        self.assertEqual({x['component'] for x in notices['components']},{'python','electron','sample'})
        self.assertEqual(notices['project_license_grant'],'NO_NEW_PROJECT_LICENSE_GRANTED_BY_THIS_INDEX')
        with zipfile.ZipFile(result['archive']) as archive:
            self.assertEqual(set(archive.namelist()),set(manifest['files'])|{'trial-manifest.json'})
        # Node validates exactly the manifest emitted by Python, not a mirrored fixture.
        completed=subprocess.run(['node','-e',"console.log(require(process.argv[1]).verifyBundle(process.argv[2]).bundle_id)",
            str(ROOT/'outputs/hakimi_trade_electron/trial-main.js'),str(self.output)],capture_output=True,text=True,check=True)
        self.assertEqual(completed.stdout.strip(),manifest['bundle_id'])
        with self.assertRaisesRegex(ValueError,'output_exists'):self.build()

    def test_runtime_or_acceptance_failure_never_blesses_partial_output(self):
        self.actual['source_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'differs_from_accepted'):self.build()
        self.assertEqual(json.loads((self.output/'BUILD-STOPPED.json').read_bytes())['status'],'STOPPED')
        self.assertFalse((self.output/'trial-manifest.json').exists())
        with self.assertRaisesRegex(ValueError,'output_exists'):self.build()

    def test_changed_runtime_archive_rejected_before_destination_creation(self):
        self.python.write_bytes(self.python.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'archive_hash_changed'):self.build()
        self.assertFalse(self.output.exists());self.probe.assert_not_called()

    def test_external_standard_library_or_different_python_version_is_rejected(self):
        self.actual['import_search_paths'].append(str(self.root/'external-python/Lib'))
        with self.assertRaisesRegex(ValueError,'external_python_search'):self.build()
        self.assertFalse((self.output/'trial-manifest.json').exists())

    def test_changed_source_archive_after_extraction_stops_without_publishing_manifest(self):
        def change_after_extraction(unused):
            self.python.write_bytes(self.python.read_bytes()+b'concurrent source change')
            return self.actual
        self.probe.side_effect=change_after_extraction
        with self.assertRaisesRegex(ValueError,'archive_changed_during'):self.build()
        self.assertTrue((self.output/'BUILD-STOPPED.json').exists())
        self.assertFalse((self.output/'trial-manifest.json').exists())

    def test_source_bindings_require_clean_accepted_bytes_and_committed_shell(self):
        root=self.root/'source';root.mkdir()
        names=[*trial.BUILD_FILES,*('outputs/hakimi_trade_electron/'+n for n in trial.APP_FILES),
            'src/hakimi_research/__init__.py','pyproject.toml','setup.py','requirements.research.lock']
        for name in names:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(name.encode())
        receipt=deepcopy(self.receipt)
        receipt['installed_runtime']['source_identity']['file_hashes']={'__init__.py':trial.sha((root/'src/hakimi_research/__init__.py').read_bytes())}
        receipt['build_inputs_sha256']={n:trial.sha((root/n).read_bytes()) for n in ['pyproject.toml','setup.py','requirements.research.lock']}
        committed={n:(root/n).read_bytes() for n in names}
        def git(argv,**unused):
            return b'b'*40+b'\n' if argv[1]=='rev-parse' else committed[argv[-1].split(':',1)[1]]
        with patch.object(trial.subprocess,'check_output',side_effect=git):
            self.assertEqual(REAL_PROVENANCE(root,receipt)['packaging_git']['status'],'CLEAN')
            for name,reason in [('src/hakimi_research/__init__.py','product_differs'),('setup.py','build_definition_changed'),
                                ('outputs/hakimi_trade_electron/research-main.js','not_committed')]:
                with self.subTest(name=name):
                    (root/name).write_bytes(committed[name]+b'changed')
                    with self.assertRaisesRegex(ValueError,reason):REAL_PROVENANCE(root,receipt)
                    (root/name).write_bytes(committed[name])
            receipt['installed_runtime']['source_identity']['build_receipt']['git']['status']='DIRTY'
            with self.assertRaisesRegex(ValueError,'clean_accepted_build'):REAL_PROVENANCE(root,receipt)

    def test_partial_acceptance_is_not_turned_into_trial_acceptance(self):
        self.receipt['test_execution']['errors']=1
        with self.assertRaises(ValueError):self.build()
        self.assertFalse(self.output.exists());self.probe.assert_not_called()

    def test_zip_paths_case_duplicates_and_links_are_rejected(self):
        cases=[['../outside'],['C:/outside'],['Case.txt','case.txt'],['name.'],['NUL.txt'],['a|b']]
        for index,names in enumerate(cases):
            path=self.root/('bad-'+str(index)+'.zip')
            with zipfile.ZipFile(path,'w') as archive:
                for name in names:archive.writestr(name,b'never extracted')
            with self.subTest(names=names),self.assertRaises(ValueError):trial.archive_members(path)
        # Windows ZipInfo normally normalizes backslashes while writing; replace
        # only equal-length archive member names to exercise a foreign ZIP.
        backslash=self.root/'backslash.zip'
        with zipfile.ZipFile(backslash,'w') as archive:archive.writestr('good!outside',b'never extracted')
        backslash.write_bytes(backslash.read_bytes().replace(b'good!outside',b'good\\outside'))
        with self.assertRaisesRegex(ValueError,'path_invalid'):trial.archive_members(backslash)
        link=self.root/'link.zip'
        with zipfile.ZipFile(link,'w') as archive:
            info=zipfile.ZipInfo('link');info.external_attr=(0o120777<<16);archive.writestr(info,b'../outside')
        with self.assertRaisesRegex(ValueError,'link'):trial.archive_members(link)

    def test_wheel_record_and_locked_dependency_version_are_required(self):
        path=next(self.wheels.glob('*.whl'))
        with zipfile.ZipFile(path,'a') as archive:archive.writestr('extra.py',b'undeclared')
        with self.assertRaisesRegex(ValueError,'record_inventory'):self.build()
        self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()
