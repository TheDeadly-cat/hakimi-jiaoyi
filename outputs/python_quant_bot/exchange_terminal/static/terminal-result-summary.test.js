"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {buildResultSummary, renderResultSummary} = require("./terminal-result-summary.js");
const fields = model => Object.fromEntries(model.rows.map(row => [row.key, row]));
const native = changes => ({schema_version:"hakimi-terminal-run-v1",status:"COMPLETED",id:"saved-native-hash",
  task_id:"task-1",engine_id:"terminal.causal-long-only-signals-v7",strategy_id:"momentum",version:2,
  input_summary:{symbol:"NDAQ",date_start:"2026-01-01",date_end:"2026-10-01",meta:{currency:"USD"}},
  configuration:{initial_cash:10000,warmup_rows:80,execution_model:"native-model-v3",costs:{fee_rate:.0005,slippage_bps:2}},
  result:{order_event_count:0,trade_count:0,open_position:{quantity:0},total_fees:0,final_cash:10000,
    evaluation_window:{start:"2026-05-01",end:"2026-10-01",context_rows:80,evaluated_rows:100}},...changes});

test("native summary uses recorded identity, percent rate and basis-point slippage without mutating input",()=>{
  const run=native(),before=JSON.stringify(run),model=buildResultSummary(run),rows=fields(model);
  assert.equal(model.kind,"NATIVE_ORIGINAL");assert.equal(rows.strategy.value,"momentum");
  assert.equal(rows.fee_rate.value,"0.05%");assert.equal(rows.slippage.value,"2 基点");
  assert.equal(rows.initial_cash.value,"10000");assert.equal(rows.currency.value,"USD");
  assert.equal(rows.engine.value,"terminal.causal-long-only-signals-v7");assert.equal(rows.task_version.value,"2");
  assert.equal(rows.fills.value,"0");assert.equal(rows.closed.value,"0");assert.equal(rows.holding.value,"0");
  assert.equal(rows.report_hash.value,"saved-native-hash");assert.equal(JSON.stringify(run),before);
  assert.match(model.zeroFillExplanation,/无法确定零成交原因/);
});

test("partial old results do not fabricate currency, capital, fills, closed positions or holdings",()=>{
  const model=buildResultSummary({schema_version:"hakimi-terminal-run-v1",status:"COMPLETED",strategy_id:"dual_ma",
    input_summary:{symbol:"AAPL"},result:{trades:[]}}),rows=fields(model);
  for(const key of ["currency","initial_cash","fills","closed","holding","final_cash","total_fees","engine","task_version"]) {
    assert.equal(rows[key].value,"未记录",key);assert.equal(rows[key].recorded,false,key);
  }
  assert.equal(model.zeroFillExplanation,null);
  assert.equal(rows.symbol.value,"AAPL");
});

test("partial ledger lengths and old trades aliases cannot become total fills or closed-position counts",()=>{
  const core={schema_version:"us-equity-research-report-v1",spec:{strategy:{name:"dual_ma"}},
    result:{trades:9,fills:[{action:"BUY"}],round_trips:[]}};
  const rows=fields(buildResultSummary(core));
  assert.equal(rows.fills.value,"未记录");assert.equal(rows.closed.value,"未记录");
  const oldNative=native({result:{trades:[{side:"BUY"}],trade_count:3}});
  assert.equal(fields(buildResultSummary(oldNative)).fills.value,"未记录");
  assert.equal(fields(buildResultSummary(oldNative)).closed.value,"3");
});

test("held positions remain explicit and zero completed rounds does not imply zero fills",()=>{
  const model=buildResultSummary(native({result:{order_event_count:1,trade_count:0,open_position:{quantity:12.5},total_fees:1.25}}));
  const rows=fields(model);assert.equal(rows.fills.value,"1");assert.equal(rows.closed.value,"0");
  assert.equal(rows.holding.value,"12.5");assert.equal(model.zeroFillExplanation,null);
});

test("canonical raw report retains its own contract, recorded signal evidence and sample limitations",()=>{
  const record={status:"COMPLETED",manifest:{run_id:"core-run",task_id:"core-task",task:{strategy:"price.dual_ma@1"},runtime:{source_identity:{content_sha256:"original-code"}}},
    report:{schema_version:"us-equity-research-report-v1",report_hash:"core-report",
      dataset:{security:{symbol:"NDAQ",currency:"USD"},sessions:[{date:"2026-09-29"},{date:"2026-10-26"}]},
      spec:{initial_cash:10000,fee_rate:.0008,slippage_pct:.0005,score_start_session:"2026-10-15",score_end_session:"2026-10-26",strategy:{name:"dual_ma"}},
      scoring_protocol:{available_context_sessions:12,scored_sessions:8},result:{execution_model:"signal-close-next-open-ohlc-v6",
        fill_count:0,round_trip_count:0,signal_count:0,decision_count:8,open_position_qty:0,total_fees:0,
        signals:Array.from({length:8},()=>({action:"HOLD",reason:"no MA crossover"})),
        statistical_status:{status:"INSUFFICIENT_EVIDENCE",annualized_return:"SHORT_SAMPLE"}}}};
  const before=JSON.stringify(record),model=buildResultSummary(record),rows=fields(model);
  assert.equal(model.kind,"CANONICAL_CORE");assert.equal(rows.strategy.value,"price.dual_ma@1");
  assert.equal(rows.engine.value,"未记录");assert.equal(rows.execution_model.value,"signal-close-next-open-ohlc-v6");
  assert.equal(rows.slippage.value,"0.05%");assert.equal(rows.fee_rate.value,"0.08%");
  assert.equal(rows.warmup.value,"12 根");assert.equal(rows.scored.value,"8 根");assert.equal(rows.source_identity.value,"original-code");
  assert.match(model.zeroFillExplanation,/8 次决策/);assert.match(model.zeroFillExplanation,/未发生均线交叉/);
  assert.ok(model.warnings.some(line=>line.includes("INSUFFICIENT_EVIDENCE")));
  assert.equal(JSON.stringify(record),before);
});

test("native last pending signal is only a bounded explanation, never a full zero-fill diagnosis",()=>{
  const model=buildResultSummary(native({result:{order_event_count:0,pending_signal_at_end:"BUY"}}));
  assert.match(model.zeroFillExplanation,/没有下一根开盘/);
  assert.match(model.zeroFillExplanation,/不能确定整个区间/);
  const partial=buildResultSummary({schema_version:"us-equity-research-report-v1",result:{fill_count:0,decision_count:8,
    signals:[{action:"HOLD",reason:"no MA crossover"}]}});
  assert.match(partial.zeroFillExplanation,/无法确定/);assert.doesNotMatch(partial.zeroFillExplanation,/各次已保存决策/);
});

test("current core detail uses only stored requested fields and never invents USD or absent accounting",()=>{
  const model=buildResultSummary({summary:{symbol:"NDAQ",strategy:{key:"price.dual_ma@1",title:"双均线价格策略",version:"1"},
    task_version_number:4,fill_count:0,open_position_qty:0,score_start:"2026-10-15",score_end:"2026-10-26"},
    configuration:{requested:{initial_cash:10000,fee_rate:.0008,slippage_pct:.0005}},identities:{run_id:"run-a",report_hash:"hash-a",task_id:"task-a"}});
  const rows=fields(model);assert.equal(rows.currency.value,"未记录");assert.equal(rows.closed.value,"未记录");
  assert.equal(rows.task_version.value,"4");assert.equal(rows.rule_version.value,"1");
  assert.equal(rows.run_id.value,"run-a");assert.equal(rows.holding.value,"0");
  assert.match(model.zeroFillExplanation,/无法确定/);
  const defaultsOnly=fields(buildResultSummary({summary:{strategy:{key:"price.dual_ma@1"}},
    configuration:{effective:{initial_cash:10000,fee_rate:.0005,slippage_pct:.0002}}}));
  for(const key of ["initial_cash","fee_rate","slippage"]) assert.equal(defaultsOnly[key].value,"未记录");
});

test("unknown and unverified records do not gain completion or zero-fill explanations",()=>{
  const unknown=buildResultSummary(native({status:"UNKNOWN",result:{order_event_count:0}}));
  assert.equal(unknown.status,"UNKNOWN");assert.equal(unknown.zeroFillExplanation,null);assert.match(unknown.warnings.join(""),/不自动重跑/);
  const unverified=buildResultSummary({...native(),verification_status:"METADATA_ONLY"});
  assert.equal(unverified.zeroFillExplanation,null);assert.match(unverified.warnings.join(""),/尚未通过读取校验/);
  const blank=buildResultSummary({});assert.equal(blank.status,"UNRECORDED");assert.equal(blank.kind,"UNKNOWN");
  assert.ok(blank.rows.every(row=>row.value==="未记录"));
  const conflict=buildResultSummary({status:"COMPLETED",report:native({status:"UNKNOWN"})});
  assert.equal(conflict.status,"UNKNOWN");assert.equal(conflict.zeroFillExplanation,null);
  assert.equal(buildResultSummary(native({status:"FAILED"})).zeroFillExplanation,null);
});

test("invalid numbers are missing instead of coerced to zero and every rendered value is escaped",()=>{
  const run=native({input_summary:{symbol:'<img src=x onerror="alert(1)">',meta:{}},
    configuration:{initial_cash:NaN,costs:{fee_rate:"0",slippage_bps:Infinity}},result:{order_event_count:"0",total_fees:null}});
  const rows=fields(buildResultSummary(run));
  for(const key of ["initial_cash","fee_rate","slippage","fills","total_fees"])assert.equal(rows[key].value,"未记录");
  const html=renderResultSummary(run);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img/);
  assert.match(html,/未记录/);assert.match(html,/已保存研究摘要/);
});

const financialNative = changes => native({
  input_summary:{symbol:"FICTIONAL",evidence_kind:"SYNTHETIC_TEST",meta:{currency:"USD"}},
  configuration:{initial_cash:10000,end_policy:"MARK_TO_MARKET",execution_model:"signal-close-next-open-ohlc-conservative-v3",costs:{fee_rate:.0005,slippage_bps:2}},
  result:{initial_cash:10000,final_cash:7234.56,final_equity:11234.56,total_return_pct:12.35,max_drawdown_pct:7.89,
    total_fees:8.9,order_event_count:5,trade_count:2,open_position:{quantity:20,unrealized_pnl:240},
    execution_model:"signal-close-next-open-ohlc-conservative-v3"},...changes});

test("A01 A02 A04: saved native equity wins over lower cash and fees are not subtracted again",()=>{
  const run=financialNative(),before=JSON.stringify(run),model=buildResultSummary(run),card=model.finance;
  assert.equal(card.title,"本段历史研究已完成");assert.equal(card.dataLabel,"虚构教学资料");
  assert.equal(card.direction,"up");assert.equal(card.values.final_equity,11234.56);assert.ok(Math.abs(card.values.net_pnl-1234.56)<1e-8);
  assert.ok(Math.abs(card.values.position_value-4000)<1e-8);assert.equal(card.values.unrealized_pnl,240);
  assert.equal(card.values.total_return_pct,12.35);assert.equal(card.values.max_drawdown_pct,7.89);
  assert.equal(card.values.realized_pnl,null);assert.equal(card.netDerived,true);assert.equal(card.positionDerived,true);
  assert.match(card.feeNote,/已在保存的现金与总资产中计入/);assert.match(card.feeNote,/不再.*重复扣除/);
  const html=renderResultSummary(run);
  for(const value of ["10,000.00 USD","11,234.56 USD","+1,234.56 USD","+12.35%","7.89%","7,234.56 USD","4,000.00 USD","+240.00 USD","8.90 USD"])assert.ok(html.includes(value),value);
  assert.doesNotMatch(html,/1235\.00%|1,225\.66/);assert.match(html,/尚未全部卖出/);
  assert.ok(html.indexOf('data-result-profit-card')<html.indexOf('查看保存的身份、数据与成本'));
  assert.equal(JSON.stringify(run),before);
});

test("A03: core realized gains cannot mask a larger holding loss in the total result",()=>{
  const report={schema_version:"us-equity-research-report-v2",status:"COMPLETED",report_hash:"saved-core-hash",
    dataset:{security:{symbol:"FICTIONAL",currency:"USD"},evidence_kind:"SYNTHETIC_TEST"},
    spec:{initial_cash:10000},result:{execution_model:"signal-close-next-open-ohlc-v6",metric_semantics_version:"research-accounting-score-start-v2",
      final_equity:9700,final_cash:8000,total_return:-.03,max_drawdown:.0789,total_fees:8.9,realized_pnl:500,unrealized_pnl:-800,
      fill_count:3,round_trip_count:1,open_position_qty:10,win_rate:1}};
  const model=buildResultSummary(report),html=renderResultSummary(report);
  assert.equal(model.kind,"CANONICAL_CORE");assert.equal(model.finance.values.net_pnl,-300);assert.equal(model.finance.direction,"down");
  assert.equal(model.finance.values.total_return_pct,-3);assert.equal(model.finance.values.max_drawdown_pct,7.89);
  for(const value of ["-300.00 USD","-3.00%","+500.00 USD","-800.00 USD"])assert.ok(html.includes(value),value);
  assert.match(model.finance.feeNote,/手续费已在/);assert.match(model.finance.closedNote,/胜率 100\.00%/);
});

test("actual core detail reads the saved last equity mark, its own ratio units and explicit currency only",()=>{
  const detail={id:"core-id",summary:{schema_version:"hakimi-offline-result-view-v1",id:"core-id",strategy:{key:"price.dual_ma@1"},
    total_return:.1235,max_drawdown:.0789,net_pnl:1234.56,realized_pnl:994.56,unrealized_pnl:240,open_position_qty:20,
    total_fees:8.9,round_trip_count:2,execution_model:"signal-close-next-open-ohlc-v6",metric_semantics_version:"research-accounting-score-start-v2"},
    configuration:{requested:{initial_cash:10000}},equity_curve:[{equity:10000,cash:10000,position_value:0},{equity:11234.56,cash:7234.56,position_value:4000}],
    candles:[{time:"2026-01-01",close:999999}],identities:{report_hash:"core-hash"}};
  const before=JSON.stringify(detail),model=buildResultSummary(detail),card=model.finance;
  assert.equal(card.complete,true);assert.equal(card.values.final_equity,11234.56);assert.equal(card.values.position_value,4000);
  assert.equal(card.values.total_return_pct,12.35);assert.equal(card.values.max_drawdown_pct,7.89);assert.equal(card.positionDerived,false);
  assert.match(card.primary[0].value,/币种未记录/);assert.doesNotMatch(renderResultSummary(detail),/USD/);
  detail.summary.currency="USD";assert.equal(buildResultSummary(detail).finance.primary[1].value,"11,234.56 USD");
  delete detail.summary.currency;assert.equal(JSON.stringify(detail),before);
});

test("A05: missing equity never becomes cash, inferred return or a current quote",()=>{
  const run=financialNative();delete run.result.final_equity;delete run.result.total_return_pct;delete run.result.max_drawdown_pct;
  run.candles=[{close:999999}];run.result.total_fees=null;
  const card=buildResultSummary(run).finance;
  for(const key of ["final_equity","net_pnl","position_value","total_return_pct","max_drawdown_pct","total_fees"])assert.equal(card.values[key],null,key);
  assert.match(card.netNote,/不会用现金变化代替/);assert.equal(card.primary[1].value,"未记录");
  const unknownModel=financialNative();unknownModel.configuration.execution_model="unrecorded-model";
  const unknownCard=buildResultSummary(unknownModel).finance;
  assert.equal(unknownCard.values.net_pnl,null);assert.equal(unknownCard.values.position_value,null);assert.match(unknownCard.feeNote,/口径未记录/);
});

test("A06: zero closed rounds are not a zero percent win rate, with and without open holdings",()=>{
  const run=financialNative();run.result.trade_count=0;run.result.win_rate_pct=0;
  let card=buildResultSummary(run).finance;
  assert.match(card.closedNote,/没有已完成持仓回合，胜率不适用/);assert.match(card.holdingNote,/仍有持仓/);
  assert.doesNotMatch(renderResultSummary(run),/胜率 0\.00%/);
  run.result.open_position.quantity=0;run.result.order_event_count=0;
  const model=buildResultSummary(run);assert.match(model.finance.holdingNote,/持仓数量为 0/);
  assert.match(model.zeroFillExplanation,/零成交/);assert.match(model.finance.closedNote,/胜率不适用/);
});

test("unknown, failed, metadata-only and cash-flow-bearing records never gain fixed-principal completion",()=>{
  for(const value of [financialNative({status:"UNKNOWN"}),financialNative({status:"FAILED"}),{...financialNative(),verification_status:"METADATA_ONLY"}]){
    const card=buildResultSummary(value).finance;
    assert.equal(card.complete,false);assert.equal(card.netDerived,false);assert.equal(card.values.net_pnl,null);
    assert.equal(card.direction,"unknown");assert.doesNotMatch(card.title,/已完成/);assert.match(card.feeNote,/口径未记录/);
    assert.match(card.closedNote,/尚未核验/);assert.match(card.holdingNote,/尚未核验/);
  }
  const withFlows=financialNative();withFlows.result.cash_flows=[{amount:1000}];
  const card=buildResultSummary(withFlows).finance;
  assert.equal(card.fixedPrincipal,false);assert.equal(card.values.net_pnl,null);assert.match(card.netNote,/资金流/);
});

test("financial formatting removes negative zero, retains tiny recorded fees and escapes currency",()=>{
  const run=financialNative();run.configuration.initial_cash=10000;run.result.final_equity=9999.999;
  run.result.final_cash=9999.999;run.result.total_return_pct=-0.00001;run.result.total_fees=.0001;
  run.input_summary.meta.currency='<img src=x>';
  const html=renderResultSummary(run);
  assert.doesNotMatch(html,/-0\.00|<img/);assert.match(html,/0\.0001 &lt;img src=x&gt;/);
  assert.match(html,/0\.00%/);
});

test("new capital currency is read only from its matching frozen task context",()=>{
  const run=financialNative();run.configuration.input_id="input-one";
  run.configuration.capital_context={schema_version:"hakimi-terminal-research-capital-v1",initial_cash:10000,input_id:"input-one",currency:"USD",currency_status:"RECORDED_FROM_FROZEN_INPUT"};
  delete run.input_summary.meta.currency;
  assert.equal(fields(buildResultSummary(run)).currency.value,"USD");
  run.configuration.capital_context.input_id="another-input";
  assert.equal(fields(buildResultSummary(run)).currency.value,"未记录");
  run.configuration.capital_context.input_id="input-one";run.configuration.capital_context.initial_cash=100;
  assert.equal(fields(buildResultSummary(run)).currency.value,"未记录");
  run.configuration.capital_context.initial_cash=10000;run.configuration.capital_context.currency=null;run.configuration.capital_context.currency_status="UNRECORDED";
  assert.equal(fields(buildResultSummary(run)).currency.value,"未记录");
});

test("post-completion financial projection warnings preserve success and are plain escaped text",()=>{
  const run=financialNative();run.presentation_warnings=["研究结果已保存；财务补充信息暂时未读全。",{message:"must not stringify"},null,"<script>no action</script>"];
  const before=JSON.stringify(run),model=buildResultSummary(run),html=renderResultSummary(run);
  assert.equal(model.finance.complete,true);assert.equal(model.status,"COMPLETED");
  assert.equal(model.warnings.length,2);assert.match(html,/研究结果已保存/);assert.match(html,/&lt;script&gt;/);
  assert.doesNotMatch(html,/<script>|must not stringify/);assert.equal(JSON.stringify(run),before);assert.equal(model.new_economic_runs,0);
});
