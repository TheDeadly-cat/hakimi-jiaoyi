"""One isolated, manifest-bound real protobuf probe; no Futu import or context."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(r'C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易')
PACKAGE = Path(r'C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029\HakimiTrade-0.7.0.dev3-candidate-r4')
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / 'run'
MANIFEST_SHA = 'a8cfa662966720fe8d46dbcdd966c08f359dc2af591168f8b8652c96be9d198a'
WHEEL_SHA = 'a3bc7609fc7b60c0ca3cd2971bc8b81819338d3c88ad25d1bd3f647d781554b5'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert not OUTPUT.exists(), 'Never overwrite prior probe output'
manifest_file = PACKAGE / 'terminal-manifest.json'
assert sha(manifest_file) == MANIFEST_SHA
manifest = json.loads(manifest_file.read_bytes())
assert manifest['source_provenance']['git']['commit'] == 'a235e8a2f1a303f72b99797105956bcd88cba399'
wheel = PACKAGE.parent / 'terminal-wheelhouse-r1/futu_api-10.7.6708-py3-none-any.whl'
assert sha(wheel) == WHEEL_SHA
runtime = PACKAGE / 'runtime/python'
# Verify all private Python runtime members up front, including executable,
# extension modules, archive and generated pb2 source. This never imports them.
runtime_verified = {}
for relative, expected in manifest['files'].items():
    if relative.startswith('runtime/python/'):
        path = PACKAGE / relative
        assert path.is_file() and sha(path) == expected, relative
        runtime_verified[relative] = expected
assert (runtime / 'python.exe').relative_to(PACKAGE).as_posix() in runtime_verified
pb = runtime / 'Lib/site-packages/futu/common/pb'
names = ['InitConnect', 'GetGlobalState', 'Trd_GetAccList', 'Trd_GetFunds', 'Trd_GetPositionList',
         'Qot_GetStaticInfo', 'Qot_GetSecuritySnapshot', 'Trd_PlaceOrder', 'Trd_GetOrderList',
         'Trd_ModifyOrder', 'Trd_GetOrderFee']
pending, allowed_pb = [name + '_pb2' for name in names], {}
while pending:
    name = pending.pop()
    if name in allowed_pb:
        continue
    path = pb / (name + '.py')
    relative = path.relative_to(PACKAGE).as_posix()
    assert sha(path) == manifest['files'][relative]
    allowed_pb[name] = {'path': str(path), 'sha256': sha(path)}
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            pending.extend(alias.name for alias in node.names if alias.name.endswith('_pb2'))
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith('_pb2'):
            pending.append(node.module)
relative_sources = [
    'exchange_terminal/__init__.py', 'exchange_terminal/services/__init__.py',
    'exchange_terminal/services/terminal_broker_candidate_service.py',
    'exchange_terminal/services/terminal_broker_execution_plan.py',
    'exchange_terminal/services/terminal_broker_wire_profile.py',
    'exchange_terminal/services/terminal_broker_execution_journal.py',
    'exchange_terminal/services/terminal_broker_response_facts.py',
    'exchange_terminal/services/terminal_saved_results.py',
    'exchange_terminal/services/terminal_result_comparison.py',
    'exchange_terminal/adapters/futu_us_equity_simulate_wire_v2.py',
    'tests/__init__.py', 'tests/test_terminal_broker_execution_plan.py',
    'tests/test_terminal_broker_wire_profile.py', 'tests/test_futu_us_equity_simulate_wire_v2.py']
source_hashes = {str(ROOT / 'outputs/python_quant_bot' / name): sha(ROOT / 'outputs/python_quant_bot' / name)
                 for name in relative_sources}
child = HERE / 'probe-child.py'
spec = {'source': str(ROOT), 'package': str(PACKAGE), 'output': str(OUTPUT),
        'package_manifest_sha256': MANIFEST_SHA, 'wheel_sha256': WHEEL_SHA,
        'package_source_commit': manifest['source_provenance']['git']['commit'],
        'parent_git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'parent_git_status': subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=ROOT, text=True, encoding='utf-8'),
        'source_hashes': source_hashes, 'allowed_pb': allowed_pb,
        'private_runtime_members_verified': len(runtime_verified),
        'child_sha256': sha(child), 'runner_sha256': sha(Path(__file__)),
        'source_scope': 'EXPLICIT_PARENT_SOURCE_AND_SYNTHETIC_ACTION_FIXTURES_NOT_INSTALLED_FACTS_SERVICE'}
OUTPUT.mkdir()
for name in ('temp', 'profile'):
    (OUTPUT / name).mkdir()
with (OUTPUT / 'invocation.json').open('x', encoding='utf-8') as stream:
    json.dump(spec, stream, ensure_ascii=False, indent=2)
env = dict(os.environ)
for key in list(env):
    if key.upper().startswith(('PYTHON', 'HAKIMI_', 'FUTU_')):
        env.pop(key)
env.update(TEMP=str(OUTPUT/'temp'), TMP=str(OUTPUT/'temp'), HOME=str(OUTPUT/'profile'),
           USERPROFILE=str(OUTPUT/'profile'), APPDATA=str(OUTPUT/'profile'), LOCALAPPDATA=str(OUTPUT/'profile'))
command = [str(runtime/'python.exe'), '-I', '-S', '-B', '-X', 'utf8', str(child), str(OUTPUT/'invocation.json')]
start = time.monotonic()
result, failure = None, None
try:
    with (OUTPUT/'stdout.log').open('xb') as stdout, (OUTPUT/'stderr.log').open('xb') as stderr:
        result = subprocess.run(command, cwd=OUTPUT, env=env, stdout=stdout, stderr=stderr, timeout=60)
except BaseException as error:
    failure = {'type': type(error).__name__, 'message': str(error)[:600]}
    raise
finally:
    receipt = {'command': command, 'exit_code': None if result is None else result.returncode,
               'elapsed_seconds': time.monotonic()-start, 'failure': failure,
               'source_hashes_unchanged': all(sha(Path(path)) == digest for path, digest in source_hashes.items()),
               'manifest_unchanged': sha(manifest_file) == MANIFEST_SHA,
               'status': 'CHILD_EXIT_ZERO' if result is not None and result.returncode == 0 else 'FAILED_PRESERVED'}
    with (OUTPUT/'runner-result.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt))
raise SystemExit(result.returncode)
