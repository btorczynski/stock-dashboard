/* One arrival represents one completed volume bar, never an individual trade. */
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
  function resume(pulses, pausedAt, now, wallNow, replay = false) {
    return pulses.filter(p => p.start+p.duration+900>pausedAt &&
      (replay || wallNow-Date.parse(p.t)<=MAX_AGE))
      .map(p => ({...p,start:p.start+Math.max(0,now-pausedAt)}));
  }
  return {create, ingest, replay, schedule, resume};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = NetworkFlow;
