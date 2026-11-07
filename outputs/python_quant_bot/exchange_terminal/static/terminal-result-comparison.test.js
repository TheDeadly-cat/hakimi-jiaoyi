"use strict";
const test = require("node:test"), assert = require("node:assert/strict");
const {renderComparison} = require("./terminal-result-comparison");
const esc = value => String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
const row = {strategy_id:"<unsafe>",strategy_params:{threshold:.015},identities:{task_version:1},
  role:"STRATEGY_RESULT",conditions:{initial_cash:10000,currency:"USD"},costs:{total_fees:null,fee_rate:.0005,slippage_rate:2,slippage_unit:"basis_points"},
  net_return_ratio:0,missing_fields:["quantity_policy"]};
test("missing cost is not zero and unknown conditions never expose a supplied delta",()=>{
  const html = renderComparison({schema_version:"hakimi-strict-saved-result-comparison-v1",status:"UNKNOWN_CONDITIONS",rows:[row,row],
    differences_from_first:[{row:2,net_return_percentage_points:999}]},esc);
  assert.match(html,/无法判断/);assert.match(html,/未记录/);assert.match(html,/0.05%/);assert.match(html,/2 基点/);
  assert.match(html,/&lt;unsafe&gt;/);assert.doesNotMatch(html,/<unsafe>/);assert.doesNotMatch(html,/净收益差：999/);
  assert.match(html,/>0%</);
});
test("only comparable records display descriptive percentage point differences",()=>{
  const html = renderComparison({schema_version:"hakimi-strict-saved-result-comparison-v1",status:"COMPARABLE_CONDITIONS",rows:[row,row],
    differences_from_first:[{row:2,net_return_percentage_points:-3}]},esc);
  assert.match(html,/净收益差：-3 个百分点/);assert.match(html,/不表示策略有效性或排名/);
  assert.throws(()=>renderComparison({schema_version:"old-comparison"},esc));
});
