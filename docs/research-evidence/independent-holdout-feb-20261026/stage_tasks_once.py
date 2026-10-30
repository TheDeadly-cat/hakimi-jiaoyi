"""Import two sealed inputs and create tasks through the existing workbench API.

No research run or cost validation is dispatched here. Native UI runs the tasks.
"""
import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import urllib.request

from hakimi_research.documents import digest
from hakimi_research.equity_dataset import verify_equity_snapshot

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', required=True)
    parser.add_argument('--protocol-sha256', required=True)
    args = parser.parse_args()
    origin = args.origin
    assert re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', origin)
    design_raw = (ROOT / 'protocol.json').read_bytes()
    assert sha256(design_raw).hexdigest() == args.protocol_sha256
    design = json.loads(design_raw)
    assert design['plan_hash'] == digest({k: v for k, v in design.items() if k != 'plan_hash'})
    assert sha256(Path(__file__).read_bytes()).hexdigest() == design['tool_hashes'][
        'docs/research-evidence/independent-holdout-feb-20261026/stage_tasks_once.py']
    prepared = Path(design['acquisition_output_path']).resolve()
    assert prepared == (ROOT / 'prepared-r1').resolve()
    receipt = read(prepared / 'preparation.json')
    assert receipt['status'] == 'READY' and receipt['plan_hash'] == design['plan_hash']
    assert receipt['design_sha256'] == args.protocol_sha256
    for name, expected in receipt['files'].items():
        path = (prepared / name).resolve()
        assert path.is_relative_to(prepared) and sha256(path.read_bytes()).hexdigest() == expected
    folder = ROOT / 'workbench-staging'
    folder.mkdir(exist_ok=False)
    with urllib.request.urlopen(origin + '/', timeout=5) as response:
        html = response.read().decode('utf-8')
    token = re.search(r'<meta name="hakimi-session" content="([^"]+)"', html).group(1)
    headers = {'Origin': origin, 'X-Hakimi-Token': token, 'Content-Type': 'application/json'}
    with urllib.request.urlopen(urllib.request.Request(origin + '/api/state', headers=headers), timeout=20) as response:
        state = json.load(response)
    assert Path(state['workspace']).resolve() == (ROOT / 'workspace').resolve()
    assert state['runtime_guard']['loaded_source_sha256'] == design['execution_runtime_source_sha256']
    assert state['runtime_guard']['restart_required'] is False

    def act(symbol, action, **values):
        op = 'blind-' + design['plan_hash'][:20] + '-' + symbol.lower() + '-' + action
        payload = dict(action=action, operation_id=op, **values)
        write(folder / (op + '-request.json'), payload)
        request = urllib.request.Request(origin + '/api/action', data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        write(folder / (op + '-response.json'), result)
        assert result['ok'] is True, result
        return result['result']

    results = {}
    for symbol in ('NDAQ', 'KO'):
        entry = receipt['symbols'][symbol]
        snapshot_file = Path(entry['snapshot_path']).resolve()
        assert snapshot_file.is_relative_to(prepared)
        snapshot_raw = snapshot_file.read_bytes()
        assert sha256(snapshot_raw).hexdigest() == entry['snapshot_sha256']
        snapshot = verify_equity_snapshot(json.loads(snapshot_raw))
        assert snapshot['security']['symbol'] == symbol and snapshot['snapshot_id'] == entry['snapshot_id']
        assert [row['date'] for row in snapshot['sessions']] == design['context_dates'] + design['score_sessions']
        spec_raw = Path(entry['spec_path']).read_bytes()
        assert sha256(spec_raw).hexdigest() == entry['spec_sha256']
        spec = json.loads(spec_raw)
        for key in ('strategy', 'initial_cash', 'fee_rate', 'slippage_pct', 'risk', 'end_policy', 'execution_policy', 'quantity_policy', 'purpose'):
            assert spec[key] == design[key], key
        imported = act(symbol, 'import_input', content_base64=base64.b64encode(snapshot_raw).decode('ascii'))
        task = act(symbol, 'create_task', title=symbol + ' 独立历史留出 · 2026年2月 · 固定5/10',
            strategy='price.dual_ma@1', snapshot=imported['ref'], params=design['strategy']['params'],
            score_start=design['score_start'], score_end=design['score_end'],
            **{key: design[key] for key in ('initial_cash', 'fee_rate', 'slippage_pct', 'risk')})
        results[symbol] = dict(snapshot_ref=imported['ref'], snapshot_id=snapshot['snapshot_id'],
            snapshot_sha256=entry['snapshot_sha256'], task_ref=task['ref'], task_id=task['task_id'])
    summary = dict(status='TASKS_STAGED_NOT_RUN', recorded_at=datetime.now(timezone.utc).isoformat(),
        plan_hash=design['plan_hash'], design_sha256=args.protocol_sha256, symbols=results,
        workbench_origin=origin, new_economic_runs=0, saved_actions=4)
    write(folder / 'staging.json', summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
