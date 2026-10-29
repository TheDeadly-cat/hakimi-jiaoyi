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
