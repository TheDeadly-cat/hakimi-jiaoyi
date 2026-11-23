/* Inline terminal research and hypothetical scenarios. All records use the original workflow API. */
(() => {
  "use strict";
  const DAYS = [7, 30, 180];
  const TOOLS = {STOCK_LONG:"正股买入",CALL_LONG:"买入看涨期权",PUT_LONG:"买入看跌期权",WAIT:"观望"};
  const TABS = {factors:"因子研究",scenario:"工具与期限",history:"保存记录"};
  const STUDIED = new Set(["QQQ","SPY"]);
  const statuses = {ENABLE:"启用",HOLD:"搁置",ABSTAIN:"样本不足"};
  const symbols = value => String(value ?? "").trim().toUpperCase().replace(/^US\./,"");
  const validSymbol = value => /^[A-Z][A-Z0-9.-]{0,39}$/.test(value);
  const num = (v,d=2) => Number.isFinite(v) ? v.toLocaleString("zh-CN",{maximumFractionDigits:d,minimumFractionDigits:d}) : "缺资料";
  const metric = (v,unit="") => Number.isFinite(v) ? num(v)+unit : "缺资料";
  const time = v => typeof v==="string" && Number.isFinite(Date.parse(v)) ?
    new Date(v).toLocaleString("zh-CN",{timeZone:"Asia/Shanghai",hour12:false})+" 北京时间" : "时间未记录";
  function el(tag,text,cls) {
    const n=document.createElement(tag);
    if (text!==undefined) n.textContent=String(text);
    if (cls) n.className=cls;
    return n;
  }
  function factGrid(values) {
    const grid=el("dl",undefined,"trp-facts");
    for (const [name,value] of values) {
      const item=el("div");item.append(el("dt",name),el("dd",value));grid.append(item);
    }
    return grid;
  }
  async function api(path,body) {
    const opts={cache:"no-store",mode:"same-origin"};
    if (body!==undefined) Object.assign(opts,{method:"POST",headers:{"Content-Type":"application/json","X-Hakimi-Write":"1"},body:JSON.stringify(body)});
    const response=await fetch("/api/workflow/"+path,opts);
    let data;try {data=await response.json();} catch {throw Error("本地服务未返回有效资料。");}
    if (!response.ok||data.ok===false) throw Error(data.error||data.message||"本地操作未完成。");
    return data;
  }
  const input = (key,label,attrs="")=>`<label>${label}<input type="number" step="any" data-field="${key}" ${attrs}></label>`;
  function mount(root,options={}) {
    if (!(root instanceof HTMLElement)) throw TypeError("A research pane element is required");
    if (root.__terminalResearchPane) return root.__terminalResearchPane;
    root.classList.add("terminal-research-pane");
    root.innerHTML=`
      <div class="trp-head"><strong>研究与模拟</strong><span data-role="identity"></span></div>
      <div class="trp-tabs" role="tablist" aria-label="研究与模拟">${Object.entries(TABS).map(([k,v])=>`<button type="button" role="tab" data-tab="${k}" aria-selected="false">${v}</button>`).join("")}</div>
      <p data-role="notice" class="trp-status" role="status" aria-live="polite"></p>
      <section data-section="factors" role="tabpanel" aria-label="因子研究">
        <div class="trp-fields trp-selection" data-role="selection">
          <label>规则<select data-field="strategy"><option value="pullback">顺势回调</option><option value="breakout">区间突破</option><option value="reversal">超跌反弹</option></select></label>
          <label>研究区间<select data-field="period"><option value="external2026">2026 外部历史区间</option><option value="seen">2023–25 已观察区间</option><option value="development">2018–22 开发期</option></select></label>
          <label>收盘观察来源<select data-field="source"><option value="recent">近期历史快照</option><option value="futu">富途历史快照</option></select></label>
        </div><div data-role="evidence"></div>
      </section>
      <section data-section="scenario" role="tabpanel" aria-label="工具与期限" hidden>
        <p class="trp-hint">用自己的价格和费用假设比较到期损益。每份记录保存一种工具和一个期限。</p>
        <div class="trp-fields" data-role="inputs">
          <label>我的方向<select data-field="direction"><option value="WAIT">未作方向判断</option><option value="BULLISH">偏多假设</option><option value="BEARISH">偏空假设</option></select></label>
          ${input("capital","本金 USD",'min="1" value="10000"')}
          ${input("entry","假设起始价 USD",'min="0.0001" placeholder="输入标的价格"')}
          ${DAYS.map(d=>input("exit"+d,d+" 天期末价 USD",'min="0" placeholder="该期限的假设"')).join("")}
          <div><label>费用口径<select data-field="feeMode">
            <option value="MANUAL">手填往返总额 USD</option>
            <option value="FUTU_US_MARGIN_SIM_20261124">富途美股模拟费表估算</option>
            <option value="EQUITY_ORDER_ASSUMPTION" hidden disabled>保存的分侧费用假设</option>
          </select></label><input type="number" step="any" min="0" placeholder="填 0 表示假设免费" aria-label="手填往返成本 USD" data-field="cost"></div>
          <label>正股暴露<select data-field="leverage"><option value="1">1 倍</option><option value="2">2 倍假设</option><option value="3">3 倍假设</option></select></label>
          ${input("rate","正股融资年率 %",'min="0" max="100" value="0"')}
        </div>
        <div data-role="option-quotes"></div><p data-role="quote-origin" class="trp-hint"></p>
        <details data-role="option-fields"><summary>期权合约假设</summary><p class="trp-hint">看涨与看跌分别输入每股权利金，假设所选期末正好到期，每张 100 股。使用同一行权价、张数及各自权利金比较已填写的期限。</p>
          <div class="trp-fields">${input("strike","行权价 USD",'min="0.0001"')}${input("call","看涨权利金 USD / 股",'min="0.0001"')}${input("put","看跌权利金 USD / 股",'min="0.0001"')}${input("contracts","合约张数",'min="1" value="1"')}</div>
          <details><summary>分别设置各期限的权利金</summary><p class="trp-hint">仅覆盖填写的期限，作为手工假设保存。</p><div class="trp-fields">${DAYS.map(d=>input("call"+d,d+" 天看涨 / 股",'min="0.0001"')+input("put"+d,d+" 天看跌 / 股",'min="0.0001"')).join("")}</div></details></details>
        <p class="trp-hint">融资费按日历天累计；实际成交、合约时间价值、保证金变化与税费未验证。观望按零损益、零利息计算。</p>
        <div class="trp-actions"><button type="button" data-action="compare">运行情景比较</button><button type="button" data-action="new" hidden>开始新分析</button></div>
        <div data-role="matrix"></div><div data-role="result"></div>
        <div class="trp-save"><label>记录名称<input type="text" data-field="title" maxlength="100" placeholder="为本次情景命名"></label><button type="button" data-action="save">保存所选情景</button></div>
      </section>
      <section data-section="history" role="tabpanel" aria-label="保存记录" hidden>
        <div class="trp-actions"><strong>本工作区已保存的记录</strong><button type="button" data-action="refresh">刷新列表</button></div><div data-role="records"></div>
      </section>`;
    const qs=selector=>root.querySelector(selector), all=selector=>Array.from(root.querySelectorAll(selector));
    const role=k=>qs('[data-role="'+k+'"]'),field=k=>qs('[data-field="'+k+'"]'),action=k=>qs('[data-action="'+k+'"]');
    const pane={root,select,showTab,openRecord,useOptionQuote,quoteHost:role("option-quotes")};
    root.__terminalResearchPane=pane;
    let symbol="",tab="factors",version=0,context=null,record=null,chosen=null,pending=null,busy=false;
    let rows=[],issues=[],runs=new Map(),selection=null,sequence=0,quoteBindings={};
    const notice=(text="",error=false)=>{role("notice").textContent=text;role("notice").classList.toggle("trp-error",error);};
    const identity=()=>{role("identity").textContent=symbol+(record?" · 已保存快照":"");};
    function showTab(key) {
      if (!Object.hasOwn(TABS,key)) return;
      tab=key;
      for (const n of all("[data-tab]")) {const on=n.dataset.tab===key;n.setAttribute("aria-selected",String(on));n.tabIndex=on?0:-1;}
      for (const n of all("[data-section]")) n.hidden=n.dataset.section!==key;
    }
    function resetAssumptions() {
      quoteBindings={};
      for (const k of ["entry","exit7","exit30","exit180","strike","call","put","title",...DAYS.flatMap(d=>["call"+d,"put"+d])]) field(k).value="";
      for (const [k,v] of Object.entries({capital:"10000",cost:"",feeMode:"MANUAL",leverage:"1",rate:"0",contracts:"1",direction:"WAIT"})) field(k).value=v;
      role("option-fields").open=false;
      role("quote-origin").textContent="";
    }
    function clearRuns() {
      runs=new Map();chosen=null;pending=null;role("matrix").replaceChildren();role("result").replaceChildren();
    }
    function controls() {
      const frozen=!!record;
      for (const n of all("[data-field]")) n.disabled=busy||frozen;
      field("cost").hidden=field("feeMode").value!=="MANUAL";
      field("cost").disabled=busy||frozen||field("cost").hidden;
      field("rate").disabled=busy||frozen||field("leverage").value==="1";
      field("title").disabled=busy||frozen||!!pending;
      action("compare").disabled=busy||frozen||!context;
      action("save").disabled=busy||frozen||!chosen||!context;
      action("new").hidden=!frozen;
      action("new").disabled=busy;
      action("refresh").disabled=busy;
      role("option-quotes").hidden=frozen;
      role("selection").hidden=!STUDIED.has(symbol)||frozen;
      for (const n of all("[data-record], [data-pick]")) n.disabled=busy||!!pending;
      identity();
    }
    function useOptionQuote(quote) {
      if (busy||record||!context||!quote||symbols(quote.symbol)!==symbol||!["C","P"].includes(quote.right)
          ||!Number.isFinite(quote.strike)||quote.strike<=0||!Number.isFinite(quote.premium)||quote.premium<=0
          ||!/^\d{4}-\d{2}-\d{2}$/.test(quote.expiry||"")||!["Nasdaq","富途 OpenD"].includes(quote.source)
          ||!Number.isFinite(Date.parse(quote.capturedAt))||!/^[a-f0-9]{64}$/.test(quote.bucketId||"")) return false;
      if (Number(field("strike").value)!==quote.strike) {field("call").value="";field("put").value="";quoteBindings={};}
      quoteBindings[quote.right]={...quote};
      field("strike").value=quote.strike;field(quote.right==="C"?"call":"put").value=quote.premium;
      if(Number.isFinite(quote.underlying)&&quote.underlying>0)field("entry").value=quote.underlying;
      role("quote-origin").textContent=quoteNote(quote);
      clearRuns();role("option-fields").open=true;showTab("scenario");controls();notice("报价已带入，填写期末价格后可比较。");return true;
    }
    function quoteNote(q) {
      return q.symbol+" "+q.expiry+" 到期 · "+(q.right==="C"?"看涨":"看跌")+" · "+q.source+
        " · 采集 "+time(q.capturedAt)+" · 报价 "+time(q.asOf)+(q.contractCode?" · "+q.contractCode:"")+
        "。7、30、180 天为假设持有期，各自按期末到期试算；不能据此估计该合约在实际到期前的市价。";
    }
    function chosenSelection() {
      return STUDIED.has(symbol)?{strategy:field("strategy").value,period:field("period").value,source:field("source").value}:null;
    }
    async function loadContext() {
      const epoch=++version;
      busy=true;context=null;selection=chosenSelection();clearRuns();renderEvidence(null);controls();notice("正在核对 "+symbol+" 的本地研究与记录…");
      try {
        const data=await api("context?"+new URLSearchParams({symbol,...selection}));
        if (epoch!==version) return false;
        if (!data.workspace_context||!data.evidence_sha256||data.evidence?.symbol!==symbol ||
            data.evidence.decision_available!==false || (selection && (!data.evidence.studio_strategy ||
              Object.keys(selection).some(k=>data.evidence.studio_strategy.selection?.[k]!==selection[k])))) throw Error("所选标的或研究版本未能核对。");
        context=data;rows=data.records||[];issues=data.record_issues||[];
        renderEvidence(data.evidence);renderRecords();notice("");return true;
      } catch (err) {
        if (epoch===version) {rows=[];issues=[];renderRecords(false);notice("研究资料读取失败："+err.message,true);}
        return false;
      } finally {if(epoch===version){busy=false;controls();}}
    }
    async function select(value) {
      const next=symbols(value);
      if (next===symbol&&(record||context||busy)) return true;
      symbol=next;version++;sequence++;record=null;context=null;pending=null;busy=false;rows=[];issues=[];
      resetAssumptions();clearRuns();renderRecords(false);renderEvidence(null);controls();
      if (!validSymbol(symbol)) {notice("请选择有效的股票或 ETF 代码。",true);return false;}
      return loadContext();
    }
    function renderEvidence(e) {
      const host=role("evidence");host.replaceChildren();
      const verdict=el("div",undefined,"trp-verdict");
      verdict.append(el("span",record?"保存时的方向判断":"当前方向"),el("strong","资料不足，无法判断"));
      host.append(verdict);
      if (!e) {host.append(el("p","尚无已核对的标的资料。","trp-hint"));return;}
      if (e.symbol!==symbol||e.decision_available!==false) {host.append(el("p","快照与当前标的不一致，研究资料不可用。","trp-error"));return;}
      const fixed=symbol==="QQQ"&&e.status==="FIXED_RESEARCH_ONLY";
      // Older non-QQQ records can retain a QQQ model and factor payload under a relabelled symbol.
      const foreign=symbol!=="QQQ"&&Boolean(e.model_version||e.filter_version||e.source_hash||e.snapshot_id||e.factors?.length);
      const cards=el("div",undefined,"trp-evidence-columns");
      for(const [label,key,empty] of [
        ["支持","supporting","暂无支持当前方向的已核验依据。"],
        ["反对或限制","opposing","暂无已记录的反向依据。"],
        ["不确定","uncertain",foreign?"原记录夹带其他标的的研究资料，本标的适用性未核实。":"当前方向的适用性仍待核实。"]
      ]) {
        const card=el("div"),texts=!foreign&&Array.isArray(e[key])?e[key].filter(v=>typeof v==="string"&&v.trim()):[];
        card.append(el("strong",label),el("p",texts[0]||empty));
        if(texts.length>1) {
          const rest=el("details");rest.append(el("summary","另 "+(texts.length-1)+" 条"));
          for(const v of texts.slice(1))rest.append(el("p",v));
          card.append(rest);
        }
        cards.append(card);
      }
      host.append(cards);
      if(fixed) {
        const asOf=typeof e.data_as_of==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(e.data_as_of)?e.data_as_of:time(e.data_as_of);
        host.append(el("p","专项研究版本 "+(e.model_version||"未记录")+" / "+(e.filter_version||"未记录")+
          " · 文件更新 "+time(e.source_updated_at)+" · 因子值截至 "+asOf,"trp-hint"));
      }
      const s=e.studio_strategy;
      if (s&&s.schema==="studio.strategy-review@1"&&s.symbol===symbol&&s.decision_available===false&&s.execution_authorized===false && STUDIED.has(symbol)) {
        const obs=s.observation||{},m=s.metrics||{},period=s.period||{};
        host.append(el("h4","历史收盘观察 · "+(s.strategy?.name||"所选规则")),el("p",s.strategy?.rule||"规则说明未记录。"),
          el("p",[obs.date||"日期未记录",obs.provider||"行情来源未知",obs.triggered===true?"收盘条件已触发":obs.triggered===false?"收盘条件未触发":"收盘状态未知"].join(" · "),"trp-emphasis"),
          el("p",obs.evidence||"缺少该收盘日的规则观察。","trp-hint"),
          el("p",(period.label||"历史区间")+" · "+(period.start||"—")+" 至 "+(period.end||"—"),"trp-subhead"),
          factGrid([["样本",Number.isInteger(m.count)?m.count+" 笔":"缺资料"],["样本胜率",metric(m.winRatePct,"%")],
            ["平均净收益",metric(m.avgNetPct,"%")],["五日定期基准",metric(m.baselineAvgNetPct,"%")],["超额",metric(m.excessPp," 个百分点")]]),
          el("p",[s.method?.baseCost,m.accounting,"胜率仅描述上述历史样本；单次交易概率与当前多空方向均未验证。"].filter(Boolean).join(" "),"trp-hint"));
        if (s.factorTraining?.status==="RECORDED") {
          const t=s.factorTraining,f=t.final||{};
          host.append(el("p","开发期训练截至 "+t.trainedThrough+" · "+(statuses[f.state]||"未知")+" · "+(f.reason||""),"trp-hint"));
        }
      } else {
        host.append(el("h4",symbol+" · "+(record?"保存时的研究资料":"当前研究范围")),
          el("p",STUDIED.has(symbol)?"此份资料未附三条策略的收盘观察与区间对照。":"此标的缺少已核对的策略研究，可继续做用户假设下的情景比较。","trp-hint"));
      }
      if (symbol==="QQQ"&&e.status==="FIXED_RESEARCH_ONLY"&&Array.isArray(e.factors)&&e.factors.length) {
        const detail=el("details");detail.append(el("summary","固定因子公式 · "+e.factors.length+" 项"));
        detail.append(el("p","已登记公式与定义；当期因子数值未获核验。","trp-hint"));
        for (const f of e.factors) {const item=el("p");item.append(el("strong",f.title||f.factor_id),document.createTextNode(" · "+(f.formula||"公式未记录")));detail.append(item);}
        host.append(detail);
      }
      if (record) host.append(el("p","研究与模拟来自 "+time(record.created_at)+" 保存的快照。","trp-hint"));
      const legacy=e.research_review;
      if(symbol==="QQQ"&&legacy?.scope_symbol==="QQQ"&&legacy.status==="HOLD"&&legacy.decision_available===false) {
        const detail=el("details");detail.append(el("summary","固定训练的适用范围与限制"));
        const basis=legacy.source||{};
        detail.append(el("p",[basis.provider,basis.range_start&&basis.range_end?(basis.range_start+" 至 "+basis.range_end):"",basis.price_basis].filter(Boolean).join(" · ")),
          el("p","历史训练状态：搁置。新增独立样本须另行取得；当前方向未获验证。","trp-hint"));
        host.append(detail);
      }
    }
    function renderRecords(loaded=true) {
      const host=role("records");host.replaceChildren();
      if (!rows.length) host.append(el("p",loaded?"暂无已保存记录。":"记录列表尚未载入。","trp-hint"));
      for (const item of rows) {
        const button=el("button",undefined,"trp-record");
        button.type="button";button.dataset.record=item.record_id;
        button.append(el("strong",item.title),el("span",[item.symbol,TOOLS[item.tool]||item.tool,item.horizon_days+" 天",time(item.created_at)].join(" · ")));
        button.addEventListener("click",()=>openRecord(item.record_id));host.append(button);
      }
      if (issues.length) host.append(el("p",issues.length+" 条记录未通过完整性核对，原文件已保留。","trp-error"));
    }
    function readNumber(key,label,min=0) {
      const raw=field(key).value.trim(),v=Number(raw);
      if (!raw||!Number.isFinite(v)||v<min) throw Error("请填写"+label+"。");
      return v;
    }
    function assumptions(tool,days) {
      const stock=tool==="STOCK_LONG",wait=tool==="WAIT",option=tool==="CALL_LONG"||tool==="PUT_LONG";
      const useFeeSchedule=!wait && field("feeMode").value==="FUTU_US_MARGIN_SIM_20261124";
      const leverage=stock?Number(field("leverage").value):1;
      const side=tool==="CALL_LONG"?"call":"put",override=option&&field(side+days).value!=="";
      const i={symbol,horizon_days:days,tool,direction:field("direction").value,capital:readNumber("capital","本金",1),
        entry_price:wait?1:readNumber("entry","起始价",.0001),exit_price:wait?1:readNumber("exit"+days,days+"天期末价"),
        round_trip_cost:wait||useFeeSchedule?0:readNumber("cost","往返成本"),leverage,
        annual_rate_pct:leverage>1?readNumber("rate","融资年率"):0,
        strike:option?readNumber("strike","行权价",.0001):0,
        premium_per_share:option?readNumber(override?side+days:side,"该方向的权利金",.0001):0,
        contracts:option?readNumber("contracts","张数",1):0,multiplier:100};
      if (useFeeSchedule) i.fee_model={mode:"FUTU_US_MARGIN_SIM_20261124",currency:"USD"};
      const bound=option&&!override&&quoteBindings[tool==="CALL_LONG"?"C":"P"];
      if(bound&&symbols(bound.symbol)===symbol&&bound.strike===i.strike&&bound.premium===i.premium_per_share)
        i.option_reference={...bound};
      return i;
    }
    function validatePreview(p,tool,days) {
      return p?.inputs?.symbol===symbol && p.inputs.tool===tool && p.inputs.horizon_days===days &&
        p.evidence?.symbol===symbol && /^[a-f0-9]{64}$/.test(p.evidence_sha256||"") &&
        p.result?.decision_available===false && p.result?.execution_authorized===false && Number.isFinite(p.result.net_pnl);
    }
    async function compare() {
      if (!context||record||busy) return;
      const epoch=++version;busy=true;clearRuns();controls();notice("正在按输入比较可计算的情景…");
      const work=[];
      for (const tool of Object.keys(TOOLS)) for (const days of DAYS) {
        const key=tool+"/"+days;
        try {work.push({key,tool,days,inputs:assumptions(tool,days)});}
        catch(err){runs.set(key,{error:err.message});}
      }
      const scope=context.workspace_context,selected=selection&&{...selection};
      async function worker() {
        while (work.length&&version===epoch) {
          const {key,tool,days,inputs}=work.shift();
          try {
            const p=await api("simulate",{workspace_context:scope,inputs,...(selected?{market_selection:selected}:{})});
            if (version!==epoch) return;
            if (!validatePreview(p,tool,days) || context.evidence_sha256!==p.evidence_sha256) throw Error("情景证据与当前资料不一致，请刷新重新比较。");
            runs.set(key,{preview:p});
          } catch(err){if(version===epoch)runs.set(key,{error:err.message});}
        }
      }
      await Promise.all([worker(),worker()]);
      if (epoch!==version) return;
      busy=false;
      const first=["STOCK_LONG/30",...Object.keys(TOOLS).flatMap(t=>DAYS.map(d=>t+"/"+d))].find(k=>runs.get(k)?.preview);
      chosen=first?runs.get(first).preview:null;
      renderMatrix();renderResult();controls();notice(chosen?"比较已完成。点表中金额查看该情景并保存。":"尚无可计算的情景。",!chosen);
    }
    function renderMatrix() {
      const table=el("table"),head=table.createTHead().insertRow();
      for(const label of ["假设净损益 USD",...DAYS.map(d=>d+" 天")])head.append(el("th",label));
      const body=table.createTBody();
      for(const tool of Object.keys(TOOLS)){
        const row=body.insertRow();row.append(el("th",TOOLS[tool]));
        for(const days of DAYS){
          const slot=runs.get(tool+"/"+days),td=row.insertCell();
          if(slot?.preview){
            const btn=el("button",num(slot.preview.result.net_pnl));btn.type="button";btn.dataset.pick=tool+"/"+days;
            btn.setAttribute("aria-label",TOOLS[tool]+" "+days+" 天，假设净损益 "+btn.textContent+" USD");btn.setAttribute("aria-pressed",String(slot.preview===chosen));
            btn.addEventListener("click",()=>{chosen=slot.preview;pending=null;renderMatrix();renderResult();controls();});td.append(btn);
          } else {td.textContent=slot?.error||"缺资料";td.className="trp-hint";}
        }
      }
      role("matrix").replaceChildren(table);
    }
    function renderResult() {
      const host=role("result");host.replaceChildren();
      const p=record||chosen;if(!p)return;
      const i=p.inputs,r=p.result;
      host.append(el("h4",(record?"保存时情景":"所选情景")+" · "+symbol+" · "+TOOLS[i.tool]+" · "+i.horizon_days+" 天"),
        factGrid([["假设毛损益",num(r.gross_pnl)],["已计交易成本",num(r.trading_cost)],["融资费用",num(r.financing_cost)],
          ["净损益 USD",num(r.net_pnl)],["期末本金 USD",num(r.end_capital)]]));
      if (i.fee_model && r.fee_breakdown) {
        const fees=r.fee_breakdown;
        const sell=fees.sell_usd==null ? "未假设卖出委托" : "卖方估费 "+num(fees.sell_usd)+" USD";
        host.append(el("p","买方估费 "+num(fees.buy_usd)+" USD · "+sell+" · 券商实付费用未核实。","trp-hint"));
      }
      if(i.tool==="CALL_LONG"||i.tool==="PUT_LONG") {
        host.append(el("p","假设权利金支出 "+num(r.premium_cost)+" USD · 到期内在价值 "+num(r.payoff)+" USD。","trp-hint"));
        host.append(el("p",i.option_reference?quoteNote(i.option_reference):
          (record?"保存时未附合约报价来源，按记录中的手工假设展示。":"此情景使用手工合约假设。"),"trp-hint"));
      }
      host.append(el("p",i.tool==="WAIT"?"观望情景不持仓，未估计现金利息。":"假设期末价 "+num(i.exit_price)+" USD · 所有金额基于输入条件。","trp-hint"));
      if(Array.isArray(r.warnings)&&r.warnings.length) {
        const details=el("details");details.append(el("summary","查看本次模拟的假设与限制"));
        for(const warning of r.warnings)details.append(el("p",warning,"trp-hint"));
        host.append(details);
      }
      if(record)host.append(el("p",record.title+" · "+time(record.created_at)+" · 只读重开","trp-emphasis"));
    }
    function fillFromSaved(doc) {
      resetAssumptions();
      const i=doc.inputs;
      for(const [k,v] of Object.entries({direction:i.direction,capital:i.capital,entry:i.entry_price,["exit"+i.horizon_days]:i.exit_price,
        cost:i.round_trip_cost,feeMode:i.fee_model?.mode||"MANUAL",leverage:i.leverage,rate:i.annual_rate_pct,title:doc.title}))field(k).value=v;
      if(i.tool==="CALL_LONG"||i.tool==="PUT_LONG"){field("strike").value=i.strike;field(i.tool==="CALL_LONG"?"call":"put").value=i.premium_per_share;
        field("contracts").value=i.contracts;role("option-fields").open=true;}
    }
    function bindRecord(doc) {
      if(doc?.schema_version!=="hakimi.factor-workflow-record@1"||!validSymbol(doc.inputs?.symbol)||!doc.record_id||
         !Object.hasOwn(TOOLS,doc.inputs.tool)||!DAYS.includes(doc.inputs.horizon_days)||doc.evidence?.symbol!==doc.inputs.symbol||
         doc.result?.decision_available!==false||doc.result?.execution_authorized!==false||!Number.isFinite(doc.result.net_pnl)) throw Error("记录标的或版本未能核实。");
      const changed=symbol!==doc.inputs.symbol;
      clearRuns();symbol=doc.inputs.symbol;record=doc;context=null;selection=null;busy=false;
      fillFromSaved(doc);renderEvidence(doc.evidence);renderResult();controls();showTab("scenario");
      notice("已读取保存时的输入、证据与结果。");
      if(changed&&options.onSelect) {
        const failed=()=>{if(record===doc)notice("快照已重开，首页标的同步未完成。",true);};
        try {Promise.resolve(options.onSelect(symbol,{source:"research-history",recordId:doc.record_id})).catch(failed);} catch {failed();}
      }
    }
    async function openRecord(id) {
      if(!/^[a-f0-9-]{36}$/.test(id||"")){notice("记录编号无效。",true);return false;}
      const epoch=++version;busy=true;controls();notice("正在打开保存记录…");
      try {const doc=await api("records/"+encodeURIComponent(id));
        if(epoch!==version)return false;
        if(doc.record_id!==id)throw Error("记录身份不一致。");
        bindRecord(doc);return true;
      } catch(err){if(epoch===version)notice("打开失败："+err.message,true);return false;}
      finally{if(epoch===version){busy=false;controls();}}
    }
    async function save() {
      if(!context||!chosen||busy||record)return;
      const title=field("title").value.trim();if(!title){notice("请填写记录名称。",true);field("title").focus();return;}
      if(!pending)pending={workspace_context:context.workspace_context,request_id:crypto.randomUUID(),title,inputs:chosen.inputs,
        expected_evidence_sha256:chosen.evidence_sha256,...(selection?{market_selection:{...selection}}:{})};
      const epoch=++version;busy=true;controls();notice("正在保存所选情景…");
      try {const doc=await api("records",pending);if(epoch!==version)return;
        if(doc.request_id!==pending.request_id||doc.evidence_sha256!==pending.expected_evidence_sha256||doc.inputs.symbol!==symbol)throw Error("保存回执与请求不一致。");
        rows=[{record_id:doc.record_id,created_at:doc.created_at,title:doc.title,symbol,
          tool:doc.inputs.tool,horizon_days:doc.inputs.horizon_days},...rows.filter(r=>r.record_id!==doc.record_id)];
        bindRecord(doc);renderRecords();notice("已保存，可从“保存记录”重开。");
      } catch(err){if(epoch===version)notice("保存未确认，可重试同一请求："+err.message,true);}
      finally {if(epoch===version){busy=false;controls();}}
    }
    async function refreshRecords(){
      const v=version, request=++sequence;notice("正在读取记录列表…");
      try {const data=await api("context?"+new URLSearchParams({symbol}));
        if(v===version&&request===sequence){rows=data.records||[];issues=data.record_issues||[];renderRecords();controls();notice("");}
      } catch(err){if(v===version&&request===sequence)notice("刷新失败："+err.message,true);}
    }
    for(const b of all("[data-tab]")){
      b.addEventListener("click",()=>showTab(b.dataset.tab));
      b.addEventListener("keydown",ev=>{const keys=Object.keys(TABS),i=keys.indexOf(tab);
        if(!["ArrowLeft","ArrowRight","Home","End"].includes(ev.key))return;
        ev.preventDefault();const key=ev.key==="Home"?keys[0]:ev.key==="End"?keys.at(-1):keys[(i+(ev.key==="ArrowLeft"?-1:1)+keys.length)%keys.length];
        showTab(key);qs('[data-tab="'+key+'"]').focus();});
    }
    for(const k of ["strategy","period","source"])field(k).addEventListener("change",loadContext);
    for(const n of all("[data-field]"))if(!["strategy","period","source","title"].includes(n.dataset.field)){
      n.addEventListener(n.tagName==="SELECT"?"change":"input",()=>{
        if(record||busy)return;
        if(["strike","call","put","entry","contracts"].includes(n.dataset.field)){quoteBindings={};role("quote-origin").textContent="";}
        clearRuns();controls();notice("假设已修改，请运行比较。");
      });
    }
    action("compare").addEventListener("click",compare);action("save").addEventListener("click",save);
    action("refresh").addEventListener("click",refreshRecords);
    action("new").addEventListener("click",()=>{record=null;resetAssumptions();loadContext();});
    showTab("factors");
    window.TerminalResearchPane.active=pane;
    pane.ready=select(options.symbol||"QQQ");return pane;
  }
  window.TerminalResearchPane={mount,active:null,select(...a){return this.active?.select(...a);},
    showTab(...a){return this.active?.showTab(...a);},openRecord(...a){return this.active?.openRecord(...a);}};
})();
