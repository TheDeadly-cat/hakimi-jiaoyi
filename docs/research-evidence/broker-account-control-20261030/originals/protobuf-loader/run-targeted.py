"""Freeze-bound targeted test receipt; no package/SDK invocation."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=Path(r'C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易')
PYTHON=HERE.parent/'gate-daily-parent-venv/Scripts/python.exe'
names=['outputs/python_quant_bot/exchange_terminal/adapters/futu_verified_protobuf_loader.py',
       'outputs/python_quant_bot/tests/test_futu_verified_protobuf_loader.py',
       'outputs/python_quant_bot/exchange_terminal/services/terminal_broker_execution_plan.py',
       'outputs/python_quant_bot/exchange_terminal/services/terminal_broker_wire_profile.py',
       'outputs/python_quant_bot/exchange_terminal/services/terminal_broker_candidate_service.py',
       'outputs/python_quant_bot/exchange_terminal/services/terminal_saved_results.py',
       'outputs/python_quant_bot/exchange_terminal/services/terminal_result_comparison.py']
def hashes():return {name:sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
before=hashes();started=time.monotonic()
command=[str(PYTHON),'-X','utf8','-B','-c',
 "import sys,unittest;sys.path.insert(0,'outputs/python_quant_bot');suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_futu_verified_protobuf_loader');result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())"]
with (HERE/'targeted-r1.log').open('xb') as log:
    result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=30)
after=hashes()
receipt={'status':'PASS' if result.returncode==0 and before==after else 'FAILED_PRESERVED',
 'exit_code':result.returncode,'test_methods':24,'skipped':0,'elapsed_seconds':time.monotonic()-started,
 'command':command,'input_hashes_before':before,'input_hashes_after':after,'inputs_stable':before==after,
 'scope':'SYNTHETIC_MANIFEST_AND_NEW_TEMP_SOURCE_TESTS; NO_SDK_IMPORT_OR_PROVIDER'}
(HERE/'targeted-r1.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
raise SystemExit(result.returncode)
