"""Chinese presentation guidance, separate from executable strategy identities.

This module returns detached display data. It never changes a task, chooses a
parameter, admits an input, or runs a strategy. The rule references below are
for maintainers; the returned text is intended for the local user interface.
"""
from copy import deepcopy


_PARAMETERS = {
    'fast_window': {
        'label': '快均线周期', 'unit': '交易日',
        'description': '用最近这些交易日的收盘价计算简单平均值；必须小于慢均线周期。数值越小，均线对近期价格变化越敏感，不代表效果更好。',
    },
    'slow_window': {
        'label': '慢均线周期', 'unit': '交易日',
        'description': '用较长一段收盘价计算简单平均值。当前规则在评分前需要慢周期加2个交易日；默认60需要62日预热，连同首个评分日至少63日数据。',
    },
    'position_pct': {
        'label': '目标仓位', 'unit': '%',
        'description': '以拟成交时开盘参考价计算的账户净值为基准，请求本次买入的参考市值比例。25%表示每100美元净值请求约25美元；实际数量还受最大仓位、现金、手续费和滑点限制。不是收益目标。',
    },
    'target_position_pct': {
        'label': '基准目标仓位', 'unit': '%',
        'description': '首次评分开盘尝试买入时，按账户净值请求的参考市值比例。25%不是满仓；剩余部分保留为现金。费用和滑点可能使实际买入数量低于请求，之后不自动再平衡。',
    },
    'stop_loss_pct': {
        'label': '止损价格距离', 'unit': '%',
        'description': '相对持仓平均买入成交价的下跌距离。实际止损距离取本参数与“最大止损距离”的较小值。跳空、费用和滑点可使实际亏损更大，不能当作账户亏损上限。',
    },
    'take_profit_pct': {
        'label': '止盈价格距离', 'unit': '%',
        'description': '相对持仓平均买入成交价的上涨距离，触及时按现有日线模型尝试退出。不是净收益率目标；手续费和滑点另外影响实际结果。',
    },
}

_RISK = {
    'max_position_pct': {
        'label': '最大仓位', 'unit': '%',
        'description': '每次新买入时，以开盘参考价计算账户净值和已有持仓，限制还能买入的空间。价格上涨后不会为保持此比例自动减仓。',
    },
    'max_single_loss_pct': {
        'label': '最大止损距离', 'unit': '%',
        'description': '限制止损价离平均买入成交价的最大距离，与策略请求的止损距离取较小值。它不是单笔账户损失保证。',
    },
    'max_daily_loss_pct': {
        'label': '日亏损后暂停新买入', 'unit': '%',
        'description': '按UTC日相对日初权益检查；当前美股日线以此前收盘权益作为新日基线。有正亏损且达到阈值后，当日停止新买入，不强制平仓，观望和卖出仍可进行。设为0时，有正亏损才触发。',
    },
    'max_leverage': {
        'label': '杠杆', 'unit': '倍',
        'description': '当前固定为1倍现货现金模式，不借款、不融资、不做空。不能通过提高数值获得杠杆交易。',
    },
    'min_cash_pct': {
        'label': '最低现金比例', 'unit': '%',
        'description': '新买入时保留按当时账户净值计算的现金底线，买入费用也占用可用现金。它约束这笔买入，不是在后续价格变化时自动再平衡。',
    },
}

_BENCHMARK_RISK = {
    'max_position_pct': {
        'label': '最大仓位兼容值', 'unit': '%',
        'description': '买入持有基准固定使用100%的现货现金准入上限；实际请求比例由“基准目标仓位”决定，不因此自动满仓。',
    },
    'max_single_loss_pct': {
        'label': '止损兼容字段', 'unit': '%',
        'description': '买入持有基准保留此固定兼容字段，但不启用策略止损保护；不会因这个数值而卖出。',
    },
    'max_daily_loss_pct': {
        'label': '日亏损兼容字段', 'unit': '%',
        'description': '买入持有基准保留此固定兼容字段，不启用主动日亏损退出，也没有后续加仓机会。',
    },
    'max_leverage': _RISK['max_leverage'],
    'min_cash_pct': {
        'label': '最低现金兼容值', 'unit': '%',
        'description': '买入持有基准固定为0%，但仍不能透支，手续费和滑点会限制可买数量；是否留有较多现金由基准目标仓位决定。',
    },
}

_COSTS = {
    'initial_cash': {
        'label': '初始本金', 'unit': '美元',
        'description': '评分开始前的现金及初始净值。每个普通任务使用自己的独立本金，多任务结果不能相加当作共享账户。',
    },
    'fee_rate': {
        'label': '比例手续费', 'unit': '%',
        'description': '每次买入和卖出都按实际成交金额收取这一比例；界面0.08%对应保存值0.0008。费用计入净损益，当前没有固定最低收费或券商阶梯费率。',
    },
    'slippage_pct': {
        'label': '固定滑点', 'unit': '%',
        'description': '买入价在参考价上调此比例，卖出价下调此比例；界面0.05%对应保存值0.0005。滑点已进入成交价，不列为额外手续费，也不是流动性或真实成交保证。',
    },
    'score_start': {
        'label': '首个评分交易日', 'unit': '交易日（YYYY-MM-DD）',
        'description': '从这一天的开盘开始计入成交、费用与盈亏。此前完整数据只用于预热，不计评分期交易；预热不足时不能靠缩短参数自动通过。',
    },
    'score_end': {
        'label': '最后评分交易日', 'unit': '交易日（YYYY-MM-DD）',
        'description': '计入这一天的收盘净值。仍持有的股票按收盘市值计价，不自动卖出；结果可能包含未实现盈亏。',
    },
}

_PRICE_INPUTS = [
    '同一只美股普通股的已封存日线行情，美元、未复权价格、股数成交量；证券身份、交易日历及公司行为窗口须通过现有输入校验。',
    '只使用已结束且已可获得的常规时段日线；评分开始前保留足够预热数据，评分区间及费用参数明确保存。',
]
_CONTENT_INPUTS = _PRICE_INPUTS + [
    '同一证券、同一公告事件的内容上下文，含候选材料、规范化文本、原始来源字节、精确发布时间与版本可用时间；不能只用一个手填财务数字代替。',
    '必须有公告前的收盘基线及公告后首个完整交易日与后续可成交日。现有模型固定公告信息延迟120秒、完整日线延迟60秒。',
]
_PROTECTIVE_EXIT = (
    '持仓还受有效止损和止盈保护：先检查已有持仓在开盘是否触及保护价，再检查日内最高/最低价；日内同时触及止损与止盈而先后未知时采用止损。'
    '跳空止损按更差的开盘参考价处理，再计费用与滑点。评分期末不强制卖出，按收盘市值计价。'
)
_DEMO_PARAMS = dict(fast_window=2, slow_window=4, position_pct=0.25,
                    stop_loss_pct=0.03, take_profit_pct=0.06)


def _example(task_name, original_name, title):
    return dict(
        available=True, kind='FICTIONAL_TEACHING', task_name=task_name,
        legacy_demo_task_name=original_name, title=title, session_count=22,
        configured_params=dict(_DEMO_PARAMS), action='prepare_teaching_examples',
        description='复用已有22个交易日的虚构行情，明确配置快/慢均线2/4、目标仓位25%、止损3%、止盈6%。只用于熟悉流程，不代表真实市场表现。',
        selection_note='仅在明确点击“添加教学示例”后追加独立教学任务，原任务不改动；添加后仍需用户选择并运行。常规新建双均线默认仍为20/60，不自动缩短参数。',
    )


_GUIDANCE = {
    # strategies/templates.py: DualMovingAverageStrategy.generate_signal
    'price.dual_ma@1': dict(
        summary='用两条收盘价简单均线的交叉决定买入或退出；只持有现货多头。',
        buy_rule='没有持仓时，上一条快均线不高于慢均线、最新快均线高于慢均线，才产生买入信号。信号在完整日线可用后形成，拟在下一常规交易日开盘成交；有持仓时不因再次上穿而加仓。',
        exit_rule='有持仓时，快均线由不低于慢均线变为低于慢均线，产生全部退出信号，拟在下一开盘成交。'+_PROTECTIVE_EXIT,
        required_inputs=_PRICE_INPUTS,
        parameter_help={key: _PARAMETERS[key] for key in _DEMO_PARAMS},
        risk_help=_RISK, cost_help=_COSTS,
        teaching_example=_example('教学-双均线', 'price', '双均线虚构教学示例'),
    ),
    # benchmarks.py: BuyAndHoldBenchmarkStrategy; experiment benchmark policy
    'price.buy_and_hold@1': dict(
        summary='按指定仓位只尝试买入一次，用作持有至评分结束的价格基准。',
        buy_rule='在首个评分交易日开盘尝试一次买入，不等待均线条件；买入仍受现金、费用和滑点约束。此后不加仓、不自动再平衡，首次未成交也不重试。',
        exit_rule='不启用策略止损、止盈或主动卖出。评分期末按收盘市值计价，不强制平仓，所以净损益可能主要是未实现盈亏。',
        required_inputs=_PRICE_INPUTS + ['评分开始前至少保留1个完整交易日。无需公告排期或内容上下文。'],
        parameter_help={'target_position_pct': _PARAMETERS['target_position_pct']},
        risk_help=_BENCHMARK_RISK, cost_help=_COSTS,
        teaching_example=dict(
            available=False, kind='FICTIONAL_TEACHING', task_name=None,
            title='使用教学行情另建买入持有任务', session_count=22, configured_params=None,
            description='现有教学准备动作只预建双均线和公告排期两项任务。可先明确添加教学示例，再选择那份虚构行情新建买入持有基准，并自行确认仓位与成本。',
            selection_note='不会自动创建或运行买入持有任务，也不会将它替换为其他策略。',
        ),
    ),
    # equity_event_context.py: EventSchedulePolicy.review / known_at
    'event.earnings_schedule@1': dict(
        summary='在双均线买入信号上叠加公告排期过滤；只看已知排期，不分析财报内容。',
        buy_rule='先按双均线空仓上穿规则产生买入意图，再在决策时和拟成交时检查当时已经可得的排期版本。已知版本标为UNKNOWN，或已公布日期等于拟成交交易日，会阻止这笔新买入；没有对应已知阻挡项时沿用价格信号。不会使用未来才公布的排期。',
        exit_rule='排期过滤不会自动卖出已有持仓，也不阻止原价格策略的退出。持仓快均线下穿慢均线时拟在下一开盘全部退出。'+_PROTECTIVE_EXIT,
        required_inputs=_PRICE_INPUTS + [
            '同一证券的版本化公告排期上下文，包含公布时间和历史可用时间；不能用财报内容上下文代替。',
            '研究结束前至少存在一个历史可用的已公布排期，否则不会执行此策略；UNKNOWN排期不能冒充已确认日期。',
        ],
        parameter_help={key: _PARAMETERS[key] for key in _DEMO_PARAMS},
        risk_help=_RISK, cost_help=_COSTS,
        teaching_example=_example('教学-公告排期', 'event', '公告排期虚构教学示例'),
    ),
    # content_protocol.py: price_confirmation; content_tasks.py: content_plan
    'content.price_confirmation@1': dict(
        summary='只观察公告后的首个完整交易日，判断价格是否高于公告前基线。',
        buy_rule='将“公告发布满120秒后才开盘”的首个完整交易日固定为确认日。其日线可用后，收盘价严格高于公告发布时已经完成的最近一个交易日收盘价，才在随后首个可成交日开盘尝试买入。只看这一次机会，不改选后来上涨的交易日；本基准不以财务字段核准为买入门槛。',
        exit_rule='没有均线退出规则，仅按配置的有效止损和止盈尝试退出；拒绝买入或退出后不重试、不重新入场。'+_PROTECTIVE_EXIT,
        required_inputs=_CONTENT_INPUTS,
        parameter_help={key: _PARAMETERS[key] for key in ('position_pct', 'stop_loss_pct', 'take_profit_pct')},
        risk_help=_RISK, cost_help=_COSTS,
        teaching_example=dict(
            available=False, kind='FICTIONAL_TEACHING', task_name=None,
            title='需要准备内容研究输入', session_count=None, configured_params=None,
            description='目前没有预建的可运行内容价格确认教学任务。旧示例中的内容候选和原文只是未核准材料，不等同于可直接选择的完整内容上下文。',
            selection_note='先导入符合现有格式与时间约束的内容上下文，再自行创建任务；不自动生成研究依据。',
        ),
    ),
    # content_protocol.py: content_condition, latest known approved version
    'content.reviewed_outlook@1': dict(
        summary='在一次公告后价格确认机会中，再检查已经核准的下季收入指引条件。',
        buy_rule='先满足公告后首个完整交易日的价格确认规则，再使用决策时已可得的最新公告版本。该版本必须有对应字段核准回执，且美元口径的下季收入指引中点严格高于本季GAAP实际收入；本季和下季期间须正确对应，币种与单位须符合规则，金额按各自缩放换算后比较。资料未知、未核准或条件不满足时保持观望，不退用旧核准版本，也不等以后再补买。这个条件不是分析师预期差。',
        exit_rule='没有均线退出规则，仅按配置的有效止损和止盈尝试退出；拒绝买入或退出后不重试、不重新入场。'+_PROTECTIVE_EXIT,
        required_inputs=_CONTENT_INPUTS + [
            '决策时最新可用公告版本的字段核准回执，以及本季GAAP实际收入和紧接下季的收入指引中点；原件及候选身份须匹配，不能把未核准字段自动当成已核准。',
        ],
        parameter_help={key: _PARAMETERS[key] for key in ('position_pct', 'stop_loss_pct', 'take_profit_pct')},
        risk_help=_RISK, cost_help=_COSTS,
        teaching_example=dict(
            available=False, kind='FICTIONAL_TEACHING', task_name=None,
            title='需要已核准的内容研究输入', session_count=None, configured_params=None,
            description='目前没有预建的可运行已核准指引教学任务。未核准的虚构内容材料不能作为核准回执使用。',
            selection_note='导入与候选及原件一致的有效核准输入后再创建任务；界面不会代替人工核准或伪造审批。',
        ),
    ),
}


def guidance_for(strategy_key):
    """Return JSON-compatible display data, without touching registry or state."""
    if type(strategy_key) is not str or strategy_key not in _GUIDANCE:
        raise ValueError('unsupported_strategy_guidance:' + str(strategy_key))
    return deepcopy(_GUIDANCE[strategy_key])
