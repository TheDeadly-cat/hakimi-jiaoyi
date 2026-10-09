"""Normal installed entry for configurable offline strategy tasks."""
from __future__ import annotations
import argparse
from importlib.resources import files
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from uuid import uuid4

from .documents import read_document
from .benchmarks import BUY_AND_HOLD_POLICY, STANDARD_RISK_POLICY
from .equity_cli import _deny_network
from .equity_dataset import build_equity_snapshot, save_equity_snapshot, load_equity_snapshot
from .equity_event_context import RULE_VERSION, verify_event_context
from .equity_research import PERMISSIONS
from .collection_import import import_collection, verify_bundle
from .offline_app import check_task, run_task, recover_report, replay_run, resume_calculation, write_new, describe_run, portable_location, resolve_location
from .source_layout import default_artifact_root
from .strategy_registry import definition, strategies, effective_parameters, new_task_parameters


def build_task_document(path, *, strategy, snapshot, event_context=None, params=None, score_start=None, score_end=None,
                initial_cash=10000, fee_rate=0.0008, slippage_pct=0.0005, risk=None, output_dir=None):
    path, snapshot = Path(path).resolve(), Path(snapshot).resolve()
    data = load_equity_snapshot(snapshot)
    entry = definition(strategy)
    params = params if params is not None else new_task_parameters(entry['engine_strategy'])
    from .experiment import required_context
    warmup = required_context(entry['engine_strategy'], params)
    if not score_start and len(data.document['sessions']) <= warmup:
        raise ValueError('insufficient_demo_or_data_warmup:choose_parameters_or_supply_more_sessions')
    spec = dict(schema_version='us-equity-experiment-spec-v1', name=entry['title'], snapshot_id=data.snapshot_id,
        score_start_session=score_start or data.document['sessions'][warmup]['date'],
        score_end_session=score_end or data.document['sessions'][-1]['date'], strategy=dict(name=entry['engine_strategy'],params=params),
        initial_cash=initial_cash, fee_rate=fee_rate, slippage_pct=slippage_pct,
        risk=default_risk(strategy) if risk is None else risk,
        end_policy='MARK_TO_MARKET', purpose='SYNTHETIC_REGRESSION' if data.document['evidence_kind']=='SYNTHETIC_TEST' else 'DESCRIPTIVE_DEVELOPMENT',
        quantity_policy='FRACTIONAL_SHARES_RESEARCH_APPROXIMATION',
        execution_policy=BUY_AND_HOLD_POLICY if entry['engine_strategy']=='buy_and_hold' else STANDARD_RISK_POLICY)
    context_path = Path(event_context).resolve() if event_context else None
    if entry['event_rule']:
        if context_path is None:raise ValueError('event_strategy_context_required')
        context = verify_event_context(read_document(context_path))
        spec.update(schema_version='us-equity-experiment-spec-v2',event_context_hash=context['context_hash'],event_rule=RULE_VERSION)
    def location(file):
        root = path.parent.parent if path.parent.name == 'tasks' else path.parent
        return portable_location(file, path.parent, relative_root=root)
    task=dict(schema_version='hakimi-offline-task-v1',strategy=strategy,state='ENABLED',snapshot=location(snapshot),
        event_context=location(context_path) if context_path else None,experiment=spec,
        output_dir=location(Path(output_dir).resolve()) if output_dir else '../runs')
    # Validate before publishing a usable task configuration.
    from .strategy_registry import validate_strategy
    from .equity_research import inspect_equity_inputs
    validate_configuration(spec)
    inspect_equity_inputs(data,validate_strategy(strategy,spec,read_document(context_path) if context_path else None),
        event_context=read_document(context_path) if context_path else None)
    return task


def create_task(path, **options):
    task = build_task_document(path, **options)
    write_new(path,task)
    return Path(path).resolve()


def default_risk(strategy):
    return dict(max_position_pct=1.0 if definition(strategy)['engine_strategy']=='buy_and_hold' else 0.25,
        max_single_loss_pct=0.03, max_daily_loss_pct=1.0, max_leverage=1.0, min_cash_pct=0.0)


def validate_runtime_configuration(spec):
    """Validate inputs against the actual models, without a strategy decision.

    Constructing a validation-only Signal checks its native numeric domains;
    no strategy, backtest, broker, order or signal publication is started.
    """
    from .config import RiskConfig
    from .risk import RiskManager
    from .models import Signal
    from .equity_research import EquityExperimentSpec
    checked = EquityExperimentSpec.from_document(spec).document
    risk, strategy = checked['risk'], checked['strategy']
    RiskManager(RiskConfig(**risk))
    params = effective_parameters(strategy['name'], strategy['params'])
    if strategy['name'] == 'buy_and_hold':
        Signal.buy('configuration validation only', params['target_position_pct'])
    else:
        Signal.buy('configuration validation only', params['position_pct'],
            stop_loss_pct=params['stop_loss_pct'], take_profit_pct=params['take_profit_pct'])
    return params


def validate_configuration(spec):
    risk = spec['risk']
    keys = set(default_risk('price.dual_ma@1'))
    if type(risk) is not dict or set(risk) != keys:
        raise ValueError('risk_fields_must_explicitly_match_supported_configuration')
    resolved = validate_runtime_configuration(spec)
    if risk['max_leverage'] != 1:
        raise ValueError('spot_mvp_requires_leverage_one')
    if spec['strategy']['name'] == 'buy_and_hold':
        if risk != default_risk('price.buy_and_hold@1'):
            raise ValueError('benchmark_has_no_active_risk_controls:use_allocation_parameter_and_fixed_benchmark_policy')
    else:
        position = resolved['position_pct']
        if position > risk['max_position_pct'] or position > 1 - risk['min_cash_pct']:
            raise ValueError('position_request_conflicts_with_risk_limit_or_cash_reserve')
        if resolved['stop_loss_pct'] > risk['max_single_loss_pct']:
            raise ValueError('stop_request_exceeds_maximum_stop_distance')


def configuration_view(spec):
    params, risk = spec['strategy']['params'], spec['risk']
    benchmark = spec['strategy']['name'] == 'buy_and_hold'
    resolved = effective_parameters(spec['strategy']['name'], params)
    effective = dict(initial_cash=spec['initial_cash'], fee_rate=spec['fee_rate'], slippage_pct=spec['slippage_pct'],
        allocation_pct=resolved['target_position_pct'] if benchmark else resolved['position_pct'],
        max_position_pct=risk['max_position_pct'], min_cash_pct=risk['min_cash_pct'], leverage=1,
        stop_loss_pct=None if benchmark else min(resolved['stop_loss_pct'], risk['max_single_loss_pct']),
        take_profit_pct=None if benchmark else resolved['take_profit_pct'],
        max_daily_loss_pct=None if benchmark else risk['max_daily_loss_pct'])
    effective['strategy_parameters'] = dict(resolved)
    if not benchmark:
        effective['strategy_parameters'].update(position_pct=effective['allocation_pct'],stop_loss_pct=effective['stop_loss_pct'],take_profit_pct=effective['take_profit_pct'])
    return dict(requested={k: spec[k] for k in ['strategy','risk','initial_cash','fee_rate','slippage_pct','score_start_session','score_end_session']},
        effective=effective, risk_policy=spec['execution_policy'],
        exit_rule='单次首次开盘入场；无策略止损/止盈、不加仓、不重新入场；期末按市值' if benchmark else '均线退出＋有效止损/止盈；期末按市值',
        notes=['请求和生效值以保存的配置为准；实际下单数量受现金、费用和成交约束，可低于目标仓位。',
            '买入持有的单笔/日亏损字段为固定兼容值，不启用主动保护。' if benchmark else '单笔约束是止损价格距离，不保证账户损失上限；日亏损约束仅阻止新 BUY，按 UTC 日计算。'])


def initialize_demo(workspace):
    workspace=Path(workspace).resolve()
    if workspace.exists():raise ValueError('workspace_already_exists:choose_a_new_directory')
    workspace.mkdir(parents=True)
    resources=files('hakimi_research').joinpath('resources')
    data=workspace/'data';data.mkdir()
    raw=resources.joinpath('trade-demo.csv').read_bytes()
    metadata=resources.joinpath('trade-demo-import.json').read_bytes()
    snapshot=build_equity_snapshot(raw,metadata)
    snapshot_path=save_equity_snapshot(snapshot,data)
    (data/'event-context.json').write_bytes(resources.joinpath('trade-demo-event-context.json').read_bytes())
    for name in ['prior','actual']:(data/(name+'.html')).write_bytes(resources.joinpath('trade-demo-source-'+name+'.html').read_bytes())
    (data/'source-manifest.json').write_bytes(resources.joinpath('trade-demo-source-manifest.json').read_bytes())
    params=dict(fast_window=2,slow_window=4,position_pct=0.25,stop_loss_pct=0.03,take_profit_pct=0.06)
    tasks=[]
    for name,strategy in [('price','price.dual_ma@1'),('event','event.earnings_schedule@1')]:
        task=create_task(workspace/'tasks'/(name+'.json'),strategy=strategy,snapshot=snapshot_path,
            event_context=data/'event-context.json' if name=='event' else None,params=params)
        tasks.append(str(task))
    write_new(workspace/'workspace.json',dict(schema_version='hakimi-offline-workspace-v1',data_kind='SYNTHETIC_TEST',
        tasks=['tasks/price.json','tasks/event.json'],source_manifest='data/source-manifest.json',execution_permission=dict(PERMISSIONS)))
    return dict(workspace=str(workspace),tasks=tasks,source_manifest=str(data/'source-manifest.json'),
        message='虚构测试数据已准备。请选择任务、检查输入，再运行；示例收益不代表真实市场表现。')


def initialize_empty(workspace):
    workspace=Path(workspace).resolve()
    if workspace.exists():raise ValueError('workspace_already_exists:choose_a_new_directory')
    for directory in [workspace/'data',workspace/'tasks']:directory.mkdir(parents=True)
    write_new(workspace/'workspace.json',dict(schema_version='hakimi-offline-workspace-v1',data_kind='USER_PROVIDED',
        tasks=[],source_manifest=None,execution_permission=dict(PERMISSIONS)))
    return dict(workspace=str(workspace),message='空白工作区已创建，可导入自有数据并创建任务。')


def print_result(view):
    entry = view['strategy']
    print(entry['title'] + '；策略版本 ' + entry['version'] + '；状态 ' + entry['state'])
    print('证券 ' + view['symbol'] + '；评分区间 ' + view['score_start'] + ' 至 ' + view['score_end'] + '；数据类型 ' + view['data_kind'])
    print('BUY 意图 ' + str(view['buy_intents']) + '；成交 ' + str(view['fill_count']) + '；事件过滤阻挡 ' + str(view['blocked_new_buys']))
    print(f"净收益率 {view['total_return']*100:+.4f}%；扣费后损益 {view['net_pnl']:+.2f} 美元；费用 {view['total_fees']:.2f} 美元")
    print(f"已实现 {view['realized_pnl']:+.2f}；未实现 {view['unrealized_pnl']:+.2f}；期末持仓 {view['open_position_qty']:.4f} 股")
    print('信号与阻挡原因：' + '；'.join(view['reasons']))
    print('有效杠杆 1；碎股、比例费用和固定滑点为模型近似；公司行为记账暂不支持。')
    for note in view['limitations']:print('模型边界：' + note)
    print('输出位置：' + view['output_directory'])
    print('任务身份：' + view['task_id'] + '；报告身份：' + view['report_hash'])


def request_browser_view(page):
    """Optional bounded dispatch; a browser is not required to read results."""
    import subprocess
    try:
        result = subprocess.run([sys.executable, '-I', '-B', '-c',
            'import sys,webbrowser; sys.exit(0 if webbrowser.open(sys.argv[1]) else 1)', Path(page).resolve().as_uri()],
            capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        print('浏览器打开请求未完成；结果已在终端显示，HTML 文件保留。')
        return False
    if result.returncode != 0:
        print('浏览器未能打开；结果已在终端显示，HTML 文件保留。')
        return False
    print('已请求浏览器打开 HTML 报告。')
    return True


def remember_run(workspace, directory):
    workspace, directory = Path(workspace).resolve(), Path(directory).resolve()
    location = portable_location(directory, workspace)
    record = dict(schema_version='hakimi-recent-run-v1', run_directory=location,
        location_kind='ABSOLUTE' if Path(location).is_absolute() else 'WORKSPACE_RELATIVE',
        recorded_at=datetime.now(timezone.utc).isoformat())
    path = workspace / ('last-run-' + directory.name + '-' + uuid4().hex + '.json')
    write_new(path, record)
    return path


def recent_runs(workspace):
    workspace = Path(workspace).resolve()
    found, warnings = {}, []
    for record_path in workspace.glob('last-run-*.json'):
        try:
            record = read_document(record_path)
            if set(record) == {'run_directory'}:
                directory = resolve_location(workspace, record['run_directory'])
            else:
                if set(record) != {'schema_version', 'run_directory', 'location_kind', 'recorded_at'} or record['schema_version'] != 'hakimi-recent-run-v1':
                    raise ValueError('recent_run_record_schema_invalid')
                path = Path(record['run_directory'])
                if record['location_kind'] == 'ABSOLUTE' and path.is_absolute():
                    directory = path.resolve()
                elif record['location_kind'] == 'WORKSPACE_RELATIVE' and not path.is_absolute() and not path.drive:
                    directory = resolve_location(workspace, record['run_directory'])
                    if not directory.is_relative_to(workspace):raise ValueError('recent_relative_run_escapes_workspace')
                else:raise ValueError('recent_run_location_kind_conflict')
            if not directory.is_dir():raise ValueError('recent_run_directory_missing:' + str(directory))
            found[directory] = max(found.get(directory, 0), record_path.stat().st_mtime_ns)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            warnings.append(record_path.name + ': ' + str(exc))
    roots={workspace/'runs'}
    from .task_manager import list_tasks, resolve_managed_task
    for original_path in list_tasks(workspace):
        try:
            task_path=resolve_managed_task(original_path,inspect_only=True)
            task=read_document(task_path)
            if task.get('schema_version') not in {'hakimi-offline-task-v1','hakimi-offline-task-v2'}:raise ValueError('task_schema_invalid')
            roots.add(resolve_location(task_path.parent,task['output_dir']))
        except (ValueError,OSError,KeyError,TypeError) as exc:warnings.append(original_path.name+': '+str(exc))
    for root in roots:
        try:
            for directory in root.glob('run-*'):
                if directory.is_dir():found.setdefault(directory.resolve(),directory.stat().st_mtime_ns)
        except OSError as exc:warnings.append(str(root)+': '+str(exc))
    return sorted(found, key=lambda path: found[path], reverse=True), warnings


def choose_item(items, prompt, label=str):
    for index,item in enumerate(items,1):print(str(index)+' '+label(item))
    number=int(input(prompt))
    if not 1<=number<=len(items):raise ValueError('selection_number_out_of_range')
    return items[number-1]


def configuration_form(options):
    """Normal entry for every supported configuration; blank preserves values."""
    options=dict(options)
    entries=list(strategies())
    old=options.get('strategy')
    print('策略编号：'+'；'.join(str(i)+' '+definition(k)['title'] for i,k in enumerate(entries,1)))
    number=int(input('策略（默认 '+str(entries.index(old)+1 if old else 1)+'）：') or str(entries.index(old)+1 if old else 1))
    if not 1<=number<=len(entries):raise ValueError('strategy_number_out_of_range')
    key=entries[number-1];entry=definition(key)
    params=dict(options.get('params',{})) if old==key else {}
    existing = old==key
    defaults = effective_parameters(entry['engine_strategy'],params) if existing else new_task_parameters(entry['engine_strategy'])
    labels={'target_position_pct':('目标仓位比例',float),'fast_window':('快均线周期',int),
        'slow_window':('慢均线周期',int),'position_pct':('每次目标仓位比例',float),
        'stop_loss_pct':('止损价格距离比例',float),'take_profit_pct':('止盈比例',float)}
    for name in entry['parameters']:
        label,cast=labels[name];value=defaults[name]
        answer=input(label+'（默认 '+str(value)+'）：').strip()
        # Blank preserves the existing raw omission as well as explicit values.
        if answer or not existing:
            params[name]=cast(answer or str(value))
    risk=dict(options.get('risk',default_risk(key))) if old==key else default_risk(key)
    if entry['engine_strategy']!='buy_and_hold':
        for name,label in [('max_position_pct','最大仓位比例'),('max_single_loss_pct','最大止损价格距离比例'),
                ('max_daily_loss_pct','UTC 日亏损后暂停新买入比例'),('min_cash_pct','最低现金比例')]:
            value=risk[name];risk[name]=float(input(label+'（默认 '+str(value)+'）：') or str(value))
    else:print('买入持有使用固定基准政策：无策略止损/止盈，单次入场、不加仓或重新入场。')
    print('有效杠杆固定为 1；期末按市值。')
    for name,label,default in [('initial_cash','初始本金（美元）',10000),('fee_rate','比例手续费',0.0008),('slippage_pct','固定滑点比例',0.0005)]:
        value=options.get(name,default);options[name]=float(input(label+'（默认 '+str(value)+'）：') or str(value))
    for name,label in [('score_start','评分首个交易日'),('score_end','评分最后交易日')]:
        value=options.get(name)
        text=input(label+' YYYY-MM-DD（默认 '+str(value or '按数据及预热选择，创建后固定')+'）：').strip()
        options[name]=text or value
    if entry['event_rule']:
        value=options.get('event_context')
        text=input('事件上下文路径（默认 '+str(value or '必填')+'）：').strip().strip('"')
        options['event_context']=Path(text) if text else value
    else:options['event_context']=None
    options.update(strategy=key,params=params,risk=risk)
    return options


def print_configuration(config, prefix=''):
    requested,effective=config['requested'],config['effective']
    print(prefix+f"本金 {requested['initial_cash']} / {effective['initial_cash']} 美元；手续费 {requested['fee_rate']} / {effective['fee_rate']}；滑点 {requested['slippage_pct']} / {effective['slippage_pct']}（请求 / 生效）")
    print(prefix+'评分区间 '+requested['score_start_session']+' 至 '+requested['score_end_session'])
    labels={'target_position_pct':'目标仓位','fast_window':'快均线周期','slow_window':'慢均线周期',
        'position_pct':'每次目标仓位','stop_loss_pct':'止损距离','take_profit_pct':'止盈距离'}
    actual=effective['strategy_parameters']
    for name,value in actual.items():
        request=requested['strategy']['params'].get(name,'策略默认')
        print(prefix+labels.get(name,name)+' '+str(request)+' / '+str(value))
    for name,label in [('max_position_pct','最大仓位'),('max_single_loss_pct','最大止损距离'),('max_daily_loss_pct','UTC 日亏损暂停新 BUY'),('min_cash_pct','最低现金')]:
        value=effective.get(name,requested['risk'][name] if effective['stop_loss_pct'] is not None else None)
        print(prefix+label+' '+str(requested['risk'][name])+' / '+('未应用' if value is None else str(value)))
    print(prefix+'有效杠杆 1；退出：'+config['exit_rule'])
    for note in config['notes']:print(prefix+note)


def print_task(view):
    print('任务：'+view.get('title','旧格式任务')+'；状态 '+view['state']+'；策略 '+definition(view['strategy'])['title'])
    if view.get('revisions'):
        for i,revision in enumerate(view['revisions'],1):print('版本 '+str(i)+' '+revision+('（当前选择）' if revision==view['selected_revision'] else ''))
        print('正在查看：'+view['viewed_revision'])
    print('请求配置与生效配置：');print_configuration(view['configuration'])
    if view.get('uncommitted_versions_retained'):print('有未提交版本保留，未激活：'+', '.join(view['uncommitted_versions_retained']))


def wizard(workspace):
    """A small terminal menu over the same commands; no separate GUI or runner."""
    workspace=Path(workspace).resolve()
    print('哈基米交易 · 离线量化工具候选\n数据、账户和订单边界以任务及报告为准。')
    last_run=None
    while True:
        print('\n1 创建虚构示例  2 检查任务  3 运行任务  4 查看结果  5 重放  6 恢复页面  7 公告原件核对  8 恢复中断计算  9 导入自有 CSV  10 创建旧格式任务  11 可选浏览器查看  12 运行历史  13 任务版本与启停  14 结果对照  15 创建可管理任务  0 退出')
        try:choice=input('选择：').strip()
        except EOFError:return 0
        if choice=='0':return 0
        try:
            if choice=='1':
                print(initialize_demo(workspace)['message']);continue
            if choice=='9':
                if not (workspace/'workspace.json').is_file():initialize_empty(workspace)
                csv_path=Path(input('行情 CSV 路径：').strip().strip('"'))
                metadata_path=Path(input('完整元数据 JSON 路径：').strip().strip('"'))
                snapshot=build_equity_snapshot(csv_path.read_bytes(),metadata_path.read_bytes())
                print('数据已导入：'+str(save_equity_snapshot(snapshot,workspace/'data')));continue
            if not (workspace/'workspace.json').is_file():
                raise ValueError('workspace_not_ready:先选择 1 或使用 init 创建工作区')
            if choice in {'2','3'}:
                from .task_manager import list_tasks, describe_task
                tasks=list_tasks(workspace)
                for index,path in enumerate(tasks,1):print(str(index)+' '+path.stem)
                number=int(input('任务编号：'))
                if number<1 or number>len(tasks):raise ValueError('task_number_out_of_range')
                task=tasks[number-1]
                if choice=='2':
                    context=check_task(task);print('输入检查通过；策略 '+context['definition']['title']+'；任务 '+context['task_id'])
                    print_task(describe_task(task))
                else:
                    last_run=run_task(task);print('运行完成。结果目录：'+str(last_run))
                    try:remember_run(workspace,last_run)
                    except (ValueError,OSError) as exc:print('运行已成功；最近运行记录未保存：'+str(exc))
            elif choice in {'4','5','6','8','11','12'}:
                if choice in {'8','12'}:
                    candidates,warnings=recent_runs(workspace)
                    for warning in warnings:print('历史记录不可用：'+warning)
                    for index,path in enumerate(candidates,1):print(str(index)+' '+path.name+('（已有报告）' if (path/'report.json').is_file() else '（未保存报告）'))
                    number=int(input('选择历史运行编号：' if choice=='12' else '选择要恢复的运行编号：'))
                    if number<1 or number>len(candidates):raise ValueError('run_number_out_of_range')
                    last_run=candidates[number-1]
                elif last_run is None:
                    candidates,warnings=recent_runs(workspace)
                    for warning in warnings:print('历史记录不可用：'+warning)
                    if not candidates:raise ValueError('no_started_run:先运行任务')
                    last_run=candidates[0]
                if choice=='5':print('重放通过。回执 '+replay_run(last_run)['receipt_hash'])
                elif choice=='8':
                    page,runs=resume_calculation(last_run);print('恢复完成，新增离线计算 '+str(runs)+' 次；原失败保留。报告：'+str(page))
                else:
                    report=recover_report(last_run);print('报告：'+str(report))
                    if choice in {'4','11','12'}:print_result(describe_run(last_run))
                    if choice=='11':request_browser_view(report)
            elif choice=='7':
                from .source_task import prepare,report
                packet=prepare(workspace/'data/source-manifest.json');print('公告核对页面：'+str(report(packet)))
            elif choice=='10':
                snapshots=sorted((workspace/'data').rglob('equity_dataset_*.json'))
                chosen_snapshot=choose_item(snapshots,'选择数据编号：',lambda p:p.relative_to(workspace).as_posix())
                key=choose_item(list(strategies()),'选择策略编号：',lambda k:definition(k)['title']+' '+k)
                entry=definition(key)
                if entry['engine_strategy']=='buy_and_hold':params=dict(target_position_pct=float(input('目标仓位比例（默认 0.25）：') or '0.25'))
                else:params=dict(fast_window=int(input('快均线周期（默认 20）：') or '20'),slow_window=int(input('慢均线周期（默认 60）：') or '60'),position_pct=0.25,stop_loss_pct=0.03,take_profit_pct=0.06)
                event=input('事件上下文 JSON 路径：').strip().strip('"') if entry['event_rule'] else None
                name=input('任务文件名（默认 new-task）：').strip() or 'new-task'
                import re
                if not re.fullmatch(r'[\w-]{1,64}',name):raise ValueError('task_name_invalid')
                print('任务已保存：'+str(create_task(workspace/'tasks'/(name+'.json'),strategy=key,snapshot=chosen_snapshot,event_context=event,params=params)))
            elif choice=='15':
                from .task_manager import create_family, describe_task
                snapshots=sorted((workspace/'data').rglob('equity_dataset_*.json'))
                for index,path in enumerate(snapshots,1):print(str(index)+' '+path.relative_to(workspace).as_posix())
                number=int(input('选择数据编号：'))
                if number<1 or number>len(snapshots):raise ValueError('data_number_out_of_range')
                chosen_snapshot=snapshots[number-1]
                options=configuration_form(dict(snapshot=chosen_snapshot))
                name=input('任务名称（默认 new-task）：').strip() or 'new-task'
                import re
                if not re.fullmatch(r'[\w-]{1,64}',name):raise ValueError('task_name_invalid')
                family=workspace/'tasks'/name
                create_family(family,**options);print('任务版本已保存：'+str(family));print_task(describe_task(family))
            elif choice=='13':
                from .task_manager import list_tasks, describe_task, version_options, create_family, revise_family, change_state, select_version
                task=choose_item(list_tasks(workspace),'任务编号：',lambda p:p.stem)
                print_task(describe_task(task))
                action=input('1 查看  2 修改为新版本  3 复制为新任务  4 暂停  5 启用  6 选择历史版本：').strip()
                if action in {'2','3'}:
                    options=configuration_form(version_options(task))
                    if action=='3':
                        name=input('新任务名称：').strip();target=workspace/'tasks'/name
                        create_family(target,**options);print_task(describe_task(target))
                    else:
                        if not task.is_dir():raise ValueError('legacy_task_is_immutable:copy_into_managed_task_first')
                        revise_family(task,**options);print_task(describe_task(task))
                elif action in {'4','5','6'}:
                    if not task.is_dir():raise ValueError('legacy_task_is_immutable:copy_into_managed_task_first')
                    if action=='6':select_version(task,int(input('历史版本编号：')))
                    else:change_state(task,'PAUSED' if action=='4' else 'ENABLED')
                    print_task(describe_task(task))
                elif action!='1':raise ValueError('task_action_invalid')
            elif choice=='14':
                from .task_comparison import compare_runs, print_comparison
                candidates,warnings=recent_runs(workspace)
                for warning in warnings:print('历史记录不可用：'+warning)
                saved=[p for p in candidates if (p/'report.json').is_file()]
                for index,path in enumerate(saved,1):print(str(index)+' '+path.name)
                numbers=[int(v.strip()) for v in input('对照运行编号（至少两个，逗号分隔）：').split(',')]
                if any(not 1<=n<=len(saved) for n in numbers):raise ValueError('run_number_out_of_range')
                view=compare_runs([saved[n-1] for n in numbers]);target=workspace/'comparisons'/(view['comparison_hash']+'.json')
                write_new(target,view);print_comparison(view);print('对照已保存：'+str(target))
            else:print('请输入菜单中的编号。')
        except (ValueError,OSError,KeyError,TypeError) as exc:print('操作停止：'+str(exc))


def main(argv=None):
    sys.addaudithook(_deny_network)
    parser=argparse.ArgumentParser(description='哈基米交易：策略配置、任务版本、离线运行与结果对照（M2-1 候选）')
    commands=parser.add_subparsers(dest='command')
    commands.add_parser('capabilities')
    commands.add_parser('strategies')
    for name in ['init','wizard']:
        p=commands.add_parser(name);p.add_argument('--workspace',type=Path,default=default_artifact_root()/'trade-offline')
        if name=='init':p.add_argument('--demo',action='store_true')
    for name in ['check','run']:
        p=commands.add_parser(name);p.add_argument('--task',required=True,type=Path)
        if name=='run':p.add_argument('--output-dir',type=Path,help='Explicit new output location; existing incomplete directories are retained.')
    for name in ['report','recover','replay']:
        p=commands.add_parser(name);p.add_argument('--run-dir',required=True,type=Path)
        if name=='recover':p.add_argument('--resume-calculation',action='store_true',help='Explicitly resume a stopped new-app computation only after its OS lock is released.')
    p=commands.add_parser('collection-import')
    for name in ['collection','first','continuation']:p.add_argument('--'+name,type=Path)
    p.add_argument('--calendar-original',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--synthetic',action='store_true',help='Only explicitly labelled fictional receipts; never real market evidence.')
    p=commands.add_parser('bundle-check');p.add_argument('--bundle',required=True,type=Path)
    p=commands.add_parser('snapshot-import')
    for name in ['csv','metadata','output-dir']:p.add_argument('--'+name,required=True,type=Path)
    for command in ['task-create','task-copy','task-revise']:
        p=commands.add_parser(command);p.add_argument('--task',required=True,type=Path)
        p.add_argument('--snapshot',required=command=='task-create',type=Path)
        p.add_argument('--strategy',required=command=='task-create')
        p.add_argument('--event-context',type=Path);p.add_argument('--parameters',type=Path);p.add_argument('--risk',type=Path)
        p.add_argument('--score-start');p.add_argument('--score-end');p.add_argument('--initial-cash',type=float)
        p.add_argument('--fee-rate',type=float);p.add_argument('--slippage-pct',type=float)
        if command=='task-create':
            p.add_argument('--managed',action='store_true',help='Create an immutable version family under workspace/tasks/name.')
            p.add_argument('--output-dir',type=Path)
        if command=='task-copy':p.add_argument('--from-task',required=True,type=Path)
    p=commands.add_parser('task-show');p.add_argument('--task',required=True,type=Path)
    p=commands.add_parser('tasks');p.add_argument('--workspace',required=True,type=Path)
    p=commands.add_parser('task-state');p.add_argument('--task',required=True,type=Path);p.add_argument('--state',required=True,choices=['ENABLED','PAUSED'])
    p=commands.add_parser('task-select');p.add_argument('--task',required=True,type=Path);p.add_argument('--version',required=True,type=int)
    p=commands.add_parser('compare');p.add_argument('--run-dir',required=True,action='append',type=Path);p.add_argument('--output',type=Path)
    p=commands.add_parser('source');p.add_argument('source_arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv)
    try:
        if args.command is None:return wizard(default_artifact_root()/'trade-offline')
        if args.command=='wizard':return wizard(args.workspace)
        if args.command=='capabilities':
            output=dict(product_target='交易量化工具',current_milestone='M2_1_STRATEGY_TASKS_CANDIDATE',
                supported=['Configurable strategy and risk parameters','Immutable task revisions, copy, selection and pause','Verified saved-run comparison',
                    'Existing price and earnings-schedule strategies','CSV and completed/resumed local quote import',
                    'Offline source workflow','Existing canonical engine and risk','Results, replay and saved-report recovery'],
                not_implemented=['Portfolio-level shared-capital risk','Supervised incremental monitoring','Broker execution in this entry'],
                execution_permission=dict(PERMISSIONS))
        elif args.command=='strategies':output=strategies()
        elif args.command=='init':output=initialize_demo(args.workspace) if args.demo else initialize_empty(args.workspace)
        elif args.command=='check':
            context=check_task(args.task);output=dict(status='INPUTS_CHECKED_NO_SIMULATION',task_id=context['task_id'],
                strategy=context['definition'],scoring=context['protocol'],output_dir=str(context['output']),execution_permission=dict(PERMISSIONS))
            output['configuration']=configuration_view(context['semantics']['experiment'])
        elif args.command=='run':
            directory=run_task(args.task,output_dir=args.output_dir);output=dict(status='OFFLINE_RUN_SAVED',run_directory=str(directory),report=str(recover_report(directory)))
        elif args.command in {'report','recover'}:
            page,runs=resume_calculation(args.run_dir) if getattr(args,'resume_calculation',False) else (recover_report(args.run_dir),0)
            output=dict(status='RETAINED_REPORT_RENDERED' if runs==0 else 'INTERRUPTED_CALCULATION_RECOVERED',report=str(page),new_economic_runs=runs,result_view=describe_run(args.run_dir))
        elif args.command=='replay':output=replay_run(args.run_dir)
        elif args.command=='collection-import':
            directory=import_collection(calendar_original=args.calendar_original,output_dir=args.output_dir,collection=args.collection,
                first=args.first,continuation=args.continuation,synthetic=args.synthetic)
            output=dict(status='LOCAL_QUOTES_IMPORTED',bundle=str(directory),**verify_bundle(directory))
        elif args.command=='bundle-check':output=dict(status='PORTABLE_BUNDLE_CHECKED',**verify_bundle(args.bundle))
        elif args.command=='snapshot-import':
            snapshot=build_equity_snapshot(args.csv.read_bytes(),args.metadata.read_bytes())
            output=dict(snapshot=str(save_equity_snapshot(snapshot,args.output_dir)),snapshot_id=snapshot.snapshot_id)
        elif args.command in {'task-create','task-copy','task-revise'}:
            from .task_manager import create_family, revise_family, version_options, describe_task
            options={name:getattr(args,name) for name in ['strategy','snapshot','event_context','score_start','score_end','initial_cash','fee_rate','slippage_pct'] if getattr(args,name) is not None}
            if args.parameters:options['params']=read_document(args.parameters)
            if args.risk:options['risk']=read_document(args.risk)
            if args.command=='task-revise':
                revise_family(args.task,**options);output=describe_task(args.task)
            elif args.command=='task-copy':
                original=version_options(args.from_task)
                if 'strategy' in options and options['strategy']!=original['strategy']:
                    original.update(params=None,risk=None,event_context=None)
                original.update(options);create_family(args.task,**original);output=describe_task(args.task)
            elif args.managed:
                create_family(args.task,output_dir=args.output_dir,**options);output=describe_task(args.task)
            else:
                path=create_task(args.task,output_dir=args.output_dir,**options)
                output=dict(task=str(path),task_id=check_task(path)['task_id'],configuration=configuration_view(read_document(path)['experiment']))
        elif args.command in {'task-show','tasks'}:
            from .task_manager import describe_task, list_tasks
            output=describe_task(args.task) if args.command=='task-show' else [describe_task(p) for p in list_tasks(args.workspace)]
        elif args.command in {'task-state','task-select'}:
            from .task_manager import change_state, select_version, describe_task
            if args.command=='task-state':change_state(args.task,args.state)
            else:select_version(args.task,args.version)
            output=describe_task(args.task)
        elif args.command=='compare':
            from .task_comparison import compare_runs
            output=compare_runs(args.run_dir,output=args.output)
        else:
            from .source_task import main as source_main
            return source_main(args.source_arguments)
        print(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False));return 0
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='STOPPED',error=str(exc),execution_permission=dict(PERMISSIONS)),ensure_ascii=False));return 1


if __name__=='__main__':raise SystemExit(main())
