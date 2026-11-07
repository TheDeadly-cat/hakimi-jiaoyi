from pathlib import Path
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import subprocess
import sys
import time

P = Path(r'C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易')
E = Path(r'C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029')
O = E / 'broker-response-worker-integrated-20261030-r1'
assert not O.exists(), 'fresh result directory required'
assert Path(sys.executable).resolve() == E / 'gate-daily-parent-venv/Scripts/python.exe'
O.mkdir()

def save(name, value):
    with (O/name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

roots = ['src/hakimi_research', 'outputs/python_quant_bot/exchange_terminal', 'outputs/python_quant_bot/tests',
         'outputs/python_quant_bot/vendor/research', 'outputs/hakimi_trade_electron', 'tools', 'tests/repository_only']

def inventory():
    names = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *roots], cwd=P).decode().split('\0')
    names = {n for n in names if n and Path(n).suffix.lower() in {'.py', '.js', '.cjs', '.json', '.html', '.css', '.toml', '.lock'}
             and not any(part in {'node_modules', '__pycache__', 'runtime'} for part in Path(n).parts)}
    names.update(['pyproject.toml', 'setup.py', 'requirements.research.lock'])
    return {n: sha256((P/n).read_bytes()).hexdigest() for n in sorted(names)}

before = inventory()
save('inputs-before.json', before)
environment = {k:v for k,v in os.environ.items() if not k.upper().startswith(('HAKIMI_', 'PYTHON'))}
environment.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
                   PYTHON=sys.executable, HAKIMI_TEST_PYTHON=sys.executable, HAKIMI_SKIP_LOCAL_AI_ENV='1',
                   HAKIMI_LOAD_LOCAL_AI_ENV='0', HAKIMI_LOCAL_ONLY='1', HAKIMI_RUNTIME_READ_ONLY='1')
save('environment.json', {'python': sys.executable, 'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=P).decode().strip(),
    'status': 'DIRTY_SOURCE_BYTES_EXPLICITLY_HASHED', 'expected_terminal_tests': 709,
    'desktop_repeated': False, 'desktop_reason': 'No JavaScript, frontend, host runtime or existing service route changed.',
    'real_sdk_probe_repeated': False, 'native_or_market_acceptance': False})
commands = {
    'terminal': [sys.executable, '-B', 'tools/run_terminal_contracts.py'],
    'packaging': [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests/repository_only', '-p', 'test_windows_terminal.py', '-v'],
    'gate_runner': [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_terminal_ci_gate.py', '-v'],
}

def run(name, command):
    env = dict(environment)
    data = O / ('new-fixtures-' + name)
    data.mkdir()
    env.update(HAKIMI_RUNTIME_DIR=str(data/'legacy'), HAKIMI_QUANT_WORKSPACE_DIR=str(data/'quant'),
               FUTU_PY_APPDATA=str(data/'unused-sdk'), HAKIMI_RESEARCH_HOME=str(data/'research'))
    started = time.monotonic()
    with (O/(name+'.log')).open('xb') as stream:
        result = subprocess.run(command, cwd=P, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
    receipt = {'gate': name, 'exit_code': result.returncode, 'seconds': round(time.monotonic()-started,3), 'command': command}
    print(json.dumps(receipt), flush=True)
    return receipt

results=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    futures={pool.submit(run,name,cmd):name for name,cmd in commands.items()}
    for future in as_completed(futures):
        try:
            results.append(future.result())
        except Exception as error:
            results.append({'gate':futures[future], 'exit_code':-1, 'error':str(error)})
after=inventory()
save('inputs-after.json',after)
lines=(O/'terminal.log').read_text(encoding='utf-8').splitlines()
terminal=json.loads([line for line in lines if line.startswith('{')][-1])
counts={}
for name,expected in [('packaging',15),('gate_runner',4)]:
    text=(O/(name+'.log')).read_text(encoding='utf-8')
    found=re.search(r'^Ran (\d+) tests? in ',text,re.M)
    counts[name]={'expected':expected,'actual':int(found[1]) if found else None,
                  'ok':bool(re.search(r'^OK\s*$',text,re.M)) and 'skipped=' not in text}
ok=(before==after and all(r['exit_code']==0 for r in results) and terminal['tests_run']==709
    and terminal['terminal_contracts']=='PASS' and terminal['skipped']==terminal['errors']==terminal['failures']==0
    and all(c['actual']==c['expected'] and c['ok'] for c in counts.values()))
summary={'status':'PASS' if ok else 'FAIL_OR_CHANGED_INPUTS','source_input_count':len(before),'source_inputs_unchanged':before==after,
         'gates':results,'terminal':terminal,'other_counts':counts,
         'changed_inputs':[n for n in set(before)|set(after) if before.get(n)!=after.get(n)],
         'scope':'NEW_SYNTHETIC_FIXTURES_ONLY_NO_SDK_OR_GUI_OR_EXTERNAL_ACCOUNT',
         'current_package_unchanged':'a235e8a/dev3-r4', 'new_candidate_built':False}
save('summary.json',summary)
print(json.dumps({'status':summary['status'],'tests':terminal['tests_run'],'source_inputs':len(before),'stable':before==after}),flush=True)
raise SystemExit(0 if ok else 1)
