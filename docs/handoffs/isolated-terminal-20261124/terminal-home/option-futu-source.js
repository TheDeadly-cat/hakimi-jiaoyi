"use strict";
(() => {
  const expiries=["2026-11-27","2026-12-18","2027-01-15"];
  const supported=(symbol,date)=>["QQQ","SPY","SOXX"].includes(symbol) && expiries.includes(date);
  const zoned=t=>typeof t==="string" && /(?:Z|[+-]\d\d:\d\d)$/.test(t) && Number.isFinite(Date.parse(t));
  const marketTime=t=>zoned(t) || (typeof t==="string" && /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d America\/New_York$/.test(t)) ? t : null;
  const count=n=>Number.isSafeInteger(n) && n>=0;
  const numberOrMissing=n=>n==null || (typeof n==="number" && Number.isFinite(n) && n>=0);
  function normalize(data,symbol,expiry) {
    const b=data?.bucket,c=b?.coverage;
    if(!data?.ok || !["AVAILABLE","PARTIAL"].includes(data.status) || data.symbol!==symbol || data.expiry!==expiry ||
       b?.symbol!==symbol || b.expiry!==expiry || b.source!=="富途 OpenD" || !zoned(b.capturedAt) ||
       typeof b.sha256!=="string" || !/^[0-9a-f]{64}$/.test(b.sha256) ||
       !Array.isArray(b.contracts) || !b.contracts.length || !c ||
       ![c.chainContractCount,c.selectedContractCount,c.returnedContractCount].every(count) ||
       c.returnedContractCount>c.selectedContractCount || c.selectedContractCount>c.chainContractCount ||
       c.selectedContractCount>400 || b.contracts.length>c.selectedContractCount) throw Error("取样标的、到期、覆盖数或来源摘要无法核对。");
    const ids=new Set();
    const spot=Number.isFinite(b.underlyingPrice)&&b.underlyingPrice>0?b.underlyingPrice:null;
    const rows=b.contracts.map(r=>{
      if(r?.symbol!==symbol || r.expiry!==expiry || !["C","P"].includes(r.type) || !Number.isFinite(r.strike) || r.strike<=0 ||
        typeof r.contractCode!=="string" || !r.contractCode || ids.has(r.contractCode) ||
        ![r.last,r.bid,r.ask,r.volume,r.openInterest].every(numberOrMissing))throw Error("本次返回的合约身份或报价字段异常。");
      ids.add(r.contractCode);
      return {...r,right:r.type,bid:r.bid??null,ask:r.ask??null,volume:r.volume??null,open_interest:r.openInterest??null,
        underlying:spot,iv_pct:r.ivPct??null,gamma:r.greeks?.gamma??null,multiplier:r.multiplier??null,
        lastPriceTime:marketTime(r.lastPriceTime),bidAsOf:null,askAsOf:null};
    });
    const latest=rows.filter(r=>r.lastPriceTime).length;
    const categories={twoSided:0,oneSided:0,noQuote:0,crossed:0};
    for(const row of rows){
      const bid=row.bid>0,ask=row.ask>0;
      const category=bid&&ask?(row.ask<row.bid?"crossed":"twoSided"):bid||ask?"oneSided":"noQuote";
      categories[category]++;
    }
    if(Object.entries(categories).some(([key,n])=>c[key]!=null && c[key]!==n))throw Error("合约行与买卖报价覆盖数不一致。");
    const coverageSummary="双边 "+categories.twoSided+" 份 · 单边 "+categories.oneSided+" 份 · 无报价 "+categories.noQuote+" 份"+
      (categories.crossed?" · 交叉 "+categories.crossed+" 份":"");
    const scope=c.completeForRequestedExpiry?"全部入选合约返回":"限量或部分取样";
    const others=Array.isArray(b.otherSeries)?b.otherSeries.length:0;
    const caption="富途 OpenD · "+symbol+" · "+expiry+" 到期 · 获取 "+b.capturedAt+" · 链中 "+c.chainContractCount+
      " 份，选取 "+c.selectedContractCount+" 份，返回 "+c.returnedContractCount+" 份（"+scope+"）。可比较方向行中："+coverageSummary+"。有 "+latest+
      " 条最新价更新时间，详见合约表。买价、卖价各自的更新时间未知。"+(others?"同执行价或方向另有 "+others+" 份待辨识系列，未纳入结构比较。":"");
    return {symbol,expiry,rows,spot,source:b.source,capturedAt:b.capturedAt,quoteTime:null,snapshotId:b.sha256,
      underlyingSourceTime:marketTime(b.underlyingSourceTime),caption,coverage:c,coverageSummary};
  }
  async function read(symbol,expiry) {
    if(!supported(symbol,expiry))throw Error("本机接口尚不支持此标的或到期日。");
    const response=await fetch("/api/studio/futu-option-quotes",{method:"POST",mode:"same-origin",cache:"no-store",
      headers:{"Content-Type":"application/json"},body:JSON.stringify({symbol,expiry}),signal:AbortSignal.timeout(75000)});
    const data=await response.json();
    if(!response.ok || data?.ok!==true)throw Error(typeof data?.message==="string" && data.message ? data.message : "本机 OpenD 未返回可用的期权取样。");
    return normalize(data,symbol,expiry);
  }
  window.OptionFutuSource=Object.freeze({expiries:Object.freeze(expiries),supported,read});
})();
