"use strict";
(() => {
  const archives = {
    recent: {label:"近期归档", path:"./market-recent.json"},
    futu: {label:"富途归档", path:"./market-history.json"}
  };
  const defaults = ["QQQ","SPY","SOXX"];
  const names = {QQQ:"纳斯达克 100 ETF",SPY:"标普 500 ETF",SOXX:"iShares 半导体 ETF",AAPL:"苹果",MSFT:"微软",NVDA:"英伟达"};
  const storageKey = "hakimi.terminal.market-watchlist.v1";
  const sourceNames = {local:"本机日线",recent:archives.recent.label,futu:archives.futu.label,manual:"富途手动日K"};
  const usSymbol = symbol => /^[A-Z]{1,6}(?:\.[A-Z])?$/.test(symbol);
  const palettes = {up:"#f06468",down:"#39bd96",flat:"#9ba7b6",grid:"#303339",text:"#a3a9b1",ma5:"#e6b554",ma20:"#79a9ed",cursor:"#cab583"};
  const countFmt = new Intl.NumberFormat("zh-CN",{maximumFractionDigits:2});
  const sharesFmt = new Intl.NumberFormat("zh-CN",{maximumFractionDigits:20});
  const priceFmt = new Intl.NumberFormat("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
  const finite = v => typeof v==="number" && Number.isFinite(v);
  const price = n => finite(n) ? (n!==0 && Math.abs(n)<1 ? n.toFixed(4) : priceFmt.format(n)) : "—";
  const signed = (n,unit="") => finite(n) ? (n>0?"+":"")+n.toFixed(2)+unit : "—";
  const trend = n => finite(n) && n!==0 ? (n>0?"up":"down") : "flat";
  const day = s => typeof s==="string" && /^\d{4}-\d\d-\d\d$/.test(s) && Number.isFinite(Date.parse(s+"T00:00:00Z")) && new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
  const volumeText = n => !finite(n)?"—":n>=1e8?(n/1e8).toFixed(2)+"亿":n>=1e4?(n/1e4).toFixed(2)+"万":countFmt.format(n);
  function ticker(input) {
    const s=String(input??"").trim().toUpperCase().replace(/^US\.(?=[A-Z])/,"");
    return /^[A-Z][A-Z0-9]{0,14}(?:[.\-][A-Z0-9]{1,12}){0,2}$/.test(s) && s.length<=40 ? s : "";
  }
  function node(tag,cls,text) {
    const n=document.createElement(tag);
    if(cls)n.className=cls;if(text!==undefined)n.textContent=text;
    return n;
  }
  function button(label,action,extra) {
    const n=node("button",extra||"",label);n.type="button";n.addEventListener("click",action);return n;
  }
  function readList() {
    try {
      const raw=localStorage.getItem(storageKey);
      if(raw!==null){const list=JSON.parse(raw);if(Array.isArray(list))return [...new Set(list.map(ticker).filter(Boolean))];}
    }catch{/* Storage may be disabled; the current session still works. */}
    return defaults.slice();
  }
  function series(rows,cutoff,local=false) {
    if(!Array.isArray(rows)||!rows.length)return [];
    const dates=new Set(),bars=[];
    for(const row of rows){
      if(!row||!day(row.date)||dates.has(row.date)||(cutoff&&row.date>cutoff)||
        (local&&(row.complete!==true||row.provisional===true))||
        ![row.open,row.high,row.low,row.close].every(v=>finite(v)&&v>0)||
        row.high<Math.max(row.open,row.close)||row.low>Math.min(row.open,row.close))return [];
      dates.add(row.date);
      const bar={date:row.date,open:row.open,high:row.high,low:row.low,close:row.close,volume:finite(row.volume)&&row.volume>=0?row.volume:null};
      if (Object.hasOwn(row,"previousClose") || Object.hasOwn(row,"reportedChangePct")) {
        bar.previousClose=finite(row.previousClose)&&row.previousClose>0 ? row.previousClose : null;
        bar.reportedChangePct=finite(row.reportedChangePct)&&row.reportedChangePct>=-100 ? row.reportedChangePct : null;
      }
      bars.push(bar);
    }
    return bars.sort((a,b)=>a.date.localeCompare(b.date));
  }
  function weekly(rows) {
    const result=[];let previousKey="";
    for(const d of rows){
      const date=new Date(d.date+"T00:00:00Z");date.setUTCDate(date.getUTCDate()-(date.getUTCDay()+6)%7);
      const key=date.toISOString().slice(0,10);
      if(key!==previousKey){result.push({...d,startDate:d.date});previousKey=key;continue;}
      const week=result.at(-1);week.high=Math.max(week.high,d.high);week.low=Math.min(week.low,d.low);week.close=d.close;week.date=d.date;
      if(week.volume===null||d.volume===null)week.volume=null;
      else{
        // Round the sum only to the precision actually supplied for the shares.
        const precision=Math.min(20,Math.max(decimals(week.volume),decimals(d.volume)));
        week.volume=Number((week.volume+d.volume).toFixed(precision));
      }
    }
    return result;
  }
  function decimals(value){
    const [digits,exponent="0"]=String(value).split("e");
    return Math.max(0,(digits.split(".")[1]?.length||0)-Number(exponent));
  }
  function moving(rows,n) {
    let sum=0;
    return rows.map((v,i)=>{sum+=v.close;if(i>=n)sum-=rows[i-n].close;return i+1<n?null:sum/n;});
  }
  function setData(bars,meta) {
    const weeks=weekly(bars);
    return {...meta,day:bars,week:weeks,ma:{day:{5:moving(bars,5),20:moving(bars,20)},week:{5:moving(weeks,5),20:moving(weeks,20)}}};
  }
  function startDate(last,months){
    const dt=new Date(last+"T00:00:00Z"),d=dt.getUTCDate();dt.setUTCDate(1);dt.setUTCMonth(dt.getUTCMonth()-months);
    dt.setUTCDate(Math.min(d,new Date(Date.UTC(dt.getUTCFullYear(),dt.getUTCMonth()+1,0)).getUTCDate()));return dt.toISOString().slice(0,10);
  }
  let state=null,earlySymbol="";
  function select(input,notify=false) {
    const symbol=ticker(input);
    if(!symbol)return false;
    if(!state){earlySymbol=symbol;return true;}
    if(state.symbol!==symbol){state.symbol=symbol;state.viewVersion++;resetWindow();render();}
    maybeLocal();
    if(notify)state.onSelect?.(symbol);
    return true;
  }
  function useSource(symbol) {
    const s=state.sources;
    if(state.preferences.has(symbol))return state.preferences.get(symbol);
    if(s.recent.has(symbol))return "recent";
    if(s.futu.has(symbol))return "futu";
    if(defaults.includes(symbol)&&!state.finished.has("recent"))return "recent";
    return "local";
  }
  function active(symbol){return state.sources[useSource(symbol)].get(symbol);}
  function delta(rows) {
    if(!rows?.length)return {};
    const last=rows.at(-1);
    if(Object.hasOwn(last,"previousClose")) {
      if(last.previousClose===null) {
        return {amount:null,pct:last.reportedChangePct,basis:finite(last.reportedChangePct)?"富途原始涨幅；上根收盘缺失":"富途上根收盘及涨幅缺失"};
      }
      const amount=last.close-last.previousClose,computed=amount/last.previousClose*100;
      if(last.reportedChangePct===null) return {amount,pct:computed,basis:"按富途上根收盘换算"};
      // Display percentages to two decimals. A larger discrepancy needs a source check.
      if(Math.abs(computed-last.reportedChangePct)>0.005000001) {
        return {amount,pct:null,basis:"富途涨幅与上根收盘不符，涨幅待核对"};
      }
      return {amount,pct:last.reportedChangePct,basis:"富途上根收盘及原始涨幅"};
    }
    if(rows.length<2)return {basis:"归档缺少上根收盘"};
    const previous=rows.at(-2);
    const amount=last.close-previous.close;
    return {amount,pct:amount/previous.close*100,basis:"较上一条已收录日线 "+previous.date};
  }
  function updateList(symbol,add) {
    let watchlist=state.list;
    try{if(localStorage.getItem(storageKey)!==null)watchlist=readList();}catch{}
    state.list=add?[...new Set([...watchlist,symbol])]:watchlist.filter(v=>v!==symbol);
    try{localStorage.setItem(storageKey,JSON.stringify(state.list));state.notice=add?symbol+" 已加入自选。":symbol+" 已移出自选。";}
    catch{state.notice="当前窗口已更新；本机存储不可用。";}
  }
  function buildWatch(root) {
    root.classList.add("tmk-watch");const top=node("div","tmk-watch-head");top.append(node("h2",null,"自选行情"));
    const tally=node("span","tmk-count");top.append(tally);
    const form=node("form","tmk-search");const input=node("input");input.type="search";input.placeholder="代码或名称";input.autocomplete="off";input.spellcheck=false;input.maxLength=80;
    input.setAttribute("aria-label","搜索并加入自选");const list=node("datalist");list.id="tmk-symbol-options";input.setAttribute("list",list.id);
    const add=node("button",null,"加入");add.type="submit";form.append(input,add,list);
    const status=node("div","tmk-watch-status");status.setAttribute("role","status");
    form.addEventListener("submit",e=>{
      e.preventDefault();const value=input.value.trim();
      const match=[...state.known].find(([k,name])=>value.toUpperCase()===k || (name && value.toLowerCase()===name.toLowerCase()));
      const symbol=match?.[0]||state.aliases.get(value.toLowerCase())||ticker(value);
      if(!symbol){state.notice="请输入有效的证券代码，或选择匹配的名称。";status.textContent=state.notice;return;}
      updateList(symbol,true);input.value="";
      select(symbol,true);renderWatch();renderChart();
    });
    const titles=node("div","tmk-watch-label");
    const sorters=new Map();
    for(const [key,label] of [["name","名称"],["close","收盘"],["amount","涨跌额"],["change","涨跌幅"]]){
      const sorter=button(label,()=>cycleSort(key));
      sorter.dataset.sort=key;sorters.set(key,{button:sorter,label});titles.append(sorter);
    }
    const body=node("div","tmk-watch-rows");body.setAttribute("aria-label","自选标的");
    const dates=node("p","tmk-watch-dates");
    root.replaceChildren(top,form,titles,body,dates,status);return {tally,input,options:list,status,body,sorters,dates};
  }
  function cycleSort(key) {
    const first=key==="name"?1:-1;
    const sort=state.sort;
    if(sort?.key!==key) state.sort={key,order:first};
    else if(sort.order===first) state.sort={key,order:-first};
    else state.sort=null;
    renderWatch();
  }
  function sortedWatchRows() {
    const items=state.list.map(symbol=>{
      const info=active(symbol),bar=info?.day.at(-1);
      const rawName=info?.name||state.known.get(symbol)||"";
      const name=rawName===symbol?"":rawName;
      const move=delta(info?.day);
      return {symbol,info,bar,name,close:bar?.close,amount:move.amount,change:move.pct,changeBasis:move.basis};
    });
    if(!state.sort)return items;
    const {key,order}=state.sort;
    return items.sort((a,b)=>{
      const left=a[key],right=b[key];
      const missingLeft=left==null||left==="",missingRight=right==null||right==="";
      if(missingLeft || missingRight)return Number(missingLeft)-Number(missingRight);
      const difference=key==="name"?left.localeCompare(right,"zh-CN",{numeric:true}):left-right;
      return difference*order;
    });
  }
  function renderWatch() {
    const {w}=state;w.tally.textContent=state.list.length;w.status.textContent=state.notice;
    for(const [key,{button:sorter,label}] of w.sorters){
      const order=state.sort?.key===key?state.sort.order:0;
      const direction=order>0?"升序":order<0?"降序":"自选顺序";
      sorter.textContent=label+(order>0?" ↑":order<0?" ↓":"");
      sorter.setAttribute("aria-label",label+"排序，当前"+direction);
      sorter.setAttribute("aria-pressed",String(!!order));
      sorter.title="按"+label+"排序，再次点击切换顺序";
    }
    const old=new Map([...w.body.querySelectorAll("[data-market-symbol]")].map(b=>[b.dataset.marketSymbol,b]));
    const items=sortedWatchRows();
    for(const [index,{symbol,info,bar,name,amount,change,changeBasis}] of items.entries()){
      let b=old.get(symbol);old.delete(symbol);
      if(!b){b=button("",()=>select(symbol,true),"tmk-watch-row");b.dataset.marketSymbol=symbol;
        const identity=node("span");identity.append(node("strong"),node("small"));
        b.append(identity,node("b"),node("span","tmk-amount"),node("span","tmk-pct"));}
      if(w.body.children[index]!==b)w.body.insertBefore(b,w.body.children[index]||null);
      b.children[0].firstChild.textContent=symbol;
      b.children[0].lastChild.textContent=name||"名称待补";
      b.children[1].textContent=price(bar?.close);
      b.children[2].textContent=signed(amount);b.children[2].className="tmk-amount tmk-"+trend(amount);
      b.children[3].textContent=signed(change,"%");b.children[3].className="tmk-pct tmk-"+trend(change);
      b.setAttribute("aria-pressed",String(symbol===state.symbol));
      b.title=[symbol,name,info?.provider,info?.basis,bar?.date,bar?changeBasis+" "+signed(change,"%"):"暂无可用日线"].filter(Boolean).join(" · ");
    }
    for(const b of old.values())b.remove();
    const dates=[...new Set(items.map(item=>item.bar?.date).filter(Boolean))].sort();
    w.dates.textContent=dates.length===0?"":dates.length===1?"历史收盘 · "+dates[0]:"收盘日 "+dates[0]+" ～ "+dates.at(-1);
    let empty=w.body.querySelector(".tmk-list-empty");
    if(!state.list.length&&!empty)w.body.append(node("p","tmk-list-empty","自选为空。输入代码即可加入。"));
    else if(state.list.length&&empty)empty.remove();
    const opts=[...state.known].sort(([a],[b])=>a.localeCompare(b));
    if(w.options.children.length!==opts.length)w.options.replaceChildren(...opts.map(([code,name])=>new Option(name||code,code)));
  }
  function buildChart(root) {
    root.classList.add("tmk-chart");const header=node("div","tmk-chart-head"),identity=node("div","tmk-identity");
    const title=node("h2","tmk-ticker"),name=node("span","tmk-instrument");identity.append(title,name);
    const star=button("",()=>{updateList(state.symbol,!state.list.includes(state.symbol));renderWatch();renderChart();},"tmk-star");
    const quote=node("div","tmk-price"),value=node("strong"),unit=node("small"),change=node("span");
    quote.append(value,unit,change);header.append(identity,star,quote);
    const meta=node("div","tmk-meta");
    const toolbar=node("div","tmk-tools"),frequency=node("div","tmk-group"),ranges=node("div","tmk-group tmk-ranges"),src=node("select","tmk-source");src.setAttribute("aria-label","K线行情来源");
    for(const [id,label] of [["day","日 K"],["week","周 K"]]){const b=button(label,()=>{state.frequency=id;resetWindow();renderChart();});b.dataset.interval=id;frequency.append(b);}
    for(const [n,label] of [[1,"1月"],[3,"3月"],[6,"6月"],[12,"1年"],[0,"全部"]]){const b=button(label,()=>{state.months=n;resetWindow();renderChart();});b.dataset.months=n;ranges.append(b);}
    src.addEventListener("change",()=>{state.viewVersion++;state.preferences.set(state.symbol,src.value);resetWindow();render();maybeLocal();});
    const manual=button("读取富途日K",()=>loadManualHistory(),"tmk-futu-read");
    manual.title="读取本机 OpenD 的美股常规时段未复权日 K。窗口截至美东昨日，共 92 个日历日，使用富途历史行情额度。";
    const status=node("p","tmk-manual-status");status.setAttribute("role","status");
    toolbar.append(frequency,src,manual);
    const indicators=node("div","tmk-indicators");
    for(const size of [5,20]){const b=button("MA"+size,()=>{if(state.enabled.has(size))state.enabled.delete(size);else state.enabled.add(size);renderChart();},"tmk-ma"+size);b.dataset.ma=size;indicators.append(b);}
    const readout=node("div","tmk-readout");readout.setAttribute("role","group");readout.setAttribute("aria-label","所选K线明细");
    const frame=node("div","tmk-plotframe"),canvas=node("canvas","tmk-plot");canvas.tabIndex=0;canvas.setAttribute("role","img");canvas.setAttribute("aria-label","价格K线与成交量，使用左右方向键、Home、End 查看");
    const empty=node("div","tmk-empty"),msg=node("span");
    const retry=button("重读本机日线",()=>loadLocal(state.symbol,true));empty.append(msg,retry);frame.append(canvas,empty);
    const navigation=node("div","tmk-chart-navigation");
    const period=node("label","tmk-period","时段"),slider=node("input","tmk-pan");
    slider.type="range";slider.min="0";slider.step="1";
    slider.setAttribute("aria-label","平移K线时段");
    slider.addEventListener("input",()=>setWindow(slider.valueAsNumber,state.bars.length));
    period.append(slider);
    const zoomOut=button("−",()=>zoom(1.4,1),"tmk-zoom");
    const zoomIn=button("＋",()=>zoom(1/1.4,1),"tmk-zoom");
    for(const [control,text] of [[zoomOut,"缩小K线"],[zoomIn,"放大K线"]]){
      control.setAttribute("aria-label",text);control.title=text;
    }
    const reset=button("复位",()=>{resetWindow();renderChart();});
    reset.title="恢复上次选择的日历区间";
    navigation.append(ranges,period,zoomOut,zoomIn,reset);
    const foot=node("p","tmk-chart-foot");root.replaceChildren(header,meta,toolbar,status,indicators,readout,frame,navigation,foot);
    return {title,name,star,value,unit,change,meta,frequency,ranges,src,manual,status,indicators,readout,canvas,frame,empty,msg,retry,foot,
      navigation,slider,zoomOut,zoomIn,reset};
  }
  function resetCursor(){state.selected=null;state.crossY=null;}
  function resetWindow(){state.viewport=null;state.drag=null;resetCursor();}
  const minBars=8;
  const clamp=(n,lo,hi)=>Math.max(lo,Math.min(n,hi));
  function setWindow(start,count) {
    const s=state,total=s.chartRows?.length;
    if(!total)return;
    count=clamp(Math.round(count),1,total);
    start=clamp(Math.round(start),0,total-count);
    if(count===s.bars.length && start===s.offset)return;
    s.viewport={start,count};resetCursor();renderChart();
  }
  function zoom(factor,anchor) {
    const s=state,total=s.chartRows?.length;
    if(!total)return;
    const count=s.bars.length;
    const next=factor<1 ? Math.max(Math.min(minBars,count),Math.round(count*factor))
                        : Math.min(total,Math.max(count+1,Math.round(count*factor)));
    setWindow(s.offset+(count-next)*clamp(anchor,0,1),next);
  }
  function updateReadout() {
    const {c,bars}=state;const i=state.selected??bars.length-1,bar=bars[i];
    c.readout.replaceChildren();if(!bar){c.readout.textContent="开 —　高 —　低 —　收 —　量 —";return;}
    c.readout.append(node("strong","tmk-date",bar.startDate?bar.startDate+" ～ "+bar.date:bar.date));
    for(const [label,v] of [["开",bar.open],["高",bar.high],["低",bar.low],["收",bar.close],["量",bar.volume]]){
      const display=label==="量"?(v!==null&&useSource(state.symbol)==="manual"?sharesFmt.format(v)+" 股":volumeText(v)):price(v);
      const n=node("span",null,label+" ");n.append(node("b",label==="收"?"tmk-"+trend(bar.close-bar.open):null,display));
      if(label==="量"&&v!==null)n.title=String(v)+(active(state.symbol)?.volumeUnit==="成交量单位 股"?" 股":"");
      c.readout.append(n);
    }
    c.canvas.setAttribute("aria-label",state.symbol+" "+(state.frequency==="day"?"日K":"周K")+"。"+c.readout.innerText.replace(/\s+/g," ")+"。左右键查看，上下键缩放，按住拖动平移。");
  }
  function renderChart() {
    const s=state, c=s.c, symbol=s.symbol, which=useSource(symbol),data=active(symbol),rows=data?.[s.frequency]||[],daily=data?.day||[];
    const last=daily.at(-1),move=delta(daily);
    c.title.textContent=symbol;c.name.textContent=data?.name||s.known.get(symbol)||"";
    const watched=s.list.includes(symbol);c.star.textContent=watched?"★ 自选":"☆ 加自选";c.star.title=watched?"移出自选":"加入自选";c.star.setAttribute("aria-pressed",String(watched));
    c.value.textContent=price(last?.close);c.unit.textContent=last?(data.currency||"原始报价单位"):"";
    c.change.textContent=finite(move.amount)||finite(move.pct)?signed(move.amount)+" ("+signed(move.pct,"%")+")":"前收对比待补";c.change.className="tmk-"+trend(move.amount??move.pct);
    c.meta.textContent=data?[data.provider,data.basis,last?"历史收盘 "+last.date:"无可用日线",move.basis].filter(Boolean).join(" · "):sourceNames[which]+" · 尚无可显示的日收盘";
    const choices=Object.keys(sourceNames).filter(id=>id==="local"||s.sources[id].has(symbol)||id===which||(id in archives&&!s.finished.has(id)&&defaults.includes(symbol)));
    if([...c.src.options].map(o=>o.value).join()!==choices.join())c.src.replaceChildren(...choices.map(id=>new Option(sourceNames[id],id)));
    c.src.value=which;
    c.manual.hidden=!usSymbol(symbol);
    c.manual.disabled=s.manualPending.has(symbol);
    c.manual.textContent=c.manual.disabled?"读取中…":"读取富途日K";
    c.status.textContent=s.manualMessages.get(symbol)||(!last&&usSymbol(symbol)?"可手动读取富途近 92 个日历日的美股日 K，将使用该标的历史行情额度。":"");
    if(which==="manual"&&data?.receivedAt)c.meta.textContent+=" · 美东交易日标签 · 常规时段 · 取样 "+data.receivedAt;
    for(const b of c.frequency.children)b.setAttribute("aria-pressed",String(b.dataset.interval===s.frequency));
    for(const b of c.indicators.children)b.setAttribute("aria-pressed",String(s.enabled.has(+b.dataset.ma)));
    if(rows!==s.chartRows){resetWindow();s.chartRows=rows;}
    for(const b of c.ranges.children)b.setAttribute("aria-pressed",String(!s.viewport && +b.dataset.months===s.months));
    if(s.viewport){
      s.offset=s.viewport.start;s.bars=rows.slice(s.offset,s.offset+s.viewport.count);
    }else{
      const cutoff=rows.length&&s.months?startDate(rows.at(-1).date,s.months):"";
      s.offset=rows.length?rows.findIndex(b=>b.date>=cutoff):0;s.bars=rows.slice(s.offset);
    }
    if(s.selected!==null && s.selected>=s.bars.length)resetCursor();
    const has=s.bars.length>0;c.empty.hidden=has;c.canvas.tabIndex=has?0:-1;
    c.navigation.hidden=!has;
    const maxStart=rows.length-s.bars.length;
    c.slider.max=String(maxStart);c.slider.value=String(s.offset);c.slider.disabled=maxStart===0;
    c.zoomOut.disabled=s.bars.length===rows.length;c.zoomIn.disabled=s.bars.length<=minBars;c.reset.disabled=!s.viewport;
    c.slider.setAttribute("aria-valuetext",has?(s.bars[0].startDate||s.bars[0].date)+" 至 "+s.bars.at(-1).date:"暂无K线");
    c.slider.style.setProperty("--tmk-window-start",(rows.length?100*s.offset/rows.length:0)+"%");
    c.slider.style.setProperty("--tmk-window-end",(rows.length?100*(s.offset+s.bars.length)/rows.length:100)+"%");
    const loading=which==="local"?s.pending.has(symbol):!s.finished.has(which);
    c.msg.textContent=loading?"正在读取 "+symbol+" 的历史日线…":(data?.problem||symbol+" 在此来源暂无可核验的日线。");
    c.retry.hidden=which!=="local"||loading;
    const first=s.bars[0],end=s.bars.at(-1),missing=s.bars.filter(b=>b.volume===null).length;
    c.foot.textContent=has?[first.startDate||first.date,"至",end.date,"·",s.bars.length+(s.frequency==="day"?" 根日 K":" 根周 K"),"·",
      s.frequency==="day"?"量按交易日":"周一至周日按已收录交易日合成，边界周可能不完整",data.volumeUnit?"· "+data.volumeUnit:"",missing?"· "+missing+" 根成交量缺失":""].filter(Boolean).join(" "):"";
    updateReadout();draw();
  }
  function render(){if(state){renderWatch();renderChart();}}
  function draw() {
    const s=state;
    if(!s)return;
    const canvas=s.c.canvas,box=canvas.getBoundingClientRect(),width=Math.floor(box.width),height=Math.floor(box.height);
    if(width<70||height<100)return;
    const scale=Math.min(window.devicePixelRatio||1,3),pixelWidth=Math.round(width*scale),pixelHeight=Math.round(height*scale);
    if(canvas.width!==pixelWidth||canvas.height!==pixelHeight){canvas.width=pixelWidth;canvas.height=pixelHeight;}
    const g=canvas.getContext("2d");if(!g)return;
    g.setTransform(scale,0,0,scale,0,0);g.clearRect(0,0,width,height);
    s.layout=null;
    if(!s.bars.length)return;
    const bars=s.bars,data=active(s.symbol),n=bars.length,left=5,right=width-(width<400?55:68),top=12;
    const priceBottom=Math.round(height*.70),volTop=priceBottom+24,volBottom=height-24;
    const step=(right-left)/n,body=Math.max(.5,Math.min(13,step*.69));
    let low=Infinity,high=-Infinity,maxVolume=null;
    for(let i=0;i<n;i++){
      const bar=bars[i];low=Math.min(low,bar.low);high=Math.max(high,bar.high);
      if(bar.volume!==null)maxVolume=Math.max(maxVolume??0,bar.volume);
      for(const ma of s.enabled){const v=data.ma[s.frequency][ma][s.offset+i];if(finite(v)){low=Math.min(low,v);high=Math.max(high,v);}}
    }
    const pad=Math.max((high-low)*.06,high*.0003,.00001);low-=pad;high+=pad;
    const x=i=>left+step*(i+.5),y=v=>top+(high-v)/(high-low)*(priceBottom-top);
    const line=(a,b,c,d,color)=>{g.strokeStyle=color;g.beginPath();g.moveTo(a,b);g.lineTo(c,d);g.stroke();};
    const tag=(val,py,color)=>{
      py=Math.min(priceBottom-8,Math.max(top+8,py));
      g.fillStyle=color;g.fillRect(right+1,py-8,width-right-1,16);g.fillStyle="#111418";
      g.fillText(price(val),right+4,py);
    };
    g.font='11px "Segoe UI","Microsoft YaHei",sans-serif';g.textBaseline="middle";g.lineWidth=1;
    for(let i=0;i<=4;i++){
      const v=high-(high-low)*i/4,py=y(v);
      line(left,py,right,py,palettes.grid);g.fillStyle=palettes.text;g.fillText(price(v),right+4,py);
    }
    line(left,volTop,right,volTop,palettes.grid);line(left,volBottom,right,volBottom,palettes.grid);
    g.fillStyle=palettes.text;g.fillText("量",right+4,volTop);g.fillText(volumeText(maxVolume),right+4,volTop+14);
    const tickCount=Math.min(n,Math.max(2,Math.floor((right-left)/122)));
    for(let j=0;j<tickCount;j++){
      const index=tickCount===1?0:Math.round(j/(tickCount-1)*(n-1)),px=x(index);
      line(px,top,px,volBottom,palettes.grid);g.fillStyle=palettes.text;
      const label=bars[index].date,textWidth=g.measureText(label).width;
      g.fillText(label,Math.max(left,Math.min(px-textWidth/2,right-textWidth)),height-10);
    }
    for(let i=0;i<n;i++){
      const b=bars[i],px=x(i),color=palettes[trend(b.close-b.open)],yo=y(b.open),yc=y(b.close);
      line(px,y(b.high),px,y(b.low),color);
      g.fillStyle=color;g.fillRect(px-body/2,Math.min(yo,yc),body,Math.max(1,Math.abs(yo-yc)));
      if(b.volume!==null&&b.volume>0){
        const h=b.volume/maxVolume*(volBottom-volTop-2);g.globalAlpha=.74;g.fillRect(px-body/2,volBottom-h,body,h);g.globalAlpha=1;
      }
    }
    for(const ma of s.enabled){
      g.beginPath();g.strokeStyle=palettes["ma"+ma];g.lineWidth=1.35;let started=false;
      for(let i=0;i<n;i++){
        const v=data.ma[s.frequency][ma][s.offset+i];if(!finite(v)){started=false;continue;}
        if(started)g.lineTo(x(i),y(v));else{g.moveTo(x(i),y(v));started=true;}
      }
      g.stroke();
    }
    const last=bars[n-1],previous=s.chartRows[s.offset+n-2];
    const mark=palettes[trend(last.close-(previous?.close??last.open))];g.lineWidth=1;
    g.setLineDash([4,4]);line(left,y(last.close),right,y(last.close),mark);g.setLineDash([]);tag(last.close,y(last.close),mark);
    s.layout={left,right,top,priceBottom,step,low,high};
    if(Number.isInteger(s.selected)){
      const px=x(s.selected);g.setLineDash([3,3]);line(px,top,px,volBottom,palettes.cursor);
      const cy=s.crossY??y(bars[s.selected].close);
      if(cy>=top&&cy<=priceBottom){line(left,cy,right,cy,palettes.cursor);tag(high-(cy-top)/(priceBottom-top)*(high-low),cy,palettes.cursor);}
      g.setLineDash([]);
    }
  }
  function bindPlot(s) {
    const canvas=s.c.canvas,opts={signal:s.controller.signal};
    const pointer=e=>{
      const l=s.layout;if(!l)return;
      const rect=canvas.getBoundingClientRect(),px=e.clientX-rect.left;
      if(px<l.left||px>l.right){resetCursor();}else{
        s.selected=Math.max(0,Math.min(s.bars.length-1,Math.floor((px-l.left)/l.step)));s.crossY=e.clientY-rect.top;
      }
      updateReadout();draw();
    };
    canvas.addEventListener("pointerdown",e=>{
      if(!s.layout||e.button!==0||!e.isPrimary)return;
      canvas.focus({preventScroll:true});pointer(e);
      s.drag={id:e.pointerId,startX:e.clientX,offset:s.offset,count:s.bars.length,step:s.layout.step};
      canvas.setPointerCapture(e.pointerId);
    },opts);
    canvas.addEventListener("pointermove",e=>{
      const drag=s.drag;
      if(drag?.id===e.pointerId){
        const dx=e.clientX-drag.startX;
        if(Math.abs(dx)>=4 || drag.moved){
          drag.moved=true;canvas.classList.add("tmk-dragging");
          setWindow(drag.offset-dx/drag.step,drag.count);return;
        }
      }
      pointer(e);
    },opts);
    canvas.addEventListener("lostpointercapture",()=>{
      s.drag=null;canvas.classList.remove("tmk-dragging");
    },opts);
    canvas.addEventListener("pointerleave",e=>{if(!s.drag&&e.pointerType==="mouse"){resetCursor();updateReadout();draw();}},opts);
    canvas.addEventListener("wheel",e=>{
      if(document.activeElement!==canvas||!s.layout||!e.deltaY||e.ctrlKey||e.metaKey)return;
      e.preventDefault();
      const x=e.clientX-canvas.getBoundingClientRect().left;
      zoom(e.deltaY<0?1/1.22:1.22,(x-s.layout.left)/(s.layout.right-s.layout.left));
    },{...opts,passive:false});
    canvas.addEventListener("keydown",e=>{
      if(!s.bars.length)return;
      if(e.key==="ArrowUp" || e.key==="ArrowDown"){
        e.preventDefault();
        const anchor=s.selected===null?1:s.selected/Math.max(1,s.bars.length-1);
        zoom(e.key==="ArrowUp"?1/1.4:1.4,anchor);
        return;
      }
      if(!["ArrowLeft","ArrowRight","Home","End","Escape"].includes(e.key))return;
      e.preventDefault();const last=s.bars.length-1,current=s.selected??last;
      if(e.key==="Escape")resetCursor();
      else{s.selected=e.key==="Home"?0:e.key==="End"?last:Math.max(0,Math.min(last,current+(e.key==="ArrowLeft"?-1:1)));s.crossY=null;}
      updateReadout();draw();
    },opts);
    if(window.ResizeObserver){s.resize=new ResizeObserver(()=>{if(s===state)draw();});s.resize.observe(s.c.frame);}
    else window.addEventListener("resize",draw,opts);
  }
  async function json(s,path) {
    const res=await fetch(path,{signal:s.controller.signal,credentials:"same-origin"});
    if(!res.ok)throw new Error("HTTP "+res.status);return res.json();
  }
  async function loadManualHistory(){
    const s=state,symbol=s.symbol,version=s.viewVersion;
    if(!usSymbol(symbol)||s.manualPending.has(symbol))return;
    s.manualPending.add(symbol);
    s.manualMessages.set(symbol,"正在读取 "+symbol+" 的富途日 K，范围截至美东昨日。");renderChart();
    try{
      const response=await fetch("/api/studio/futu-history",{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json","X-Hakimi-Write":"1"},body:JSON.stringify({symbol}),signal:s.controller.signal});
      const d=await response.json();if(s!==state)return;
      if(!response.ok||d.ok!==true){throw new Error(typeof d.message==="string"?d.message:"本机行情服务未能返回日 K。");}
      const bars=series(d.bars,d.requestedEnd);
      if(d.symbol!==symbol||d.status!=="AVAILABLE"||d.provider!=="富途 OpenD"||d.basis!=="未复权"||
        d.session!=="RTH"||d.currency!=="USD"||d.timeZone!=="America/New_York"||!day(d.requestedStart)||!day(d.requestedEnd)||
        !bars.length||bars.length>92||bars.length!==d.count||bars.some(b=>b.volume===null)||bars[0].date<d.requestedStart||
        d.asOf!==bars.at(-1).date||!/^\d{4}-\d\d-\d\dT.*(Z|[+-]\d\d:\d\d)$/.test(d.receivedAt)||!Number.isFinite(Date.parse(d.receivedAt)))
        throw new Error("返回日线的标的、记录或来源口径未通过核对。");
      s.sources.manual.set(symbol,setData(bars,{provider:d.provider,name:s.known.get(symbol)||symbol,basis:d.basis,currency:d.currency,
        volumeUnit:"成交量单位 股",receivedAt:d.receivedAt}));
      const current=s.symbol===symbol&&s.viewVersion===version;
      if(current){s.preferences.set(symbol,"manual");resetWindow();}
      s.manualMessages.set(symbol,"富途返回 "+bars.length+" 根日 K · 请求 "+d.requestedStart+" 至 "+d.requestedEnd+
        (current?" · 仅收录美东昨日及以前的交易日。":" · 可在来源中查看。"));
    }catch(error){
      if(s!==state)return;
      const message=(error instanceof SyntaxError||error instanceof TypeError)?"本机日线服务未返回有效响应。":error.message;
      s.manualMessages.set(symbol,"本次富途读取失败："+message+(s.sources.manual.has(symbol)?" 上次成功取样仍可按取样时间查看。":""));
    }finally{if(s===state){s.manualPending.delete(symbol);render();}}
  }
  async function loadArchive(s,id) {
    try {
      const archive=await json(s,archives[id].path);if(s!==state)return;
      if(!day(archive.as_of)||!archive.symbols||typeof archive.symbols!=="object")return;
      for(const [symbol,asset] of Object.entries(archive.symbols)){
        if(!ticker(symbol)||!asset)continue;
        const bars=series(asset.bars,archive.as_of);const name=asset.name||s.known.get(symbol)||symbol;
        s.known.set(symbol,name);
        s.sources[id].set(symbol,setData(bars,{name,provider:archive.provider||archives[id].label,basis:archive.basis||"价格口径待核",
          currency:archive.currency||"",volumeUnit:"成交量单位 股",problem:symbol+" 的归档日线缺失或未通过价格、日期核对。"}));
      }
    }catch{/* An unavailable archive does not prevent using another source. */}
    finally{if(s===state){s.finished.add(id);render();maybeLocal();}}
  }
  const basisLabels={FORWARD_ADJUSTED_QFQ:"前复权",FORWARD_ADJUSTED_TOTAL_RETURN:"前复权总回报",RAW:"未复权",
    UNADJUSTED:"未复权",UNKNOWN:"价格口径待核",YAHOO_CHART_CLOSE_UNVERIFIED:"Yahoo 收盘价，复权口径待核",
    STOOQ_CLOSE_UNVERIFIED:"Stooq 收盘价，复权口径待核",PROVIDER_CRYPTO_PRICE:"供应方数字资产历史价格"};
  async function loadLocal(symbol,force=false) {
    const s=state;if(s.pending.has(symbol)||(!force&&s.sources.local.has(symbol)))return;
    s.pending.add(symbol);if(s.symbol===symbol)renderChart();
    let data;
    try{
      const result=await json(s,"/api/local/terminal-market?symbol="+encodeURIComponent(symbol));
      if(s!==state)return;
      const market=result.market||result,meta=market.meta||{},quality=market.quality||{};
      const source=Array.isArray(meta.source_lineage)?meta.source_lineage.filter(v=>typeof v==="string").join(" / "):"";
      const allows=market.symbol===symbol&&quality.status==="REVIEW"&&!quality.blockers?.length;
      const complete=Array.isArray(market.rows)?market.rows.filter(r=>r?.complete===true&&r.provisional!==true):[];
      const bars=allows?series(complete,null,true):[];
      data=setData(bars,{name:s.known.get(symbol)||"",provider:[source||market.source_id||"本机缓存","来源待复核"].join(" · "),
        basis:basisLabels[meta.price_basis]||meta.price_basis||"价格口径待核",currency:meta.currency||"",
        volumeUnit:meta.volume_unit&&meta.volume_unit!=="UNKNOWN"?"成交量单位 "+meta.volume_unit:"成交量单位待核",
        problem:symbol+" 暂无可核验的本机完整日线。"});
    }catch{data=setData([],{provider:"本机缓存",problem:symbol+" 的本机日线未能读取。"});}
    finally{if(s===state){s.pending.delete(symbol);if(data)s.sources.local.set(symbol,data);render();}}
  }
  function maybeLocal(){if(state&&useSource(state.symbol)==="local")loadLocal(state.symbol);}
  async function loadCatalog(s){
    try {
      const res=await json(s,"/api/local/terminal-markets");if(s!==state||!Array.isArray(res.items))return;
      for(const item of res.items){const symbol=ticker(item?.symbol);if(!symbol)continue;
        if(!s.known.has(symbol))s.known.set(symbol,item.name||symbol);
        if(item.available===true&&s.list.includes(symbol)&&!defaults.includes(symbol))loadLocal(symbol);
      }
      renderWatch();
    }catch{/* Ticker entry is available independently of the catalog. */}
  }
  function destroy(){
    if(!state)return;
    state.resize?.disconnect();state.controller.abort();
    for(const [el,cls] of [[state.watch,"tmk-watch"],[state.chart,"tmk-chart"]]){el.replaceChildren();el.classList.remove(cls);}
    state=null;
  }
  function mount({watch,chart,symbol,markets,onSelect}={}){
    if(typeof watch==="string")watch=document.querySelector(watch);if(typeof chart==="string")chart=document.querySelector(chart);
    if(!(watch instanceof Element)||!(chart instanceof Element)||watch===chart)return false;
    destroy();const list=readList();
    const s={watch,chart,list,aliases:new Map(),symbol:earlySymbol||ticker(symbol)||list[0]||defaults[0],onSelect:typeof onSelect==="function"?onSelect:null,
      frequency:"day",months:6,enabled:new Set([5,20]),known:new Map(Object.entries(names)),notice:"",selected:null,crossY:null,bars:[],
      sort:null,viewport:null,chartRows:null,drag:null,
      sources:{local:new Map(),recent:new Map(),futu:new Map(),manual:new Map()},preferences:new Map(),finished:new Set(),pending:new Set(),
      manualPending:new Set(),manualMessages:new Map(),viewVersion:0,controller:new AbortController()};
    for(const market of Array.isArray(markets)?markets:[]){
      const code=ticker(market?.symbol);if(!code)continue;
      if(typeof market.name==="string"&&market.name.trim())s.aliases.set(market.name.trim().toLowerCase(),code);
      if(!s.known.has(code))s.known.set(code,market.name||code);
    }
    earlySymbol="";state=s;s.w=buildWatch(watch);s.c=buildChart(chart);bindPlot(s);
    window.addEventListener("storage",e=>{if(e.key===storageKey||e.key===null){s.list=readList();render();}},{signal:s.controller.signal});
    render();for(const id of Object.keys(archives))loadArchive(s,id);loadCatalog(s);maybeLocal();return true;
  }
  if (typeof module === "object" && module.exports) module.exports = {series, delta};
  if (typeof window !== "undefined") window.TerminalMarketPane=Object.freeze({mount,select:symbol=>select(symbol),destroy});
})();
