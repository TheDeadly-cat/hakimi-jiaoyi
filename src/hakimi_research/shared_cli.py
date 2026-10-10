"""Cold console and terminal desk for explicitly synthetic shared accounts."""
from pathlib import Path

from .documents import read_document
from .shared_account import create_shared_account, demo_account_config, describe_shared_account, transact_shared_account
from .shared_signals import demo_competing_intents, step_shared_tasks


def initialize_shared_demo(directory):
    from .trade_cli import create_task, initialize_demo
    directory=Path(directory).resolve()
    if directory.exists():raise ValueError('shared_demo_requires_new_directory')
    directory.mkdir(parents=True)
    workspace=directory/'workspace'
    initialize_demo(workspace)
    snapshot=next((workspace/'data').glob('equity_dataset_*.json'))
    common=dict(snapshot=snapshot,score_start='2024-11-11',score_end='2024-12-03',initial_cash=1234,fee_rate=0,slippage_pct=0)
    tasks=[create_task(workspace/'tasks/shared-benchmark.json',strategy='price.buy_and_hold@1',
        params=dict(target_position_pct=.8),**common),
        create_task(workspace/'tasks/shared-ma.json',strategy='price.dual_ma@1',
        params=dict(fast_window=2,slow_window=4,position_pct=.8,stop_loss_pct=.03,take_profit_pct=.06),
        risk=dict(max_position_pct=.8,max_single_loss_pct=.03,max_daily_loss_pct=1,max_leverage=1,min_cash_pct=0),**common)]
    config=demo_account_config();config['as_of']='2024-11-11T14:30:00Z'
    config['securities']['SYNTHETIC:RESEARCH:TEST']['price']=104
    view=create_shared_account(directory/'account',config)
    return dict(status='SHARED_SYNTHETIC_DEMO_CREATED',account=str(directory/'account'),tasks=list(map(str,tasks)),
        at=config['as_of'],cash=view['cash'],competition=view['competition'],evidence_kind='SYNTHETIC_TEST',
        message='共享账户本金 10000；两任务各申请 8000。任务原独立本金 1234 不用于共享账户。先 shared-step，再显式结算、取消或拒绝。')


def add_commands(commands):
    p=commands.add_parser('shared-demo');p.add_argument('--directory',required=True,type=Path)
    p=commands.add_parser('shared-init');p.add_argument('--account',required=True,type=Path)
    sources=p.add_mutually_exclusive_group(required=True)
    sources.add_argument('--config',type=Path);sources.add_argument('--demo',action='store_true')
    for name in ['show','receipt','reserve','step','mark','cancel','reject','settle','pause','resume','day-reset']:
        p=commands.add_parser('shared-'+name);p.add_argument('--account',required=True,type=Path)
        if name=='show':p.add_argument('--journal',action='store_true')
        elif name=='receipt':p.add_argument('--operation-id',required=True)
        else:
            p.add_argument('--operation-id',required=True,help='Durable unique operation ID; inspect shared-receipt after an unknown outcome. No automatic retry.')
            p.add_argument('--at',required=True,help='Exact fixed UTC second, YYYY-MM-DDTHH:MM:SSZ.')
            if name=='reserve':
                source=p.add_mutually_exclusive_group(required=True)
                source.add_argument('--intents',type=Path);source.add_argument('--demo',action='store_true')
            elif name=='step':p.add_argument('--task',required=True,action='append',type=Path)
            elif name=='mark':p.add_argument('--prices',required=True,type=Path)
            elif name in {'cancel','reject','settle'}:p.add_argument('--intent-id',required=True)
            if name in {'cancel','reject','pause'}:p.add_argument('--reason',required=True)
            if name in {'resume','day-reset'}:p.add_argument('--expected-head',required=True)


def account_summary(view):
    result={k:v for k,v in view.items() if k not in {'state','history'}}
    state=view['state']
    result['state']={k:v for k,v in state.items() if k not in {'intents','opportunities'}}
    result['intents']=[dict(intent_id=key,**{k:r[k] for k in ['owner','security_id','action','quantity','reserved_cash','status','reason','fill']})
        for key,r in state['intents'].items()]
    result['history']=[dict(sequence=r['sequence'],operation_id=r['operation_id'],kind=r['request']['kind'],at=r['request']['at'],
        outcome=r['outcome'],receipt_hash=r['receipt_hash']) for r in view['history']]
    return result


def dispatch(args):
    action=args.command.removeprefix('shared-')
    if action=='demo':return initialize_shared_demo(args.directory)
    if action=='init':return account_summary(create_shared_account(args.account,demo_account_config() if args.demo else read_document(args.config)))
    if action in {'show','receipt'}:
        view=describe_shared_account(args.account)
        if action=='show':return view if args.journal else account_summary(view)
        receipt=next((r for r in view['history'] if r['operation_id']==args.operation_id),None)
        return dict(status='COMMITTED' if receipt else 'NOT_RECORDED',operation_id=args.operation_id,
            receipt=receipt,sequence=view['sequence'],receipt_head=view['receipt_head'],automatic_retry=False)
    if action=='step':return step_shared_tasks(args.account,args.task,operation_id=args.operation_id,at=args.at)
    payload={}
    if action=='reserve':payload=dict(intents=demo_competing_intents() if args.demo else read_document(args.intents))
    elif action=='mark':payload=dict(prices=read_document(args.prices))
    elif action in {'cancel','reject','settle'}:payload=dict(intent_id=args.intent_id)
    if action in {'cancel','reject','pause'}:payload['reason']=args.reason
    if action in {'resume','day-reset'}:payload=dict(expected_head=args.expected_head)
    return transact_shared_account(args.account,operation_id=args.operation_id,kind=action.upper().replace('-','_'),at=args.at,payload=payload)


def print_account(view):
    print('合成共享账户 · USD · '+view['account_id'])
    if view['legacy_read_only']:print('dev1 账户仅可读取，原记录保留；新操作使用 dev2 新账户。')
    else:print('操作使用当前固定时点；先更新全体价格才可推进时点。')
    print('现金 '+view['cash']+'；预留 '+view['reserved_cash']+'；可用 '+view['available_cash']+'；权益 '+view['equity'])
    print('按提交流水顺序，整笔通过或拒绝；暂停 '+str(view['state']['paused'])+'；损失停机 '+str(view['state']['loss_halted']))
    print('固定时点 '+view['state']['current_at']+'；流水 '+str(view['sequence'])+'；当前头 '+view['receipt_head'])
    for p in view['state']['positions'].values():print('持仓 '+p['owner']+' '+p['security_id']+' 数量 '+p['quantity'])
    for key,row in view['state']['intents'].items():print('意图 '+key+' '+row['status']+' '+row['reason']+'；预留 '+row['reserved_cash'])
    for r in view['history']:print('流水 '+str(r['sequence'])+' '+r['operation_id']+' '+r['request']['kind']+' '+r['outcome']['status'])


def shared_wizard(workspace):
    workspace=Path(workspace).resolve();root=workspace/'shared-accounts'
    print('离线共享资金台：仅合成账户和固定输入。无券商连接、后台监控或订单。')
    selected=None
    while True:
        print('\n1 新建两策略共享示例  2 选择账户  3 状态与流水  4 已有策略生成意图  5 结算  6 取消  7 拒绝  8 全局暂停  9 恢复  10 更新全体价格  11 新日基线  12 查询操作回执  0 返回')
        try:
            choice=input('共享资金选择：').strip()
            if choice=='0':return
            if choice=='1':
                from .shared_account import _key
                name=_key(input('新示例名称（默认 shared-demo）：').strip() or 'shared-demo')
                created=initialize_shared_demo(root/name);selected=Path(created['account'])
                print(created['message']);print_account(describe_shared_account(selected));continue
            if choice=='2':
                from .trade_cli import choose_item
                accounts=sorted(p/'account' for p in root.iterdir() if (p/'account/account.json').is_file()) if root.exists() else []
                selected=choose_item(accounts,'账户编号：',lambda p:p.parent.name);continue
            if selected is None:raise ValueError('shared_select_or_create_account_first')
            view=describe_shared_account(selected)
            if choice=='3':print_account(view);continue
            if choice=='12':
                operation=input('操作 ID：').strip();row=next((r for r in view['history'] if r['operation_id']==operation),None)
                print('已提交：'+str(row['outcome']) if row else '尚无该操作记录；系统不会自动重试。');continue
            if choice not in {'4','5','6','7','8','9','10','11'}:raise ValueError('shared_menu_choice_invalid')
            operation=input('本次唯一操作 ID：').strip()
            at=input('固定 UTC 时点（默认 '+view['state']['current_at']+'）：').strip() or view['state']['current_at']
            if choice=='4':
                defaults=[selected.parent/'workspace/tasks/shared-benchmark.json',selected.parent/'workspace/tasks/shared-ma.json']
                text=input('任务完整路径，逗号分隔（默认示例两任务）：').strip()
                tasks=[Path(t.strip().strip('"')) for t in text.split(',')] if text else defaults
                receipt=step_shared_tasks(selected,tasks,operation_id=operation,at=at)
            else:
                kind={'5':'SETTLE','6':'CANCEL','7':'REJECT','8':'PAUSE','9':'RESUME','10':'MARK','11':'DAY_RESET'}[choice]
                payload={}
                if choice in {'5','6','7'}:payload['intent_id']=input('意图 ID：').strip()
                if choice in {'6','7','8'}:payload['reason']=input('原因：').strip()
                if choice=='10':payload['prices']=read_document(Path(input('全体证券价格 JSON 路径：').strip().strip('"')))
                if choice in {'9','11'}:payload['expected_head']=view['receipt_head']
                receipt=transact_shared_account(selected,operation_id=operation,kind=kind,at=at,payload=payload)
            print('已提交流水 '+str(receipt['sequence'])+'：'+str(receipt['outcome']));print_account(describe_shared_account(selected))
        except EOFError:return
        except (ValueError,OSError,TypeError,KeyError,RuntimeError) as exc:
            print('共享操作停止：'+str(exc)+'；若提交结果不明，先用菜单 12 查回执。')
