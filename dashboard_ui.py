"""Front-end (HTML/CSS/JS) — v2 glass UI. Polls /api/data and renders a tabbed
dashboard (Market / Signals / Strategies / Radar) in a dark glassmorphism theme.
Previous single-scroll UI archived in archive/dashboard_ui_v1_archived_2026-07-05.py"""

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Market Pulse · Live Signals & Simulators</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Sora:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#06070f;
    --panel:rgba(255,255,255,.045);--panel2:rgba(255,255,255,.06);
    --line:rgba(255,255,255,.09);--line2:rgba(255,255,255,.18);
    --txt:#edf1fd;--fg:#edf1fd;--muted:#94a2c0;
    --up:#2ee6a8;--down:#ff6b8b;--accent:#ffc94d;--buy:#2ee6a8;--sell:#ff6b8b;--hold:#e8b33e;
    --card-grad:linear-gradient(155deg,rgba(255,255,255,.075),rgba(255,255,255,.028) 55%,rgba(255,255,255,.015));
    --shadow:0 10px 40px -12px rgba(0,0,0,.6);
    --glass:blur(22px) saturate(140%);
    --radius:20px;
    --grad-a:linear-gradient(135deg,#8fb3ff,#59e6c4);
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0;color:var(--txt);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--bg);-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
  ::selection{background:rgba(89,230,196,.3)}
  ::-webkit-scrollbar{width:10px;height:10px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:6px;border:2px solid #0a0c18}
  ::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.22)}
  /* ---- aurora background ---- */
  .bgfx{position:fixed;inset:0;z-index:-1;overflow:hidden;
    background:radial-gradient(1200px 800px at 85% -15%,rgba(109,74,255,.15),transparent 60%),
               radial-gradient(1000px 700px at -15% 25%,rgba(0,180,255,.10),transparent 55%),
               radial-gradient(900px 700px at 55% 115%,rgba(46,230,168,.08),transparent 60%),var(--bg)}
  .orb{position:absolute;border-radius:50%;filter:blur(90px);opacity:.5;animation:drift 26s ease-in-out infinite alternate}
  .o1{width:520px;height:520px;left:-140px;top:-160px;background:radial-gradient(circle,rgba(124,77,255,.5),transparent 65%)}
  .o2{width:460px;height:460px;right:-120px;top:10%;background:radial-gradient(circle,rgba(0,190,255,.35),transparent 65%);animation-delay:-9s}
  .o3{width:560px;height:560px;left:30%;bottom:-260px;background:radial-gradient(circle,rgba(46,230,168,.26),transparent 65%);animation-delay:-17s}
  @keyframes drift{from{transform:translate(0,0) scale(1)}to{transform:translate(60px,40px) scale(1.12)}}
  /* ---- header ---- */
  header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:10px 20px;
    background:rgba(9,11,22,.55);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass);
    border-bottom:1px solid var(--line);position:sticky;top:0;z-index:40}
  .brand{display:flex;align-items:center;gap:9px}
  .logo{width:30px;height:30px;display:grid;place-items:center;border-radius:10px;font-size:15px;font-weight:800;color:#0b0d1a;
    background:linear-gradient(135deg,#7c4dff,#00c2ff);box-shadow:0 0 18px -2px rgba(0,194,255,.65)}
  h1{font-family:Sora,Inter,sans-serif;font-size:16px;margin:0;white-space:nowrap;font-weight:700;letter-spacing:.4px}
  h1 b{background:var(--grad-a);-webkit-background-clip:text;background-clip:text;color:transparent}
  .grow{flex:1}
  .badge{padding:5px 12px;border-radius:999px;font-size:11.5px;font-weight:700;border:1px solid var(--line);white-space:nowrap;letter-spacing:.2px;background:rgba(255,255,255,.03)}
  .badge.regular{background:rgba(46,230,168,.13);color:#7ef0c4;border-color:rgba(46,230,168,.35)}
  .badge.pre{background:rgba(255,201,77,.13);color:#ffd98a;border-color:rgba(255,201,77,.35)}
  .badge.post{background:rgba(139,125,255,.15);color:#c3baff;border-color:rgba(139,125,255,.4)}
  .badge.closed{background:rgba(148,162,192,.1);color:#aab6cf;border-color:rgba(148,162,192,.25)}
  .pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}.pill b{color:var(--txt)}
  .clock{font-variant-numeric:tabular-nums;font-weight:700;font-size:13.5px;font-family:Sora,Inter,sans-serif}
  .toggle{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);cursor:pointer;user-select:none}
  .toggle input{accent-color:#59e6c4;width:15px;height:15px}
  button.refresh{background:rgba(255,255,255,.06);color:var(--txt);border:1px solid var(--line);border-radius:10px;padding:6px 13px;font-size:13px;cursor:pointer;transition:.18s;backdrop-filter:blur(8px)}
  button.refresh:hover{border-color:rgba(89,230,196,.6);color:#59e6c4;box-shadow:0 0 14px -4px rgba(89,230,196,.7)}
  .regchip{padding:4px 10px;border-radius:8px;font-size:11px;font-weight:800;border:1px solid var(--line);background:rgba(255,255,255,.03)}
  /* ---- tabs ---- */
  .tabs{display:flex;gap:4px;padding:4px;border-radius:14px;background:rgba(255,255,255,.05);border:1px solid var(--line);max-width:100%;overflow-x:auto;scrollbar-width:none}
  .tabs::-webkit-scrollbar{display:none}
  .tabbtn{border:0;background:transparent;color:var(--muted);font:inherit;font-size:12.5px;font-weight:700;padding:7px 15px;border-radius:10px;cursor:pointer;transition:.18s;white-space:nowrap}
  .tabbtn:hover{color:var(--txt)}
  .tabbtn.on{color:#0b0d1a;background:var(--grad-a);box-shadow:0 4px 18px -4px rgba(89,230,196,.55)}
  main{max-width:1560px;margin:0 auto}
  .tabpane{display:none;padding:16px 20px 8px}
  .tabpane.active{display:block;animation:fadein .3s ease}
  @keyframes fadein{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  /* ---- cards ---- */
  .card{background:var(--card-grad);border:1px solid var(--line);border-radius:var(--radius);padding:15px 17px;box-shadow:var(--shadow);
    backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass);position:relative}
  .card::before{content:"";position:absolute;left:14px;right:14px;top:0;height:1px;pointer-events:none;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,.28),transparent)}
  .cardgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:14px;margin-top:14px}
  .cardgrid.sig{grid-template-columns:repeat(auto-fit,minmax(340px,1fr));align-items:start;margin-top:14px}
  #crashRadar>div,#topCalls>div{backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}
  .section-title{display:flex;align-items:center;gap:8px;font-family:Sora,Inter,sans-serif;font-size:11.5px;text-transform:uppercase;letter-spacing:1.4px;color:#b8c4de;margin:0 0 10px;font-weight:700}
  .section-title::before{content:"";width:8px;height:8px;border-radius:3px;background:var(--grad-a);box-shadow:0 0 10px rgba(89,230,196,.8);flex-shrink:0}
  .section-title.ranked{margin:22px 2px 12px;font-size:13px}
  .disc{font-size:10px;color:#8291ad;margin-top:9px;line-height:1.55}
  .empty{color:var(--muted);font-size:12px;padding:12px 4px;text-align:center}
  /* ---- loader ---- */
  .loadwrap{max-width:520px;margin:70px auto;text-align:center}
  .loadtrack{height:12px;background:rgba(255,255,255,.06);border:1px solid var(--line);border-radius:99px;overflow:hidden}
  .loadfill{height:100%;border-radius:99px;background:linear-gradient(90deg,#7c4dff,#00c2ff,#59e6c4,#00c2ff,#7c4dff);background-size:220% 100%;animation:shine 1.6s linear infinite;transition:width .35s ease}
  @keyframes shine{to{background-position:-220% 0}}
  /* ---- movers ---- */
  .movers{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
  .movers .col{background:var(--card-grad);border:1px solid var(--line);border-radius:var(--radius);padding:12px 15px;box-shadow:var(--shadow);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}
  .mv{display:flex;align-items:center;gap:8px;padding:5px 2px;font-size:12.5px}
  .mv .s{font-weight:800;width:58px}.mv .sec{color:var(--muted);font-size:10px;flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
  .mv .c{font-weight:800;font-variant-numeric:tabular-nums}
  @media(max-width:760px){.movers{grid-template-columns:1fr}}
  /* ---- bubbles ---- */
  .bubcard{padding:13px 15px}
  .cardbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
  .bubbles{display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:center;padding:10px 4px 4px}
  .bubfield{display:block;position:relative;height:460px;padding:0;overflow:hidden;border-radius:16px;
    background:radial-gradient(600px 380px at 50% 45%,rgba(100,140,255,.07),transparent 70%),rgba(4,6,14,.35)}
  .bubfield .bub{position:absolute;margin:0;will-change:left,top;z-index:2}
  .bubhead{position:absolute;top:10px;left:12px;z-index:5;display:flex;gap:9px;align-items:center;font-size:12.5px}
  .backchip{cursor:pointer;padding:4px 12px;border-radius:999px;border:1px solid var(--line2);background:rgba(10,13,26,.7);color:var(--muted);font-weight:700;backdrop-filter:blur(8px)}
  .backchip:hover{color:#59e6c4;border-color:rgba(89,230,196,.6)}
  .bubempty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:12px;z-index:4}
  .bub{border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;color:#fff;border:1px solid var(--glow,rgba(255,255,255,.25));position:relative;text-align:center;line-height:1.05;text-shadow:0 1px 4px rgba(0,0,0,.7);box-shadow:0 0 22px -2px var(--glow,rgba(255,255,255,.25)),inset 0 0 20px -5px var(--glow,rgba(255,255,255,.18));transition:transform .2s cubic-bezier(.34,1.56,.64,1),box-shadow .2s,filter .2s;backdrop-filter:blur(4px)}
  .bub:hover{transform:scale(1.09);box-shadow:0 0 36px 1px var(--glow,rgba(255,255,255,.55)),inset 0 0 22px -3px var(--glow,rgba(255,255,255,.3));filter:brightness(1.13)}
  .bub.sel{outline:3px solid #59e6c4;outline-offset:3px}
  .bub .bsym{font-weight:800}.bub .bpct{font-variant-numeric:tabular-nums;opacity:.95}
  .bub .bflag{position:absolute;top:6px;right:8px;font-size:12px;filter:drop-shadow(0 0 4px rgba(245,200,90,.9))}
  .bub.alive{animation:pulse 1.8s ease-in-out infinite}
  @keyframes pulse{0%,100%{box-shadow:0 0 18px -3px var(--glow),inset 0 0 16px -5px var(--glow),0 0 0 0 rgba(255,201,77,0)}50%{box-shadow:0 0 28px 1px var(--glow),inset 0 0 16px -4px var(--glow),0 0 0 4px rgba(255,201,77,.5)}}
  .legend{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted);margin-top:12px}
  .scale{height:10px;flex:1;border-radius:5px;background:linear-gradient(90deg,#ff6b8b,#57283a,#141a2b,#1d5f46,#2ee6a8)}
  .detail{margin-top:14px;background:var(--card-grad);border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;display:none;box-shadow:var(--shadow);backdrop-filter:var(--glass)}
  .detail.open{display:block;animation:rise .25s ease}
  @keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  .detail h2{font-size:15px;margin:0 0 8px}.detail .close{float:right;cursor:pointer;color:var(--muted);font-size:18px}
  .detail .close:hover{color:var(--txt)}
  /* ---- rows / cells ---- */
  .row{display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:12px;background:var(--panel2);border:1px solid var(--line);margin-bottom:6px;transition:border-color .15s,background .15s}
  .row:hover{border-color:var(--line2);background:rgba(255,255,255,.09)}
  .row .l{flex:1;min-width:0}.row .sym{font-weight:800;font-size:13px}.row .sub{font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .row .px{font-size:11px;color:var(--muted);text-align:right;min-width:58px;font-variant-numeric:tabular-nums}
  .act{font-size:11px;font-weight:800;padding:3px 8px;border-radius:9px;white-space:nowrap;text-align:center;min-width:70px;border:1px solid rgba(255,255,255,.08)}
  .act small{display:block;font-size:9px;opacity:.85}
  .rank{font-size:13px;font-weight:800;font-family:Sora,Inter,sans-serif;background:var(--grad-a);-webkit-background-clip:text;background-clip:text;color:transparent;width:18px;text-align:center}
  .grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}
  .cell{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:7px 9px}
  .cell .k{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
  .cell .v{font-size:13px;font-weight:800;font-variant-numeric:tabular-nums;margin-top:1px}
  .regime{padding:3px 9px;border-radius:999px;font-size:11px;font-weight:800}
  .RiskOn{background:rgba(46,230,168,.14);color:#7ef0c4;border:1px solid rgba(46,230,168,.35)}
  .Neutral{background:rgba(148,162,192,.12);color:#c2cee0;border:1px solid rgba(148,162,192,.3)}
  .Cautious{background:rgba(255,201,77,.14);color:#ffd98a;border:1px solid rgba(255,201,77,.35)}
  .RiskOff{background:rgba(255,107,139,.14);color:#ff9fb3;border:1px solid rgba(255,107,139,.4)}
  .ev{display:flex;gap:8px;font-size:11.5px;padding:4px 2px;border-bottom:1px solid rgba(255,255,255,.05);align-items:center}
  .ev .d{color:var(--muted);width:46px}.ev .n{flex:1}.ev .cd{font-weight:800}
  .evfed{color:#ffd98a}.evcpi{color:#b3baff}.evjobs{color:#9fe8c0}.evsupply{color:#ff9fb3}.evspacex{color:#cfa7ff}
  .news{font-size:11.5px;line-height:1.45}.news li{margin-bottom:4px;color:#cdd6e8}
  .warn{color:#ff9fb3;font-weight:700}
  .ahchip{display:inline-block;font-size:9px;font-weight:700;padding:1px 5px;border-radius:5px;background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.18)}
  .tag{display:inline-block;font-size:9px;font-weight:800;padding:1px 5px;border-radius:5px;margin-left:4px}
  .tag.p{background:rgba(139,125,255,.2);color:#c3baff;border:1px solid rgba(139,125,255,.4)}.tag.etf{background:rgba(255,255,255,.08);color:#cdd6e8;border:1px solid var(--line)}
  /* ---- simulator panels ---- */
  .sim{margin:14px 0;background:var(--card-grad);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow);
    backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass);position:relative}
  .sim::before{content:"";position:absolute;left:16px;right:16px;top:0;height:1px;pointer-events:none;background:linear-gradient(90deg,transparent,rgba(255,255,255,.25),transparent)}
  .sim h2{font-size:15px;margin:0 0 2px}.sim .sub{font-size:11px;color:var(--muted);margin-bottom:10px}
  .simgrid{display:flex;gap:16px;flex-wrap:wrap}
  .chartbox{flex:1;min-width:320px;position:relative}
  .zoombtn{position:absolute;top:8px;right:10px;z-index:6;width:26px;height:26px;display:flex;align-items:center;justify-content:center;border:1px solid var(--line);border-radius:7px;background:rgba(13,18,32,.85);color:var(--muted);cursor:pointer;font-size:13px;user-select:none}
  .zoombtn:hover{color:#fff;border-color:#5aa9ff}
  .chartmodal{position:fixed;inset:0;background:rgba(4,7,14,.93);z-index:1000;display:flex;align-items:center;justify-content:center;padding:14px;cursor:zoom-out}
  .chartmodal-inner{width:min(1250px,100%)}
  .chartmodal-inner svg{width:100%;height:auto;max-height:86vh;display:block}
  .chartmodal-hint{text-align:center;color:#8a97ad;font-size:11px;margin-top:8px}
  svg.eq{width:100%;height:250px;background:rgba(5,8,18,.5);border:1px solid var(--line);border-radius:14px;display:block;touch-action:pan-y}
  #eqtip,#mom_tip,#bsk_tip,#voo_tip,#pny_tip,#dip_tip,#conf_tip,#fvLump_tip,#fvDca_tip{position:absolute;top:8px;pointer-events:none;background:rgba(9,12,24,.92);backdrop-filter:blur(10px);border:1px solid var(--line2);border-radius:10px;padding:6px 9px;font-size:11px;display:none;max-width:230px;line-height:1.4;z-index:5;box-shadow:0 8px 24px -8px rgba(0,0,0,.7)}
  .zbtn{cursor:pointer;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px;border:1px solid var(--line);color:var(--muted);transition:.15s;background:rgba(255,255,255,.03)}
  .zbtn:hover{color:var(--txt);border-color:var(--line2);background:rgba(255,255,255,.07)}
  .zbtn.on{border-color:rgba(89,230,196,.55);color:#59e6c4;background:rgba(89,230,196,.1);box-shadow:0 0 10px -3px rgba(89,230,196,.6)}
  .lgd{display:flex;gap:14px;font-size:11px;color:var(--muted);margin:6px 2px;flex-wrap:wrap}
  .lgd i{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:5px}
  .stats{display:grid;grid-template-columns:repeat(2,minmax(110px,1fr));gap:7px;min-width:240px;align-content:start}
  .stat{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:9px 11px}
  .stat .k{font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}.stat .v{font-size:17px;font-weight:800;font-family:Sora,Inter,sans-serif;font-variant-numeric:tabular-nums;margin-top:1px}
  table.tr{width:100%;border-collapse:collapse;margin-top:12px;font-size:11px}
  table.tr th{text-align:left;color:var(--muted);font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--line);padding:5px 6px}
  table.tr td{padding:4px 6px;border-bottom:1px solid rgba(255,255,255,.05);font-variant-numeric:tabular-nums;vertical-align:top}
  table.tr tbody tr{transition:background .12s}
  table.tr tbody tr:hover{background:rgba(255,255,255,.04)}
  footer{color:#75829c;font-size:11px;padding:16px 20px 30px;line-height:1.5;border-top:1px solid var(--line);margin-top:16px;text-align:center}
  .spin{display:inline-block;width:22px;height:22px;border:3px solid var(--line);border-top-color:#59e6c4;border-radius:50%;animation:sp 1s linear infinite;vertical-align:-5px;margin-right:8px}
  @keyframes sp{to{transform:rotate(360deg)}}
  @media(max-width:900px){.tabpane{padding:12px 12px}header{padding:10px 12px}.pill.upd{display:none}}
  @media(max-width:700px){
    .orb{filter:blur(52px);opacity:.38}
    .card,.sim,.movers .col,header{backdrop-filter:blur(10px) saturate(130%);-webkit-backdrop-filter:blur(10px) saturate(130%)}
    .bub{backdrop-filter:none}
    .bubhead{font-size:12px}
    .legend{flex-wrap:wrap}
  }
</style>
</head>
<body>
<div class="bgfx" aria-hidden="true"><i class="orb o1"></i><i class="orb o2"></i><i class="orb o3"></i></div>

<header>
  <div class="brand"><span class="logo">∿</span><h1>Market <b>Pulse</b></h1></div>
  <nav class="tabs" id="tabs">
    <button class="tabbtn on" data-tab="tab-market">🫧 Market</button>
    <button class="tabbtn" data-tab="tab-signals">🎯 Signals</button>
    <button class="tabbtn" data-tab="tab-strategies">📊 Strategies</button>
    <button class="tabbtn" data-tab="tab-radar">🛰️ Radar</button>
  </nav>
  <span class="grow"></span>
  <span id="sessionBadge" class="badge closed">Loading…</span>
  <span id="regimeChip" class="regchip">—</span>
  <span class="pill">ET <span id="clock" class="clock">--:--:--</span></span>
  <span class="pill upd">Updated <b id="updated">—</b> · <b id="countdown">—</b>s</span>
  <button class="refresh" id="refreshBtn">↻</button>
</header>

<main>

<section id="tab-market" class="tabpane active">
  <div class="movers" id="movers"></div>
  <div class="card bubcard">
    <div class="cardbar">
      <div class="section-title" style="margin:0">S&amp;P Sectors — bubble size = size of the move · click to drill in</div>
      <label class="toggle"><input type="checkbox" id="onlyUnusual"/> Only unusual</label>
    </div>
    <div id="bubbles" class="bubbles"><div class="loadwrap"><div style="font-size:13px;color:var(--muted);margin-bottom:8px">Starting…</div><div class="loadtrack"><div class="loadfill" style="width:2%"></div></div></div></div>
    <div class="legend"><span>−</span><div class="scale"></div><span>+</span>
      <span style="margin-left:14px">Bigger bubble = bigger % move · ⚡ = unusual volume/price</span></div>
  </div>
  <div id="detail" class="detail"></div>
  <div class="cardgrid">
    <div class="card" id="macroCard"><div class="empty">Loading…</div></div>
    <div class="card" id="futCard"><div class="empty">Loading…</div></div>
    <div class="card" id="evCard"><div class="empty">Loading…</div></div>
    <div class="card" id="newsCard"><div class="empty">Loading…</div></div>
    <div class="card" id="resCard"><div class="empty">Loading…</div></div>
  </div>
</section>

<section id="tab-signals" class="tabpane">
  <div id="topCalls" style="margin-bottom:14px"></div>
  <div class="cardgrid sig" style="margin-top:0">
    <div class="card" id="picksCard"><div class="empty">Loading…</div></div>
    <div class="card" id="ltCard"><div class="empty">Loading…</div></div>
    <div class="card" id="sigCard"><div class="empty">Loading…</div></div>
    <div class="card" id="unuCard"><div class="empty">Loading…</div></div>
    <div class="card" id="insiderCard"><div class="empty">Loading…</div></div>
  </div>
</section>

<section id="tab-strategies" class="tabpane">
  <div class="sim" id="foreverPanel"><div class="section-title">💎 Buy &amp; Hold Forever — watchlist's durable names, never timed</div><div class="empty">Warming up… (first build fetches full history)</div></div>
  <div class="sim" id="confPanel"><div class="section-title">🎯 Watchlist Confidence Backtest — predicted vs actual</div><div class="empty">Warming up… (first build fetches ~3y of history)</div></div>
  <div class="section-title ranked">📊 Strategies — ranked by backtested return (best → worst)</div>
  <div class="sim" id="pennyPanel"><div class="section-title">$500 Penny Sleeve</div><div class="empty">Warming up…</div></div>
  <div class="sim" id="dipPanel"><div class="section-title">VOO Dip → Best Mega-Cap</div><div class="empty">Warming up…</div></div>
  <div class="sim" id="momPanel"><div class="section-title">My Strategy to Beat the S&amp;P 500</div><div class="empty">Warming up…</div></div>
  <div class="sim" id="basketPanel"><div class="section-title">Momentum Basket</div><div class="empty">Warming up…</div></div>
  <div class="sim" id="vooPanel"><div class="section-title">S&amp;P 500 (VOO) Timing</div><div class="empty">Warming up…</div></div>
</section>

<section id="tab-radar" class="tabpane">
  <div id="crashRadar"></div>
  <div class="cardgrid">
    <div class="card" id="crashCard"><div class="empty">Loading…</div></div>
  </div>
</section>

</main>

<footer>
  Data: Yahoo Finance (via yfinance), polled locally. Signals, the crash-risk gauge and the simulators are mechanical research
  tools recomputed daily. <b>Information only — not financial advice; past results and risk gauges do not predict the future.</b>
</footer>
<script>
const POLL_MS=15000, LOAD_EST=42000;
const st={data:null,onlyUnusual:false,selected:null,nextAt:0,simScale:null,simView:null,simZoom:'max',vooZoom:'max',momZoom:'max',bskZoom:'max',pnyZoom:'max',dipZoom:'max',confZoom:'max',loadStart:0};
const $=id=>document.getElementById(id);
function fmtPct(p){return (p===null||p===undefined)?'—':(p>=0?'+':'')+p.toFixed(2)+'%';}
function fmtPrice(p){return (p===null||p===undefined)?'—':'$'+p.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});}
function fmtRvol(r){return (r===null||r===undefined)?'—':r.toFixed(2)+'×';}
function fmtMoney(v){return v==null?'—':'$'+Math.round(v).toLocaleString();}
function money(v){return (v>=0?'+':'-')+'$'+Math.abs(Math.round(v)).toLocaleString();}
function arrow(p){return (p===null||p===undefined)?'':(p>0?'▲':(p<0?'▼':'•'));}
function etNow(){return new Date().toLocaleTimeString('en-US',{timeZone:'America/New_York',hour12:false});}
function heatColor(pct){if(pct===null||pct===undefined)return 'rgb(34,42,56)';const x=Math.max(-3,Math.min(3,pct))/3,mag=Math.abs(x),nt=[27,34,48],tg=x>=0?[22,163,74]:[220,53,69];const c=nt.map((n,i)=>Math.round(n+(tg[i]-n)*mag));return `rgb(${c[0]},${c[1]},${c[2]})`;}
function glow(p){return (p||0)>=0?'rgba(34,197,110,.75)':'rgba(248,90,108,.75)';}
function rgba(c,a){const m=(c.match(/\d+/g)||[27,34,48]).slice(0,3).join(',');return `rgba(${m},${a})`;}
function orb(p){const b=heatColor(p);return `radial-gradient(circle at 50% 42%, ${rgba(b,.82)}, ${rgba(b,.42)} 62%, ${rgba(b,.12)})`;}
function actColor(a){return a==='BUY'?'var(--buy)':a==='SELL'?'var(--sell)':a==='HOLD'?'var(--hold)':'#6b7280';}
function actBg(a){return a==='BUY'?'rgba(22,163,74,.18)':a==='SELL'?'rgba(220,53,69,.18)':a==='HOLD'?'rgba(184,134,11,.18)':'rgba(107,114,128,.18)';}
function ahChip(m){if(!m||m.ext_change_pct==null||!m.ext_kind)return '';return `<span class="ahchip">${m.ext_kind==='pre'?'PRE':'AH'} ${fmtPct(m.ext_change_pct)}</span>`;}
function bubSize(pct){return Math.round(50+Math.min(Math.abs(pct||0),5)/5*102);}

function renderLoad(){
  if(st.data)return;
  const pct=Math.min(96,((Date.now()-(st.loadStart||Date.now()))/LOAD_EST)*100);
  const b=$('bubbles');if(!b)return;
  b.innerHTML=`<div class="loadwrap"><div style="font-size:13px;color:var(--muted);margin-bottom:10px">Loading market data, signals, crash-risk &amp; the backtests…</div>
    <div class="loadtrack"><div class="loadfill" style="width:${pct.toFixed(0)}%"></div></div>
    <div style="font-size:22px;font-weight:800;margin-top:10px">${pct.toFixed(0)}%</div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px">first launch pulls ~20 years of history; this is a one-time wait</div></div>`;
}

function render(){
  const d=st.data;if(!d)return;
  const sess=d.session,b=$('sessionBadge');b.className='badge '+sess.state;b.textContent=sess.label;
  const mb=d.market_bias,lab=mb<=-0.4?'Risk-Off':mb<=-0.1?'Cautious':mb<0.1?'Neutral':'Risk-On';
  const rc=$('regimeChip');rc.className='regchip '+lab.replace(/[^A-Za-z]/g,'');
  rc.innerHTML=`${lab} ${mb>=0?'+':''}${mb.toFixed(2)}`+(d.event_risk>=0.4?' · ⚠ event':'');
  $('updated').textContent=d.updated_at_str.replace(' ET','');
  renderCrashRadar();renderTopCalls();renderMovers();renderBubbles();renderDetail();renderLT();renderCrash();renderMacro();renderFutures();renderEvents();renderNews();renderResources();renderPicks();renderSignals();renderUnusual();renderInsider();renderConfSim();renderForever();renderVooSim();renderMomSim();renderBasket();renderPenny();renderDip();
}
function renderMovers(){
  const m=st.data.movers||{losers:[],gainers:[]};
  const row=x=>`<div class="mv"><span class="s">${x.symbol}</span><span class="sec">${x.sector||''}</span><span class="c" style="color:${x.change_pct>=0?'var(--up)':'var(--down)'}">${arrow(x.change_pct)} ${fmtPct(x.change_pct)}</span></div>`;
  $('movers').innerHTML=`<div class="col"><div class="section-title" style="color:var(--down)">▼ Top 5 Losers</div>${(m.losers||[]).map(row).join('')||'<div class="empty">—</div>'}</div>`+
    `<div class="col"><div class="section-title" style="color:var(--up)">▲ Top 5 Gainers</div>${(m.gainers||[]).map(row).join('')||'<div class="empty">—</div>'}</div>`;
}
// ---- Kalshi-style physics bubble field --------------------------------------
const fld={nodes:new Map(),raf:0,t:0,W:0,H:460};
function sizeField(){
  const b=$('bubbles');if(!b||!b.classList.contains('bubfield'))return;
  fld.W=b.clientWidth||fld.W||900;
  const mob=fld.W<520;
  fld.H=mob?Math.max(360,Math.min(540,Math.round(window.innerHeight*0.52))):460;
  b.style.height=fld.H+'px';
}
function fieldItems(){
  const d=st.data;if(!d)return [];
  if(st.selected){
    const s=d.sectors.find(x=>x.symbol===st.selected);
    if(s){let ss=s.stocks.slice();if(st.onlyUnusual)ss=ss.filter(x=>x.metrics.unusual);
      return ss.map(x=>({key:x.symbol,sym:x.symbol,m:x.metrics,drill:false}));}
  }
  const secs=d.sectors.filter(s=>!st.onlyUnusual||s.metrics.unusual||s.unusual_members>0);
  return secs.map(s=>({key:s.symbol,sym:s.symbol,m:s.metrics,drill:true}));
}
function renderBubbles(){
  const box=$('bubbles');
  if(!box.classList.contains('bubfield')||!$('bubhead')){
    box.className='bubbles bubfield';
    box.innerHTML='<canvas id="bubmesh" style="position:absolute;inset:0;z-index:0"></canvas><div class="bubhead" id="bubhead"></div><div class="bubempty" id="bubempty" style="display:none"></div>';meshStars=null;
    fld.nodes.clear();
  }
  const d=st.data,sec=st.selected&&d.sectors.find(x=>x.symbol===st.selected);
  $('bubhead').innerHTML=sec?`<span class="backchip" data-close="1">◀ All sectors</span><b>${sec.name}</b> <span style="font-weight:800;color:${(sec.metrics.change_pct||0)>=0?'var(--up)':'var(--down)'}">${fmtPct(sec.metrics.change_pct)}</span>`:'';
  const items=fieldItems();
  $('bubempty').style.display=items.length?'none':'flex';
  $('bubempty').textContent=items.length?'':'No unusual activity right now.';
  sizeField();
  const mob=fld.W<520;
  // area-fit: scale radii so bubbles fill the field
  const raw=items.map(x=>bubSize(x.m.change_pct)/2*1.35);
  const s=Math.min(1.6,Math.sqrt((fld.W*fld.H*0.55)/Math.max(1,raw.reduce((a,r)=>a+Math.PI*r*r,0))));
  const seen=new Set();
  items.forEach((it,k)=>{
    seen.add(it.key);
    const r=Math.max(mob?19:24,raw[k]*s);
    let n=fld.nodes.get(it.key);
    if(!n){
      const ang=(k/Math.max(1,items.length))*2*Math.PI;
      n={key:it.key,x:fld.W/2+Math.cos(ang)*60,y:fld.H/2+Math.sin(ang)*40,vx:0,vy:0,r:2,tr:r,
         ph:Math.random()*6.28,el:document.createElement('div')};
      n.el.className='bub';box.appendChild(n.el);
      fld.nodes.set(it.key,n);
    }
    n.tr=r;n.dead=false;n.pct=it.m.change_pct||0;
    const m=it.m,fs=Math.max(mob?10:9,Math.round(r/3.2));
    n.el.className='bub'+(m.unusual?' alive':'');
    if(it.drill)n.el.dataset.sym=it.sym;else delete n.el.dataset.sym;
    n.el.style.background=orb(m.change_pct);n.el.style.setProperty('--glow',glow(m.change_pct));
    n.el.style.fontSize=fs+'px';n.el.style.cursor=it.drill?'pointer':'default';
    n.el.innerHTML=`${m.unusual?'<span class="bflag">⚡</span>':''}<div class="bsym">${it.sym}</div><div class="bpct">${fmtPct(m.change_pct)}</div>`;
  });
  fld.nodes.forEach(n=>{if(!seen.has(n.key)){n.dead=true;n.tr=0;}});
  if(!fld.raf)fld.raf=requestAnimationFrame(tickField);
}
function tickField(){
  fld.raf=requestAnimationFrame(tickField);
  fld.frame=(fld.frame||0)+1;
  const mob=fld.W<520;
  if(mob&&(fld.frame&1))return;          // phones: ~30fps is smooth enough
  fld.t+=mob?0.032:0.016;
  const ns=[...fld.nodes.values()],cx=fld.W/2,cy=fld.H/2;
  for(const n of ns){
    n.r+=(n.tr-n.r)*0.12;                      // grow/shrink toward target size
    if(n.dead&&n.r<2){if(n.el.parentNode)n.el.parentNode.removeChild(n.el);fld.nodes.delete(n.key);continue;}
    n.vx+=(cx-n.x)*0.0011;n.vy+=(cy-n.y)*0.0016;   // gentle pull to center
  }
  for(let i=0;i<ns.length;i++)for(let j=i+1;j<ns.length;j++){   // soft collisions
    const a=ns[i],b=ns[j],dx=b.x-a.x,dy=b.y-a.y;
    const dist=Math.sqrt(dx*dx+dy*dy)||0.01,min=a.r+b.r+3;
    if(dist<min){const f=(min-dist)/dist*0.18,fx=dx*f,fy=dy*f;a.vx-=fx;a.vy-=fy;b.vx+=fx;b.vy+=fy;}
  }
  for(const n of ns){
    if(!fld.nodes.has(n.key))continue;
    n.vx*=0.86;n.vy*=0.86;n.x+=n.vx;n.y+=n.vy;
    n.x=Math.max(n.r+2,Math.min(fld.W-n.r-2,n.x));
    n.y=Math.max(n.r+2,Math.min(fld.H-n.r-2,n.y));
    const wx=Math.sin(fld.t*0.9+n.ph)*2.4,wy=Math.cos(fld.t*0.7+n.ph*1.4)*2.2;  // idle bobbing
    n.dx=wx;n.dy=wy;
    n.el.style.width=n.el.style.height=(n.r*2).toFixed(1)+'px';
    n.el.style.left=(n.x-n.r+wx).toFixed(1)+'px';
    n.el.style.top=(n.y-n.r+wy).toFixed(1)+'px';
  }
  drawMesh(ns);
}
// ---- starfield + central glow under the bubbles ----
let meshStars=null;
function drawMesh(ns){
  const cv=document.getElementById('bubmesh');if(!cv)return;
  const dpr=Math.min(window.devicePixelRatio||1,1.75),W=fld.W,H=fld.H;if(!W||!H)return;
  if(cv.width!==Math.round(W*dpr)||cv.height!==Math.round(H*dpr)){cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);cv.style.width=W+'px';cv.style.height=H+'px';meshStars=null;}
  const ctx=cv.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
  const NSTAR=W<520?36:70;
  if(!meshStars||meshStars.length!==NSTAR){meshStars=[];for(let i=0;i<NSTAR;i++)meshStars.push([Math.random()*W,Math.random()*H,Math.random()*1.2+0.3,Math.random()*6.28]);}
  for(const st of meshStars){const tw=0.22+0.18*Math.sin(fld.t*1.3+st[3]);ctx.fillStyle=`rgba(180,200,255,${tw.toFixed(3)})`;ctx.beginPath();ctx.arc(st[0],st[1],st[2],0,6.283);ctx.fill();}
  const cx=W/2,cy=H/2;
  const cg=ctx.createRadialGradient(cx,cy,0,cx,cy,Math.min(W,H)*0.45);
  cg.addColorStop(0,'rgba(140,170,255,0.05)');cg.addColorStop(1,'rgba(140,170,255,0)');
  ctx.fillStyle=cg;ctx.fillRect(0,0,W,H);
}
window.addEventListener('resize',sizeField);window.addEventListener('orientationchange',()=>setTimeout(sizeField,120));
function renderDetail(){const box=$('detail');if(box){box.className='detail';box.innerHTML='';}}
function renderCrash(){
  const cr=st.data.crash_risk,box=$('crashCard');
  if(!cr||cr.score==null){box.innerHTML='<div class="section-title">Crash Risk</div><div class="empty">—</div>';return;}
  const col=cr.level==='Low'?'#5ee08a':cr.level==='Elevated'?'#ffcd6b':cr.level==='High'?'#ff9f6b':'#ff8f9c';
  const comps=(cr.components||[]).map(c=>{const rc=c.risk==='High'?'#ff8f9c':c.risk==='Medium'?'#ffcd6b':'#9fe0b0';return `<div style="display:flex;justify-content:space-between;gap:8px;font-size:11px;padding:2px 0"><span style="color:#cdd6e4">${c.name}</span><span style="color:${rc};font-weight:800">${c.risk}</span></div>`;}).join('');
  box.innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px"><div class="section-title" style="margin:0">Crash Risk <span style="text-transform:none;color:var(--muted)">· daily</span></div><span style="font-weight:800;color:${col}">${cr.level} · ${cr.score}/100</span></div>
    <div class="loadtrack" style="height:8px"><div style="height:100%;width:${cr.score}%;background:${col}"></div></div>
    <div style="margin-top:8px">${comps}</div>
    <div class="disc"><b>If it unwinds:</b> ${cr.scale_note}</div>
    <div class="disc">${cr.timing_note}</div>`;
}
function renderMacro(){
  const mc=st.data.macro;const cls=(mc.label||'Neutral').replace(/[^A-Za-z]/g,'');
  const mcol=(v,g,r)=>v==null?'var(--muted)':(v<=g?'#5ee08a':(v>=r?'#ff8f9c':'#ffcd6b'));
  const cell=(k,v,disp,g,r)=>{const c=mcol(v,g,r);return `<div class="cell" style="border-left:3px solid ${c};background:${v==null?'var(--panel2)':(v<=g?'rgba(22,163,74,.12)':(v>=r?'rgba(220,53,69,.12)':'rgba(245,165,36,.10)'))}"><div class="k">${k}</div><div class="v" style="color:${c}">${disp}</div></div>`;};
  $('macroCard').innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><div class="section-title" style="margin:0">Macro Backdrop</div><span class="regime ${cls}">${mc.label}</span></div>
    <div class="grid2">
      ${cell('10Y Yield',mc.tnx,mc.tnx!=null?mc.tnx.toFixed(2)+'%':'—',3.5,4.5)}
      ${cell('VIX',mc.vix,mc.vix!=null?mc.vix.toFixed(1):'—',16,26)}
      ${cell('CPI YoY',mc.cpi,mc.cpi!=null?mc.cpi.toFixed(1)+'%':'—',2.5,3.5)}
      ${cell('Shiller CAPE',mc.cape,mc.cape!=null?mc.cape.toFixed(0):'—',22,32)}
    </div>
    <div class="disc"><span style="color:#5ee08a">green</span> supportive · <span style="color:#ffcd6b">amber</span> neutral · <span style="color:#ff8f9c">red</span> headwind. ${(mc.drivers||[]).join(' · ')}. CAPE vs ${mc.cape_mean} avg. As of ${mc.as_of}.</div>`;
}
function renderFutures(){
  const f=st.data.futures||{items:[]};
  const cell=i=>`<div class="cell"><div class="k">${i.name}</div><div class="v">${i.price!=null?i.price.toLocaleString():'—'}</div><div style="font-size:10px;color:${(i.chg_pct||0)>=0?'var(--up)':'var(--down)'}">${fmtPct(i.chg_pct)}</div></div>`;
  $('futCard').innerHTML=`<div class="section-title">Futures (live)</div><div class="grid2">${(f.items||[]).map(cell).join('')}</div>
    <div class="disc">Index-futures tilt ${f.bias>=0?'+':''}${(f.bias!=null?f.bias.toFixed(2):'0')} feeds the market bias.</div>`;
}
function renderEvents(){
  const c=st.data.calendar||{events:[]};
  const rows=(c.events||[]).map(e=>{const rc=e.risk==='High'?'#ff8f9c':e.risk==='Medium'?'#ffcd6b':'#9fe0b0';return `<div class="ev"><span class="d">${e.date.slice(5)}</span><span class="n ev${e.kind}">${e.label}</span><span style="font-size:8.5px;font-weight:800;color:${rc};border:1px solid ${rc};border-radius:5px;padding:0 4px;margin:0 5px">${e.risk||''}</span><span class="cd">${e.days===0?'today':e.days+'d'}</span></div>`;}).join('');
  $('evCard').innerHTML=`<div class="section-title">Upcoming Events <span style="text-transform:none;color:var(--muted)">· risk</span></div>${rows||'<div class="empty">—</div>'}
    <div class="disc">${c.event_risk>=0.4?'<span class="warn">⚠ Big event near — signal conviction reduced.</span>':'Risk = market impact × how soon. Conviction auto-reduces 1–2 days before Fed/CPI.'}</div>`;
}
function renderNews(){
  const n=st.data.news||{headlines:[]};
  const risk=n.geo_risk||0;const lbl=risk>=0.66?'High':risk>=0.34?'Elevated':'Low';
  const hl=(n.headlines||[]).slice(0,5).map(h=>`<li>${h.replace(/</g,'&lt;')}</li>`).join('');
  $('newsCard').innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><div class="section-title" style="margin:0">News · War/Geo Risk</div><span class="regchip" style="color:${risk>=0.34?'#ff8f9c':'#9fe0b0'}">${lbl} ${risk.toFixed(2)}</span></div>
    ${hl?`<ul class="news" style="margin:4px 0 0;padding-left:16px">${hl}</ul>`:`<div class="empty">${n.note||'No headlines'}</div>`}
    <div class="disc">Best-effort free feed; nudges the bias risk-off when conflict headlines spike. Not predictive.</div>`;
}
function renderResources(){
  const c=st.data.commodities||{readings:{}};const r=c.readings||{};
  const cell=(k,v)=>`<div class="cell"><div class="k">${k} 1mo</div><div class="v" style="color:${(v||0)>=0?'var(--up)':'var(--down)'}">${v!=null?fmtPct(v):'—'}</div></div>`;
  $('resCard').innerHTML=`<div class="section-title">Resources · Supply/Demand</div>
    <div class="grid2">${cell('Crude',r.crude_1mo)}${cell('Nat Gas',r.natgas_1mo)}${cell('Copper',r.copper_1mo)}${cell('Gold',r.gold_1mo)}</div>
    <div class="disc">${(c.notes||[]).join(' · ')}. Tilts Energy ${c.energy_tilt>=0?'+':''}${c.energy_tilt}, Materials ${c.materials_tilt>=0?'+':''}${c.materials_tilt}.</div>`;
}
function renderLT(){
  const box=$('ltCard');if(!box)return;
  const wl=st.data.watchlist||[];
  const rows=[],avoid=[];
  for(const w of wl){
    const d=w.drift,lv=w.levels,s=w.signal||{};
    if(!d||d.cagr_pct==null)continue;
    if(d.tag==='avoid'){if(w.ticker)avoid.push(w.ticker);continue;}
    const odds=(lv&&lv.lt_up!=null)?lv.lt_up:null;
    const sale=!!(lv&&s.price!=null&&lv.buy!=null&&s.price<=lv.buy);
    const score=Math.min(d.cagr_pct,40)+(odds!=null?(odds-50)*0.8:0)+(s.action==='BUY'?5:0)+(sale?3:0);
    rows.push({w,d,lv,s,odds,sale,score});
  }
  rows.sort((a,b)=>b.score-a.score);
  let h='<div class="section-title">🏛️ Long-Term Buy &amp; Hold — top compounders</div>';
  h+=rows.length?rows.slice(0,8).map((x,i)=>{
    const cagrCol=x.d.cagr_pct>=20?'#7fe0b0':'#e8c06a';
    const oddsTxt=x.odds!=null?`1yr ↑odds <b style="color:${x.odds>=60?'#7fe0b0':'#e8c06a'}">${x.odds}%</b>`:'';
    const buyTxt=(x.lv&&x.lv.buy!=null)?`${oddsTxt?' · ':''}add ≤ <b style="color:#7fe0b0">$${x.lv.buy}</b>`:'';
    const sale=x.sale?' <span style="font-size:9px;font-weight:800;color:#08120b;background:#22c55e;border-radius:5px;padding:1px 5px">ON SALE</span>':'';
    return `<div class="row"><div class="rank">${i+1}</div><div class="l"><div class="sym">${x.w.label} <span style="color:var(--muted);font-weight:600;font-size:10px">${x.w.ticker}</span>${sale}</div><div class="sub">${oddsTxt}${buyTxt}</div></div>
      <div class="px">${fmtPrice(x.s.price)}<br><span style="color:${cagrCol};font-weight:800">${x.d.cagr_pct>=0?'+':''}${x.d.cagr_pct}%/yr</span></div></div>`;
  }).join(''):'<div class="empty">Building long-term history…</div>';
  if(avoid.length)h+=`<div class="disc" style="color:#f0a0a0">Not for holding (negative long-term drift): ${avoid.join(', ')}</div>`;
  h+='<div class="disc">Ranked by ~10-yr CAGR + historical 1-yr up-odds; "add ≤" = the name\'s own typical dip entry. Long-horizon lens — not advice.</div>';
  box.innerHTML=h;
}
function pr(r){return (r||[]).filter(x=>!/^macro|event/.test(x)).slice(0,2).join(' · ');}
function renderPicks(){
  const p=st.data.picks||[];
  let h='<div class="section-title">Top 5 Buy Signals <span style="text-transform:none;color:var(--muted)">· short-term</span></div>';
  h+=p.length?p.map((x,i)=>`<div class="row"><div class="rank">${i+1}</div><div class="l"><div class="sym">${x.symbol} <span style="color:var(--muted);font-weight:600;font-size:10px">${x.sector||''}</span></div><div class="sub">${pr(x.reasons)}</div></div>
     <div class="px">${fmtPrice(x.price)}<br><span style="color:${(x.change_pct||0)>=0?'var(--up)':'var(--down)'}">${fmtPct(x.change_pct)}</span></div>
     <div class="act" style="color:${actColor(x.action)};background:${actBg(x.action)}">${x.action}<small>${x.strength}%</small></div></div>`).join(''):'<div class="empty">—</div>';
  h+='<div class="disc">Highest mechanical score (incl. macro/futures/commodity/event tilt). Not advice.</div>';
  $('picksCard').innerHTML=h;
}
function driftBadge(w){const d=w.drift;if(!d)return '';
  if(d.tag==='avoid')return ` <span style="color:#ff8f9c;font-weight:700;font-size:9px;border:1px solid #6b1c26;border-radius:4px;padding:0 3px" title="Negative long-term drift — buy & hold has lost money">⚠ AVOID·LT ${d.cagr_pct}%/yr</span>`;
  if(d.tag==='strong')return ` <span style="color:#5ee08a;font-weight:700;font-size:9px;border:1px solid #1c6b3a;border-radius:4px;padding:0 3px" title="Strong long-term compounder">★ LT +${d.cagr_pct}%/yr</span>`;
  return '';}
function renderSignals(){
  const _ltRank=w=>{const t=(w.drift||{}).tag;return t==='strong'?0:(t==='long'?1:(t==='avoid'?3:2));};
  const wl=(st.data.watchlist||[]).slice().sort((a,b)=>(_ltRank(a)-_ltRank(b))||((((b.signal||{}).strength)||0)-(((a.signal||{}).strength)||0)));
  const oc=p=>p==null?'var(--muted)':(p>=60?'#7fe0b0':(p>=50?'#e8c06a':'#f0a0a0'));
  let h='<div class="section-title">Signals — Buy / Sell / Hold <span style="text-transform:none;color:var(--muted)">· long-term compounders first</span></div>';
  h+=wl.map(w=>{const s=w.signal||{},t=w.ticker||w.proxy||'';const sub=w.private?('Private · via '+(w.proxy||'')):(w.note||t);const lv=w.levels;
    const px=s.price!=null?`${fmtPrice(s.price)}<br><span style="color:${(s.change_pct||0)>=0?'var(--up)':'var(--down)'}">${fmtPct(s.change_pct)}</span>`:'—';
    const up=lv?lv.up_now:(s.sma_state?s.sma_state==='above':((s.mom1m||0)>=0));
    const stren=s.strength!=null?s.strength:(s.mom1m!=null?Math.min(100,Math.abs(s.mom1m)*8):40);
    const s01=Math.max(0.2,Math.min(1,stren/100));
    const _W=10,_H=16,_c=up?'var(--up)':'var(--down)',_tail=3+s01*9;
    const _line=up?`<line x1="5" y1="4" x2="5" y2="${(4+_tail).toFixed(1)}" stroke="${_c}" stroke-width="1.8" stroke-linecap="round"/>`
                  :`<line x1="5" y1="${(_H-4-_tail).toFixed(1)}" x2="5" y2="${_H-4}" stroke="${_c}" stroke-width="1.8" stroke-linecap="round"/>`;
    const _head=up?`<polygon points="5,0 2,4 8,4" fill="${_c}"/>`:`<polygon points="5,${_H} 2,${_H-4} 8,${_H-4}" fill="${_c}"/>`;
    const arr=`<svg width="${_W}" height="${_H}" viewBox="0 0 ${_W} ${_H}" style="vertical-align:middle;margin-left:5px" title="${up?'Trending up':'Trending down'} — longer tail = stronger trend (strength ${Math.round(stren)})">${_line}${_head}</svg>`;
    const pooled=lv&&(lv.st_basis==='pooled'||lv.lt_basis==='pooled');
    const odds=lv?`<span title="Historical odds the stock was higher 1 month / 1 year later, judged from its current trend state over ~10y${pooled?' — pooled (thin history)':''}">📈 1mo <b style="color:${oc(lv.st_up)}">${lv.st_up}%</b> · 1yr <b style="color:${oc(lv.lt_up)}">${lv.lt_up}%</b> <span style="color:#5a6675">↑odds${pooled?'*':''}</span></span>`:`<span style="color:#5a6675">📈 odds — building history</span>`;
    const lvls=lv?`<span title="Backtested: typical 1-month pullback entry & typical 3-month target, from this name's own ~10y history">🎯 Buy ≤ <b style="color:#7fe0b0">$${lv.buy}</b> · Sell ≥ <b style="color:#e8c06a">$${lv.sell}</b></span>`:'';
    return `<div style="margin-bottom:6px">
      <div class="row" style="margin-bottom:2px"><div class="l"><div class="sym">${w.label} <span style="color:var(--muted);font-weight:600;font-size:10px">${t}</span>${driftBadge(w)}</div><div class="sub">${sub}${ahChip(s)?' · '+ahChip(s):''}</div></div>
        <div class="px">${px}</div><div class="act" style="color:${actColor(s.action)};background:${actBg(s.action)};display:inline-flex;align-items:center;justify-content:center;gap:5px"><span>${s.action||'N/A'}${s.strength?`<small>${s.strength}%</small>`:''}</span>${arr}</div></div>
      <div style="display:flex;justify-content:space-between;gap:8px;font-size:9.5px;padding:0 8px 1px;font-variant-numeric:tabular-nums">${odds}${lvls}</div>
    </div>`;}).join('');
  h+='<div class="disc">▲/▼ = current price trend (above/below its 50-day). 📈 <b>↑odds</b> = historical chance the stock was higher 1mo / 1yr later from this same trend state (1yr reads high — 2008–26 was mostly a bull market, so weigh it against the ~70% base). 🎯 <b>Buy/Sell</b> = its own typical 1-month dip entry &amp; 3-month target. <small>*pooled = thin history, uses watchlist average.</small> Mechanical &amp; backtested — not advice.</div>';
  $('sigCard').innerHTML=h;
}
function renderUnusual(){
  const u=st.data.unusual||[];
  let h='<div class="section-title">⚡ Unusual Activity</div>';
  h+=u.length?u.slice(0,12).map(x=>{const up=x.change_pct>=0;
      const vol=x.reasons.includes('volume')?`<span class="tag" style="background:${up?'rgba(22,163,74,.2)':'rgba(220,53,69,.2)'};color:${up?'#5ee08a':'#ff8f9c'};border:1px solid ${up?'#1c6b3a':'#6b1c26'}">VOL ${fmtRvol(x.rvol)} ${up?'↑buy':'↓sell'}</span>`:'';
      const tags=(x.is_etf?'<span class="tag etf">ETF</span>':'')+vol+(x.reasons.includes('price')?'<span class="tag p">±</span>':'');
    return `<div class="row" data-sector="${x.sector}" style="cursor:pointer"><div class="l"><div class="sym">${x.symbol} ${tags}</div><div class="sub">${x.sector}</div></div>
      <div class="px" style="color:${up?'var(--up)':'var(--down)'}">${arrow(x.change_pct)} ${fmtPct(x.change_pct)}<br><span style="color:var(--muted)">${fmtPrice(x.price)}</span></div></div>`;}).join(''):'<div class="empty">Nothing unusual yet.</div>';
  h+='<div class="disc">Volume tag is <span style="color:#5ee08a">green = buying</span> (price up that day) or <span style="color:#ff8f9c">red = selling</span> (price down).</div>';
  $('unuCard').innerHTML=h;
}

// ---- shared chart helpers for the simulators ----
function expandChart(btn){
  const host=btn.closest('.chartbox')||btn.parentElement;
  const svg=host&&host.querySelector('svg');if(!svg)return;
  const code=svg.outerHTML
    .replace(/ on[a-z]+="[^"]*"/g,'')
    .replace(/id="([^"]*)"/g,'id="zz_$1"')
    .replace(/url\(#([^)]*)\)/g,'url(#zz_$1)')
    .replace(/style="[^"]*"/,'style="width:100%;height:auto;max-height:86vh"');
  const ov=document.createElement('div');
  ov.className='chartmodal';
  ov.onclick=()=>ov.remove();
  ov.innerHTML='<div class="chartmodal-inner">'+code+'<div class="chartmodal-hint">tap anywhere to close</div></div>';
  document.body.appendChild(ov);
}
function chartSVG(eq,bm,trades,dates,zoom,stratCol,id,ref){
  const n=eq.length,W=760,H=id?230:250,padL=48,padR=10,padTop=12,padBot=24;
  const hasRef=ref&&ref.length===n;
  const all=hasRef?eq.concat(bm,ref):eq.concat(bm),lo=Math.max(1,Math.min(...all)),hi=Math.max(...all);
  const llo=Math.log(lo),lhi=Math.log(hi),lrng=(lhi-llo)||1;
  const xs=i=>padL+(i/Math.max(1,n-1))*(W-padL-padR), ys=v=>H-padBot-((Math.log(Math.max(1,v))-llo)/lrng)*(H-padTop-padBot);
  if(!id){st.simScale={llo,lrng,W,H,padL,padR,padTop,padBot,n};}else{st.scales=st.scales||{};st.scales[id]={llo,lrng,W,H,padL,padR,padTop,padBot,n};}
  const line=arr=>arr.map((v,i)=>xs(i).toFixed(1)+','+ys(v).toFixed(1)).join(' ');
  const uid=id||'eq';
  const defs=`<defs><linearGradient id="${uid}_grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${stratCol}" stop-opacity="0.30"/><stop offset="55%" stop-color="${stratCol}" stop-opacity="0.08"/><stop offset="100%" stop-color="${stratCol}" stop-opacity="0"/></linearGradient></defs>`;
  const area=`<polygon fill="url(#${uid}_grad)" stroke="none" points="${line(eq)} ${xs(n-1).toFixed(1)},${(H-padBot).toFixed(1)} ${xs(0).toFixed(1)},${(H-padBot).toFixed(1)}"/>`;
  let yaxis='';for(let k=0;k<=4;k++){const v=Math.exp(llo+(lhi-llo)*k/4),y=ys(v).toFixed(1);yaxis+=`<line x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}" stroke="#1e2942" stroke-width="1" stroke-dasharray="3 5" opacity="0.7"/><text x="${padL-5}" y="${(+y+3).toFixed(1)}" text-anchor="end" font-size="9" fill="#8a97ad">$${v>=1000?(v/1000).toFixed(v>=10000?0:1)+'k':v.toFixed(0)}</text>`;}
  let xaxis='';const xc=Math.min(5,Math.max(1,n-1));for(let k=0;k<=xc;k++){const i=Math.round(k/xc*(n-1)),x=xs(i).toFixed(1);xaxis+=`<text x="${x}" y="${H-7}" text-anchor="middle" font-size="9" fill="#8a97ad">${['1y','2y','6m','3m','ytd'].includes(zoom)?dates[i].slice(0,7):dates[i].slice(0,4)}</text>`;}
  const marks=trades.map((t,i)=>{let o='';if(t.entered&&t.entered.length)o+=`<circle cx="${xs(i).toFixed(1)}" cy="${ys(eq[i]).toFixed(1)}" r="${id?2.8:2.4}" fill="#22c55e" stroke="#0c1220" stroke-width="1"/>`;if(t.exited&&t.exited.length)o+=`<circle cx="${xs(i).toFixed(1)}" cy="${ys(eq[i]).toFixed(1)}" r="${id?2.8:1.8}" fill="#ef4444" stroke="#0c1220" stroke-width="1"/>`;return o;}).join('');
  const hover=(id?` id="${id}_svg" onmousemove="chartHover(event,'${id}')" onmouseleave="chartLeave('${id}')"`:' id="eqsvg" onmousemove="simHover(event)" onmouseleave="simLeave()"')
    +` ontouchstart="chartTouch(event,'${id||''}')" ontouchmove="chartTouch(event,'${id||''}')" ontouchend="chartTouchEnd(event,'${id||''}')" ontouchcancel="chartTouchEnd(event,'${id||''}')"`;
  const extra=`<line id="${id?id+'_guide':'eqguide'}" x1="0" y1="${padTop}" x2="0" y2="${H-padBot}" stroke="#f5a524" stroke-width="1" stroke-dasharray="2 3" style="display:none"/><circle id="${id?id+'_dot':'eqdot'}" r="4" fill="#fff" stroke="${stratCol}" stroke-width="2" style="display:none"/><line id="${id?id+'_guide2':'eqguide2'}" x1="0" y1="${padTop}" x2="0" y2="${H-padBot}" stroke="#f5a524" stroke-width="1" stroke-dasharray="2 3" style="display:none"/><circle id="${id?id+'_dot2':'eqdot2'}" r="4" fill="#fff" stroke="${stratCol}" stroke-width="2" style="display:none"/>`;
  const glow=`<polyline fill="none" stroke="${stratCol}" stroke-width="6" opacity="0.16" stroke-linejoin="round" stroke-linecap="round" points="${line(eq)}"/>`;
  return `<svg class="eq"${hover} viewBox="0 0 ${W} ${H}" style="${id?'height:230px':''}">${defs}${yaxis}${xaxis}${area}${hasRef?`<polyline fill="none" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="5 3" opacity="0.85" stroke-linejoin="round" points="${line(ref)}"/>`:''}<polyline fill="none" stroke="#5a6675" stroke-width="1.6" opacity="0.9" stroke-linejoin="round" points="${line(bm)}"/>${glow}<polyline fill="none" stroke="${stratCol}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" points="${line(eq)}"/>${marks}${extra}</svg><div class="zoombtn" onclick="expandChart(this)" title="Enlarge">⛶</div>`;
}
function windowStats(eq,bm,dates){
  const n=eq.length,wStart=eq[0],wEnd=eq[n-1],bStart=bm[0],bEnd=bm[n-1];
  const wYrs=Math.max(1e-6,(new Date(dates[n-1])-new Date(dates[0]))/(365.25*864e5));
  let pk=eq[0],wMdd=0;eq.forEach(v=>{pk=Math.max(pk,v);wMdd=Math.min(wMdd,v/pk-1);});
  return {wEnd,bEnd,wYrs,wRet:(wEnd/wStart-1)*100,wBRet:(bEnd/bStart-1)*100,wProfit:wEnd-wStart,wBProfit:bEnd-bStart,
    wCagr:(Math.pow(wEnd/wStart,1/wYrs)-1)*100,wBCagr:(Math.pow(bEnd/bStart,1/wYrs)-1)*100,wMdd:wMdd*100};
}
function zoomCut(dates,zoom){
  const fullN=dates.length;let i0=0;
  if(zoom!=='max'){const last=new Date(dates[fullN-1]);const cut=new Date(last);if(zoom==='ytd'){cut.setMonth(0,1);}else{const mo={'3m':3,'6m':6}[zoom];if(mo){cut.setMonth(cut.getMonth()-mo);}else{const yrs={'1y':1,'2y':2,'3y':3,'5y':5,'10y':10}[zoom]||1;cut.setFullYear(cut.getFullYear()-yrs);}}i0=dates.findIndex(d=>new Date(d)>=cut);if(i0<0)i0=0;}
  return i0;
}
function sliceByZoom(sim,zoom){const i0=zoomCut(sim.dates,zoom);
  return {dates:sim.dates.slice(i0),eq:sim.equity.slice(i0),bm:sim.benchmark_equity.slice(i0),trades:sim.trades.slice(i0)};
}
// Window-aware stats for the VOO buy-the-dip sim. Anchors the window's opening balance/contributions
// at the point just before i0 so every figure reduces EXACTLY to the full-period stat at MAX zoom.
function vooWindowStats(vs,zoom){
  const i0=zoomCut(vs.dates,zoom),last=vs.dates.length-1;
  const eqB=i0>0?vs.equity[i0-1]:0,bmB=i0>0?vs.benchmark_equity[i0-1]:0;
  const invB=i0>0?vs.invested[i0-1]:0,shB=i0>0?vs.shares[i0-1]:0;
  const invWin=vs.invested[last]-invB,shWin=vs.shares[last]-shB;
  const gain=vs.equity[last]-eqB-invWin,bGain=vs.benchmark_equity[last]-bmB-invWin;
  const cap=eqB+invWin,bCap=bmB+invWin;
  const roi=cap>0?gain/cap*100:0,bRoi=bCap>0?bGain/bCap*100:0;
  const vRet=vs.price[i0]>0?(vs.price[last]/vs.price[i0]-1)*100:0;
  let pk=vs.price[i0],dd=0;for(let k=i0;k<=last;k++){pk=Math.max(pk,vs.price[k]);dd=Math.min(dd,vs.price[k]/pk-1);}
  const mos=Math.max(1,(new Date(vs.dates[last])-new Date(vs.dates[i0]))/(30.44*864e5));
  return {valueEnd:vs.equity[last],benchEnd:vs.benchmark_equity[last],invWin,shWin,gain,vsLump:gain-bGain,
    roi,bRoi,vRet,ddPct:dd*100,years:(new Date(vs.dates[last])-new Date(vs.dates[i0]))/(365.25*864e5),dipsPerMo:shWin/mos};
}

function setZoom(z){st.simZoom=z;renderSim();}
function renderSim(){
  const sim=st.data&&st.data.sim,box=$('simPanel');
  if(!sim||!sim.dates||!sim.dates.length){box.innerHTML='<div class="section-title">Strategy Simulator</div><div class="empty">Warming up…</div>';return;}
  const meta=sim.meta||{},s=sim.stats||{},zoom=st.simZoom||'max';
  const v=sliceByZoom(sim,zoom);st.simView=v;const {dates,eq,bm,trades}=v,n=eq.length;
  const nl=(sim.neutral_equity&&sim.neutral_equity.length===sim.dates.length)?sim.neutral_equity.slice(zoomCut(sim.dates,zoom)):null;
  const w=windowStats(eq,bm,dates);
  const stratCol=w.wRet>=w.wBRet?'#16a34a':'#f5a524';
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setZoom('${z}')">${z.toUpperCase()}</span>`;
  const sug=(sim.suggestion||[]).length?'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:2px 0 10px;align-items:center"><span style="font-size:11px;color:var(--muted);font-weight:700">NEXT-YEAR IDEAS:</span>'+sim.suggestion.map(x=>`<span style="font-size:11.5px;padding:4px 9px;border-radius:8px;border:1px solid ${actColor(x.action)};background:${actBg(x.action)}"><b style="color:${actColor(x.action)}">${x.action} ${x.symbol}</b> · ${x.confidence}% · ~$${x.price}<br><span style="color:var(--muted);font-size:9.5px">${x.reason||''}</span></span>`).join('')+'</div>':'';
  const cb=meta.confidence_basis;
  const cbNote=cb?`<div class="disc"><b>How confidence works:</b> historical chance the call was right over ${cb.horizon} — a stock in an uptrend was higher a year later <b>${cb.p_up_given_uptrend}%</b> of the time (vs <b>${cb.p_up_unconditional}%</b> for any stock). Not a probability of profit.</div>`:'';
  const trs=trades.slice().reverse().slice(0,12).map(t=>`<tr><td>${t.date}</td><td style="color:${t.ret_pct>=0?'var(--up)':'var(--down)'}">${t.ret_pct>=0?'+':''}${t.ret_pct.toFixed(2)}%</td><td style="color:#9fe0b0">${(t.entered||[]).join(', ')||'—'}</td><td style="color:#ff9f9f">${(t.exited||[]).join(', ')||'—'}</td></tr>`).join('');
  const sgB=(sim.suggestion||[]).filter(x=>toneOf(x.action)==='buy');const dn=doNext(sgB.length?`<b>At the next open, buy:</b> ${sgB.slice(0,5).map(x=>x.symbol+' ('+x.confidence+'%)').join(', ')} <span style="color:var(--muted);font-weight:400">then sell into the close — mechanical, daily</span>`:`<b>Hold / stay in cash</b> — no fresh buy signals flagged for the next session.`, sgB.length?'buy':'hold');
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">Strategy Simulator — $${(meta.start_capital||5000).toLocaleString()} self-test</div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('6m')}${zbt('ytd')}${zbt('1y')}${zbt('5y')}${zbt('10y')}${zbt('max')}</div></div>
    <div class="sub">${meta.strategy||''} 🟢 added / 🔴 removed. Showing ${dates[0]} → ${dates[n-1]} (${w.wYrs.toFixed(1)}y window, log scale). Stats reflect the selected window.</div>
    ${sug}
    <div class="simgrid">
      <div class="chartbox">${chartSVG(eq,bm,trades,dates,zoom,stratCol,'',nl||undefined)}
        <div id="eqtip"></div>
        <div class="lgd"><span><i style="background:${stratCol}"></i>Strategy after-tax & slippage ${fmtMoney(w.wEnd)} (${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%)</span>
          ${nl?`<span><i style="background:#38bdf8"></i>Same rule, 9 sector ETFs (no stock-picking) ${fmtMoney(nl[nl.length-1])}</span>`:''}
          <span><i style="background:#5a6675"></i>S&P 500 (never sold) ${fmtMoney(w.bEnd)} (${w.wBRet>=0?'+':''}${w.wBRet.toFixed(1)}%)</span></div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">Profit (after tax)</div><div class="v" style="color:${w.wProfit>=0?'var(--up)':'var(--down)'}">${money(w.wProfit)}</div></div>
        <div class="stat"><div class="k">vs S&P P/L</div><div class="v" style="color:${w.wBProfit>=0?'var(--up)':'var(--down)'}">${money(w.wBProfit)}</div></div>
        <div class="stat"><div class="k">CAGR</div><div class="v">${w.wCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">vs S&P CAGR</div><div class="v">${w.wBCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${w.wMdd.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Window</div><div class="v">${w.wYrs.toFixed(1)}y</div></div>
      </div>
    </div>
    <table class="tr"><thead><tr><th>Date</th><th>P/L</th><th>🟢 Bought</th><th>🔴 Sold off</th></tr></thead><tbody>${trs}</tbody></table>
    ${cbNote}
    ${meta.hindsight_note?`<div class="disc"><b style="color:var(--down)">Hindsight warning:</b> ${meta.hindsight_note}${s.neutral_return_pct!=null?` Over the full backtest the neutral-universe line made <b>${s.neutral_return_pct>=0?'+':''}${s.neutral_return_pct.toFixed(0)}%</b> vs the stock-picked <b>${s.total_return_pct>=0?'+':''}${(s.total_return_pct||0).toFixed(0)}%</b> and the S&P's <b>${s.benchmark_return_pct>=0?'+':''}${(s.benchmark_return_pct||0).toFixed(0)}%</b>.`:''}</div>`:''}
    <div class="disc">Mechanical backtest — not advice; past results don't predict the future.</div>`;
}

function setVooZoom(z){st.vooZoom=z;renderVooSim();}
function renderVooSim(){
  const vs=st.data&&st.data.voo_sim,box=$('vooPanel');
  if(!vs||!vs.dates||!vs.dates.length){box.innerHTML='<div class="section-title">Buy-the-Dip (VOO)</div><div class="empty">Warming up…</div>';return;}
  const meta=vs.meta||{},s=vs.stats||{},zoom=st.vooZoom||'max';
  const v=sliceByZoom(vs,zoom);st.views=st.views||{};st.views.voo=v;const {dates,eq,bm,trades}=v,n=eq.length;
  const W=(vs.price&&vs.shares&&vs.invested)?vooWindowStats(vs,zoom):null;
  const lump=W?W.vsLump:(s.value-s.benchmark_equity);
  const stratCol=lump>=0?'#16a34a':'#f5a524';
  const val=W?W.valueEnd:s.value,bval=W?W.benchEnd:s.benchmark_equity,roi=W?W.roi:s.roi_pct,broi=W?W.bRoi:s.benchmark_roi_pct;
  const inv=W?W.invWin:s.invested,prof=W?W.gain:s.profit,vret=W?W.vRet:null;
  const dd=W?W.ddPct:s.voo_drawdown_pct,yrs=W?W.years:s.years,buysW=W?W.shWin:s.shares,cad=W?W.dipsPerMo:s.avg_dips_per_month;
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setVooZoom('${z}')">${z.toUpperCase()}</span>`;
  const rec=(vs.recommendation||[]).map(r=>{const ac=r.action.indexOf('BUY')>=0?'var(--buy)':(r.action.indexOf('WAIT')>=0?'var(--hold)':'var(--accent)');
    return `<div style="flex:1;min-width:155px;background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:8px 10px;border-left:3px solid ${ac}"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px">${r.horizon}</div><div style="font-weight:800;color:${ac};font-size:13px;margin:2px 0">${r.action} · $${r.price}</div><div style="font-size:10px;color:var(--muted);line-height:1.35">${r.note}</div></div>`;}).join('');
  const dn=recNext(vs.recommendation);
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">Buy-the-Dip (VOO) — 1 share every ${meta.dip_pct||2}% drop</div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('6m')}${zbt('ytd')}${zbt('1y')}${zbt('5y')}${zbt('10y')}${zbt('max')}</div></div>
    <div class="sub">${meta.strategy||''} Showing ${dates[0]} → ${dates[n-1]} (${(+yrs).toFixed(1)}y window): ${buysW} buys (~${(+cad).toFixed(1)}/mo). 🟢 = a dip-buy. Stats reflect the selected window.</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:11px">${rec}</div>
    <div class="simgrid">
      <div class="chartbox">${chartSVG(eq,bm,trades,dates,zoom,stratCol,'voo')}
        <div id="voo_tip"></div>
        <div class="lgd"><span><i style="background:${stratCol}"></i>Buy-the-dip ${fmtMoney(val)} (ROI ${roi>=0?'+':''}${(+roi).toFixed(1)}%)</span>
          <span><i style="background:#5a6675"></i>Same $, lump at year-start ${fmtMoney(bval)} (ROI ${broi>=0?'+':''}${(+broi).toFixed(1)}%)</span></div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">VOO return (window)</div><div class="v" style="color:${(vret==null?0:vret)>=0?'var(--up)':'var(--down)'}">${vret==null?'—':(vret>=0?'+':'')+vret.toFixed(1)+'%'}</div></div>
        <div class="stat"><div class="k">Invested (window)</div><div class="v">${fmtMoney(inv)}</div></div>
        <div class="stat"><div class="k">Gain net of buys</div><div class="v" style="color:${prof>=0?'var(--up)':'var(--down)'}">${money(prof)}</div></div>
        <div class="stat"><div class="k">vs lump-sum</div><div class="v" style="color:${lump>=0?'var(--up)':'var(--down)'}">${money(lump)}</div></div>
        <div class="stat"><div class="k">ROI (window)</div><div class="v">${(+roi).toFixed(1)}%</div></div>
        <div class="stat"><div class="k">VOO drawdown</div><div class="v" style="color:var(--down)">${(+dd).toFixed(1)}%</div></div>
      </div>
    </div>
    <div class="disc">Both lines deploy the same dollars in the visible window — the dip line spreads them onto ${meta.dip_pct||2}% down-days, the benchmark invests up front. "Gain net of buys" strips out the cash you added, so it's the real growth of the holdings; "vs lump-sum" is how much dip-timing beat (or trailed) deploying the same dollars at the start. Not advice.</div>`;
}

function setConfZoom(z){st.confZoom=z;renderConfSim();}
function renderConfSim(){
  const cs=st.data&&st.data.watchlist_sim,box=$('confPanel');
  if(!cs||!cs.dates||!cs.dates.length){box.innerHTML='<div class="section-title">🎯 Watchlist Confidence Backtest — predicted vs actual</div><div class="empty">Warming up… (first build fetches ~3y of history)</div>';return;}
  const meta=cs.meta||{},s=cs.stats||{},cal=cs.calibration||{},zoom=st.confZoom||'max';
  const v=sliceByZoom(cs,zoom);st.views=st.views||{};st.views.conf=v;const {dates,eq,bm,trades}=v,n=eq.length;
  const ref=(cs.perfect_equity||[]).slice(zoomCut(cs.dates,zoom));
  const w=windowStats(eq,bm,dates);
  const stratCol=w.wRet>=w.wBRet?'#16a34a':'#f5a524';
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setConfZoom('${z}')">${z.toUpperCase()}</span>`;
  const basket=(meta.current_basket||[]);
  const chips=basket.slice(0,10).map(b=>`<span style="font-size:11px;padding:4px 9px;border-radius:8px;border:1px solid var(--buy);background:rgba(22,163,74,.14)"><b>${b.symbol}</b> <span style="color:var(--muted)">${b.weight_pct}%</span> · <span style="color:#9fe0b0">raw ${b.confidence}% → <b>cal ${b.calibrated!=null?b.calibrated+'%':'—'}</b></span></span>`).join('');
  const basketBlock=basket.length?`<div style="margin:2px 0 6px;font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Today's basket — ${basket.length} names, sized by CALIBRATED edge (acting 1 day after the signal). raw = signal strength · cal = what that strength has actually been worth</div><div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">${chips}</div>`:`<div class="sub">No name has a positive calibrated edge right now — the strategy would be sitting in cash today.</div>`;
  const life=`<div style="display:flex;flex-wrap:wrap;gap:7px;margin:8px 0 4px">
    ${lifeChip('$5k →',fmtMoney(s.value),'a computer '+fmtMoney(s.perfect_value),s.value>=s.benchmark_value)}
    ${lifeChip('CAGR',s.cagr_pct+'%','S&P '+s.benchmark_cagr_pct+'%',s.cagr_pct>=s.benchmark_cagr_pct)}
    ${lifeChip('Total return',fmtPctInt(s.total_return_pct),'S&P '+fmtPctInt(s.benchmark_total_pct),s.total_return_pct>=s.benchmark_total_pct)}
    ${lifeChip('Cost of 1-day wait','−'+Math.round(s.realism_drag_pct||0)+' pts','vs instant computer',false)}
    ${lifeChip('Worst drawdown',s.max_drawdown_pct+'%','S&P '+s.benchmark_dd_pct+'%',s.max_drawdown_pct>=s.benchmark_dd_pct)}
    ${lifeChip('Sharpe',s.sharpe,'S&P '+s.benchmark_sharpe,s.sharpe>=s.benchmark_sharpe)}
  </div>`;
  const bands=(cal.bands||[]);const maxHit=Math.max(62,...bands.map(b=>b.hit_rate||0));
  const calRows=bands.map(b=>{const hr=b.hit_rate==null?'—':b.hit_rate+'%';const av=b.avg_fwd_pct==null?'—':(b.avg_fwd_pct>=0?'+':'')+b.avg_fwd_pct+'%';const barW=b.hit_rate?Math.max(2,Math.round((b.hit_rate-50)/(maxHit-50)*100)):0;return `<tr><td style="white-space:nowrap">${b.band}</td><td style="color:var(--muted)">${(b.n||0).toLocaleString()}</td><td><div style="display:flex;align-items:center;gap:6px"><div style="flex:1;min-width:60px;height:8px;background:var(--panel2);border-radius:4px;overflow:hidden"><div style="width:${barW}%;height:100%;background:${(b.hit_rate||0)>=55?'var(--up)':'var(--hold)'}"></div></div><b>${hr}</b></div></td><td style="color:${(b.avg_fwd_pct||0)>=0?'var(--up)':'var(--down)'}">${av}</td></tr>`;}).join('');
  const ov=cal.overall||{};
  const calBlock=bands.length?`<div style="margin-top:10px"><div style="font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">WHAT THE MODEL HAS LEARNED — raw confidence vs the win-rate it ACTUALLY delivered, applied walk-forward to size every trade (graded ${ov.horizon_days||10}d after a ${ov.exec_lag||1}-day wait, over ${s.years}y · bar = edge over a 50/50 coin-flip)</div>
    <table class="tr"><thead><tr><th>Confidence band</th><th>Calls</th><th>Actual hit rate</th><th>Avg move</th></tr></thead><tbody>${calRows}</tbody>
    <tfoot><tr style="border-top:1px solid var(--line)"><td><b>All BUYs</b></td><td style="color:var(--muted)">${(ov.n||0).toLocaleString()}</td><td><b>${ov.hit_rate==null?'—':ov.hit_rate+'%'}</b></td><td style="color:${(ov.avg_fwd_pct||0)>=0?'var(--up)':'var(--down)'}">${ov.avg_fwd_pct==null?'—':(ov.avg_fwd_pct>=0?'+':'')+ov.avg_fwd_pct+'%'}</td></tr></tfoot></table></div>`:'';
  const bkN=(cs.meta&&cs.meta.current_basket)||[];const dn=doNext(bkN.length?`<b>Buy / hold the calibrated basket:</b> ${bkN.slice(0,6).map(x=>x.symbol+' '+x.weight_pct+'%').join(', ')}${bkN.length>6?' +'+(bkN.length-6)+' more':''} <span style="color:var(--muted);font-weight:400">— enter 1 trading day after the signal, sized by calibrated edge</span>`:`<b>Sit in cash today</b> — no watchlist name has a positive calibrated edge right now.`, bkN.length?'buy':'hold');
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">🎯 Watchlist Confidence Backtest — predicted vs actual</div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('3m')}${zbt('6m')}${zbt('ytd')}${zbt('1y')}${zbt('2y')}${zbt('max')}</div></div>
    <div class="sub">${meta.strategy||''} Showing ${dates[0]} → ${dates[n-1]} (${w.wYrs.toFixed(1)}y window, log scale). Stats reflect the selected window.</div>
    ${basketBlock}
    ${life}
    <div class="simgrid">
      <div class="chartbox">${chartSVG(eq,bm,trades,dates,zoom,stratCol,'conf',ref)}
        <div id="conf_tip"></div>
        <div class="lgd"><span><i style="background:${stratCol}"></i>Realistic — 1-day lag + calibrated ${fmtMoney(w.wEnd)} (${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%)</span>
          <span><i style="background:#38bdf8"></i>Perfect (instant computer) ${fmtMoney(ref&&ref.length?ref[ref.length-1]:s.perfect_value)}</span>
          <span><i style="background:#5a6675"></i>S&P 500 (actual) ${fmtMoney(w.bEnd)} (${w.wBRet>=0?'+':''}${w.wBRet.toFixed(1)}%)</span></div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">Return (window)</div><div class="v" style="color:${w.wRet>=0?'var(--up)':'var(--down)'}">${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">vs S&P (window)</div><div class="v" style="color:${(w.wRet-w.wBRet)>=0?'var(--up)':'var(--down)'}">${(w.wRet-w.wBRet)>=0?'+':''}${(w.wRet-w.wBRet).toFixed(1)}%</div></div>
        <div class="stat"><div class="k">CAGR</div><div class="v">${w.wCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Avg names held</div><div class="v">${s.avg_names}</div></div>
        <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${w.wMdd.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">In-market</div><div class="v">${s.exposure_pct}%</div></div>
      </div>
    </div>
    ${calBlock}
    ${meta.hindsight_note?`<div class="disc"><b style="color:var(--down)">Hindsight warning:</b> ${meta.hindsight_note}</div>`:''}
    <div class="disc"><b>Read this honestly:</b> the <b>solid</b> line waits a full trading day before acting — you're not the <b>dashed "perfect" computer</b> that trades the signal's own close — sizes each position by its <b>walk-forward calibrated</b> win-probability, learned only from outcomes already known at that date, so it sharpens as the record grows (that's the "${s.calib_events?s.calib_events.toLocaleString():''} graded calls" behind the table), and pays <b>${meta.slippage_bps||10} bps slippage</b> on every dollar it reweights${s.slippage_paid?` (~${fmtMoney(s.slippage_paid)} paid over the backtest)`:''}. The 1-day wait alone costs about ${Math.round(s.realism_drag_pct||0)} points of total return. The gap to the S&P is still inflated by <b>survivorship</b> (the watchlist is today's hand-picked winners) and untaxed gains. The honest core: raw confidence is only signal <i>strength</i> — its real hit-rate tops out near 60%, which is exactly why the sizing now leans on calibrated edge, not the raw %. Information only — not financial advice; past results don't predict the future.</div>`;
}
function setFvZoom(z){st.fvZoom=z;renderForever();}
function renderForever(){
  const fh=st.data&&st.data.forever_hold,box=$('foreverPanel');if(!box)return;
  if(!fh||!fh.dates||!fh.dates.length){box.innerHTML=`<div class="section-title">💎 Buy & Hold Forever — watchlist's durable names, never timed</div><div class="empty">${(fh&&fh.meta&&fh.meta.note)||'Warming up… (first build fetches full history)'}</div>`;return;}
  const meta=fh.meta||{},s=fh.stats||{},zoom=st.fvZoom||'max';
  const i0=zoomCut(fh.dates,zoom);
  const dates=fh.dates.slice(i0);
  const eqd=fh.equity.slice(i0),eqr=fh.equity_rebal.slice(i0),bm=fh.benchmark_equity.slice(i0),trades=fh.trades.slice(i0);
  const dcav=fh.dca_value.slice(i0),dcar=fh.dca_value_rebal.slice(i0),dcab=fh.dca_benchmark.slice(i0);
  st.views=st.views||{};
  st.views.fvLump={dates,eq:eqd,bm,trades,ref:eqr};
  st.views.fvDca={dates,eq:dcav,bm:dcab,trades:[],ref:dcar};
  const lumpCol=s.value>=s.benchmark_value?'#16a34a':'#f5a524';
  const dcaCol=s.dca_value>=s.dca_benchmark_value?'#16a34a':'#f5a524';
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setFvZoom('${z}')">${z.toUpperCase()}</span>`;
  const basket=(meta.current_basket||[]);
  const chips=basket.map(b=>`<span style="font-size:11px;padding:3px 8px;border-radius:8px;border:1px solid var(--line);background:var(--panel2)"><b>${b.symbol}</b></span>`).join('');
  const tgt=basket.length?(100/basket.length).toFixed(1):'';
  const basketBlock=`<div style="margin:2px 0 6px;font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">The basket — ${basket.length} durable names, bought equal weight (${tgt}% each) and held</div><div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px">${chips}</div>`;
  const lump=`<div style="font-size:11.5px;font-weight:800;margin:10px 0 3px">💵 Lump sum — $${(meta.base||5000).toLocaleString()} invested once, ${s.years}y ago</div>
    <div style="display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 4px">
    ${lifeChip('Buy & hold (drift)',fmtMoney(s.value),fmtPctInt(s.total_return_pct)+' · CAGR '+s.cagr_pct+'%',s.value>=s.benchmark_value)}
    ${lifeChip('Annual rebalance',fmtMoney(s.value_rebal),fmtPctInt(s.total_return_rebal_pct)+' · CAGR '+s.cagr_rebal_pct+'%',s.value_rebal>=s.benchmark_value)}
    ${lifeChip('S&P 500 ($5k held)',fmtMoney(s.benchmark_value),fmtPctInt(s.benchmark_total_pct)+' · CAGR '+s.benchmark_cagr_pct+'%',true)}
    ${lifeChip('Worst drop — drift',s.max_drawdown_pct+'%','rebalanced '+s.max_drawdown_rebal_pct+'%',s.max_drawdown_pct>=s.benchmark_dd_pct)}
    ${lifeChip('Beat S&P',s.years_beat+'/'+s.years_total+' yrs','drift · calendar years',s.years_beat*2>=s.years_total)}
    </div>`;
  const lumpChart=`<div class="simgrid"><div class="chartbox">${chartSVG(eqd,bm,trades,dates,zoom,lumpCol,'fvLump',eqr)}
      <div id="fvLump_tip"></div>
      <div class="lgd"><span><i style="background:${lumpCol}"></i>Buy &amp; hold (drift) ${fmtMoney(eqd[eqd.length-1])}</span>
        <span><i style="background:#38bdf8"></i>Annual rebalance ${fmtMoney(eqr[eqr.length-1])}</span>
        <span><i style="background:#5a6675"></i>S&amp;P 500 ${fmtMoney(bm[bm.length-1])}</span></div></div>
    <div class="stats">
      <div class="stat"><div class="k">Drift vs S&amp;P</div><div class="v" style="color:${s.alpha_pct>=0?'var(--up)':'var(--down)'}">${fmtPctInt(s.alpha_pct)}</div></div>
      <div class="stat"><div class="k">CAGR (drift)</div><div class="v">${s.cagr_pct}%</div></div>
      <div class="stat"><div class="k">Sharpe</div><div class="v">${s.sharpe}</div></div>
      <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${s.max_drawdown_pct}%</div></div>
    </div></div>`;
  const dca=`<div style="font-size:11.5px;font-weight:800;margin:14px 0 3px">📆 Dollar-cost averaging — $${(meta.dca_monthly||250).toLocaleString()}/mo, $${(s.dca_contributed||0).toLocaleString()} put in over ${s.years}y</div>
    <div style="display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 4px">
    ${lifeChip('Buy & hold (drift)',fmtMoney(s.dca_value),(s.dca_mwr_pct!=null?s.dca_mwr_pct+'%/yr money-wtd':''),s.dca_value>=s.dca_benchmark_value)}
    ${lifeChip('Annual rebalance',fmtMoney(s.dca_value_rebal),(s.dca_mwr_rebal_pct!=null?s.dca_mwr_rebal_pct+'%/yr money-wtd':''),s.dca_value_rebal>=s.dca_benchmark_value)}
    ${lifeChip('Same into S&P 500',fmtMoney(s.dca_benchmark_value),(s.dca_benchmark_mwr_pct!=null?s.dca_benchmark_mwr_pct+'%/yr money-wtd':''),true)}
    ${lifeChip('Total contributed',fmtMoney(s.dca_contributed),'$'+(meta.dca_monthly||250)+'/mo · cost basis',true)}
    </div>`;
  const dcaChart=`<div class="simgrid"><div class="chartbox">${chartSVG(dcav,dcab,[],dates,zoom,dcaCol,'fvDca',dcar)}
      <div id="fvDca_tip"></div>
      <div class="lgd"><span><i style="background:${dcaCol}"></i>Basket (drift) ${fmtMoney(dcav[dcav.length-1])}</span>
        <span><i style="background:#38bdf8"></i>Annual rebalance ${fmtMoney(dcar[dcar.length-1])}</span>
        <span><i style="background:#5a6675"></i>S&amp;P 500 (same schedule) ${fmtMoney(dcab[dcab.length-1])}</span></div></div>
    <div class="stats">
      <div class="stat"><div class="k">Gain on cash in</div><div class="v" style="color:${s.dca_gain_pct>=0?'var(--up)':'var(--down)'}">${fmtPctInt(s.dca_gain_pct)}</div></div>
      <div class="stat"><div class="k">Money-weighted</div><div class="v">${s.dca_mwr_pct!=null?s.dca_mwr_pct+'%/yr':'—'}</div></div>
      <div class="stat"><div class="k">vs S&amp;P (mwr)</div><div class="v" style="color:${(s.dca_mwr_pct-s.dca_benchmark_mwr_pct)>=0?'var(--up)':'var(--down)'}">${fmtPctInt((s.dca_mwr_pct||0)-(s.dca_benchmark_mwr_pct||0))}</div></div>
      <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${s.dca_max_drawdown_pct}%</div></div>
    </div></div>`;
  const hp=fh.holdings_perf||[];const maxW=Math.max(...hp.map(h=>h.weight_now_pct||0),1);
  const rows=hp.map(h=>{const bw=Math.max(2,Math.round((h.weight_now_pct||0)/maxW*100));return `<tr><td><b>${h.symbol}</b></td><td style="color:${h.ret_pct>=0?'var(--up)':'var(--down)'}">${fmtPctInt(h.ret_pct)}</td><td><div style="display:flex;align-items:center;gap:6px"><div style="flex:1;min-width:50px;height:8px;background:var(--panel2);border-radius:4px;overflow:hidden"><div style="width:${bw}%;height:100%;background:var(--up)"></div></div><b>${h.weight_now_pct}%</b></div></td></tr>`;}).join('');
  const topd=(meta.drift_weights||[])[0]||{};const eqw=hp.length?(100/hp.length).toFixed(1):'';
  const driftTable=hp.length?`<div style="margin-top:12px"><div style="font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">WHO CARRIED THE BASKET — each name's total return since ${meta.since}, and the weight it has DRIFTED to (all started at ${eqw}%, never rebalanced)</div>
    <table class="tr"><thead><tr><th>Holding</th><th>Total return</th><th>Weight now (drift)</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="sub" style="margin-top:5px">Started equal at ${eqw}% each; with no rebalancing, <b>${topd.symbol}</b> grew into <b>${topd.weight_pct}%</b> of the basket — that concentration is the entire case for, and the hidden risk of, buying and holding forever.</div></div>`:'';
  const en=fh.entry||{},eh=(en.holdings||[]).slice().sort((a,b)=>b.buy_now-a.buy_now),eo=en.overall||{},ep=en.params||{};
  const vcol=v=>v==='Accumulate'?'var(--up)':(v==='Expensive'?'var(--down)':'#f5a524');
  const acol2=a=>a==='BUY'?'var(--up)':(a==='SELL'?'var(--down)':'var(--muted)');
  const hcell=ht=>(!ht||!ht.n)?'<span style="color:var(--muted)">—</span>':`<span style="color:${ht.fwd_avg_pct>=0?'var(--up)':'var(--down)'};font-weight:700">${ht.fwd_avg_pct>=0?'+':''}${ht.fwd_avg_pct}%</span> <span style="color:var(--muted)">· ${ht.hit_pct}% pos · n=${(ht.n||0).toLocaleString()}</span>`;
  const vbadge=v=>`<span style="font-size:9.5px;font-weight:800;padding:2px 7px;border-radius:6px;color:#08120b;background:${vcol(v)}">${(v||'—').toUpperCase()}</span>`;
  const erows=eh.map(h=>`<tr><td><b>${h.symbol}</b></td><td><div style="display:flex;align-items:center;gap:6px">${vbadge(h.verdict)}<span style="color:var(--muted)">${h.buy_now}</span></div></td><td style="color:${h.vs200_pct<=0?'var(--up)':'var(--muted)'}">${h.vs200_pct>=0?'+':''}${h.vs200_pct}%</td><td style="color:${h.off_high_pct<=-10?'var(--up)':'var(--muted)'}">${h.off_high_pct}%</td><td style="color:var(--muted)">${h.rsi}</td><td style="color:${acol2(h.live_action)};font-weight:700">${h.live_action||'—'}${h.live_strength?' '+h.live_strength+'%':''}</td><td>${hcell(h.hist_today)}</td></tr>`).join('');
  const entryBlock=eh.length?`<div style="margin:12px 0 2px"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
    <div style="font-size:11.5px;font-weight:800">🟢 Buy now? — is today a good moment to add <span style="font-weight:400;color:var(--muted)">(blend: ${Math.round((ep.w_dip||.6)*100)}% cheapness + ${Math.round((ep.w_live||.4)*100)}% live signal)</span></div>
    <div style="font-size:11px">Basket: ${vbadge(eo.verdict)} <span style="color:var(--muted)">${eo.buy_now!=null?'('+eo.buy_now+') ':''}· ${eo.n_accumulate||0}/${eo.n_total||eh.length} on sale</span></div></div>
    <table class="tr"><thead><tr><th>Holding</th><th>Buy now?</th><th>vs 200-day</th><th>Off 52w high</th><th>RSI</th><th>Live signal</th><th>When this cheap → next 1y</th></tr></thead><tbody>${erows}</tbody>${eo.hist_today&&eo.hist_today.n?`<tfoot><tr style="border-top:1px solid var(--line)"><td colspan="6" style="color:var(--muted)">Whole basket — when it was this cheap (${eo.dip_band}), the next year averaged</td><td>${hcell(eo.hist_today)}</td></tr></tfoot>`:''}</table>
    <div class="sub" style="margin-top:4px">"Cheapness" rewards a name trading below its own 200-day trend, far off its 52-week high, with a low RSI; the live signal is the same macro-aware BUY/SELL the watchlist shows. <b>History is the price-only forward return from that valuation</b> (no macro overlay), graded ${ep.fwd_days||252} trading days out — context, not a promise. For a forever holding, time in the market beats timing this; it just flags better vs worse moments to add.</div></div>`:'';
  const accN=(eh||[]).filter(h=>h.verdict==='Accumulate');const dn=doNext(accN.length?`<b>Add to ${accN.length} name${accN.length>1?'s':''} on sale:</b> ${accN.slice(0,8).map(h=>h.symbol).join(', ')}${accN.length>8?'…':''} <span style="color:var(--muted);font-weight:400">— keep DCAing the rest; next rebalance ${meta.next_rebalance||'—'}</span>`:`<b>Hold &amp; keep DCAing</b> — nothing is clearly on sale (basket ${eo.verdict||'—'}); next rebalance ${meta.next_rebalance||'—'}.`, accN.length?'buy':'hold');
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">💎 Buy & Hold Forever — watchlist's durable names, never timed</div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('1y')}${zbt('2y')}${zbt('5y')}${zbt('max')}</div></div>
    <div class="sub">${meta.strategy||''} Showing ${dates[0]} → ${dates[dates.length-1]} (log scale; headline figures are lifetime since ${meta.since}).</div>
    ${basketBlock}
    ${entryBlock}
    ${lump}
    ${lumpChart}
    ${dca}
    ${dcaChart}
    ${driftTable}
    <div class="disc"><b>Read this honestly:</b> this is the patient opposite of the Confidence Backtest above — no signals, no selling. The <b>drift</b> line never rebalances, so one winner (${topd.symbol} at ${topd.weight_pct}%) can come to dominate: huge upside, but real concentration risk and a deeper drawdown (${s.max_drawdown_pct}% vs ${s.max_drawdown_rebal_pct}% rebalanced). The gap to the S&P is inflated by <b>survivorship</b> — this is today's hand-picked list of names that already won; a "forever" list written years ago would look different, and the basket even <b>holds VOO</b> (the S&P itself). Rebalancing is modeled cost- and tax-free; in a taxable account, trimming winners is taxed, so the drift line is the cheapest to actually run. Information only — not financial advice; past results don't predict the future.</div>`;
}
function setMomZoom(z){st.momZoom=z;renderMomSim();}
function lifeChip(k,a,b,good){return `<div style="flex:1;min-width:118px;background:var(--panel2);border:1px solid var(--line);border-left:3px solid ${good?'var(--up)':'var(--down)'};border-radius:9px;padding:7px 9px"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px">${k}</div><div style="font-size:15px;font-weight:800;color:${good?'var(--up)':'var(--fg)'}">${a}</div><div style="font-size:10px;color:var(--muted)">${b}</div></div>`;}
function fmtPctInt(v){return (v>=0?'+':'')+Math.round(v).toLocaleString()+'%';}
function toneOf(a){a=(''+(a||'')).toUpperCase();return a.includes('SELL')?'sell':(a.includes('WAIT')?'wait':((a.includes('BUY')||a.includes('ACCUM')||a.includes('ADD'))?'buy':'hold'));}
function doNext(html,tone){const c=tone==='buy'?'var(--buy)':(tone==='sell'?'var(--down)':(tone==='wait'?'var(--hold)':'var(--accent)'));
  return `<div style="display:flex;gap:9px;align-items:baseline;margin:2px 0 10px;padding:9px 12px;background:var(--panel2);border:1px solid var(--line);border-left:4px solid ${c};border-radius:10px">
    <span style="font-size:10px;font-weight:800;color:${c};text-transform:uppercase;letter-spacing:.6px;white-space:nowrap">▶ Do next</span>
    <span style="font-size:12.5px;font-weight:600;color:var(--fg);line-height:1.4">${html}</span></div>`;}
function recNext(arr){const r=(arr||[])[0];if(!r)return '';return doNext(`<b>${r.horizon}:</b> ${r.action}${r.price?` ($${r.price})`:''}${r.note?` — <span style="color:var(--muted);font-weight:400">${r.note}</span>`:''}`,toneOf(r.action));}
function renderMomSim(){
  const ms=st.data&&st.data.momentum_sim,box=$('momPanel');
  if(!ms||!ms.dates||!ms.dates.length){box.innerHTML='<div class="section-title">🏆 My Strategy to Beat the S&P 500</div><div class="empty">Warming up… (first build fetches ~20y of data)</div>';return;}
  const meta=ms.meta||{},s=ms.stats||{},zoom=st.momZoom||'max';
  const v=sliceByZoom(ms,zoom);st.views=st.views||{};st.views.mom=v;const {dates,eq,bm,trades}=v,n=eq.length;
  const w=windowStats(eq,bm,dates);
  const stratCol=w.wRet>=w.wBRet?'#16a34a':'#f5a524';
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setMomZoom('${z}')">${z.toUpperCase()}</span>`;
  const pick=meta.current_pick,pickName={SPY:'S&P 500 (SPY)',QQQ:'Nasdaq-100 (QQQ)',IEF:'Treasuries (IEF)'}[pick]||pick||'—';
  const pickCol=pick==='IEF'?'var(--hold)':'var(--buy)';
  const rec=(ms.recommendation||[]).map(r=>`<div style="background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:7px 9px;border-left:3px solid ${pickCol}"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px">${r.horizon}</div><div style="font-weight:800;color:${pickCol};font-size:12.5px;margin:1px 0">${r.action}</div><div style="font-size:10px;color:var(--muted);line-height:1.35">${r.note}</div></div>`).join('');
  const rules=`<ol style="margin:4px 0 8px;padding-left:20px;font-size:12px;line-height:1.55">
    <li><b>Once a month</b> (last trading day), check the trailing <b>12-month return</b> of the S&P 500 (SPY) and the Nasdaq-100 (QQQ).</li>
    <li><b>Hold the leader</b> — whichever of the two is higher — for the next month.</li>
    <li><b>The brake:</b> if that leader's 12-month return is <b>negative</b>, hold <b>Treasury bonds (IEF)</b> instead.</li>
    <li>Repeat — about <b>2 trades a year</b>.</li></ol>
    <div style="font-size:11px;color:var(--muted);line-height:1.5">Own what's winning (momentum is the market's most durable edge); the bond brake steps aside before the deep bear markets whose −50% holes take years to recover. Dodging the holes while compounding the leader is the edge.</div>`;
  const life=`<div style="display:flex;flex-wrap:wrap;gap:7px;margin:10px 0 4px">
    ${lifeChip('CAGR',s.cagr_pct+'%','S&P '+s.benchmark_cagr_pct+'%',s.cagr_pct>=s.benchmark_cagr_pct)}
    ${lifeChip('Total return',fmtPctInt(s.total_return_pct),'S&P '+fmtPctInt(s.benchmark_total_pct),s.total_return_pct>=s.benchmark_total_pct)}
    ${lifeChip('Worst drawdown',s.max_drawdown_pct+'%','S&P '+s.benchmark_dd_pct+'%',s.max_drawdown_pct>=s.benchmark_dd_pct)}
    ${lifeChip('Sharpe',s.sharpe,'S&P '+s.benchmark_sharpe,s.sharpe>=s.benchmark_sharpe)}
    ${lifeChip('Beat S&P',s.years_beat+'/'+s.years_total+' yrs','~'+s.switches_per_yr+' trades/yr',s.years_beat>s.years_total/2)}
    ${lifeChip('In bonds',s.pct_in_bonds+'% of mo','over '+s.years+'y',true)}
  </div>`;
  const dn=recNext(ms.recommendation);
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">🏆 My Strategy to Beat the S&P 500 — Momentum Rotation</div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('1y')}${zbt('2y')}${zbt('3y')}${zbt('5y')}${zbt('10y')}${zbt('max')}</div></div>
    <div class="sub">Backtested ${dates[0]} → ${dates[n-1]} on dividend-adjusted prices. 🟢/🔴 mark the months it switched holdings.</div>
    <div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:2;min-width:290px">${rules}</div>
      <div style="flex:1;min-width:236px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px">
        <div style="font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">This month, hold</div>
        <div style="font-size:19px;font-weight:800;color:${pickCol};margin:2px 0 8px">${pickName}</div>
        <div style="display:flex;flex-direction:column;gap:6px">${rec}</div>
      </div>
    </div>
    ${life}
    <div class="simgrid">
      <div class="chartbox">${chartSVG(eq,bm,trades,dates,zoom,stratCol,'mom')}
        <div id="mom_tip"></div>
        <div class="lgd"><span><i style="background:${stratCol}"></i>Strategy ${fmtMoney(w.wEnd)} (${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%)</span>
          <span><i style="background:#5a6675"></i>S&P 500 buy &amp; hold ${fmtMoney(w.bEnd)} (${w.wBRet>=0?'+':''}${w.wBRet.toFixed(1)}%)</span></div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">Return (window)</div><div class="v" style="color:${w.wRet>=0?'var(--up)':'var(--down)'}">${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">vs S&P (window)</div><div class="v" style="color:${(w.wRet-w.wBRet)>=0?'var(--up)':'var(--down)'}">${(w.wRet-w.wBRet)>=0?'+':''}${(w.wRet-w.wBRet).toFixed(1)}%</div></div>
        <div class="stat"><div class="k">CAGR</div><div class="v">${w.wCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">S&P CAGR</div><div class="v">${w.wBCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${w.wMdd.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Window</div><div class="v">${w.wYrs.toFixed(1)}y</div></div>
      </div>
    </div>
    <div class="disc"><b>Honest caveats:</b> a backtest is not a promise. It beat the S&P in ${s.years_beat} of ${s.years_total} years — so it <b>trailed in ${s.years_total-s.years_beat}</b>, typically sharp V-shaped rebounds where the brake re-enters late. Real switching triggers taxes (shown untaxed here) and the future may not rhyme with the past. Information only — not financial advice.</div>`;
}
function setBskZoom(z){st.bskZoom=z;renderBasket();}
function renderBasket(){
  const bs=st.data&&st.data.momentum_basket,box=$('basketPanel');
  if(!bs||!bs.dates||!bs.dates.length){box.innerHTML='<div class="section-title">🧺 Momentum Basket</div><div class="empty">Warming up… (first build fetches ~20y of data)</div>';return;}
  const meta=bs.meta||{},s=bs.stats||{},zoom=st.bskZoom||'max';
  const v=sliceByZoom(bs,zoom);st.views=st.views||{};st.views.bsk=v;const {dates,eq,bm,trades}=v,n=eq.length;
  const w=windowStats(eq,bm,dates);
  const stratCol=w.wRet>=w.wBRet?'#16a34a':'#f5a524';
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setBskZoom('${z}')">${z.toUpperCase()}</span>`;
  const holds=meta.current_holds||[];
  const holdCards=holds.map((h,k)=>`<div style="flex:1;min-width:118px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:9px 11px;border-left:3px solid ${h.cash?'var(--hold)':'var(--buy)'}"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px">#${k+1} ${h.cash?'· parked':''}</div><div style="font-size:16px;font-weight:800;color:${h.cash?'var(--hold)':'var(--fg)'}">${h.name}</div><div style="font-size:11px;color:${h.mom_pct>=0?'var(--up)':'var(--down)'}">${h.lead} 12-mo ${h.mom_pct>=0?'+':''}${h.mom_pct}%</div></div>`).join('');
  const rules=`<ol style="margin:4px 0 8px;padding-left:20px;font-size:12px;line-height:1.55">
    <li><b>Once a month</b>, rank 9 S&P sectors + Semiconductors + Gold by trailing <b>12-month return</b>.</li>
    <li><b>Hold the top 3</b>, equal weight (~⅓ each), for the next month.</li>
    <li><b>The filter:</b> any of the 3 with a <b>negative</b> 12-month return parks in <b>Treasuries (IEF)</b>.</li>
    <li>Re-rank and rotate monthly.</li></ol>
    <div style="font-size:11px;color:var(--muted);line-height:1.5">Cross-sectional momentum — own this month's strongest groups, spread across 3 bets instead of one, with a bond brake. A retail-scale take on the "many small uncorrelated bets" idea.</div>`;
  const life=`<div style="display:flex;flex-wrap:wrap;gap:7px;margin:10px 0 4px">
    ${lifeChip('CAGR',s.cagr_pct+'%','S&P '+s.benchmark_cagr_pct+'%',s.cagr_pct>=s.benchmark_cagr_pct)}
    ${lifeChip('Total return',fmtPctInt(s.total_return_pct),'S&P '+fmtPctInt(s.benchmark_total_pct),s.total_return_pct>=s.benchmark_total_pct)}
    ${lifeChip('Worst drawdown',s.max_drawdown_pct+'%','S&P '+s.benchmark_dd_pct+'%',s.max_drawdown_pct>=s.benchmark_dd_pct)}
    ${lifeChip('Sharpe',s.sharpe,'S&P '+s.benchmark_sharpe,s.sharpe>=s.benchmark_sharpe)}
    ${lifeChip('Beat S&P',s.years_beat+'/'+s.years_total+' yrs','top 3 of 11',s.years_beat>s.years_total/2)}
    ${lifeChip('Turnover',s.rebalances_per_yr+' chg/yr',s.pct_in_cash+'% in cash',true)}
  </div>`;
  const dn=recNext(bs.recommendation);
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">🧺 Momentum Basket — top 3 of 11 by momentum</div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('1y')}${zbt('2y')}${zbt('3y')}${zbt('5y')}${zbt('10y')}${zbt('max')}</div></div>
    <div class="sub">Backtested ${dates[0]} → ${dates[n-1]}, dividend-adjusted, equal-weight top 3. 🟢/🔴 mark groups rotating in / out.</div>
    <div style="margin:2px 0 4px;font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Holding this month</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">${holdCards}</div>
    <div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:280px">${rules}</div>
    </div>
    ${life}
    <div class="simgrid">
      <div class="chartbox">${chartSVG(eq,bm,trades,dates,zoom,stratCol,'bsk')}
        <div id="bsk_tip"></div>
        <div class="lgd"><span><i style="background:${stratCol}"></i>Basket ${fmtMoney(w.wEnd)} (${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%)</span>
          <span><i style="background:#5a6675"></i>S&P 500 buy &amp; hold ${fmtMoney(w.bEnd)} (${w.wBRet>=0?'+':''}${w.wBRet.toFixed(1)}%)</span></div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">Return (window)</div><div class="v" style="color:${w.wRet>=0?'var(--up)':'var(--down)'}">${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">vs S&P (window)</div><div class="v" style="color:${(w.wRet-w.wBRet)>=0?'var(--up)':'var(--down)'}">${(w.wRet-w.wBRet)>=0?'+':''}${(w.wRet-w.wBRet).toFixed(1)}%</div></div>
        <div class="stat"><div class="k">CAGR</div><div class="v">${w.wCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">S&P CAGR</div><div class="v">${w.wBCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${w.wMdd.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Window</div><div class="v">${w.wYrs.toFixed(1)}y</div></div>
      </div>
    </div>
    <div class="disc"><b>Honest caveats:</b> a backtest, not a promise. It beat the S&P in ${s.years_beat} of ${s.years_total} years and it churns (~${s.rebalances_per_yr} changes/yr), so real-world taxes and costs would bite (shown untaxed here). Only 3 sectors at a time means it can swing harder than the index. Information only — not financial advice.</div>`;
}
function setPnyZoom(z){st.pnyZoom=z;renderPenny();}
function renderPenny(){
  const ph=st.data&&st.data.penny_hold,box=$('pennyPanel');if(!box)return;
  if(!ph||!ph.dates||!ph.dates.length){box.innerHTML='<div class="section-title">🎰 $500 Penny Sleeve</div><div class="empty">Warming up… (first build fetches ~9y of data)</div>';return;}
  const meta=ph.meta||{},s=ph.stats||{},zoom=st.pnyZoom||'max';
  const v=sliceByZoom(ph,zoom);st.views=st.views||{};st.views.pny=v;const {dates,eq,bm,trades}=v,n=eq.length;
  const w=windowStats(eq,bm,dates);
  const stratCol=w.wRet>=w.wBRet?'#16a34a':'#f5a524';
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setPnyZoom('${z}')">${z.toUpperCase()}</span>`;
  const holds=meta.current_holds||[];
  const holdCards=holds.length?holds.map((h,k)=>`<div style="flex:1;min-width:104px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:8px 10px;border-left:3px solid var(--buy)"><div style="font-size:10px;color:var(--muted)">#${k+1} · $${h.price}</div><div style="font-size:15px;font-weight:800">${h.ticker}</div><div style="font-size:11px;color:var(--up)">12-mo +${h.mom_pct}%</div></div>`).join(''):'<div class="empty" style="font-size:12px">All cash — nothing trending up right now.</div>';
  const rules=`<ol style="margin:4px 0 8px;padding-left:20px;font-size:12px;line-height:1.55">
    <li>Rank these low-priced <b>listed</b> (Robinhood-tradable) names by <b>12-month return</b>.</li>
    <li>Hold the <b>top 3 with positive momentum</b>, equal weight; cash for any empty slot.</li>
    <li><b>Rebalance once a quarter</b> — low turnover keeps slippage small.</li></ol>
    <div style="font-size:11px;color:var(--muted);line-height:1.5">The ONLY penny approach that survived testing — active all-in/all-out trading of these names went to ~$0 after 2.5% slippage. "Hold, don't churn."</div>`;
  const life=`<div style="display:flex;flex-wrap:wrap;gap:7px;margin:10px 0 4px">
    ${lifeChip('$500 →',fmtMoney(s.value),'CAGR '+s.cagr_pct+'%',s.cagr_pct>=s.benchmark_cagr_pct)}
    ${lifeChip('vs S&P',fmtPctInt(s.total_return_pct),'SPY '+fmtPctInt(s.benchmark_total_pct),s.total_return_pct>=s.benchmark_total_pct)}
    ${lifeChip('Worst drawdown',s.max_drawdown_pct+'%','SPY '+s.benchmark_dd_pct+'%',s.max_drawdown_pct>=s.benchmark_dd_pct)}
    ${lifeChip('Beat S&P',s.years_beat+'/'+s.years_total+' yrs','~'+s.trades_per_yr+' trades/yr',s.years_beat>s.years_total/2)}
  </div>`;
  const dn=recNext(ph.recommendation);
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">🎰 $500 Penny Sleeve — low-priced momentum (hold, don't churn)</div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('1y')}${zbt('2y')}${zbt('3y')}${zbt('5y')}${zbt('max')}</div></div>
    <div class="sub">Backtested ${dates[0]} → ${dates[n-1]}, $500 start, 2.5% slippage modeled. 🟢/🔴 = quarterly rotation.</div>
    <div style="margin:2px 0 4px;font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Holding this quarter</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">${holdCards}</div>
    <div style="display:flex;gap:14px;flex-wrap:wrap"><div style="flex:1;min-width:280px">${rules}</div></div>
    ${life}
    <div class="simgrid">
      <div class="chartbox">${chartSVG(eq,bm,trades,dates,zoom,stratCol,'pny')}
        <div id="pny_tip"></div>
        <div class="lgd"><span><i style="background:${stratCol}"></i>Sleeve ${fmtMoney(w.wEnd)} (${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%)</span>
          <span><i style="background:#5a6675"></i>S&P 500 ${fmtMoney(w.bEnd)} (${w.wBRet>=0?'+':''}${w.wBRet.toFixed(1)}%)</span></div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">Return (window)</div><div class="v" style="color:${w.wRet>=0?'var(--up)':'var(--down)'}">${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">vs S&P (window)</div><div class="v" style="color:${(w.wRet-w.wBRet)>=0?'var(--up)':'var(--down)'}">${(w.wRet-w.wBRet)>=0?'+':''}${(w.wRet-w.wBRet).toFixed(1)}%</div></div>
        <div class="stat"><div class="k">CAGR</div><div class="v">${w.wCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${w.wMdd.toFixed(1)}%</div></div>
      </div>
    </div>
    <div class="disc"><b style="color:var(--down)">High risk — read this:</b> backtest drawdown ${s.max_drawdown_pct}% (you'd have nearly been wiped out), and it beat the S&P in only ${s.years_beat}/${s.years_total} years — the gains came from a few explosive stretches.${s.ex_value!=null?` <b style="color:var(--down)">Strip out the 2019–21 COVID/meme boom and it's ${s.ex_total_pct}% ($500 → ${fmtMoney(s.ex_value)}) vs the S&P's +${s.ex_spy_total_pct}% — the entire edge was that one regime.</b>`:''} The return is also inflated by <b>hindsight</b> in choosing this universe; forward results will likely be far lower. Only money you can afford to lose. Not advice.</div>`;
}
function setCrZoom(z){st.crZoom=z;renderCrashRadar();}
function renderCrashRadar(){
  const cr=st.data&&st.data.crash_radar,box=$('crashRadar');if(!box)return;
  if(!cr||!cr.hist||!cr.hist.price||!cr.hist.price.length){box.innerHTML='';return;}
  const z=st.crZoom||'1y',K={'3m':63,'6m':126,'1y':252,'2y':504,'max':99999}[z]||252;
  const H=cr.hist.price.slice(-K),HD=cr.hist.dates.slice(-K),PH=(cr.hist.prob_hist||[]).slice(-K),F=cr.fwd,n=H.length,m=F.up.length,total=n+m;
  const h1=cr.h1||{},h3=cr.h3||{},h6=cr.h6||{},L=cr.lead||{},TH=L.thresholds||{},rec=cr.recession||{},lf=cr.live_feats||{};
  const last=cr.last||H[n-1], crashLvl=last*0.90;
  const W=900,Ht=240,padL=48,padR=70,padT=14,padB=22;
  const lo=Math.min(Math.min(...H),Math.min(...F.down),crashLvl),hi=Math.max(Math.max(...H),Math.max(...F.up));
  const xs=i=>padL+(i/(total-1))*(W-padL-padR), ys=v=>Ht-padB-((v-lo)/((hi-lo)||1))*(Ht-padT-padB);
  const pMax=50, pys=p=>(Ht-padB)-(Math.max(0,Math.min(pMax,p))/pMax)*(Ht-padT-padB);
  const histLine=H.map((v,i)=>xs(i).toFixed(1)+','+ys(v).toFixed(1)).join(' ');
  const probLine=PH.map((v,i)=>v==null?'':xs(i).toFixed(1)+','+pys(v).toFixed(1)).filter(Boolean).join(' ');
  let pLast=null,pLastX=null;for(let i=PH.length-1;i>=0;i--){if(PH[i]!=null){pLast=PH[i];pLastX=xs(i);break;}}
  let upP=[[n-1,H[n-1]]],dnP=[[n-1,H[n-1]]];
  F.up.forEach((v,i)=>upP.push([n+i,v])); F.down.forEach((v,i)=>dnP.push([n+i,v]));
  const poly=upP.map(p=>xs(p[0]).toFixed(1)+','+ys(p[1]).toFixed(1)).concat(dnP.slice().reverse().map(p=>xs(p[0]).toFixed(1)+','+ys(p[1]).toFixed(1))).join(' ');
  const upLine=upP.map(p=>xs(p[0]).toFixed(1)+','+ys(p[1]).toFixed(1)).join(' ');
  const downLine=dnP.map(p=>xs(p[0]).toFixed(1)+','+ys(p[1]).toFixed(1)).join(' ');
  const i1=(F.i_1m!=null?F.i_1m:20), x1=xs(n+i1), y1=ys(F.down[i1]!=null?F.down[i1]:F.down[m-1]);
  const i3=(F.i_3m!=null?F.i_3m:62), x3=xs(n+i3), y3=ys(F.down[i3]!=null?F.down[i3]:F.down[m-1]);
  const nowx=xs(n-1),ex=xs(total-1),eyD=ys(F.down[m-1]),clY=ys(crashLvl);
  let yax='';for(let k=0;k<=3;k++){const v=lo+(hi-lo)*k/3,y=ys(v).toFixed(1);yax+=`<line x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}" stroke="#1c2433"/><text x="${padL-4}" y="${(+y+3)}" text-anchor="end" font-size="9" fill="#8a97ad">${(v/1000).toFixed(2)}k</text>`;}
  let pax='';[0,15,30,45].forEach(p=>{const y=pys(p).toFixed(1);pax+=`<text x="${(W-padR+5).toFixed(1)}" y="${(+y+3).toFixed(1)}" font-size="8.5" fill="#e8a33d">${p}%</text>`;});
  const lvl=cr.crash_level||'',sc=cr.crash_score;
  const pcol=p=>p==null?'#8a97ad':(p>=15?'#f85a6c':(p>=8?'#f5a524':'#22a36e'));
  const ccol=c=>c==='High'?'#7fe0b0':(c==='Medium'?'#f5a524':'#f0a0a0');
  const border=/Severe|High/.test(lvl)?'#f85a6c':(/Elevated/.test(lvl)?'#f5a524':'#2a3343');
  const zbt=zz=>`<span class="zbtn ${z===zz?'on':''}" onclick="setCrZoom('${zz}')">${zz.toUpperCase()}</span>`;
  const cell=(lab,hh)=>`<div style="flex:1;min-width:215px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:8px 11px">
     <div style="font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.4px">${lab}</div>
     <div style="display:flex;gap:16px;align-items:flex-end;margin-top:3px">
       <div><div style="font-size:9.5px;color:var(--muted)">crash odds</div><div style="font-size:21px;font-weight:800;color:${pcol(hh.prob)}">${hh.prob==null?'—':hh.prob+'%'}</div></div>
       <div><div style="font-size:9.5px;color:var(--muted)">downside</div><div style="font-size:21px;font-weight:800;color:#f0a0a0">${hh.downside_pct==null?'—':hh.downside_pct+'%'}</div></div>
       <div><div style="font-size:9.5px;color:var(--muted)">confidence</div><div style="font-size:15px;font-weight:800;color:${ccol(hh.conf)}">${hh.conf||'—'}${hh.conf_pct!=null?' '+hh.conf_pct+'%':''}</div></div>
     </div>
     <div style="font-size:9.5px;color:var(--muted);margin-top:3px">vs ${hh.base==null?'—':hh.base+'%'} normal · 90% CI ${hh.ci_lo==null?'n/a':hh.ci_lo+'–'+hh.ci_hi+'%'}</div></div>`;
  const thrRow=(nm,t)=>t?`<tr><td style="text-transform:capitalize;white-space:nowrap">${nm}${t.on_now?' <b style="color:#f85a6c">● ON</b>':''}</td><td style="color:var(--muted)">≥${t.level}%</td><td><b style="color:${(t.hit_rate_pct||0)>=60?'#7fe0b0':'#f5a524'}">${t.hit_rate_pct==null?'—':t.hit_rate_pct+'%'}</b> <span style="color:var(--muted);font-size:10px">${t.caught}/${t.episodes}</span></td><td><b>${t.median_lead_days==null?'—':'~'+t.median_lead_days+'d'}</b></td><td style="color:#f0a0a0">${t.false_alarm_pct==null?'—':t.false_alarm_pct+'%'}</td></tr>`:'';
  const fmDur=d=>d==null?'—':(d<42?d+' days':(d<252?'~'+Math.round(d/21)+' mo':'~'+(d/252).toFixed(1)+' yr'));
  const du=cr.duration;
  const durRows=du&&du.buckets?du.buckets.filter(b=>b.n>0).map(b=>`<tr><td><b>${b.name}</b></td><td><b>${b.share_pct}%</b></td><td style="color:#f0a0a0">${b.med_depth_pct}%</td><td>${fmDur(b.med_down_days)}</td><td>${fmDur(b.med_rec_days)}</td><td style="color:var(--muted)">${b.rec_link_pct}% <span style="font-size:9px">(n=${b.n})</span></td></tr>`).join(''):'';
  const durNow=(du&&du.current&&du.current.active)?`<div style="font-size:11px;margin-top:6px">📍 Right now the S&P is <b style="color:#f0a0a0">${du.current.dd_pct}%</b> off its high, <b>${fmDur(du.current.days)}</b> in — corrections typically bottom in ${fmDur((du.buckets[0]||{}).med_down_days)}, bears in ${fmDur((du.buckets[1]||{}).med_down_days)}.</div>`:'';
  const durBlock=durRows?`<div style="background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:8px 11px;margin-bottom:9px">
    <div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px">⏳ If a 10%+ drop starts — how deep &amp; how long? <span style="text-transform:none">· every S&P drawdown since ${du.since} (${du.episodes_n} episodes)</span></div>
    <table class="tr" style="font-size:11px"><thead><tr><th>It becomes…</th><th>Odds</th><th>Typical bottom</th><th>Fall takes</th><th>Recovery takes</th><th>Recession-linked</th></tr></thead><tbody>${durRows}</tbody></table>
    ${du.linked&&du.linked.med_down_days!=null?`<div style="font-size:10.5px;margin-top:6px">The recession split is the real tell: <b style="color:#f0a0a0">recession-linked</b> drawdowns bottomed in a median <b>${fmDur(du.linked.med_down_days)}</b> (depth ${du.linked.med_depth_pct}%, recovery ${fmDur(du.linked.med_rec_days)}) vs <b style="color:#7fe0b0">${fmDur(du.unlinked.med_down_days)}</b> (depth ${du.unlinked.med_depth_pct}%, recovery ${fmDur(du.unlinked.med_rec_days)}) when no recession followed — so the curve/credit row below is also the best available guess at <b>length</b>.</div>`:''}
    ${durNow}
    <div style="font-size:10px;color:var(--muted);margin-top:5px">"Odds" = share of all 10%+ drawdowns that ended in that bucket. "Fall takes" = peak → trough; "recovery" = trough → back to the old high. Historical medians, not promises — no model can time the bottom.</div>
  </div>`:'';
  const valBlock=TH.balanced?`<div style="background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:8px 11px;margin-bottom:9px"><div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px">📋 Early-warning track record — walk-forward / out-of-sample${L.span?' · '+L.span[0]+' → '+L.span[1]:''}</div><div style="font-size:10.5px;color:var(--muted);margin:3px 0 6px">Across <b>${L.n_episodes}</b> past 10%+ drawdowns: how often the leading 3-month signal fired <b>before</b> the drop, its typical head-start, and how often it cried wolf. Pick your tolerance for false alarms.</div><table class="tr" style="font-size:11px"><thead><tr><th>Threshold</th><th>Fires</th><th>Caught</th><th>Median lead</th><th>False alarms</th></tr></thead><tbody>${thrRow('sensitive',TH.sensitive)}${thrRow('balanced',TH.balanced)}${thrRow('precise',TH.precise)}</tbody></table><div style="font-size:10px;color:var(--muted);margin-top:5px">Median lead ≈ trading days before the drop the warning first appeared. False alarms = warnings not followed by a 10% drop within 3 months — the unavoidable cost of early warning.</div></div>`:'';
  box.innerHTML=`<div style="background:var(--card-grad);border:1px solid ${border};border-radius:16px;padding:14px 16px;box-shadow:var(--shadow)">
   <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:8px"><div style="font-size:14px;font-weight:800">🛰️ Crash Radar — S&P 500, 1 / 3 / 6-month risk</div><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font-size:12px;color:var(--muted)">VIX ${cr.meta.vix} · gauge ${sc!=null?sc+'/100 '+lvl:'—'}</span><span style="display:flex;gap:4px">${zbt('3m')}${zbt('6m')}${zbt('1y')}${zbt('2y')}${zbt('max')}</span></div></div>
   <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:9px">${cell('1 month',h1)}${cell('3 months',h3)}${cell('6 months',h6)}</div>
   <div style="font-size:10px;color:var(--muted);margin:-4px 0 8px">↑ <b style="color:#7fe0b0">Leading model (v7):</b> fit on the yield curve, credit spreads, breadth (equal- vs cap-weight) &amp; the VIX term structure — signals that historically move <b>weeks-to-months before</b> a drawdown, not the old reactive stress gauges. Every number is computed walk-forward (out-of-sample). Track record ↓.</div>
   ${valBlock}
   ${durBlock}
   ${rec.available?`<div style="background:var(--panel2);border:1px solid var(--line);border-left:3px solid ${rec.curve_status==='inverted'?'#f85a6c':(rec.curve_status==='flat'?'#f5a524':'#22a36e')};border-radius:9px;padding:8px 11px;margin-bottom:9px;font-size:11.5px">🏛️ <b>Leading inputs right now:</b> 10y−3m curve <b style="color:${rec.curve_status==='inverted'?'#f85a6c':'#7fe0b0'}">${rec.curve>=0?'+':''}${rec.curve}% (${rec.curve_status})</b> · credit <b>${rec.credit_status}</b>${lf.breadth_mom!=null?` · breadth 3mo <b style="color:${lf.breadth_mom<0?'#f0a0a0':'#7fe0b0'}">${lf.breadth_mom>=0?'+':''}${lf.breadth_mom}%</b>`:''}${lf.vix_ts!=null?` · VIX term <b style="color:${lf.vix_ts<0?'#f0a0a0':'#7fe0b0'}">${lf.vix_ts>=0?'+':''}${lf.vix_ts}%</b>`:''}. ${rec.curve_status==='inverted'?'<b style="color:#f85a6c">Curve inverted</b> — the classic late-cycle warning; the model weighs it alongside the others.':'No curve inversion right now.'}</div>`:''}
   <div style="position:relative"><div class="zoombtn" onclick="expandChart(this)" title="Enlarge">⛶</div><svg viewBox="0 0 ${W} ${Ht}" style="width:100%;height:225px;background:rgba(8,12,26,.5);border:1px solid var(--line);border-radius:10px;display:block">
     <defs><linearGradient id="cr_pgrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#5aa9ff" stop-opacity="0.22"/><stop offset="100%" stop-color="#5aa9ff" stop-opacity="0"/></linearGradient></defs>
     ${yax}${pax}
     <rect x="${nowx.toFixed(1)}" y="${padT}" width="${(W-padR-nowx).toFixed(1)}" height="${Ht-padB-padT}" fill="rgba(245,165,36,.05)"/>
     <polygon points="${histLine} ${xs(n-1).toFixed(1)},${(Ht-padB).toFixed(1)} ${xs(0).toFixed(1)},${(Ht-padB).toFixed(1)}" fill="url(#cr_pgrad)" stroke="none"/>
     <polygon points="${poly}" fill="rgba(248,90,108,.20)" stroke="none"/>
     <polyline points="${upLine}" fill="none" stroke="#5a6675" stroke-width="1" stroke-dasharray="3 3"/>
     <polyline points="${downLine}" fill="none" stroke="#f85a6c" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
     <polyline points="${histLine}" fill="none" stroke="#5aa9ff" stroke-width="4.5" opacity="0.18" stroke-linejoin="round" stroke-linecap="round"/>
     <polyline points="${histLine}" fill="none" stroke="#5aa9ff" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>
     ${probLine?`<polyline points="${probLine}" fill="none" stroke="#f5a524" stroke-width="5" opacity="0.18" stroke-linejoin="round" stroke-linecap="round"/><polyline points="${probLine}" fill="none" stroke="#f5a524" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>`:''}
     ${pLast!=null?`<circle cx="${pLastX.toFixed(1)}" cy="${pys(pLast).toFixed(1)}" r="3" fill="#f5a524"/><text x="${(pLastX-6).toFixed(1)}" y="${(pys(pLast)-5).toFixed(1)}" text-anchor="end" font-size="10" font-weight="700" fill="#f5a524">${pLast}% · 3-mo risk</text>`:''}
     <line x1="${padL}" y1="${clY.toFixed(1)}" x2="${W-padR}" y2="${clY.toFixed(1)}" stroke="#f85a6c" stroke-width="1" stroke-dasharray="5 4" opacity=".85"/>
     <text x="${W-padR+3}" y="${(+clY+3).toFixed(1)}" font-size="9" fill="#f85a6c">−10% crash</text>
     <line x1="${x1.toFixed(1)}" y1="${padT}" x2="${x1.toFixed(1)}" y2="${Ht-padB}" stroke="#5a6675" stroke-width="1" stroke-dasharray="2 3"/>
     <circle cx="${x1.toFixed(1)}" cy="${y1.toFixed(1)}" r="3" fill="#f0a0a0"/>
     <text x="${x1.toFixed(1)}" y="${padT+9}" text-anchor="middle" font-size="9" fill="#8a97ad">1mo</text>
     <text x="${x1.toFixed(1)}" y="${(y1+14).toFixed(1)}" text-anchor="middle" font-size="10" font-weight="700" fill="#f0a0a0">${h1.downside_pct}%</text>
     <line x1="${x3.toFixed(1)}" y1="${padT}" x2="${x3.toFixed(1)}" y2="${Ht-padB}" stroke="#5a6675" stroke-width="1" stroke-dasharray="2 3"/>
     <circle cx="${x3.toFixed(1)}" cy="${y3.toFixed(1)}" r="3" fill="#f0a0a0"/>
     <text x="${x3.toFixed(1)}" y="${padT+9}" text-anchor="middle" font-size="9" fill="#8a97ad">3mo</text>
     <text x="${x3.toFixed(1)}" y="${(y3+14).toFixed(1)}" text-anchor="middle" font-size="10" font-weight="700" fill="#f0a0a0">${h3.downside_pct}%</text>
     <circle cx="${ex.toFixed(1)}" cy="${eyD.toFixed(1)}" r="3.6" fill="#f85a6c"/>
     <text x="${(ex-5).toFixed(1)}" y="${(eyD+4).toFixed(1)}" text-anchor="end" font-size="12" font-weight="800" fill="#f85a6c">6mo ${h6.downside_pct}%</text>
     <line x1="${nowx.toFixed(1)}" y1="${padT}" x2="${nowx.toFixed(1)}" y2="${Ht-padB}" stroke="#f5a524" stroke-width="1" stroke-dasharray="3 3"/>
     <text x="${(nowx+3).toFixed(1)}" y="${padT+9}" font-size="9" fill="#f5a524">now · ${fmtMoney(last)}</text>
     <text x="${((nowx+ex)/2).toFixed(1)}" y="${Ht-7}" text-anchor="middle" font-size="9" fill="#8a97ad">↤ 6-month forecast ↦</text>
     <text x="${padL}" y="${Ht-7}" font-size="9" fill="#8a97ad">${HD[0]}</text></svg></div>
   <div class="lgd" style="margin:7px 2px 0"><span><i style="background:#5aa9ff"></i>S&amp;P 500 price</span><span><i style="background:#f5a524"></i>3-mo crash risk (right axis)</span><span><i style="background:#f85a6c"></i>downside path · 90% band</span><span><i style="background:#f5a524;opacity:.55"></i>now</span></div>
   <div style="font-size:11px;color:var(--muted);margin-top:6px">📈 The <b style="color:#f5a524">orange line</b> is the model's <b>3-month crash probability</b> (right axis, %) computed walk-forward — it <b>rises before</b> drawdowns, not during them. Watch it climb ahead of a selloff and fade once the drop is underway. Blue = S&P price.</div>
   <div style="font-size:10.5px;color:var(--muted);margin-top:7px">Right of the amber "now" line: <b style="color:#f85a6c">bold red</b> = the "if it rolls over" path, red zone = 90% range, dashed = a −10% crash; the 1‑ and 3‑month points are marked. <b>Confidence</b> = how stable each odds estimate is when the history is resampled (90% CI). <b>A leading gauge with real but noisy lead — it can't name the day or guarantee a crash.</b> Not advice.</div>
  </div>`;
}
function renderTopCalls(){
  const x=st.data&&st.data.top_calls,box=$('topCalls');if(!box)return;
  if(!x||!x.top||!x.top.length){box.innerHTML='';return;}
  const ac=a=>a==='BUY'?'var(--buy)':(a==='SELL'?'var(--down)':'var(--hold)');
  const cards=x.top.map((t,i)=>`<div style="flex:1;min-width:210px;display:flex;align-items:center;gap:10px;background:var(--panel2);border:1px solid var(--line);border-left:5px solid ${ac(t.action)};border-radius:10px;padding:9px 13px"><span style="font-size:11px;color:var(--muted);font-weight:700">#${i+1}</span><span style="font-size:18px;font-weight:800">${t.symbol}</span><span style="font-size:14px;font-weight:800;color:${ac(t.action)}">${t.action}</span><span style="font-size:11px;color:var(--muted)">${t.confidence}% conf</span><span style="margin-left:auto;font-size:13px">$${t.price}${t.change_pct!=null?` <span style="color:${t.change_pct>=0?'var(--up)':'var(--down)'}">${t.change_pct>=0?'+':''}${(+t.change_pct).toFixed(1)}%</span>`:''}</span></div>`).join('');
  const s=x.scorecard||{};
  const rep=s.graded?`📊 Model report card: <b style="color:${s.hit_rate>=50?'var(--up)':'var(--down)'}">${s.hit_rate}%</b> of <b>${s.graded}</b> graded calls were right (${s.horizon_days}-day outcome) · avg <b style="color:${s.avg_aligned_return>=0?'var(--up)':'var(--down)'}">${s.avg_aligned_return>=0?'+':''}${s.avg_aligned_return}%</b> if followed · ${s.open} pending`:`📊 Model report card: building a live track record — ${s.open||0} call(s) logged, first grades appear after ~${s.horizon_days||14} days`;
  box.innerHTML=`<div style="background:var(--card-grad);border:1px solid var(--line);border-radius:16px;padding:14px 16px;box-shadow:var(--shadow)"><div style="font-size:14px;font-weight:800;margin-bottom:9px">⭐ Top Calls — Buy / Hold / Sell <span style="font-size:11px;color:var(--muted);font-weight:500">· live, updates every refresh</span></div><div style="display:flex;gap:10px;flex-wrap:wrap">${cards}</div><div style="font-size:11px;color:var(--muted);margin-top:9px">${rep} <span style="opacity:.7">— logged daily &amp; graded forward to improve the model. Not advice.</span></div></div>`;
}
function setDipZoom(z){st.dipZoom=z;renderDip();}
function renderDip(){
  const dp=st.data&&st.data.dip_rotate,box=$('dipPanel');if(!box)return;
  if(!dp||!dp.dates||!dp.dates.length){box.innerHTML='<div class="section-title">📈 VOO Dip → Best Mega-Cap</div><div class="empty">Warming up… (first build fetches ~10y of data)</div>';return;}
  const meta=dp.meta||{},s=dp.stats||{},zoom=st.dipZoom||'max';
  const v=sliceByZoom(dp,zoom);st.views=st.views||{};st.views.dip=v;const {dates,eq,bm,trades}=v,n=eq.length;
  const w=windowStats(eq,bm,dates);
  const stratCol=w.wRet>=w.wBRet?'#16a34a':'#f5a524';
  const zbt=z=>`<span class="zbtn ${zoom===z?'on':''}" onclick="setDipZoom('${z}')">${z.toUpperCase()}</span>`;
  const pick=meta.current_pick,pickTxt=pick?`Currently holding <b style="color:var(--buy)">${pick}</b> — indicators picked it at the ${meta.pick_date} dip`:'Currently in VOO — waiting for the next 5%-from-peak dip';
  const rec=(dp.recommendation||[]).map(r=>`<div style="flex:1;min-width:165px;background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:7px 9px;border-left:3px solid ${r.action.indexOf('EXTREME')>=0?'var(--down)':'var(--buy)'}"><div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px">${r.horizon}</div><div style="font-weight:800;font-size:12.5px;margin:1px 0">${r.action}</div><div style="font-size:10px;color:var(--muted);line-height:1.35">${r.note}</div></div>`).join('');
  const life=`<div style="display:flex;flex-wrap:wrap;gap:7px;margin:10px 0 4px">
    ${lifeChip('$10k →',fmtMoney(s.value),'CAGR '+s.cagr_pct+'%',s.cagr_pct>=s.benchmark_cagr_pct)}
    ${lifeChip('VOO hold',fmtMoney(s.benchmark_value),'CAGR '+s.benchmark_cagr_pct+'%',true)}
    ${lifeChip('Worst drawdown',s.max_drawdown_pct+'%','VOO '+s.benchmark_dd_pct+'%',s.max_drawdown_pct>=s.benchmark_dd_pct)}
    ${lifeChip('Beat VOO',s.years_beat+'/'+s.years_total+' yrs',(s.trades!=null?s.trades+' trades total':'≤5/yr cap'),s.years_beat>s.years_total/2)}
  </div>`;
  const dn=recNext(dp.recommendation);
  box.innerHTML=`${dn}<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><div class="section-title" style="margin:0">📈 VOO ⇄ Best Mega-Cap on Dips <span style="font-size:11px;color:var(--muted);font-weight:500">· indicator pick · max 5 trades/yr</span></div><div style="display:flex;gap:5px;flex-wrap:wrap">${zbt('1y')}${zbt('2y')}${zbt('3y')}${zbt('5y')}${zbt('max')}</div></div>
    <div class="sub">${meta.strategy||''} ${pickTxt}.</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0">${rec}</div>
    ${life}
    <div class="simgrid">
      <div class="chartbox">${chartSVG(eq,bm,trades,dates,zoom,stratCol,'dip')}
        <div id="dip_tip"></div>
        <div class="lgd"><span><i style="background:${stratCol}"></i>Strategy ${fmtMoney(w.wEnd)} (${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%)</span>
          <span><i style="background:#5a6675"></i>VOO buy &amp; hold ${fmtMoney(w.bEnd)} (${w.wBRet>=0?'+':''}${w.wBRet.toFixed(1)}%)</span></div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">Return (window)</div><div class="v" style="color:${w.wRet>=0?'var(--up)':'var(--down)'}">${w.wRet>=0?'+':''}${w.wRet.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">vs VOO (window)</div><div class="v" style="color:${(w.wRet-w.wBRet)>=0?'var(--up)':'var(--down)'}">${(w.wRet-w.wBRet)>=0?'+':''}${(w.wRet-w.wBRet).toFixed(1)}%</div></div>
        <div class="stat"><div class="k">CAGR</div><div class="v">${w.wCagr.toFixed(1)}%</div></div>
        <div class="stat"><div class="k">Max drawdown</div><div class="v" style="color:var(--down)">${w.wMdd.toFixed(1)}%</div></div>
      </div>
    </div>
    ${meta.hindsight_note?`<div class="disc"><b style="color:var(--down)">Hindsight warning:</b> ${meta.hindsight_note}</div>`:''}
    <div class="disc"><b style="color:var(--down)">Reality check:</b> full backtest turned $10k into ${fmtMoney(s.value)} vs VOO's ${fmtMoney(s.benchmark_value)} — barely ahead, beating VOO in only ${s.years_beat}/${s.years_total} years with a ${s.max_drawdown_pct}% drawdown (VOO ${s.benchmark_dd_pct}%). It rotates VOO⇄stock on dips/recoveries but at most 5 trades a year, so while it's in one name it can ride it down hard (it held TSLA through the 2022 crash). Not advice.</div>`;
}
function renderInsider(){
  const x=st.data&&st.data.insiders,box=$('insiderCard');if(!box)return;
  if(!x||!x.signals){box.innerHTML='<div class="section-title">🏦 Insider Buying</div><div class="empty">Loading…</div>';return;}
  const sigs=x.signals,bull=x.bullish||[];
  let h='<div class="section-title">🏦 Insider Buying — SEC Form 4</div>';
  if(bull.length){
    h+=bull.map(t=>{const d=sigs[t];return `<div style="display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid var(--line)"><span><b style="color:var(--up)">${t}</b> <span style="color:var(--muted);font-size:11px">${d.buyers} insider${d.buyers>1?'s':''} · ${d.n_buy} buys</span></span><span style="color:#7fe0b0;font-weight:700">$${(d.buy_val/1e6).toFixed(1)}M</span></div>`;}).join('');
  } else {
    h+='<div class="empty" style="font-size:12px">No open-market insider buying clusters right now.</div>';
  }
  const sellers=Object.keys(sigs).filter(t=>sigs[t].tone==='soft').length;
  h+=`<div style="font-size:10.5px;color:var(--muted);margin-top:8px;line-height:1.5">Open-market <b style="color:#7fe0b0">buying</b> is the signal; selling is mostly noise${sellers?` (${sellers} names selling — not flagged bearish)`:''}. Public filings, not advice.</div>`;
  box.innerHTML=h;
}
function simHover(e){
  const v=st.simView,sc=st.simScale;if(!v||!sc)return;
  const svg=$('eqsvg'),rect=svg.getBoundingClientRect();
  let idx=Math.round((e.clientX-rect.left)/rect.width*(sc.n-1));idx=Math.max(0,Math.min(sc.n-1,idx));
  const vbx=sc.padL+(idx/Math.max(1,sc.n-1))*(sc.W-sc.padL-sc.padR);
  const vby=sc.H-sc.padBot-((Math.log(Math.max(1,v.eq[idx]))-sc.llo)/sc.lrng)*(sc.H-sc.padTop-sc.padBot);
  const g=$('eqguide');g.setAttribute('x1',vbx);g.setAttribute('x2',vbx);g.style.display='';
  const dot=$('eqdot');dot.setAttribute('cx',vbx);dot.setAttribute('cy',vby);dot.style.display='';
  const t=v.trades[idx],tip=$('eqtip');
  tip.innerHTML=`<b>${v.dates[idx]}</b> · ${fmtMoney(v.eq[idx])} <span style="color:var(--muted)">(S&P ${fmtMoney(v.bm[idx])})</span>`+
    (t?`<br>${t.ret_pct>=0?'+':''}${t.ret_pct}% · ${t.n} held`+(t.entered&&t.entered.length?`<br>🟢 ${t.entered.join(', ')}`:'')+(t.exited&&t.exited.length?`<br>🔴 ${t.exited.join(', ')}`:''):'');
  tip.style.display='block';const rel=e.clientX-rect.left;tip.style.left=Math.max(4,Math.min(rect.width-220,rel+10))+'px';
}
function simLeave(){['eqtip','eqguide','eqdot'].forEach(id=>{const el=$(id);if(el)el.style.display='none';});}
function chartHover(e,key){
  const v=st.views&&st.views[key],sc=st.scales&&st.scales[key];if(!v||!sc)return;
  const svg=$(key+'_svg');if(!svg)return;const rect=svg.getBoundingClientRect();
  let idx=Math.round((e.clientX-rect.left)/rect.width*(sc.n-1));idx=Math.max(0,Math.min(sc.n-1,idx));
  const vbx=sc.padL+(idx/Math.max(1,sc.n-1))*(sc.W-sc.padL-sc.padR);
  const vby=sc.H-sc.padBot-((Math.log(Math.max(1,v.eq[idx]))-sc.llo)/sc.lrng)*(sc.H-sc.padTop-sc.padBot);
  const g=$(key+'_guide');if(g){g.setAttribute('x1',vbx);g.setAttribute('x2',vbx);g.style.display='';}
  const dot=$(key+'_dot');if(dot){dot.setAttribute('cx',vbx);dot.setAttribute('cy',vby);dot.style.display='';}
  const t=v.trades[idx],tip=$(key+'_tip');if(!tip)return;
  let ex='';
  if(t){
    if(t.hold!==undefined&&t.hold!==null){const h=Array.isArray(t.hold)?t.hold.join(', '):t.hold;if(h)ex+=`<br>Holding: <b>${h}</b>`;}
    if(t.entered&&t.entered.length)ex+=`<br>🟢 bought: ${t.entered.join(', ')}`;
    if(t.exited&&t.exited.length)ex+=`<br>🔴 sold: ${t.exited.join(', ')}`;
    if(!ex&&t.ret_pct!==undefined)ex+=`<br>${t.ret_pct>=0?'+':''}${t.ret_pct}%`;
  }
  tip.innerHTML=`<b>${v.dates[idx]}</b> · ${fmtMoney(v.eq[idx])} <span style="color:var(--muted)">(vs ${fmtMoney(v.bm[idx])})</span>${ex}`;
  tip.style.display='block';const rel=e.clientX-rect.left;tip.style.left=Math.max(4,Math.min(rect.width-230,rel+10))+'px';
}
function chartLeave(key){[key+'_tip',key+'_guide',key+'_dot'].forEach(id=>{const el=$(id);if(el)el.style.display='none';});}

document.addEventListener('click',e=>{
  const bub=e.target.closest('.bub[data-sym]');
  if(bub){st.selected=bub.dataset.sym;render();return;}
  if(e.target.dataset.close){st.selected=null;render();return;}
  const r=e.target.closest('.row[data-sector]');
  if(r){const m=st.data.sectors.find(x=>x.name===r.dataset.sector);if(m){st.selected=m.symbol;switchTab('tab-market');render();$('bubbles').scrollIntoView({behavior:'smooth',block:'nearest'});}}
});
$('onlyUnusual').addEventListener('change',e=>{st.onlyUnusual=e.target.checked;render();});
$('refreshBtn').addEventListener('click',async()=>{$('refreshBtn').textContent='…';const t0=(st.data||{}).updated_at;
  try{await fetch('/api/refresh',{method:'POST'});}catch(e){}
  let n=0;const poll=async()=>{await fetchData();n++;
    if(((st.data||{}).updated_at)!==t0||n>=25){$('refreshBtn').textContent='↻';}else{setTimeout(poll,2500);}};
  poll();});
async function fetchData(){
  if(!st.loadStart)st.loadStart=Date.now();
  try{const r=await fetch('/api/data',{cache:'no-store'});
    if(r.status===503){if(!st.data)renderLoad();setTimeout(fetchData,1500);return;}
    const j=await r.json();if(j.error){if(!st.data)renderLoad();setTimeout(fetchData,1500);return;}
    st.data=j;st.nextAt=Date.now()+POLL_MS;render();
  }catch(e){if(!st.data){renderLoad();setTimeout(fetchData,2000);}}
}
// ---- tab navigation ----
function switchTab(id){
  document.querySelectorAll('.tabpane').forEach(p=>p.classList.toggle('active',p.id===id));
  document.querySelectorAll('.tabbtn').forEach(b=>b.classList.toggle('on',b.dataset.tab===id));
  if(id==='tab-market')sizeField();
}
document.querySelectorAll('.tabbtn').forEach(b=>b.addEventListener('click',()=>switchTab(b.dataset.tab)));
// ---- touch support for chart hovers ----
function chartTouch(e,id){const t=e.touches&&e.touches[0];if(!t)return;const ev={clientX:t.clientX,clientY:t.clientY};if(id)chartHover(ev,id);else simHover(ev);}
function chartTouchEnd(e,id){if(id)chartLeave(id);else simLeave();}
setInterval(()=>{$('clock').textContent=etNow();if(st.nextAt)$('countdown').textContent=Math.max(0,Math.round((st.nextAt-Date.now())/1000));},1000);
setInterval(()=>{if(!st.data)renderLoad();},300);
setInterval(fetchData,POLL_MS);fetchData();
</script>
</body>
</html>
"""

# --- end of dashboard_ui.py ---
