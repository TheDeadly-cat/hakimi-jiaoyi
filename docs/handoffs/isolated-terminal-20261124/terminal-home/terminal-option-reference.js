/* Quote a single strike on the current terminal. Only the explicit read button calls OpenD. */
(() => {
  "use strict";
  const expiries = window.OptionFutuSource?.expiries || [];
  const positive = value => Number.isFinite(value) && value > 0;
  const price = value => positive(value) ? value.toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:4}) : "—";
  const dateTime = value => typeof value === "string" && /(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));
  let archiveFiles;
  async function archives() {
    if (!archiveFiles) archiveFiles = Promise.allSettled(["option-snapshots.json","option-expiries.json"].map(async name => {
      const response = await fetch("./" + name, {mode:"same-origin"});
      if (!response.ok) throw Error("合约归档读取失败");
      return response.json();
    })).then(results => results.map(result => result.status === "fulfilled" ? result.value : null));
    const files = await archiveFiles;
    if (files.some(file => !file)) archiveFiles = null;
    return files;
  }
  function normalizeArchive(raw, symbol, expiry) {
    if (raw?.symbol !== symbol || raw.expiry !== expiry || !dateTime(raw.capturedAt) ||
        !/^[a-f0-9]{64}$/.test(raw.sha256) || !Array.isArray(raw.contracts)) return null;
    const rows = raw.contracts.filter(r => r.symbol === symbol && r.expiry === expiry && ["C","P"].includes(r.type) && positive(r.strike));
    return {symbol,expiry,rows,source:"Nasdaq",spot:raw.underlyingPrice,capturedAt:raw.capturedAt,
      quoteTime:dateTime(raw.contractQuoteAsOf) ? raw.contractQuoteAsOf : null,snapshotId:raw.sha256};
  }
  function mount(host, useQuote) {
    host.classList.add("terminal-option-ref");
    host.innerHTML = `<details><summary>合约报价 <small>查看买卖价并带入期权情景</small></summary><div class="tor-inner">
      <div class="tor-controls"><label>到期日<select data-ref="expiry"></select></label>
      <label>报价来源<select data-ref="source"><option value="archive">Nasdaq 归档</option><option value="futu">富途 OpenD</option></select></label>
      <button type="button" data-ref="read">读取本期富途报价</button></div>
      <p data-ref="status" role="status"></p><label data-ref="strike-label" hidden>行权价 USD <select data-ref="strike"></select></label>
      <div data-ref="quotes"></div></div></details>`;
    const get = key => host.querySelector('[data-ref="'+key+'"]');
    const detail = host.querySelector("details"), expiry = get("expiry"), source = get("source"), strike = get("strike");
    for (const date of expiries) expiry.add(new Option(date,date));
    const cache = new Map();
    let symbol, version=0, bucket=null, reading=false;
    function clear(status) {
      bucket=null; strike.replaceChildren(); get("quotes").replaceChildren(); get("strike-label").hidden=true;
      get("status").textContent=status;
    }
    function displayRows() {
      const rows=bucket?.rows.filter(row=>row.strike===Number(strike.value)) || [];
      const hostRows=get("quotes");
      hostRows.replaceChildren();
      if (!rows.length) return;
      const table=document.createElement("table");
      table.innerHTML="<thead><tr><th>合约</th><th>买价 USD</th><th>卖价 USD</th><th>情景</th></tr></thead>";
      const body=table.createTBody();
      for (const row of rows) {
        const side=row.type || row.right;
        const tr=body.insertRow();
        for (const value of [side==="C"?"看涨":"看跌",price(row.bid),price(row.ask)]) tr.insertCell().textContent=value;
        const cell=tr.insertCell();
        const sameSide=rows.filter(r=>(r.type||r.right)===side);
        const unsupported=row.adjusted || row.suspended || (row.contractRoot && row.contractRoot!==symbol) ||
          (row.specIssues?.length>0) || (row.multiplier!=null && row.multiplier!==100);
        if (unsupported || sameSide.length!==1 || !positive(row.ask) || (positive(row.bid) && row.bid>row.ask)) {
          cell.textContent=unsupported || sameSide.length!==1 ? "规格待核对" : "卖价不可用";continue;
        }
        const button=document.createElement("button");
        button.type="button";button.textContent="采用卖价";
        button.setAttribute("aria-label",(side==="C"?"看涨":"看跌")+" "+row.strike+" 采用卖价");
        const reference={symbol,right:side,strike:row.strike,premium:row.ask,expiry:bucket.expiry,source:bucket.source,
          capturedAt:bucket.capturedAt,asOf:row.askAsOf||bucket.quoteTime||null,bucketId:bucket.snapshotId,
          contractCode:bucket.source==="富途 OpenD"?row.contractCode:null,underlying:positive(bucket.spot)?bucket.spot:null};
        button.addEventListener("click",()=>{if (!useQuote(reference)) get("status").textContent="请先打开当前标的的可编辑情景。";});
        cell.append(button);
      }
      hostRows.append(table);
    }
    function display(next) {
      clear("");
      if (!next?.rows.length) {clear(symbol+" 在该来源和到期日暂无可用合约。");return;}
      bucket=next;
      const levels=[...new Set(next.rows.map(r=>r.strike))].sort((a,b)=>a-b);
      for (const value of levels) strike.add(new Option(String(value),String(value)));
      if (positive(next.spot)) strike.value=String(levels.reduce((best,x)=>Math.abs(x-next.spot)<Math.abs(best-next.spot)?x:best));
      get("strike-label").hidden=false;
      get("status").textContent=next.source+" · "+symbol+" · "+next.expiry+" 到期 · 采集 "+next.capturedAt+
        (next.quoteTime?" · 报价 "+next.quoteTime:" · 买卖报价时点未知")+" · "+next.rows.length+" 份收录合约";
      displayRows();
    }
    const key=()=>symbol+"/"+expiry.value;
    async function refresh() {
      const token=++version;
      get("read").disabled=reading || !window.OptionFutuSource?.supported(symbol,expiry.value);
      clear("");
      if (!detail.open) return;
      if (source.value==="futu") {
        if (cache.has(key())) display(cache.get(key()));
        else clear(get("read").disabled && !reading?"该标的或到期日暂未接入富途期权。":"尚未读取本期富途合约。");
        return;
      }
      clear("正在读取本地归档…");
      try {
        const [weekly,monthly]=await archives();
        if (token!==version) return;
        const raw=weekly?.expiry===expiry.value ? weekly?.symbols?.[symbol] : monthly?.expiries?.[expiry.value]?.symbols?.[symbol];
        display(normalizeArchive(raw,symbol,expiry.value));
      } catch { if(token===version)clear("本期合约归档暂不可用。"); }
    }
    get("read").addEventListener("click",async()=>{
      if (reading || !window.OptionFutuSource?.supported(symbol,expiry.value)) return;
      const token=++version, id=key();
      reading=true;source.value="futu";get("read").disabled=true;clear("正在读取富途报价…");
      try {
        const result=await window.OptionFutuSource.read(symbol,expiry.value);
        if(token===version){cache.set(id,result);display(result);}
      } catch(error) {if(token===version){cache.delete(id);clear(error.message||"富途读取失败。");}}
      finally {reading=false;get("read").disabled=!window.OptionFutuSource?.supported(symbol,expiry.value);}
    });
    expiry.addEventListener("change",refresh);source.addEventListener("change",refresh);
    strike.addEventListener("change",displayRows);detail.addEventListener("toggle",refresh);
    return {select(next){if(symbol===next)return; symbol=next; source.value="archive"; return refresh();}};
  }
  window.TerminalOptionReference={mount};
})();
