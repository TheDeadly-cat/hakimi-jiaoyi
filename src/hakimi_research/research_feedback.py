"""A deterministic, local Markdown handoff for a verified schedule research run.

The returned bytes are a human-readable file for an existing room-material file
import. They are not a new research protocol or a claim of remote delivery.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape

from .input_workflow import saved_input_outcome


EXPORT_NAMES = (
    'quant-report.json',
    'collaboration-result.json',
    'event-context.json',
    'input-assessment.json',
    'human-confirmation.json',
    'project-source.raw',
    'result-view.json',
    'task-input-binding.json',
)


def _cell(value):
    """Keep untrusted report text from adding Markdown/HTML table structure."""
    if value is None:
        value = '未提供'
    return (escape(str(value), quote=True).replace('\\', '\\\\')
            .replace('|', '\\|').replace('`', '\\`')
            .replace('\r', ' ').replace('\n', ' '))


def _known_versions(rows):
    if not rows:
        return '当时无已可用版本'
    return '；'.join(
        f"{_cell(row['event_id'])} v{_cell(row['version'])} "
        f"事件哈希 {_cell(row['event_hash'])}，公开 {_cell(row['version_public_at'])}，"
        f"可用 {_cell(row['available_at'])}，排期 {_cell(row['schedule']['status'])} "
        f"{_cell(row['schedule']['date'])}"
        for row in rows
    )


def _disposition_reason(audit):
    disposition = audit['disposition']
    if disposition == 'BLOCK_NEW_BUY':
        return '已确认规则阻止本次新买入；阻挡事件哈希见本行'
    if disposition == 'NO_PENDING_BUY':
        return '此阶段没有待执行的新买入'
    if disposition == 'ALLOW_PRICE_BUY':
        return ('当时无已可用排期版本' if not audit['known_versions']
                else '已知版本未触发本次新买入限制')
    return '以原生报告中的 disposition 为准'


def build_feedback_markdown(manifest, report, assessment, confirmation, binding, exported_bytes):
    """Return UTF-8 bytes from already verified, frozen inputs and exact export bytes."""
    if set(exported_bytes) != set(EXPORT_NAMES) or any(type(raw) is not bytes for raw in exported_bytes.values()):
        raise ValueError('research_feedback_export_bytes_incomplete')
    if (assessment['status'] != 'READY_FOR_EXPLICIT_INPUT_CHECK'
            or confirmation['decision'] != 'ACCEPT_FOR_INPUT_CHECK'
            or binding['task_id'] != manifest['task_id']
            or binding['assessment_hash'] != assessment['assessment_hash']
            or manifest['task']['event_context_hash'] != assessment['context_hash']):
        raise ValueError('research_feedback_binding_mismatch')
    permission = manifest['execution_permission']
    if permission['research_only'] is not True or permission['order_allowed'] is not False:
        raise ValueError('research_feedback_permission_mismatch')
    outcome = saved_input_outcome(report)
    spec = report['spec']
    result = report['result']
    if len(result['signals']) != len(outcome['reviews']):
        raise ValueError('research_feedback_review_count_mismatch')
    source = manifest['runtime']['source_identity']

    lines = [
        '# 量化研究反馈（本地生成）',
        '',
        '> 这是本地已保存研究结果的说明。原公告仅是财报排期输入来源，**不是**这份量化结果的发布地址。'
        ' 文件尚未被交易分析接收；导入房间资料仍需人工选择。此结果只供研究，不能据此下单。',
        '',
        '## 身份与边界',
        '',
        f"- 证券：{_cell(assessment['security_id'])}",
        f"- 研究结果：{_cell(assessment['research_result_id'])}；结果 SHA-256：{_cell(assessment['research_result_sha256'])}；原文件 SHA-256：{_cell(assessment['research_result_file_sha256'])}",
        f"- 研究侧项目来源项：{_cell(assessment['research_source_item_id'])}；修订：{_cell(assessment['research_source_revision'])}。这只绑定研究侧声明，不认证公告。",
        f"- 排期上下文：context_hash {_cell(assessment['context_hash'])}；原文件 SHA-256 {_cell(assessment['context_file_sha256'])}",
        f"- 原始来源文件 SHA-256：{sha256(exported_bytes['project-source.raw']).hexdigest()}；来源真实性状态：{_cell(assessment['source_authentication'])}",
        f"- 人工接纳：{_cell(confirmation['decision'])}；声明人 {_cell(confirmation['actor'])}；记录时间 {_cell(confirmation['confirmed_at'])}；理由 {_cell(confirmation['reason'])}；确认文件 SHA-256 {_cell(assessment['confirmation_file_sha256'])}。署名身份未获独立认证。",
        f"- 输入评估 SHA-256：{_cell(assessment['assessment_hash'])}；任务 ID：{_cell(manifest['task_id'])}；任务族 ID：{_cell(binding.get('family_id'))}；版本：{_cell(binding.get('revision'))}；绑定 SHA-256：{_cell(binding['binding_hash'])}",
        f"- 原生运行 ID：{_cell(manifest['run_id'])}；报告身份：{_cell(report['report_hash'])}；报告文件 SHA-256：{sha256(exported_bytes['quant-report.json']).hexdigest()}",
        f"- 代码来源身份：{_cell(source['content_sha256'])}（{_cell(source['status'])}）",
        f"- 权限：research_only={str(permission['research_only']).lower()}；order_allowed={str(permission['order_allowed']).lower()}。本反馈不更改策略参数，也不代表研究侧已接收或批准。",
        '',
        '## 评分设置与结果',
        '',
        f"- 评分区间：{_cell(spec['score_start_session'])} 至 {_cell(spec['score_end_session'])}；策略：{_cell(manifest['task']['strategy'])}。",
        f"- 初始资金：{_cell(spec['initial_cash'])}；手续费率：{_cell(spec['fee_rate'])}；滑点率：{_cell(spec['slippage_pct'])}。",
        f"- 研究输入影响：{_cell(outcome['status'])}；阻止新增买入 {outcome['blocked_new_buys']} 次。{_cell(outcome['explanation'])}",
        f"- 原生研究结果：净收益率 {_cell(result['total_return'])}；最大回撤 {_cell(result['max_drawdown'])}；总费用 {_cell(result['total_fees'])}；成交 {_cell(result['fill_count'])} 次。这些数值不构成与未使用排期规则的收益因果比较。",
        '',
        '## 排期事件版本（输入证据）',
        '',
        '| 事件与版本 | 事件哈希 | 公告公开 / 输入可用 | 排期状态与日期 |',
        '| --- | --- | --- | --- |',
    ]
    for event in assessment['event_versions']:
        lines.append(f"| {_cell(event['event_id'])} v{_cell(event['version'])} | {_cell(event['event_hash'])} | "
                     f"{_cell(event['version_public_at'])} / {_cell(event['available_at'])} "
                     f"({_cell(event['available_at_kind'])}) | {_cell(event['schedule_status'])} "
                     f"{_cell(event['scheduled_date'])}；{_cell(event['time_precision'])} |")
    lines.extend(['', '以下地址仅指向排期输入公告，不是量化反馈的发布地址：', ''])
    for event in assessment['event_versions']:
        lines.append(f"- {_cell(event['event_id'])} v{_cell(event['version'])}：{_cell(event['source_url'])}；"
                     f"公告原文字节 SHA-256 {_cell(event['raw_content_sha256'])}；"
                     f"前一版本哈希 {_cell(event['prior_version_hash'])}。")
    lines.extend([
        '',
        '## 逐时点输入影响',
        '',
        '每行是原生报告保存的决策或执行阶段。已知版本只包括当时可用的版本；无阻挡不表示排期输入证明策略有效。',
        '',
        '| 阶段 / 已知时点 | 对应执行日 | 原信号 → 输出 / 处置 | 理由与阻挡哈希 | 当时已知版本 |',
        '| --- | --- | --- | --- | --- |',
    ])
    for signal, review in zip(result['signals'], outcome['reviews']):
        for stage in ('decision', 'execution'):
            audit = review.get(stage)
            if audit is None:
                continue
            hashes = ', '.join(audit['blocking_event_hashes']) or '无'
            reason = (f"{_disposition_reason(audit)}；原信号理由：{audit['input_signal']['reason']}；"
                      f"阻挡哈希：{hashes}；保存信号理由：{signal['reason']}")
            lines.append(f"| {_cell(stage)} / {_cell(audit['as_of'])} | {_cell(audit['execution_session'])} | "
                         f"{_cell(audit['input_action'])} → {_cell(audit['output_action'])} / {_cell(audit['disposition'])} | "
                         f"{_cell(reason)} | {_known_versions(audit['known_versions'])} |")
    lines.extend([
        '',
        '## 同目录冻结原件',
        '',
        '下表 SHA-256 按原始文件字节计算。导入交易分析的房间资料后，仅提取的文本和原字节哈希入库；原件继续保存在此本地目录。',
        '',
        '| 文件 | 字节数 | SHA-256 |',
        '| --- | ---: | --- |',
    ])
    for name in EXPORT_NAMES:
        raw = exported_bytes[name]
        lines.append(f'| [{name}]({name}) | {len(raw)} | {sha256(raw).hexdigest()} |')
    lines.extend(['', '原生报告及研究输入均以这些冻结文件为准。本文件不声称公告发布了量化结论。', ''])
    return '\n'.join(lines).encode('utf-8')
