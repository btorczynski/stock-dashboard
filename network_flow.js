/* Packets represent reported shares, never individual trades or aggressor side. */
const NetworkFlow = (() => {
  const MAX_AGE = 180000;
  function valid(event) {
    return event && typeof event.symbol === 'string' && Number.isFinite(Date.parse(event.t)) &&
      Number.isFinite(event.volume) && event.volume > 0 && Number.isFinite(event.close) && event.close > 0 &&
      Number.isFinite(event.open) && event.open > 0;
  }
  function create() { return {seen: new Map(), snapshot: -Infinity}; }
  function ingest(tracker, events, snapshot, now, paused = false, visible = true) {
    // Do not consume a fresh snapshot until its animation can actually be seen.
    if (!visible && !paused) return [];
    if (!Number.isFinite(snapshot) || snapshot <= tracker.snapshot || snapshot > now + 120000) return [];
    tracker.snapshot = snapshot;
    const arrivals = [];
    for (const event of [...events].filter(valid).sort((a,b) => Date.parse(a.t)-Date.parse(b.t))) {
      const stamp = Date.parse(event.t), previous = tracker.seen.get(event.symbol) ?? -Infinity;
      if (stamp + 60000 > now || stamp <= previous) continue;
      tracker.seen.set(event.symbol, stamp);
      if (!paused && now - stamp <= MAX_AGE) arrivals.push({...event});
    }
    return arrivals.slice(-120);
  }
  function replay(events) {
    // Bounded, single playback of recorded bars. Does not affect live deduplication.
    const unique = new Map();
    events.filter(valid).forEach(e => unique.set(e.symbol+'|'+e.t, {...e}));
    return [...unique.values()].sort((a,b) => Date.parse(a.t)-Date.parse(b.t)).slice(-80);
  }
  function schedule(events, now, spreadMs = 16000) {
    const spacing = spreadMs / Math.max(events.length, 1);
    return events.map((event,i) => ({...event, start:now+i*spacing, duration:2400, ordinal:i}));
  }
  function volumeSchedule(events, now, spreadMs = 50000, minimumUnit = 10000) {
    const rows=events.filter(valid), total=rows.reduce((sum,e)=>sum+e.volume,0);
    // One shared scale per batch preserves cross-stock comparisons. Raise it only
    // to keep at most ~800 particles, rather than clipping the busiest stocks.
    const maxVolume=Math.max(0,...rows.map(e=>e.volume));
    const unit=Math.max(minimumUnit,Math.ceil(Math.max(total/600,maxVolume/80)/minimumUnit)*minimumUnit);
    const pulses=[];
    rows.forEach((event,index)=>{
      const count=Math.ceil(event.volume/unit);
      for(let part=0;part<count;part++){
        const shares=Math.min(unit,event.volume-part*unit);
        pulses.push({...event,representedShares:shares,unit,fragment:part,
          start:now+(part+(index+.5)/Math.max(rows.length,1))/count*spreadMs,
          duration:2400,ordinal:pulses.length});
      }
    });
    pulses.sort((a,b)=>a.start-b.start);
    return {pulses,unit,total,bars:rows.length};
  }
  function activitySummary(events) {
    const rows=events.filter(valid);
    const latest=Math.max(-Infinity,...rows.map(e=>Date.parse(e.t)));
    const aligned=rows.filter(e=>Date.parse(e.t)===latest);
    const total=aligned.reduce((sum,e)=>sum+e.volume,0);
    const rising=aligned.filter(e=>e.close>e.open).reduce((sum,e)=>sum+e.volume,0);
    const falling=aligned.filter(e=>e.close<e.open).reduce((sum,e)=>sum+e.volume,0);
    const eligible=aligned.filter(e=>Number.isFinite(e.volume_ratio));
    return {time:aligned[0]?.t||null,count:aligned.length,total,rising,falling,flat:total-rising-falling,
      baselineCount:eligible.length,surges:eligible.filter(e=>e.volume_ratio>=2).length,
      leaders:[...eligible].sort((a,b)=>b.volume_ratio-a.volume_ratio||b.volume-a.volume).slice(0,5)};
  }
  function resume(pulses, pausedAt, now, wallNow, replay = false) {
    return pulses.filter(p => p.start+p.duration+900>pausedAt &&
      (replay || wallNow-Date.parse(p.t)<=MAX_AGE))
      .map(p => ({...p,start:p.start+Math.max(0,now-pausedAt)}));
  }
  return {create, ingest, replay, schedule, volumeSchedule, activitySummary, resume};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = NetworkFlow;
