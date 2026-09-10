const test = require('node:test');
const assert = require('node:assert/strict');
const flow = require('./network_flow.js');
const now = Date.parse('2026-09-09T15:02:00Z');
const bar = (symbol='AAPL', minute='01', volume=1000) => ({symbol,t:`2026-09-09T15:${minute}:00Z`,open:100,close:101,volume});

test('arrivals retain reported bar volume and price', () => {
  assert.deepEqual(flow.ingest(flow.create(),[bar()],now,now),[bar()]);
});
test('polling or bar revisions never duplicate an arrival', () => {
  const t=flow.create();
  assert.equal(flow.ingest(t,[bar()],now,now).length,1);
  assert.equal(flow.ingest(t,[bar()],now,now).length,0);
  assert.equal(flow.ingest(t,[bar('AAPL','01',1500)],now+10000,now+10000).length,0);
});
test('only a newer completed bar creates the next arrival', () => {
  const t=flow.create(); flow.ingest(t,[bar()],now,now);
  assert.equal(flow.ingest(t,[bar('AAPL','02')],now+10000,now+10000).length,0);
  assert.equal(flow.ingest(t,[bar('AAPL','02')],now+60000,now+60000).length,1);
});
test('closed or stale feed consumes the batch without replay on resume', () => {
  const t=flow.create(); assert.equal(flow.ingest(t,[bar()],now,now,true).length,0);
  assert.equal(flow.ingest(t,[bar()],now+10000,now+10000).length,0);
});
test('old history, future bars and invalid volume do not masquerade as live activity', () => {
  const events=[bar('A','55'),{...bar('B'),t:'2026-09-08T15:01:00Z'},bar('C','01',0),{...bar('D'),close:NaN}];
  assert.deepEqual(flow.ingest(flow.create(),events,now,now),[]);
});
test('out-of-order snapshots cannot replay or roll back the watermark', () => {
  const t=flow.create(); flow.ingest(t,[bar()],now,now);
  assert.deepEqual(flow.ingest(t,[bar('B')],now-1000,now),[]);
  assert.equal(t.snapshot,now);
});
test('explicit replay is bounded, deduplicated and preserves recorded timestamps', () => {
  const events=Array.from({length:100},(_,i)=>bar('S'+i));
  const replay=flow.replay(events.concat(events));
  assert.equal(replay.length,80); assert.equal(replay[0].t,events[0].t);
});
test('animation schedule is finite and never splits volume into invented trades', () => {
  const events=Array.from({length:100},(_,i)=>bar('S'+i));
  const queued=flow.schedule(events,1234);
  assert.equal(queued.length,100); assert.equal(queued[0].volume,1000);
  assert.ok(queued.at(-1).start+queued.at(-1).duration < 1234+20000);
});

test('off-screen updates remain available when the sphere scrolls into view', () => {
  const tracker=flow.create();
  assert.deepEqual(flow.ingest(tracker,[bar()],now,now,false,false),[]);
  assert.equal(tracker.snapshot,-Infinity);
  assert.deepEqual(flow.ingest(tracker,[bar()],now,now+15000,false,true),[bar()]);
  assert.deepEqual(flow.ingest(tracker,[bar()],now,now+16000,false,true),[]);
});
test('off-screen buffering cannot present old records as active trading', () => {
  const tracker=flow.create(); flow.ingest(tracker,[bar()],now,now,false,false);
  assert.deepEqual(flow.ingest(tracker,[bar()],now,now+300000,false,true),[]);
});
test('hidden-tab playback resumes instead of disappearing', () => {
  const pending=flow.schedule([bar()],1000);
  const resumed=flow.resume(pending,2000,32000,now+30000);
  assert.equal(resumed.length,1);
  assert.equal(32000-resumed[0].start,2000-pending[0].start);
});
test('expired live pulses are discarded while explicit recorded replay is preserved', () => {
  const pending=flow.schedule([bar()],1000);
  assert.deepEqual(flow.resume(pending,2000,302000,now+300000),[]);
  assert.equal(flow.resume(pending,2000,302000,now+300000,true).length,1);
});
test('live batch is spread across the refresh interval without duplicating bars', () => {
  const events=Array.from({length:90},(_,i)=>bar('S'+i));
  const pending=flow.schedule(events,1000,50000);
  assert.equal(pending.length,90);
  assert.ok(pending.at(-1).start>49000);
  assert.ok(pending.at(-1).start+pending.at(-1).duration<55000);
});

test('ten times the shares produces ten times the full-size projectiles', () => {
  const batch=flow.volumeSchedule([bar('A','01',10000),bar('B','01',100000)],1000);
  assert.equal(batch.unit,10000);
  assert.equal(batch.pulses.filter(p=>p.symbol==='A').length,1);
  assert.equal(batch.pulses.filter(p=>p.symbol==='B').length,10);
});
test('partial projectiles conserve the exact reported share volume', () => {
  const events=[bar('A','01',25001),bar('B','01',1234)];
  const batch=flow.volumeSchedule(events,1000);
  for(const e of events)assert.equal(batch.pulses.filter(p=>p.symbol===e.symbol).reduce((n,p)=>n+p.representedShares,0),e.volume);
  assert.equal(batch.pulses.filter(p=>p.symbol==='A').at(-1).representedShares,5001);
});
test('busy batches use one disclosed scale without clipping the largest stock', () => {
  const batch=flow.volumeSchedule(Array.from({length:120},(_,i)=>bar('S'+i,'01',1e8)),1000);
  assert.ok(batch.unit>10000);
  assert.ok(batch.pulses.length<=800);
  assert.equal(new Set(batch.pulses.map(p=>p.unit)).size,1);
  assert.equal(batch.pulses.reduce((n,p)=>n+p.representedShares,0),batch.total);
});
test('higher volume raises density across the playback window', () => {
  const batch=flow.volumeSchedule([bar('A','01',100000)],1000,50000);
  assert.equal(batch.pulses.length,10);
  assert.ok(batch.pulses[0].start<5000);
  assert.ok(batch.pulses.at(-1).start>45000);
});
test('activity summary aligns timestamps instead of mixing different minutes', () => {
  const a={...bar('A','00',900000),volume_ratio:9};
  const b={...bar('B','01',10000),volume_ratio:3};
  const c={...bar('C','01',30000),close:99,volume_ratio:1};
  const s=flow.activitySummary([a,b,c]);
  assert.equal(s.count,2);assert.equal(s.total,40000);assert.equal(s.rising,10000);
  assert.equal(s.falling,30000);assert.equal(s.surges,1);assert.equal(s.leaders[0].symbol,'B');
});
test('missing baselines do not become zero-volume or surge claims', () => {
  const s=flow.activitySummary([bar()]);
  assert.equal(s.baselineCount,0);assert.equal(s.surges,0);assert.deepEqual(s.leaders,[]);
});
