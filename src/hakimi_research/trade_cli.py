"""Normal installed entry for the M1 offline quantitative-tool candidate."""
from __future__ import annotations
import argparse
from importlib.resources import files
import json
from pathlib import Path
import sys

from .documents import read_document
from .benchmarks import BUY_AND_HOLD_POLICY, STANDARD_RISK_POLICY
from .equity_cli import _deny_network
from .equity_dataset import build_equity_snapshot, save_equity_snapshot, load_equity_snapshot
from .equity_event_context import RULE_VERSION, verify_event_context
from .equity_research import PERMISSIONS
from .collection_import import import_collection, verify_bundle
from .offline_app import check_task, run_task, recover_report, replay_run, resume_calculation, write_new
from .source_layout import default_artifact_root
from .strategy_registry import definition, strategies


def create_task(path, *, strategy, snapshot, event_context=None, params=None, score_start=None, score_end=None,
                initial_cash=10000, fee_rate=0.0008, slippage_pct=0.0005, output_dir=None):
    path, snapshot = Path(path).resolve(), Path(snapshot).resolve()
    data = load_equity_snapshot(snapshot)
    entry = definition(strategy)
    params = params if params is not None else (dict(target_position_pct=0.25) if entry['engine_strategy']=='buy_and_hold'
        else dict(fast_window=20, slow_window=60, position_pct=0.25, stop_loss_pct=0.03, take_profit_pct=0.06))
    warmup = 1 if entry['engine_strategy']=='buy_and_hold' else int(params.get('slow_window',60))+2
    if not score_start and len(data.document['sessions']) <= warmup:
        raise ValueError('insufficient_demo_or_data_warmup:choose_parameters_or_supply_more_sessions')
    spec = dict(schema_version='us-equity-experiment-spec-v1', name=entry['title'], snapshot_id=data.snapshot_id,
        score_start_session=score_start or data.document['sessions'][warmup]['date'],
        score_end_session=score_end or data.document['sessions'][-1]['date'], strategy=dict(name=entry['engine_strategy'],params=params),
        initial_cash=initial_cash, fee_rate=fee_rate, slippage_pct=slippage_pct,
        risk=dict(max_position_pct=1.0 if entry['engine_strategy']=='buy_and_hold' else 0.25,max_single_loss_pct=0.03,max_daily_loss_pct=1.0,max_leverage=1.0,min_cash_pct=0.0),
        end_policy='MARK_TO_MARKET', purpose='SYNTHETIC_REGRESSION' if data.document['evidence_kind']=='SYNTHETIC_TEST' else 'DESCRIPTIVE_DEVELOPMENT',
        quantity_policy='FRACTIONAL_SHARES_RESEARCH_APPROXIMATION',
        execution_policy=BUY_AND_HOLD_POLICY if entry['engine_strategy']=='buy_and_hold' else STANDARD_RISK_POLICY)
    context_path = Path(event_context).resolve() if event_context else None
    if entry['event_rule']:
        if context_path is None:raise ValueError('event_strategy_context_required')
        context = verify_event_context(read_document(context_path))
        spec.update(schema_version='us-equity-experiment-spec-v2',event_context_hash=context['context_hash'],event_rule=RULE_VERSION)
    def location(file):
        import os
        try:return Path(os.path.relpath(file,path.parent)).as_posix()
        except ValueError:return str(file)  # Different Windows drive: explicit location, not content identity.
    task=dict(schema_version='hakimi-offline-task-v1',strategy=strategy,state='ENABLED',snapshot=location(snapshot),
        event_context=location(context_path) if context_path else None,experiment=spec,
        output_dir=location(Path(output_dir).resolve()) if output_dir else '../runs')
    # Validate before publishing a usable task configuration.
    from .strategy_registry import validate_strategy
    from .equity_research import inspect_equity_inputs
    inspect_equity_inputs(data,validate_strategy(strategy,spec,read_document(context_path) if context_path else None),
        event_context=read_document(context_path) if context_path else None)
    write_new(path,task)
    return path


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


def wizard(workspace):
    """A small terminal menu over the same commands; no separate GUI or runner."""
    workspace=Path(workspace).resolve()
    print('哈基米交易 · 离线量化工具候选\n数据、账户和订单边界以任务及报告为准。')
    last_run=None
    while True:
        print('\n1 创建虚构示例  2 检查任务  3 运行任务  4 查看报告  5 重放  6 恢复页面  7 公告原件核对  8 恢复中断计算  9 导入自有 CSV  10 创建策略任务  0 退出')
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
                tasks=sorted((workspace/'tasks').glob('*.json'))
                for index,path in enumerate(tasks,1):print(str(index)+' '+path.stem)
                number=int(input('任务编号：'))
                if number<1 or number>len(tasks):raise ValueError('task_number_out_of_range')
                task=tasks[number-1]
                if choice=='2':
                    context=check_task(task);print('输入检查通过；策略 '+context['definition']['title']+'；任务 '+context['task_id'])
                else:
                    last_run=run_task(task);print('运行完成。结果目录：'+str(last_run))
                    write_new(workspace/('last-run-'+last_run.name+'.json'),dict(run_directory=last_run.relative_to(workspace).as_posix()))
            elif choice in {'4','5','6','8'}:
                if choice=='8':
                    candidates=sorted((workspace/'runs').glob('run-*'),key=lambda p:p.stat().st_mtime,reverse=True)
                    for index,path in enumerate(candidates,1):print(str(index)+' '+path.name+('（已有报告）' if (path/'report.json').is_file() else '（未保存报告）'))
                    number=int(input('选择要恢复的运行编号：'))
                    if number<1 or number>len(candidates):raise ValueError('run_number_out_of_range')
                    last_run=candidates[number-1]
                elif last_run is None:
                    records=sorted(workspace.glob('last-run-*.json'),key=lambda p:p.stat().st_mtime)
                    if records:last_run=workspace/read_document(records[-1])['run_directory']
                    else:
                        interrupted=sorted((workspace/'runs').glob('run-*'),key=lambda p:p.stat().st_mtime)
                        if not interrupted:raise ValueError('no_started_run:先运行任务')
                        last_run=interrupted[-1]
                if choice=='5':print('重放通过。回执 '+replay_run(last_run)['receipt_hash'])
                elif choice=='8':
                    page,runs=resume_calculation(last_run);print('恢复完成，新增离线计算 '+str(runs)+' 次；原失败保留。报告：'+str(page))
                else:
                    report=recover_report(last_run);print('报告：'+str(report))
                    if choice=='4':
                        import webbrowser
                        webbrowser.open(report.as_uri())
            elif choice=='7':
                from .source_task import prepare,report
                packet=prepare(workspace/'data/source-manifest.json');print('公告核对页面：'+str(report(packet)))
            elif choice=='10':
                snapshots=sorted((workspace/'data').rglob('equity_dataset_*.json'))
                for index,path in enumerate(snapshots,1):print(str(index)+' '+path.relative_to(workspace).as_posix())
                number=int(input('选择数据编号：'))
                if number<1 or number>len(snapshots):raise ValueError('data_number_out_of_range')
                chosen_snapshot=snapshots[number-1]
                entries=list(strategies())
                for index,key in enumerate(entries,1):print(str(index)+' '+definition(key)['title']+' '+key)
                number=int(input('选择策略编号：'))
                if number<1 or number>len(entries):raise ValueError('strategy_number_out_of_range')
                key=entries[number-1];entry=definition(key)
                if entry['engine_strategy']=='buy_and_hold':params=dict(target_position_pct=float(input('目标仓位比例（默认 0.25）：') or '0.25'))
                else:params=dict(fast_window=int(input('快均线周期（默认 20）：') or '20'),slow_window=int(input('慢均线周期（默认 60）：') or '60'),position_pct=0.25,stop_loss_pct=0.03,take_profit_pct=0.06)
                event=input('事件上下文 JSON 路径：').strip().strip('"') if entry['event_rule'] else None
                name=input('任务文件名（默认 new-task）：').strip() or 'new-task'
                import re
                if not re.fullmatch(r'[\w-]{1,64}',name):raise ValueError('task_name_invalid')
                print('任务已保存：'+str(create_task(workspace/'tasks'/(name+'.json'),strategy=key,snapshot=chosen_snapshot,event_context=event,params=params)))
            else:print('请输入菜单中的编号。')
        except (ValueError,OSError,KeyError,TypeError) as exc:print('操作停止：'+str(exc))


def main(argv=None):
    sys.addaudithook(_deny_network)
    parser=argparse.ArgumentParser(description='哈基米交易：任务／策略、数据、离线运行、结果与恢复（M1 候选）')
    commands=parser.add_subparsers(dest='command')
    commands.add_parser('capabilities')
    commands.add_parser('strategies')
    for name in ['init','wizard']:
        p=commands.add_parser(name);p.add_argument('--workspace',type=Path,default=default_artifact_root()/'trade-offline')
        if name=='init':p.add_argument('--demo',action='store_true')
    for name in ['check','run']:
        p=commands.add_parser(name);p.add_argument('--task',required=True,type=Path)
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
    p=commands.add_parser('task-create')
    for name in ['task','snapshot']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--strategy',required=True);p.add_argument('--event-context',type=Path);p.add_argument('--parameters',type=Path)
    p.add_argument('--score-start');p.add_argument('--score-end');p.add_argument('--initial-cash',type=float,default=10000)
    p.add_argument('--fee-rate',type=float,default=0.0008);p.add_argument('--slippage-pct',type=float,default=0.0005);p.add_argument('--output-dir',type=Path)
    p=commands.add_parser('source');p.add_argument('source_arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv)
    try:
        if args.command is None:return wizard(default_artifact_root()/'trade-offline')
        if args.command=='wizard':return wizard(args.workspace)
        if args.command=='capabilities':
            output=dict(product_target='交易量化工具',current_milestone='M1_INSTALLABLE_OFFLINE_CANDIDATE',
                supported=['Versioned task adapters','Existing price and earnings-schedule strategies','CSV and completed/resumed local quote import',
                    'Offline source workflow','Existing canonical engine and risk','Results, replay and saved-report recovery'],
                not_implemented=['Portfolio-level shared-capital risk','Supervised incremental monitoring','Broker execution in this entry'],
                execution_permission=dict(PERMISSIONS))
        elif args.command=='strategies':output=strategies()
        elif args.command=='init':output=initialize_demo(args.workspace) if args.demo else initialize_empty(args.workspace)
        elif args.command=='check':
            context=check_task(args.task);output=dict(status='INPUTS_CHECKED_NO_SIMULATION',task_id=context['task_id'],
                strategy=context['definition'],scoring=context['protocol'],output_dir=str(context['output']),execution_permission=dict(PERMISSIONS))
        elif args.command=='run':
            directory=run_task(args.task);output=dict(status='OFFLINE_RUN_SAVED',run_directory=str(directory),report=str(recover_report(directory)))
        elif args.command in {'report','recover'}:
            page,runs=resume_calculation(args.run_dir) if getattr(args,'resume_calculation',False) else (recover_report(args.run_dir),0)
            output=dict(status='RETAINED_REPORT_RENDERED' if runs==0 else 'INTERRUPTED_CALCULATION_RECOVERED',report=str(page),new_economic_runs=runs)
        elif args.command=='replay':output=replay_run(args.run_dir)
        elif args.command=='collection-import':
            directory=import_collection(calendar_original=args.calendar_original,output_dir=args.output_dir,collection=args.collection,
                first=args.first,continuation=args.continuation,synthetic=args.synthetic)
            output=dict(status='LOCAL_QUOTES_IMPORTED',bundle=str(directory),**verify_bundle(directory))
        elif args.command=='bundle-check':output=dict(status='PORTABLE_BUNDLE_CHECKED',**verify_bundle(args.bundle))
        elif args.command=='snapshot-import':
            snapshot=build_equity_snapshot(args.csv.read_bytes(),args.metadata.read_bytes())
            output=dict(snapshot=str(save_equity_snapshot(snapshot,args.output_dir)),snapshot_id=snapshot.snapshot_id)
        elif args.command=='task-create':
            path=create_task(args.task,strategy=args.strategy,snapshot=args.snapshot,event_context=args.event_context,
                params=read_document(args.parameters) if args.parameters else None,score_start=args.score_start,score_end=args.score_end,
                initial_cash=args.initial_cash,fee_rate=args.fee_rate,slippage_pct=args.slippage_pct,output_dir=args.output_dir)
            output=dict(task=str(path),task_id=check_task(path)['task_id'])
        else:
            from .source_task import main as source_main
            return source_main(args.source_arguments)
        print(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False));return 0
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='STOPPED',error=str(exc),execution_permission=dict(PERMISSIONS)),ensure_ascii=False));return 1


if __name__=='__main__':raise SystemExit(main())
