"""Beginner-facing input selection; all admission and persistence are shared."""
from pathlib import Path

from .input_workflow import (list_inputs, print_input, import_input, import_price_csv, import_schedule_events,
    import_content_packet, check_inputs, bind_inputs)


def choose_snapshot(workspace):
    from .trade_cli import choose_item
    rows = [r for r in list_inputs(workspace)['items'] if r['kind'] == 'PRICE_SNAPSHOT']
    for row in rows:
        if row['status'] != 'READY':
            print_input(row)
    ready = [r for r in rows if r['status'] == 'READY']
    if not ready:
        raise ValueError('no_usable_snapshot:先导入并检查行情')
    selected = choose_item(ready, '选择行情编号：',
        lambda r: r['security']['symbol']+' '+r['coverage_start']+' 至 '+r['coverage_end']+' '+r['input_id']+' 文件 '+r['file_sha256'][:12])
    print_input(selected)
    return Path(selected['path'])


def input_wizard(workspace):
    from .task_manager import list_tasks, describe_task, version_options, create_family
    from .trade_cli import choose_item, configuration_form, print_task
    workspace = Path(workspace).resolve()
    while True:
        print('\n输入中心：1 查看输入  2 导入行情 CSV  3 导入既有快照或上下文  4 导入研究输入  5 检查适用性  6 创建绑定任务  7 更新任务输入为新版本  0 返回')
        try:
            choice = input('输入操作：').strip()
        except EOFError:
            return
        if choice == '0':
            return
        try:
            if choice == '1':
                rows = list_inputs(workspace)['items']
                if not rows:
                    print('尚无输入。先导入自有行情，或返回主菜单创建虚构示例。')
                for row in rows:
                    print_input(row)
            elif choice == '2':
                csv = Path(input('行情 CSV 路径：').strip().strip('"'))
                metadata = Path(input('既有完整元数据 JSON 路径：').strip().strip('"'))
                saved = import_price_csv(csv, metadata, workspace)
                print_input(saved); print('输入已封存：'+saved['path'])
            elif choice == '3':
                saved = import_input(Path(input('既有快照或上下文 JSON 路径：').strip().strip('"')), workspace)
                print_input(saved); print('输入已封存：'+saved['path'])
            elif choice == '4':
                kind = input('1 既有排期事件版本  2 既有财报字段候选包：').strip()
                if kind == '1':
                    paths = [Path(p.strip().strip('"')) for p in input('事件 JSON 完整路径（多版本以 | 分隔）：').split('|')]
                    saved = import_schedule_events(paths, workspace)
                elif kind == '2':
                    packet = Path(input('字段候选包路径：').strip().strip('"'))
                    event_id = input('候选包中的事件 ID：').strip()
                    texts = Path(input('规范文本 .txt 所在目录：').strip().strip('"'))
                    originals = input('原件 .html/.txt 所在目录（可留空；缺失原件会停止任务准入）：').strip().strip('"')
                    approval = input('既有字段核准回执路径（可留空；未核准内容保持 UNKNOWN/HOLD）：').strip().strip('"')
                    synthetic = input('是否全为虚构测试输入？输入 TEST 标记，否则按未认证用户导入：').strip() == 'TEST'
                    saved = import_content_packet(packet, workspace, event_id=event_id, texts_dir=texts,
                        originals_dir=Path(originals) if originals else None, approval=Path(approval) if approval else None, synthetic=synthetic)
                else:
                    raise ValueError('research_input_kind_invalid')
                print_input(saved); print('研究输入已封存：'+saved['path'])
            elif choice in {'5', '6'}:
                snapshot = choose_snapshot(workspace)
                options = configuration_form(dict(snapshot=snapshot), workspace=workspace)
                checked = check_inputs(options, location=workspace/'tasks/.input-preview.json')
                print('适用性检查通过；新增计算 0。'); print_input(checked['snapshot'])
                if checked['research'] is not None: print_input(checked['research'])
                if choice == '6':
                    name = input('新任务名称：').strip()
                    family = workspace/'tasks'/name
                    create_family(family, **options)
                    print_task(describe_task(family))
            elif choice == '7':
                family = choose_item(list_tasks(workspace), '任务编号：', lambda p: p.stem)
                if not family.is_dir():
                    raise ValueError('legacy_task_is_immutable:先在主菜单 13 复制为可管理任务')
                before = describe_task(family)
                print_task(before)
                change = input('1 更新行情  2 更新研究输入  3 同时更新  4 清除研究输入：').strip()
                changes = {}
                if change in {'1', '3'}:
                    changes['snapshot'] = choose_snapshot(workspace)
                if change in {'2', '3'}:
                    from .strategy_registry import definition
                    entry = definition(before['strategy'])
                    kind = 'CONTENT_CONTEXT' if entry['engine_strategy'] == 'equity_post_release_confirmation' else 'SCHEDULE_CONTEXT'
                    rows = [r for r in list_inputs(workspace)['items'] if r['kind'] == kind and r['status'] == 'READY']
                    chosen = choose_item(rows, '研究输入编号：', lambda r: r['security_id']+' '+r['input_id']+' 文件 '+r['file_sha256'][:12])
                    print_input(chosen); changes['event_context'] = Path(chosen['path'])
                elif change == '4':
                    changes['event_context'] = None
                elif change != '1':
                    raise ValueError('input_binding_action_invalid')
                options = dict(version_options(family), **changes)
                check_inputs(options, location=family/'.input-preview/task.json')
                print('适用性检查通过。保存会建立新版本；原版本、报告和暂停状态保留。')
                if input('输入 SAVE 保存新版本，留空取消：').strip() == 'SAVE':
                    print_task(bind_inputs(family, **changes))
                else:
                    print('已取消，未提交新版本。')
            else:
                print('请输入输入中心的编号。')
        except (ValueError, OSError, KeyError, TypeError) as exc:
            print('输入操作停止：'+str(exc))
