"""API-driven trading-terminal view; no external charting runtime required."""
from pathlib import Path

FLOW_JS = Path(__file__).with_name('network_flow.js').read_text(encoding='utf-8')

CSS = r'''
.live-desk{padding:18px 20px;color:#dce9f1;font-family:Inter,system-ui,sans-serif}
.live-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:2px 0 12px}
.live-head h2{font-size:22px;margin:0;letter-spacing:-.6px}.live-head p{font-size:11px;color:#89a0b3;margin:5px 0 0}
.live-status{border:1px solid #244557;padding:6px 10px;border-radius:6px;font:11px ui-monospace,monospace;color:#5fe1ba}
.live-tape{display:flex;gap:9px;overflow:auto;padding:3px 0 12px;scrollbar-width:thin;scrollbar-color:#294959 #0b1722}
.live-tape button{white-space:nowrap;cursor:pointer;background:#0b1722;border:1px solid #1e3444;border-radius:5px;color:#dce9f1;padding:8px;font:11px ui-monospace,monospace}
.live-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px}
.ld-panel{background:linear-gradient(135deg,#0b1723,#080e17);border:1px solid #213243;border-radius:10px;min-width:0;overflow:hidden}
.ld-title{display:flex;align-items:center;justify-content:space-between;gap:8px;border-bottom:1px solid #213243;padding:11px 13px;font-size:10px;font-weight:700;letter-spacing:1px;color:#9db7cb}
.ld-body{padding:13px}.ld-chart{grid-column:span 8}.ld-readout{grid-column:span 4}.ld-network{grid-column:span 5}.ld-sectors{grid-column:span 7}.ld-volume{grid-column:span 8}.ld-events{grid-column:span 4}
.ld-chart select{background:#102438;color:#dcf2ff;border:1px solid #2a4357;border-radius:5px;padding:4px;font:11px ui-monospace,monospace}
.ld-controls{display:flex;gap:5px;align-items:center}.ld-controls button{background:transparent;color:#8aa4b8;border:1px solid #294054;border-radius:4px;font-size:10px;padding:4px 7px;cursor:pointer}.ld-controls button.on{color:#64ecc5;border-color:#3aab91}
.ld-price{font:700 30px ui-monospace,monospace;letter-spacing:-1px}.ld-price-meta{display:flex;align-items:baseline;gap:12px;padding:12px 14px 0}.ld-muted{font-size:10px;color:#8097a9;line-height:1.5}
.ld-chart svg{display:block;width:100%;height:225px}.ld-empty{padding:60px 15px;color:#8298aa;text-align:center;font-size:12px}
.ld-stats{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:14px}.ld-stat{padding:9px;background:#0d1e2d;border:1px solid #1c3447;border-radius:6px}.ld-stat b{display:block;font:700 22px ui-monospace,monospace;margin:5px 0}.ld-bar{height:5px;display:flex;border-radius:5px;overflow:hidden;background:#213344;margin:10px 0}
.ld-validation{margin:0 13px 12px;padding:10px;border:1px solid #70542b;border-radius:6px;background:#241d13;color:#e6c081;font-size:11px;line-height:1.5}
#marketNetwork{display:block;width:100%;height:300px;max-width:100%;touch-action:pan-y}.ld-network-foot{padding:0 12px 12px;color:#829bad;font-size:10px;display:flex;justify-content:space-between}
.ld-flow-toolbar{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 12px;background:#0c1c2b;color:#72d9ee;font:10px ui-monospace,monospace}.ld-flow-toolbar button{border:1px solid #35576b;border-radius:4px;background:#102a3b;color:#c6edf7;padding:5px 8px;font-size:10px;cursor:pointer}.ld-flow-toolbar button:disabled{opacity:.45;cursor:default}.ld-flow-feed{margin:0 12px 10px;padding:8px 9px;border:1px solid #1d3547;border-radius:5px;min-height:38px;color:#9fc2d9;font:10px/1.7 ui-monospace,monospace}.ld-flow-feed b{color:#e1f6ff}.ld-flow-footer{font-size:10px;color:#839bab;padding:0 12px 12px;line-height:1.5}
.ld-volume-scale{padding:7px 12px;background:#102432;color:#afdfe8;font:10px/1.5 ui-monospace,monospace}.ld-volume-context{padding:0 12px 12px}.ld-volume-summary{display:flex;justify-content:space-between;gap:10px;color:#a0bbcd;font-size:11px;line-height:1.6}.ld-volume-summary b{display:block;color:#e6f4ff;font:700 19px ui-monospace,monospace}.ld-flow-balance{height:6px;display:flex;overflow:hidden;border-radius:3px;margin:9px 0 5px;background:#243849}.ld-volume-leaders{display:grid;gap:5px;margin-top:10px}.ld-volume-leader{display:grid;grid-template-columns:56px 1fr 52px 58px;align-items:center;gap:6px;font:10px ui-monospace,monospace;color:#acd0e4}.ld-volume-leader i{height:4px;background:#e8c173;display:block;max-width:100%}.ld-volume-leader b{color:#ecf6ff}.ld-volume-heading{display:flex;justify-content:space-between;gap:10px;margin-top:12px;font-size:10px;color:#a4bfd1}
.ld-heatgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;padding:12px}.ld-heat{border:1px solid #38524f;border-radius:5px;min-height:75px;cursor:pointer;text-align:left;color:#eef6f4;padding:8px;background:#142932}.ld-heat b{font:700 15px ui-monospace,monospace;display:block;margin:7px 0 4px}.ld-heat span{font-size:10px;display:block;color:#d0dfdf}.ld-heat.active{outline:2px solid #8dfff0;outline-offset:1px}
.ld-rows{padding:5px 12px}.ld-row{display:grid;grid-template-columns:60px 1fr 80px;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid #1d2e3d;font:11px ui-monospace,monospace}.ld-meter{height:5px;background:#192d3c;border-radius:3px;overflow:hidden}.ld-meter i{display:block;height:100%;background:#57bddc}.ld-volume svg{display:block;width:100%;height:145px}.ld-mini-note{padding:0 13px 12px;font-size:10px;line-height:1.5;color:#849eb2}
@media(max-width:850px){.ld-chart,.ld-volume{grid-column:span 8}.ld-readout,.ld-events{grid-column:span 4}.ld-network,.ld-sectors{grid-column:span 6}.ld-heatgrid{grid-template-columns:repeat(3,minmax(0,1fr))}.ld-price{font-size:24px}}
@media(max-width:600px){.live-desk{padding:12px}.live-grid{grid-template-columns:minmax(0,1fr)}.ld-panel{grid-column:1}.ld-network{order:3}.ld-sectors{order:4}.ld-volume{order:5}.ld-events{order:6}.ld-readout{order:2}.ld-heatgrid{grid-template-columns:repeat(3,minmax(0,1fr))}#marketNetwork{height:250px}.ld-chart svg{height:205px}.live-head h2{font-size:20px}}
@media(prefers-reduced-motion:reduce){.live-desk *{animation:none!important;transition:none!important}}
'''

HTML = r'''
<section id="tab-live" class="tabpane active live-desk">
  <div class="live-head"><div><h2>Market Live Desk</h2><p>PRICE ACTION / SECTOR BREADTH / PURCHASE CONDITIONS</p></div><div class="live-status" id="liveFeedStatus">CONNECTING TO MARKET SNAPSHOT</div></div>
  <div class="live-tape" id="liveTape" aria-label="Watchlist quote strip"></div>
  <div class="live-grid">
    <div class="ld-panel ld-chart"><div class="ld-title"><span>PRICE ACTION <select id="liveSymbol" aria-label="Chart symbol"></select></span><div class="ld-controls"><button data-live-range="intraday" class="on">1M BARS</button><button data-live-range="daily">6 MONTHS</button></div></div><div id="livePriceChart"></div></div>
    <div class="ld-panel ld-readout"><div class="ld-title">ENTRY CONDITIONS <span id="liveEntryLabel">WAIT</span></div><div id="liveReadout"></div><div class="ld-validation"><b>Timing edge not established</b><br>Price/sector rule tests did not show consistent improvement over ordinary entries. Full live overlays remain unvalidated. BUY means the entry rules pass.</div></div>
    <div class="ld-panel ld-network"><div class="ld-title">MARKET ACTIVITY <span id="liveNodeCount"></span></div><div class="ld-flow-toolbar"><span id="networkFlowStatus">WAITING FOR VOLUME UPDATES</span><button id="networkReplay" disabled>Replay recent activity</button></div><div id="networkVolumeScale" class="ld-volume-scale">Density = shares · full projectile = 10,000 shares</div><canvas id="marketNetwork" aria-label="Volume-weighted stock sphere: denser projectiles mean more reported shares; amber node halos mark volume surges" role="img"></canvas><div class="ld-network-foot"><span>Node size: volume surge · amber: ≥2×</span><span>Drag to rotate</span></div><div id="networkVolumeContext" class="ld-volume-context"></div><div id="networkFlowFeed" class="ld-flow-feed">No incoming activity yet.</div><div class="ld-flow-footer">Green/red = price rose/fell during the minute, not buyer/seller direction. A projectile is a share-volume packet, not an individual trade. Surge compares with the preceding 20 minutes in the same session (at least 10 bars). Activity is context, not a buy signal.</div></div>
    <div class="ld-panel ld-sectors"><div class="ld-title">SECTOR HEATMAP <span id="liveBreadth"></span></div><div id="liveHeatmap" class="ld-heatgrid"></div><div class="ld-mini-note">Select a sector to inspect its price and volume. Gray cells indicate unavailable data.</div></div>
    <div class="ld-panel ld-volume"><div class="ld-title">VOLUME BY BAR <span id="liveVolumePeriod"></span></div><div id="liveVolumeChart"></div><div class="ld-mini-note" id="liveChartTime"></div></div>
    <div class="ld-panel ld-events"><div class="ld-title">RELATIVE VOLUME <span>WATCHLIST</span></div><div class="ld-rows" id="liveActivity"></div><div class="ld-mini-note">Volume reflects reported activity, not buy/sell order flow.</div></div>
  </div>
</section>
'''

JS = r'''
const liveDesk={symbol:'VOO',range:'intraday',angle:0,drag:false,lastX:0,raf:0,lastFrame:0};
const networkFlow={tracker:NetworkFlow.create(),pulses:[],mode:'live',recent:[],count:0,uiAt:0,pausedAt:null,unit:10000,nodeActivity:new Map()};
function liveTone(n){return n==null?'#718799':n>=0?'#43dfac':'#fa6a80';}
function liveBars(){const series=st.data?.telemetry?.series?.[liveDesk.symbol];return series?.[liveDesk.range]||[];}
function liveFmtTime(t){if(!t)return '—';return t.includes('T')?quoteTime(t):t;}
function liveSelect(symbol){if(!st.data?.telemetry?.series?.[symbol])return;liveDesk.symbol=symbol;renderTelemetry();}
function chartMarkup(bars,volume=false){
  if(!bars.length)return '<div class="ld-empty">No '+(liveDesk.range==='intraday'?'intraday':'daily')+' bars available. Try the other timeframe.</div>';
  const W=Math.max(320,Math.round($('livePriceChart').clientWidth||760)),H=volume?145:225,left=12,right=56,top=12,bottom=27,plotW=W-left-right,plotH=H-top-bottom;
  const lo=volume?0:Math.min(...bars.map(b=>b.l)),hi=volume?Math.max(...bars.map(b=>b.v),1):Math.max(...bars.map(b=>b.h));
  const pad=volume?0:Math.max((hi-lo)*.08,hi*.0002),lower=lo-pad,upper=hi+pad,span=upper-lower||1;
  const y=v=>top+(upper-v)/span*plotH,step=plotW/bars.length,x=i=>left+step*(i+.5),width=Math.max(.8,step*.62);
  let svg=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(liveDesk.symbol)} ${volume?'volume bars':'candlestick price chart'}">`;
  for(let j=0;j<4;j++){const yy=top+j*plotH/3,value=upper-j*span/3;svg+=`<line x1="${left}" y1="${yy}" x2="${W-right}" y2="${yy}" stroke="#1d3445" stroke-dasharray="2 5"/><text x="${W-right+5}" y="${yy+3}" fill="#8299ad" font-size="10">${volume?(value>=1e6?(value/1e6).toFixed(1)+'m':value>=1e3?(value/1e3).toFixed(0)+'k':value.toFixed(0)):value.toFixed(2)}</text>`;}
  bars.forEach((b,i)=>{const color=b.c>=b.o?'#43dfac':'#fa6a80',xx=x(i),title=`${liveFmtTime(b.t)} | O ${b.o} H ${b.h} L ${b.l} C ${b.c} | volume ${b.v.toLocaleString()}`;
    if(volume)svg+=`<rect x="${xx-width/2}" y="${y(b.v)}" width="${width}" height="${Math.max(.5,top+plotH-y(b.v))}" fill="${color}" opacity=".78"><title>${esc(title)}</title></rect>`;
    else svg+=`<g><title>${esc(title)}</title><line x1="${xx}" y1="${y(b.h)}" x2="${xx}" y2="${y(b.l)}" stroke="${color}"/><rect x="${xx-width/2}" y="${y(Math.max(b.o,b.c))}" width="${width}" height="${Math.max(1,Math.abs(y(b.o)-y(b.c)))}" fill="${color}"/></g>`;
  });
  const first=bars[0],last=bars[bars.length-1];
  if(!volume)svg+=`<line x1="${left}" y1="${y(last.c)}" x2="${W-right}" y2="${y(last.c)}" stroke="${liveTone(last.c-first.c)}" opacity=".5" stroke-dasharray="5 4"/>`;
  svg+=`<text x="${left}" y="${H-6}" fill="#8299ad" font-size="10">${esc(liveFmtTime(first.t))}</text><text text-anchor="end" x="${W-right}" y="${H-6}" fill="#8299ad" font-size="10">${esc(liveFmtTime(last.t))}</text></svg>`;
  return svg;
}
function renderTelemetry(){
  if(!$('livePriceChart'))return;
  if(!st.data){
    $('liveFeedStatus').textContent=st.fetchError?'FEED UNAVAILABLE · RETRYING':'CONNECTING TO MARKET SNAPSHOT';
    $('liveFeedStatus').style.color=st.fetchError?'#e9b963':'#5fe1ba';
    $('livePriceChart').innerHTML='<div class="ld-empty">Waiting for market data. Retrying automatically…</div>';
    $('liveReadout').textContent='WAIT · Market data is not available yet.';
    return;
  }
  const d=st.data,t=d.telemetry,stale=feedStale();
  $('liveFeedStatus').textContent=stale?'STALE SNAPSHOT · PURCHASES PAUSED':'YAHOO FEED · '+(d.session?.state==='closed'?'MARKET CLOSED':'60s SNAPSHOTS');
  $('liveFeedStatus').style.color=stale?'#e9b963':'#5fe1ba';
  if(!t){$('livePriceChart').innerHTML='<div class="ld-empty">Waiting for chart data from the API…</div>';return;}
  const symbols=Object.keys(t.series||{});
  if(!symbols.includes(liveDesk.symbol))liveDesk.symbol=symbols[0];
  $('liveSymbol').innerHTML=symbols.map(s=>`<option ${s===liveDesk.symbol?'selected':''}>${esc(s)}</option>`).join('');
  document.querySelectorAll('[data-live-range]').forEach(b=>b.classList.toggle('on',b.dataset.liveRange===liveDesk.range));
  const wl=d.watchlist||[],w=wl.find(x=>x.ticker===liveDesk.symbol),sector=(d.sectors||[]).find(x=>x.symbol===liveDesk.symbol),s=w?.signal||sector?.metrics||{},a=w?purchaseAction(s):'CONTEXT';
  const bars=liveBars();
  $('livePriceChart').innerHTML=`<div class="ld-price-meta"><span class="ld-price">${fmtPrice(s.price)}</span><span style="color:${liveTone(s.change_pct)};font:12px ui-monospace,monospace">${fmtPct(s.change_pct)}</span><span class="ld-muted">${esc(liveDesk.symbol||'')} · ${liveDesk.symbol?.endsWith('.TO')?'CAD':'USD'}</span></div>`+(s.data_status&&!['current','close'].includes(s.data_status)?`<div class="ld-muted" style="padding:6px 14px;color:#e9b963">${esc(s.data_reason||'Quote unavailable or stale')}</div>`:'')+chartMarkup(bars);
  $('liveVolumeChart').innerHTML=chartMarkup(bars,true);
  $('liveVolumePeriod').textContent=liveDesk.range==='intraday'?'1 MINUTE':'DAILY';
  $('liveChartTime').textContent='Last chart bar: '+liveFmtTime(bars.at(-1)?.t)+'. '+t.note;
  $('liveEntryLabel').textContent=a;$('liveEntryLabel').style.color=entryColor(a);
  const counts={BUY:0,WAIT:0,AVOID:0};wl.forEach(w=>counts[purchaseAction(w.signal||{})]++);
  const total=wl.length||1,up=d.breadth?.up||0,dn=d.breadth?.down||0;
  $('liveReadout').innerHTML=`<div class="ld-stats"><div class="ld-stat"><span class="ld-muted">BUY CHECKS PASS</span><b style="color:#43dfac">${counts.BUY}</b><span class="ld-muted">of ${wl.length} watchlist names</span></div><div class="ld-stat"><span class="ld-muted">WAIT / AVOID</span><b style="color:#e6bd68">${counts.WAIT} / ${counts.AVOID}</b><span class="ld-muted">current entry conditions</span></div></div><div style="padding:0 14px 12px"><div class="ld-bar"><span style="width:${counts.BUY/total*100}%;background:#43dfac"></span><span style="width:${counts.WAIT/total*100}%;background:#e6bd68"></span><span style="width:${counts.AVOID/total*100}%;background:#fa6a80"></span></div><div class="ld-muted">${esc(stale?'Waiting for fresh data':s.entry_reason||'Sector context — select a watchlist stock for purchase conditions')}</div></div>`;
  $('liveTape').innerHTML=wl.filter(w=>w.signal?.price!=null).map(w=>`<button data-live-symbol="${esc(w.ticker)}"><b>${esc(w.ticker)}</b> ${fmtPrice(w.signal.price)} <span style="color:${liveTone(w.signal.change_pct)}">${fmtPct(w.signal.change_pct)}</span></button>`).join('');
  $('liveBreadth').textContent=up+' UP / '+dn+' DOWN';
  $('liveHeatmap').innerHTML=(d.sectors||[]).map(sec=>{const m=sec.metrics||{},p=['current','close'].includes(m.data_status)?m.change_pct:null;return `<button class="ld-heat ${liveDesk.symbol===sec.symbol?'active':''}" data-live-symbol="${esc(sec.symbol)}" style="background:${heatColor(p)}"><strong>${esc(sec.symbol)}</strong><b>${fmtPct(p)}</b><span>${esc(sec.name)}</span></button>`;}).join('');
  const metrics=new Map((t.nodes||[]).map(x=>[x.symbol,x]));
  const active=wl.map(w=>({symbol:w.ticker,...metrics.get(w.ticker)})).filter(x=>Number.isFinite(x.rvol)).sort((a,b)=>b.rvol-a.rvol).slice(0,5),max=Math.max(...active.map(x=>x.rvol),1);
  $('liveActivity').innerHTML=active.map(x=>`<div class="ld-row"><b>${esc(x.symbol)}</b><div class="ld-meter"><i style="width:${x.rvol/max*100}%"></i></div><span style="text-align:right">${x.rvol.toFixed(2)}×</span></div>`).join('')||'<div class="ld-empty" style="padding:28px 0">No current relative-volume data</div>';
  $('liveNodeCount').textContent=(t.nodes||[]).filter(n=>n.price!=null).length+' STOCKS';
  ingestNetworkFlow();
  drawMarketNetwork();
}
function flowEvents(){return st.data?.telemetry?.activity?.events||[];}
function flowVisible(){
  const rect=$('marketNetwork')?.getBoundingClientRect();
  return !!rect&&rect.top<innerHeight-40&&rect.bottom>100&&$('tab-live')?.classList.contains('active')&&!document.hidden;
}
function ingestNetworkFlow(){
  networkFlow.nodeActivity=new Map(flowEvents().map(e=>[e.symbol,e]));
  renderVolumeContext();
  const paused=feedStale()||st.data?.session?.state==='closed';
  const events=NetworkFlow.ingest(networkFlow.tracker,flowEvents(),Number(st.data?.updated_at)*1000,Date.now(),paused,flowVisible());
  if(paused&&networkFlow.mode==='live')networkFlow.pulses=[];
  if(feedStale()){networkFlow.pulses=[];networkFlow.mode='live';}
  if(networkFlow.mode==='live'&&events.length){
    const batch=NetworkFlow.volumeSchedule(events,performance.now(),50000);
    networkFlow.unit=batch.unit;
    networkFlow.pulses=networkFlow.pulses.filter(p=>performance.now()<p.start+p.duration+900).concat(batch.pulses);
    networkFlow.recent=events.slice(-3).reverse();networkFlow.count=events.length;
  }
  renderNetworkFlowStatus();
}
function renderNetworkFlowStatus(){
  const status=$('networkFlowStatus'),replay=$('networkReplay');if(!status)return;
  const stale=feedStale(),replaying=networkFlow.mode==='replay',closed=st.data?.session?.state==='closed';
  const pending=networkFlow.pulses.length;
  status.textContent=stale?'FLOW PAUSED · STALE DATA':replaying?(pending?'REPLAY · RECORDED VOLUME':'REPLAY COMPLETE'):closed?'MARKET CLOSED · FLOW IDLE':pending?'VOLUME FLOW · '+pending+' PACKETS':'LISTENING FOR NEW VOLUME';
  status.style.color=replaying?'#eac079':stale?'#e9b963':'#72d9ee';
  replay.textContent=replaying?'Return to live':'Replay recent activity';
  replay.disabled=stale||(!replaying&&!flowEvents().length);
  const latest=flowEvents().at(-1)?.t;
  const units=[...new Set(networkFlow.pulses.map(p=>p.unit))].filter(Number.isFinite).sort((a,b)=>a-b);
  const scale=units.length>1?units.map(u=>Number(u).toLocaleString()).join(' / '):Number(units[0]||networkFlow.unit).toLocaleString();
  $('networkVolumeScale').textContent='Full projectile = '+scale+' shares · smaller = partial'+(units.length>1?' · overlapping batch scales':'');
  $('networkFlowFeed').innerHTML=networkFlow.recent.length?`${replaying?'RECORDED':'LATEST RECEIVED'} · ${networkFlow.count} volume bars<br>`+networkFlow.recent.map(e=>`<b>${esc(e.symbol)}</b> ${Number(e.volume).toLocaleString()} shares · ${esc(liveFmtTime(e.t))}`).join('<br>'):(closed?'No active flow while markets are closed. Replay the latest recorded bars above.':'Waiting for fresh volume.'+(latest?' Latest available bar: '+esc(liveFmtTime(latest))+'.':''));
}
function renderVolumeContext(){
  const box=$('networkVolumeContext');if(!box)return;
  const summary=NetworkFlow.activitySummary(flowEvents());
  if(!summary.count){box.innerHTML='<div class="ld-muted">No completed volume bars available.</div>';return;}
  const total=summary.total||1,up=summary.rising/total*100,down=summary.falling/total*100;
  const stale=feedStale()||Date.now()-Date.parse(summary.time)>180000;
  const largest=Math.max(2,...summary.leaders.map(e=>e.volume_ratio));
  box.innerHTML=`<div class="ld-volume-summary"><span>Latest minute · ${summary.count} tracked stocks<b>${Number(summary.total).toLocaleString()} shares</b></span><span>≥2× volume<b>${summary.baselineCount?summary.surges+' / '+summary.baselineCount:'—'}</b></span></div><div class="ld-muted">${stale?'Historical / delayed · ':''}${esc(liveFmtTime(summary.time))} · aligned bar timestamps</div><div class="ld-flow-balance"><span style="width:${up}%;background:#43dfac"></span><span style="width:${down}%;background:#fa6a80"></span><span style="flex:1;background:#70d6f5"></span></div><div class="ld-muted">${up.toFixed(0)}% of shares in rising-price bars · ${down.toFixed(0)}% in falling-price bars</div><div class="ld-volume-heading"><b>VOLUME SURGE WATCH</b><span>vs prior 20 min · price Δ</span></div><div class="ld-volume-leaders">${summary.leaders.map(e=>`<div class="ld-volume-leader"><b>${esc(e.symbol)}</b><span><i style="width:${e.volume_ratio/largest*100}%;background:${e.volume_ratio>=2?'#e8c173':'#497c96'}"></i></span><span>${e.volume_ratio.toFixed(1)}×</span><span style="color:${liveTone(e.close-e.open)}">${fmtPct((e.close/e.open-1)*100)}</span></div>`).join('')||'<div class="ld-muted">Insufficient preceding-minute history for a surge comparison.</div>'}</div>`;
}
function toggleNetworkReplay(){
  if(feedStale())return;
  networkFlow.pulses=[];networkFlow.recent=[];networkFlow.count=0;networkFlow.pausedAt=null;
  if(networkFlow.mode==='replay'){networkFlow.mode='live';}
  else{
    const events=NetworkFlow.replay(flowEvents());
    networkFlow.mode='replay';networkFlow.count=events.length;
    networkFlow.recent=events.slice(-3).reverse();
    const batch=NetworkFlow.volumeSchedule(events,performance.now(),16000);
    networkFlow.unit=batch.unit;
    networkFlow.pulses=matchMedia('(prefers-reduced-motion: reduce)').matches?[]:batch.pulses;
  }
  renderNetworkFlowStatus();drawMarketNetwork();
}
function drawIncomingVolume(ctx,projected,W,H,now,motion){
  const targets=new Map(projected.map(n=>[n.symbol,n]));
  networkFlow.pulses=networkFlow.pulses.filter(p=>now<p.start+p.duration+900&&targets.has(p.symbol));
  if(!motion)return;
  for(const p of networkFlow.pulses){
    if(now<p.start)continue;
    const target=targets.get(p.symbol),t=Math.min(1,(now-p.start)/p.duration);
    const side=p.ordinal%2===0?-1:1,sx=side<0?4:W-4,sy=24+(p.ordinal*61)%Math.max(40,H-48);
    const controlX=W*.5+side*W*.30,controlY=H*.15+(p.ordinal%3)*H*.3;
    const point=u=>({x:(1-u)**2*sx+2*(1-u)*u*controlX+u*u*target.x,y:(1-u)**2*sy+2*(1-u)*u*controlY+u*u*target.y});
    const color=p.close===p.open?'#70d6f5':p.close>p.open?'#43efb7':'#ff758a';
    ctx.strokeStyle=color;ctx.fillStyle=color;
    if(t<1){
      // A curved light trail follows the current position of the rotating node.
      for(let j=0;j<10;j++){
        const u=Math.max(0,t-j*.018),a=point(u),b=point(Math.max(0,u-.02));
        const fraction=Math.max(.08,p.representedShares/p.unit);
        ctx.globalAlpha=(1-j/10)*(.35+.45*fraction);ctx.lineWidth=(1.5+(1-j/10)*1.5)*Math.sqrt(fraction);
        ctx.beginPath();ctx.moveTo(b.x,b.y);ctx.lineTo(a.x,a.y);ctx.stroke();
      }
      const head=point(t);ctx.globalAlpha=1;ctx.shadowBlur=12;ctx.shadowColor=color;
      ctx.beginPath();ctx.arc(head.x,head.y,Math.max(1,3.8*Math.sqrt(p.representedShares/p.unit)),0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
      if(p.fragment===0&&p.ordinal%3===0){
        const shares=p.volume>=1e6?(p.volume/1e6).toFixed(1)+'m':p.volume>=1000?(p.volume/1000).toFixed(1)+'k':p.volume;
        ctx.font='9px ui-monospace,monospace';ctx.fillStyle='#e5f5ff';ctx.textAlign=side<0?'left':'right';
        ctx.fillText(p.symbol+' '+shares+'/min',Math.max(8,Math.min(W-8,head.x)),Math.max(12,head.y-9));ctx.textAlign='left';
      }
    }else{
      const fade=(now-p.start-p.duration)/900;ctx.globalAlpha=(1-fade)*.95;ctx.lineWidth=2;
      ctx.beginPath();ctx.arc(target.x,target.y,target.r+fade*23,0,Math.PI*2);ctx.stroke();
      ctx.globalAlpha=(1-fade)*.5;ctx.beginPath();ctx.arc(target.x,target.y,target.r+4,0,Math.PI*2);ctx.fill();
    }
  }
  ctx.globalAlpha=1;ctx.shadowBlur=0;ctx.lineWidth=1;
}
function drawMarketNetwork(now=performance.now()){
  const canvas=$('marketNetwork');if(!canvas)return;
  const visible=flowVisible();
  const motion=!matchMedia('(prefers-reduced-motion: reduce)').matches;
  cancelAnimationFrame(liveDesk.raf);
  if(!visible&&networkFlow.pausedAt===null)networkFlow.pausedAt=now;
  if(visible&&networkFlow.pausedAt!==null){
    networkFlow.pulses=NetworkFlow.resume(networkFlow.pulses,networkFlow.pausedAt,now,Date.now(),networkFlow.mode==='replay');
    networkFlow.pausedAt=null;ingestNetworkFlow();
  }
  if(visible){
    const rect=canvas.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2),W=rect.width,H=rect.height;
    if(W&&H){
      if(canvas.width!==Math.round(W*ratio)||canvas.height!==Math.round(H*ratio)){canvas.width=Math.round(W*ratio);canvas.height=Math.round(H*ratio);}
      const ctx=canvas.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,W,H);
      if(!liveDesk.drag&&motion)liveDesk.angle+=Math.min(now-liveDesk.lastFrame,50)*.00009;
      const nodes=(st.data?.telemetry?.nodes||[]),cx=W*.5,cy=H*.5,R=Math.min(W,H)*.39;
      const glow=ctx.createRadialGradient(cx,cy,4,cx,cy,R*1.3);glow.addColorStop(0,'#12324c');glow.addColorStop(.75,'#0b1a2b');glow.addColorStop(1,'#080f19');ctx.fillStyle=glow;ctx.fillRect(0,0,W,H);
      ctx.strokeStyle='#29455a';ctx.lineWidth=.6;ctx.beginPath();ctx.arc(cx,cy,R,0,Math.PI*2);ctx.stroke();
      const projected=nodes.map((n,i)=>{const yy=1-2*(i+.5)/nodes.length,rr=Math.sqrt(1-yy*yy),phi=i*2.399963+liveDesk.angle,xx=Math.cos(phi)*rr,zz=Math.sin(phi)*rr,e=networkFlow.nodeActivity.get(n.symbol),fresh=e&&!feedStale()&&(networkFlow.mode==='replay'||Date.now()-Date.parse(e.t)<=180000),ratio=fresh&&Number.isFinite(e.volume_ratio)?e.volume_ratio:null;return {...n,bar:fresh?e:null,surge:ratio,x:cx+xx*R,y:cy+yy*R*.95,z:zz,r:ratio===null?2.4:2+Math.sqrt(Math.min(ratio,9))*2};}).sort((a,b)=>a.z-b.z);
      projected.forEach((n,i)=>{const alpha=.2+(n.z+1)*.35;ctx.globalAlpha=alpha;ctx.strokeStyle='#335572';ctx.lineWidth=.5;
        projected.slice(i+1).filter(q=>q.sector===n.sector&&Math.hypot(q.x-n.x,q.y-n.y)<R*.9).slice(0,3).forEach(q=>{ctx.beginPath();ctx.moveTo(n.x,n.y);ctx.lineTo(q.x,q.y);ctx.stroke();});
        ctx.fillStyle=feedStale()||!n.bar?'#77899a':n.bar.close===n.bar.open?'#70d6f5':liveTone(n.bar.close-n.bar.open);ctx.beginPath();ctx.arc(n.x,n.y,n.r*(.8+(n.z+1)*.25),0,Math.PI*2);ctx.fill();ctx.strokeStyle=n.surge>=2?'#e8c173':ctx.fillStyle;ctx.lineWidth=n.surge>=2?1.4:.5;ctx.beginPath();ctx.arc(n.x,n.y,n.r*2.1,0,Math.PI*2);ctx.stroke();
        if(n.z>.5&&i%7===0){ctx.font='9px ui-monospace,monospace';ctx.fillStyle='#bed5e6';ctx.fillText(n.symbol,n.x+9,n.y+3);}
      });ctx.globalAlpha=1;
      if(feedStale()||(!motion&&networkFlow.mode==='live'))networkFlow.pulses=[];
      drawIncomingVolume(ctx,projected,W,H,now,motion);
      if(now-networkFlow.uiAt>250){renderNetworkFlowStatus();networkFlow.uiAt=now;}
    }
  }
  liveDesk.lastFrame=now;
  if(motion)liveDesk.raf=requestAnimationFrame(drawMarketNetwork);
}
document.addEventListener('click',e=>{const symbol=e.target.closest('[data-live-symbol]');if(symbol)liveSelect(symbol.dataset.liveSymbol);const range=e.target.closest('[data-live-range]');if(range){liveDesk.range=range.dataset.liveRange;renderTelemetry();}if(e.target.closest('[data-tab="tab-live"]'))renderTelemetry();});
$('liveSymbol').addEventListener('change',e=>liveSelect(e.target.value));
$('networkReplay').addEventListener('click',toggleNetworkReplay);
document.addEventListener('visibilitychange',()=>{
  if(document.hidden&&networkFlow.pausedAt===null)networkFlow.pausedAt=performance.now();
  else if(!document.hidden)drawMarketNetwork();
});
const network=$('marketNetwork');
network.addEventListener('pointerdown',e=>{liveDesk.drag=true;liveDesk.lastX=e.clientX;network.setPointerCapture(e.pointerId);});
network.addEventListener('pointermove',e=>{if(liveDesk.drag){liveDesk.angle+=(e.clientX-liveDesk.lastX)*.008;liveDesk.lastX=e.clientX;drawMarketNetwork();}});
network.addEventListener('pointerup',()=>{liveDesk.drag=false;});network.addEventListener('pointercancel',()=>{liveDesk.drag=false;});
window.addEventListener('resize',renderTelemetry);
'''


def enhance_dashboard(html):
    html = html.replace('</style>', CSS + '\n</style>', 1)
    # Keep the detailed purchase list on Signals; the desk has its compact summary.
    start = html.index('<section class="card" style="margin:18px 20px" aria-label="Purchase timing">')
    end = html.index('</section>',start) + len('</section>')
    purchase = html[start:end]
    html = html[:start] + html[end:]
    html = html.replace('<section id="tab-signals" class="tabpane">', '<section id="tab-signals" class="tabpane">\n'+purchase, 1)
    html = html.replace('<section id="tab-market" class="tabpane active">', HTML+'\n<section id="tab-market" class="tabpane">',1)
    html = html.replace('class="tabbtn on" data-tab="tab-market"', 'class="tabbtn" data-tab="tab-market"',1)
    marker = '<button class="tabbtn" data-tab="tab-market"'
    html = html.replace(marker,'<button class="tabbtn on" data-tab="tab-live">◉ Live Desk</button>\n'+marker,1)
    html = html.replace('renderPurchases();renderCrashRadar();','renderPurchases();renderTelemetry();renderCrashRadar();',1)
    html = html.replace('st.fetchError=true;if(st.data)', 'st.fetchError=true;if(!st.data)renderTelemetry();if(st.data)', 1)
    return html.replace('</script>',FLOW_JS+'\n'+JS+'\n</script>',1)
