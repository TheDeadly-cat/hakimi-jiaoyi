"""Build a new self-contained Windows x64 trial from accepted, local bytes.

No downloads, global installs, old-data copying, shortcut replacement or research
calculation. Full CPython, Electron and the exact locked dependency wheels are
vendored in a new directory. Existing local-desktop/venv contracts stay intact.
"""
from __future__ import annotations
import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
from prepare_workbench_desktop import INSTALLATION_PROBE, _clean_env
from release_wheel_bundle import export_bundle

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = {
    'python': dict(version='3.14.6', sha256='75afa83f93b284d19040e24bc440ab741c09582c0d5310504d607a4e08c3dbaf',
        url='https://www.python.org/ftp/python/3.14.6/python-3.14.6-amd64.zip'),
    'electron': dict(version='31.7.7', sha256='e91986dd243d55947e6c5d3fad21795562ec21fa0eec5e95f7e28c830571467f',
        url='https://github.com/electron/electron/releases/download/v31.7.7/electron-v31.7.7-win32-x64.zip'),
}
APP_FILES = ('trial-main.js', 'research-main.js', 'desktop-security-policy.js')
BUILD_FILES = ('tools/build_windows_trial.py', 'tools/prepare_workbench_desktop.py', 'tools/release_wheel_bundle.py',
               'outputs/hakimi_trade_electron/package.json')
MAX_UNPACKED = 2 * 1024**3


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def write_new(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def archive_members(path):
    """Inspect all names and limits before extraction; never follow archive links."""
    require(Path(path).is_file() and not Path(path).is_symlink(), 'trial_archive_regular_file_required')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(0 < len(entries) <= 30000 and sum(e.file_size for e in entries) <= MAX_UNPACKED,
                'trial_archive_size_limit')
        seen = set()
        for item in entries:
            require(item.orig_filename == item.filename, 'trial_archive_path_invalid')
            name = item.filename.rstrip('/')
            parts = name.split('/')
            require(name and not re.search(r'[<>:"\\|?*\x00-\x1f]', name) and not name.startswith('/')
                and all(part and part not in {'.', '..'} and not part.endswith((' ', '.'))
                    and not re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part)
                    for part in parts), 'trial_archive_path_invalid')
            require(name.casefold() not in seen, 'trial_archive_duplicate_path')
            seen.add(name.casefold())
            require(not stat.S_ISLNK(item.external_attr >> 16) and not item.flag_bits & 1, 'trial_archive_link_or_encryption')
        return [item.filename for item in entries if not item.is_dir()]


def extract_checked(path, target, *, transform=None):
    names = archive_members(path)
    target = Path(target).resolve()
    with zipfile.ZipFile(path) as archive:
        for name in names:
            relative = transform(name) if transform else name
            destination = (target / relative).resolve()
            require(destination.is_relative_to(target), 'trial_archive_destination_escape')
            write_new(destination, archive.read(name))


def inspect_wheel(path, *, name=None, version=None):
    names = archive_members(path)
    require(not any('.data/' in value for value in names), 'trial_wheel_data_layout_not_supported')
    with zipfile.ZipFile(path) as archive:
        metadata_names = [n for n in names if n.endswith('.dist-info/METADATA')]
        records = [n for n in names if n.endswith('.dist-info/RECORD')]
        require(len(metadata_names) == len(records) == 1, 'trial_wheel_metadata_invalid')
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        normalized = re.sub(r'[-_.]+', '-', metadata['Name']).lower()
        require(name is None or normalized == re.sub(r'[-_.]+', '-', name).lower(), 'trial_dependency_name_changed')
        require(version is None or metadata['Version'] == version, 'trial_dependency_version_changed')
        observed = {}
        for row in csv.reader(io.StringIO(archive.read(records[0]).decode('utf-8'))):
            require(len(row) == 3 and row[0] not in observed, 'trial_wheel_record_invalid')
            observed[row[0]] = row[1:]
        require(set(observed) == set(names), 'trial_wheel_record_inventory_changed')
        for member in names:
            expected, size = observed[member]
            raw = archive.read(member)
            if member == records[0]:
                require(expected == size == '', 'trial_wheel_record_self_hash_invalid')
            else:
                require(expected == 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
                    and size == str(len(raw)), 'trial_wheel_record_hash_changed')
        return dict(name=normalized, version=metadata['Version'], sha256=sha(Path(path).read_bytes()), filename=Path(path).name,
            license_files=[n for n in names if any(word in n.lower() for word in ('license', 'licence', 'copying', 'notice'))])


def packaging_provenance(root, receipt):
    """Bind the accepted product bytes and the independently committed desktop shell."""
    root = Path(root)
    source = receipt['installed_runtime']['source_identity']
    require(source['build_receipt']['git']['status'] == 'CLEAN', 'trial_requires_clean_accepted_build')
    for name, expected in source['file_hashes'].items():
        require(sha((root/'src/hakimi_research'/name).read_bytes()) == expected, 'trial_current_product_differs_from_accepted_wheel:' + name)
    for name, expected in receipt['build_inputs_sha256'].items():
        require(name in {'pyproject.toml', 'setup.py', 'requirements.research.lock'}
            and sha((root/name).read_bytes()) == expected, 'trial_accepted_build_definition_changed:' + name)
    names = [*BUILD_FILES, *('outputs/hakimi_trade_electron/'+name for name in APP_FILES)]
    hashes = {name: sha((root/name).read_bytes()) for name in names}
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
        require(re.fullmatch('[0-9a-f]{40}', commit) is not None, 'trial_packaging_commit_invalid')
        for name, expected in hashes.items():
            blob = subprocess.check_output(['git', 'show', commit+':'+name], cwd=root, stderr=subprocess.PIPE)
            require(sha(blob) == expected, 'trial_packaging_file_not_committed:' + name)
    except subprocess.CalledProcessError as error:
        raise ValueError('trial_packaging_files_require_committed_bytes') from error
    return dict(accepted_product_git=source['build_receipt']['git'], accepted_product_source_sha256=source['content_sha256'],
        packaging_git=dict(commit=commit, status='CLEAN', scope='ONLY_PACKAGED_DESKTOP_FILES_AND_BUILD_DEFINITIONS'), files_sha256=hashes)


def probe_installation(output):
    python = output / 'runtime/python/python.exe'
    probe = output / 'resources/app/runtime-probe.py'
    result = subprocess.run([str(python), '-I', '-B', '-X', 'utf8', str(probe)], cwd=output,
        env=_clean_env(), capture_output=True, text=True, encoding='utf-8', timeout=60)
    require(result.returncode == 0, 'trial_private_runtime_probe_failed:' + result.stderr[-1000:])
    return json.loads(result.stdout)


def build(receipt, python_archive, electron_archive, wheelhouse, output, *, root=ROOT):
    output, wheelhouse, root = Path(output).resolve(), Path(wheelhouse).resolve(), Path(root).resolve()
    require(os.name == 'nt', 'trial_build_requires_windows_x64_host')
    archive_path = Path(str(output) + '.zip')
    require(not output.exists() and not archive_path.exists(), 'trial_output_exists_use_new_destination')
    require(not output.is_relative_to(root), 'trial_output_must_be_outside_checkout')
    provenance = packaging_provenance(root, receipt)
    archives = {'python': Path(python_archive), 'electron': Path(electron_archive)}
    for kind, path in archives.items():
        require(sha(path.read_bytes()) == RUNTIMES[kind]['sha256'], 'trial_runtime_archive_hash_changed:' + kind)
        archive_members(path)
    with zipfile.ZipFile(archives['python']) as archive:
        declared = json.loads(archive.read('__install__.json'))
        require(declared['sort-version'] == RUNTIMES['python']['version'] and declared['url'] == RUNTIMES['python']['url'],
                'trial_python_distribution_identity_changed')
        require(all(name in archive.namelist() for name in ('python.exe', 'python314.dll', 'LICENSE.txt', 'vcruntime140.dll')), 'trial_python_distribution_incomplete')
    with zipfile.ZipFile(archives['electron']) as archive:
        require(archive.read('version').decode().strip().lstrip('v') == RUNTIMES['electron']['version'], 'trial_electron_version_changed')
        require(all(name in archive.namelist() for name in ('electron.exe', 'LICENSE', 'LICENSES.chromium.html')), 'trial_electron_distribution_incomplete')
    expected_packages = receipt['installed_runtime']['environment_verified']['packages']
    dependencies = []
    wheels = list(wheelhouse.glob('*.whl'))
    require(len(wheels) == len(expected_packages), 'trial_dependency_wheel_inventory_changed')
    for path in wheels:
        require(path.name.endswith(('-cp314-cp314-win_amd64.whl', '-none-any.whl')), 'trial_dependency_platform_not_cp314_windows_x64')
        info = inspect_wheel(path)
        require(info['name'] in expected_packages and expected_packages[info['name']]['required'] == info['version'], 'trial_dependency_pin_changed')
        require(info['license_files'], 'trial_dependency_license_notice_missing')
        dependencies.append((path, info))
    require({info['name'] for _, info in dependencies} == set(expected_packages), 'trial_dependency_set_changed')
    inspect_wheel(receipt['wheel'], name='hakimi-research')
    # Existing acceptance gate checks ordinary wheel bytes, complete test/workflow
    # receipts and clean provenance before creating the first output directory.
    public = export_bundle(receipt, output / 'accepted-wheel')
    try:
        extract_checked(archives['python'], output / 'runtime/python')
        extract_checked(archives['electron'], output, transform=lambda name: 'HakimiWorkbench.exe' if name == 'electron.exe' else name)
        site = output / 'runtime/python/Lib/site-packages'
        for path, _ in dependencies:
            extract_checked(path, site)
            write_new(output / 'wheelhouse' / path.name, path.read_bytes())
        extract_checked(receipt['wheel'], site)
        for name in APP_FILES:
            write_new(output / 'resources/app' / name, (root / 'outputs/hakimi_trade_electron' / name).read_bytes())
            require(sha((output/'resources/app'/name).read_bytes()) == provenance['files_sha256']['outputs/hakimi_trade_electron/'+name],
                'trial_shell_changed_during_packaging')
        write_new(output / 'resources/app/package.json', canonical(dict(name='hakimi-research-trial', version=public['wheel'].split('-')[1], main='trial-main.js')) + b'\n')
        # Import both extension packages during metadata verification, never run a strategy.
        write_new(output / 'resources/app/runtime-probe.py', ('import numpy, pandas\n' + INSTALLATION_PROBE).encode('utf-8'))
        actual = probe_installation(output)
        source, environment = receipt['installed_runtime']['source_identity'], receipt['installed_runtime']['environment_verified']
        expected = dict(version=public['wheel'].split('-')[1], source_status='BUILD_VERIFIED', source_sha256=source['content_sha256'],
            build_receipt=source['build_receipt'], environment_status='VERIFIED', lock_sha256=environment['lock_sha256'])
        require(all(actual.get(key) == value for key, value in expected.items()), 'trial_vendored_installation_differs_from_accepted_wheel')
        require(Path(actual['python']).resolve() == output / 'runtime/python/python.exe'
            and Path(actual['package_directory']).resolve() == site / 'hakimi_research'
            and actual['isolated_venv'] is False and actual['package_inside_venv'] is True, 'trial_runtime_not_private_and_relocatable')
        prefix = output/'runtime/python'
        require(actual['python_version'] == RUNTIMES['python']['version']
            and Path(actual['python_prefix']).resolve() == prefix and Path(actual['python_base_prefix']).resolve() == prefix
            and type(actual['import_search_paths']) is list and actual['import_search_paths']
            and all(type(p) is str and p and Path(p).resolve().is_relative_to(prefix) for p in actual['import_search_paths']),
            'trial_external_python_search_path_or_version')
        licenses = []
        for kind, runtime_archive in archives.items():
            prefix_name = 'runtime/python/' if kind == 'python' else ''
            members = archive_members(runtime_archive)
            paths = [prefix_name+name for name in members if any(word in name.lower() for word in ('license', 'licence', 'copying', 'notice'))]
            licenses.append(dict(component=kind, version=RUNTIMES[kind]['version'], source=RUNTIMES[kind]['url'],
                notices={name:sha((output/name).read_bytes()) for name in paths}))
        for _, info in dependencies:
            paths = ['runtime/python/Lib/site-packages/'+name for name in info['license_files']]
            licenses.append(dict(component=info['name'], version=info['version'], source_wheel_sha256=info['sha256'],
                notices={name:sha((output/name).read_bytes()) for name in paths}))
        write_new(output/'THIRD-PARTY-NOTICES.json', canonical(dict(schema_version='trial-third-party-notices-v1', components=licenses,
            original_notice_bytes_retained=True, project_license_grant='NO_NEW_PROJECT_LICENSE_GRANTED_BY_THIS_INDEX'))+b'\n')
        write_new(output/'THIRD-PARTY-NOTICES.txt', ('Third-party notices are retained without modification.\n'
            'This index does not grant an additional license for the Hakimi project.\n\n'+
            '\n\n'.join(item['component']+' '+item['version']+'\n'+'\n'.join(item['notices']) for item in licenses)+'\n').encode('utf-8'))
        write_new(output / 'README.txt', (
            '哈基米量化工作台 Windows x64 试用版\n\n'
            '将整个 ZIP 解压到一个新文件夹，双击 HakimiWorkbench.exe。无需安装 Python、Node 或 Electron。\n'
            '不要只复制 exe，也不要覆盖原有版本。首次打开会检查程序文件。\n'
            '数据保存在当前用户的 LocalAppData\\HakimiTradeTrial\\workspaces 下，与旧工作台分开。\n'
            '关闭后从同一 exe 重开即可查看已保存记录。工作台菜单可以复制诊断信息并打开数据文件夹。\n'
            '这是开发试用包，不是签名正式安装器。当前尚未完成没有开发环境的独立 Windows 机器验收。\n'
        ).encode('utf-8'))
        for kind, runtime_archive in archives.items():
            require(sha(runtime_archive.read_bytes()) == RUNTIMES[kind]['sha256'], 'trial_runtime_archive_changed_during_packaging')
        for dependency, info in dependencies:
            require(sha(dependency.read_bytes()) == info['sha256']
                and sha((output/'wheelhouse'/dependency.name).read_bytes()) == info['sha256'],
                'trial_dependency_changed_during_packaging')
        require(sha(Path(receipt['wheel']).read_bytes()) == receipt['wheel_sha256'], 'trial_accepted_wheel_changed_during_packaging')
        require(packaging_provenance(root, receipt) == provenance, 'trial_sources_changed_during_packaging')
        files = {p.relative_to(output).as_posix(): sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}
        core = dict(schema_version='research-windows-trial-v1', platform='win32-x64',
            scope='SELF_CONTAINED_DEVELOPMENT_TRIAL_NOT_SIGNED_RELEASE', version=expected['version'],
            python='runtime/python/python.exe', package_directory='runtime/python/Lib/site-packages/hakimi_research',
            desktop_entry='HakimiWorkbench.exe', probe='resources/app/runtime-probe.py', expected_installation=expected,
            runtimes=RUNTIMES, dependency_wheels=[info for _, info in sorted(dependencies)], source_provenance=provenance,
            third_party_notices='THIRD-PARTY-NOTICES.json',
            workspace_policy='LOCALAPPDATA/HakimiTradeTrial/workspaces/<first_20_bundle_id>; exclusive marker binds full bundle_id',
            maximum_relative_program_path_utf16_characters=max(len(name.encode('utf-16-le'))//2 for name in files),
            no_external_runtime_required=True, clean_windows_acceptance='NOT_PERFORMED',
            economic_calculations_during_packaging=0, files=files)
        manifest = {**core, 'bundle_id': sha(canonical(core))}
        write_new(output / 'trial-manifest.json', canonical(manifest) + b'\n')
        with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(output.rglob('*')):
                if path.is_file():
                    entry = zipfile.ZipInfo(path.relative_to(output).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, path.read_bytes())
        return dict(status='BUILT_AND_PRIVATE_RUNTIME_VERIFIED', bundle_id=manifest['bundle_id'],
            output=str(output), archive=str(archive_path), archive_sha256=sha(archive_path.read_bytes()),
            manifest_sha256=sha((output/'trial-manifest.json').read_bytes()),
            clean_windows_acceptance='NOT_PERFORMED', new_economic_runs=0)
    except Exception as error:
        write_new(output / 'BUILD-STOPPED.json', canonical(dict(status='STOPPED', reason=str(error),
            automatic_retry=False, original_artifacts_retained=True, new_economic_runs=0)) + b'\n')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('acceptance', 'python-archive', 'electron-archive', 'wheelhouse', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.acceptance.read_text(encoding='utf-8-sig'))
    print(json.dumps(build(receipt, args.python_archive, args.electron_archive, args.wheelhouse, args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
