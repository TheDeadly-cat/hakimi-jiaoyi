/* Render only the strict saved-result projection; no inferred metrics. */
(() => {
  "use strict";
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const number = value => finite(value) ? value.toLocaleString("zh-CN", {maximumFractionDigits:6}) : "未记录";
  const shown = value => value === null || value === undefined || value === "" ? "未记录"
    : typeof value === "object" ? JSON.stringify(value) : String(value);
  function renderComparison(comparison, esc) {
    if (comparison?.schema_version !== "hakimi-strict-saved-result-comparison-v1") throw new Error("比较记录格式不受支持，请重新读取。");
    const rows = comparison.rows || [], comparable = comparison.status === "COMPARABLE_CONDITIONS";
    const parameters = [...new Set(rows.flatMap(row => Object.keys(row.strategy_params || {})))];
    const fields = [
      ["结果用途", row => row.role === "BENCHMARK_REFERENCE" ? "基准参考（独立政策）" : "策略研究"],
      ["规则", row => row.strategy_id],
      ["证券身份", row => row.conditions?.security_identity],
      ["评分开始", row => row.conditions?.score_start], ["评分结束", row => row.conditions?.score_end],
      ["本金", row => number(row.conditions?.initial_cash)], ["币种", row => row.conditions?.currency],
      ["净收益率", row => finite(row.net_return_ratio) ? number(row.net_return_ratio * 100) + "%" : "未记录"],
      ["最大回撤", row => finite(row.max_drawdown_ratio) ? number(row.max_drawdown_ratio * 100) + "%" : "未记录"],
      ["已记录手续费", row => number(row.costs?.total_fees)],
      ["手续费率", row => finite(row.costs?.fee_rate) ? number(row.costs.fee_rate * 100) + "%" : "未记录"],
      ["滑点参数", row => finite(row.costs?.slippage_rate) ? (row.costs.slippage_unit === "basis_points"
        ? number(row.costs.slippage_rate) + " 基点" : row.costs.slippage_unit === "ratio"
          ? number(row.costs.slippage_rate * 100) + "%" : number(row.costs.slippage_rate) + "（" + shown(row.costs.slippage_unit) + "）") : "未记录"],
      ["已记录滑点金额", row => number(row.costs?.slippage_amount_recorded)],
      ["仓位及风险（原记录）", row => row.conditions?.position_risk],
      ["数量政策", row => row.conditions?.quantity_policy], ["执行方式", row => row.conditions?.execution_model],
      ["结果证据", row => row.evidence_status],
      ...parameters.map(key => ["参数 " + key, row => row.strategy_params?.[key]]),
    ];
    const message = comparable ? "已记录的关键条件一致。下方收益差仅描述这几份独立本金结果，不表示策略有效性或排名。"
      : comparison.status === "UNKNOWN_CONDITIONS" ? "部分关键条件未记录或记录冲突：只并排展示，无法判断收益差是否可比。"
        : "数据、仓位、成本或执行条件不同，或包含独立基准：只并排展示，不计算收益差。";
    const conditionNotes = rows.map((row, index) => {
      const missing = row.missing_fields?.length || 0;
      const difference = (comparison.mismatches || []).find(item => item.row === index + 1)?.fields?.length || 0;
      return `第 ${index + 1} 项：${missing ? missing + " 项关键条件未记录" : "关键条件已记录"}${difference ? "；" + difference + " 项条件与首项不同" : ""}`;
    }).join("。 ");
    const differences = comparable ? (comparison.differences_from_first || []).map(row =>
      `第 ${row.row} 项相对第一项净收益差：${number(row.net_return_percentage_points)} 个百分点`).join("；") : "";
    return `<h3>保存结果与成本对照</h3><p class="notice">${esc(message)}</p>
      <p>${esc(conditionNotes)}</p><div class="tq-table section-gap"><table><thead><tr><th>字段</th>
      ${rows.map((row,index) => `<th>第 ${index+1} 项<br>${esc(shown(row.strategy_id))}<br>版本 ${esc(shown(row.identities?.task_version))}</th>`).join("")}
      </tr></thead><tbody>${fields.map(([label,get]) => `<tr><th>${esc(label)}</th>${rows.map(row => `<td>${esc(shown(get(row)))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
      ${differences ? `<p>${esc(differences)}</p>` : ""}<p class="muted">未记录的费用或滑点金额不会按零处理。基准保留其原有的入场与保护政策。</p>
      <details><summary>查看完整比较条件、缺失字段与保存身份</summary><pre class="code-detail">${esc(JSON.stringify(comparison,null,2))}</pre></details>`;
  }
  globalThis.HakimiResultComparison = {renderComparison};
  if (typeof module === "object" && module.exports) module.exports = {renderComparison};
})();
