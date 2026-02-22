/**
 * nav-v2.js — Training Run shared nav shell
 * Drop <script src="nav-v2.js"></script> into any page body to inject
 * the new top-bar + ticker + h-nav, replacing the old <nav>.
 */
(function(){
'use strict';

// ── Active tab detection (exact basename match — no false positives) ─────────
const basename = window.location.pathname.split('/').pop() || 'index.html';
function isActive(keys){ return keys.some(k => basename === k); }
const tabs = [
  { label:'Overview',   pill:'',          href:'v2.html',              keys:['v2.html','index.html'] },
  { label:'TRS Arena',  pill:'Soon',      href:'#',                    keys:['__never__'], soon:true },
  { label:'TRSbench',   pill:'Overall',   href:'scores.html',          keys:['scores.html'] },
  { label:'TRUscore',   pill:'Truth',     href:'truscore-scores.html', keys:['truscore-scores.html'] },
  { label:'TRScode',    pill:'Coding',    href:'trscode.html',         keys:['trscode.html','trscode-scores.html'] },
  { label:'TRFcast',    pill:'Prediction',href:'trfcast.html',         keys:['trfcast.html','trfcast-scores.html'] },
  { label:'TRAgents',   pill:'Agents',    href:'tragents-scores.html', keys:['tragents-scores.html'] },
];

// ── Lab logos + fallback colors ───────────────────────────────────────────────
const LOGOS = {
  'Anthropic':   'https://www.google.com/s2/favicons?domain=anthropic.com&sz=64',
  'Google':      'https://www.google.com/s2/favicons?domain=deepmind.google&sz=64',
  'OpenAI':      'https://www.google.com/s2/favicons?domain=openai.com&sz=64',
  'xAI':         'https://www.google.com/s2/favicons?domain=x.ai&sz=64',
  'Mistral':     'https://www.google.com/s2/favicons?domain=mistral.ai&sz=64',
  'Mistral AI':  'https://www.google.com/s2/favicons?domain=mistral.ai&sz=64',
  'DeepSeek':    'https://www.google.com/s2/favicons?domain=deepseek.com&sz=64',
  'Meta':        'https://www.google.com/s2/favicons?domain=meta.com&sz=64',
  'Alibaba':     'https://www.google.com/s2/favicons?domain=qwenlm.github.io&sz=64',
  'Zhipu AI':    'https://www.google.com/s2/favicons?domain=zhipuai.cn&sz=64',
  'MiniMax':     'https://www.google.com/s2/favicons?domain=minimax.com&sz=64',
  'Cohere':      'https://www.google.com/s2/favicons?domain=cohere.com&sz=64',
  'Moonshot AI': 'https://www.google.com/s2/favicons?domain=moonshot.cn&sz=64',
  'Amazon':      'https://www.google.com/s2/favicons?domain=aws.amazon.com&sz=64',
  'Microsoft':   'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
};
const LC = {
  'Anthropic':{bg:'rgba(204,93,57,0.22)'},  'Google':{bg:'rgba(66,133,244,0.2)'},
  'OpenAI':{bg:'rgba(16,163,127,0.2)'},     'xAI':{bg:'rgba(200,200,200,0.1)'},
  'Mistral':{bg:'rgba(255,140,0,0.18)'},    'DeepSeek':{bg:'rgba(100,149,237,0.2)'},
  'Meta':{bg:'rgba(24,119,242,0.18)'},
};
function lc(co){ return LC[co]||{bg:'rgba(255,255,255,0.08)'}; }
function logoImg(co, size){
  const url = LOGOS[co];
  const s = size||18;
  if(url) return '<img src="'+url+'" width="'+s+'" height="'+s+'" style="border-radius:4px;object-fit:contain;background:rgba(255,255,255,0.06);padding:2px;flex-shrink:0;display:block" alt="" onerror="this.style.display='none'">';
  const bg = (LC[co]||{bg:'rgba(255,255,255,0.08)'}).bg;
  const init = (co||'?').slice(0,2).toUpperCase();
  return '<span style="width:'+s+'px;height:'+s+'px;border-radius:4px;background:'+bg+';display:inline-flex;align-items:center;justify-content:center;font-size:'+(Math.round(s*0.45))+'px;font-weight:700;color:rgba(255,255,255,0.5);flex-shrink:0">'+init+'</span>';
}

// ── CSS ──────────────────────────────────────────────────────────────────────
const NAV_HEIGHT = 130; // top-bar(50) + glow(1) + wglow(1) + ticker(33) + wglow(1) + hnav(42) + glow(1) = 129
const css = `
/* Hide old nav */
nav { display:none !important; }
.back-btn { display:none !important; }
.container { padding-top:${NAV_HEIGHT + 20}px !important; }
body { min-width:1100px; }

/* Nav shell positioning */
#trv2-shell {
  position: fixed; top:0; left:0; right:0; z-index:9999;
  display:flex; flex-direction:column;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Top bar */
#trv2-topbar {
  height:50px; background:#0a0a20; display:flex; align-items:center; padding:0 24px;
  position:relative;
}
.trv2-logo-block { display:flex; flex-direction:column; gap:1px; }
.trv2-logo-text  { font-size:18px; font-weight:800; color:#00e5ff; letter-spacing:-.5px; line-height:1; text-shadow:0 0 14px rgba(0,229,255,0.5); text-decoration:none; }
.trv2-logo-sub   { font-size:7.5px; font-weight:600; letter-spacing:2.8px; text-transform:uppercase; color:rgba(255,255,255,0.35); }
.trv2-date       { position:absolute; left:50%; transform:translateX(-50%); font-size:10px; letter-spacing:1.8px; text-transform:uppercase; color:rgba(255,255,255,0.22); }
.trv2-topright   { margin-left:auto; display:flex; align-items:center; gap:18px; }
.trv2-toplink    { font-size:11.5px; color:rgba(255,255,255,0.38); text-decoration:none; }
.trv2-toplink:hover { color:rgba(255,255,255,0.75); }
.trv2-watchpill  { display:flex; align-items:center; gap:6px; background:linear-gradient(135deg,rgba(139,92,246,0.2),rgba(6,182,212,0.2)); border:1px solid rgba(139,92,246,0.35); border-radius:20px; padding:5px 13px; font-size:11px; font-weight:700; color:rgba(255,255,255,0.82); cursor:pointer; text-decoration:none; }
.trv2-watchpill:hover { border-color:rgba(139,92,246,0.6); }

/* Glow lines */
.trv2-glow  { height:1px; flex-shrink:0; background:linear-gradient(90deg,transparent 0%,rgba(0,229,255,0.1) 10%,#00e5ff 40%,#00e5ff 60%,rgba(0,229,255,0.1) 90%,transparent 100%); box-shadow:0 0 6px rgba(0,229,255,0.45),0 0 18px rgba(0,229,255,0.1); }
.trv2-wglow { height:1px; flex-shrink:0; background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,0.08) 8%,rgba(255,255,255,0.65) 35%,rgba(255,255,255,0.65) 65%,rgba(255,255,255,0.08) 92%,transparent 100%); box-shadow:0 0 6px rgba(255,255,255,0.35),0 0 16px rgba(255,255,255,0.08); }

/* Ticker */
#trv2-ticker { height:33px; background:#06061a; overflow:hidden; display:flex; align-items:center; }
.trv2-track  { display:inline-flex; white-space:nowrap; }
.trv2-track.go { animation:trv2tick 32s linear infinite; }
@keyframes trv2tick { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.trv2-ti   { display:inline-flex; align-items:center; gap:7px; padding:0 20px; height:33px; border-right:1px solid rgba(255,255,255,0.05); white-space:nowrap; }
.trv2-tl   { font-size:9px; color:rgba(255,255,255,0.28); letter-spacing:.5px; }
.trv2-tc   { font-size:9px; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; color:#00e5ff; }
.trv2-ico  { width:16px; height:16px; border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:7px; font-weight:800; color:rgba(255,255,255,0.65); flex-shrink:0; }
.trv2-tn   { font-size:12px; font-weight:700; color:#fff; }
.trv2-ts   { font-size:12px; font-weight:800; color:#00e5ff; }
.trv2-up   { color:#22d3a3; font-size:10.5px; font-weight:700; }
.trv2-dn   { color:#f87171; font-size:10.5px; font-weight:700; }

/* Horizontal nav */
#trv2-hnav { height:42px; background:#0a0a20; display:flex; align-items:stretch; padding:0 24px; justify-content:space-between; }
.trv2-htabs { display:flex; align-items:stretch; }
.trv2-htab  { display:flex; align-items:center; gap:6px; padding:0 14px; font-size:12px; font-weight:600; color:rgba(255,255,255,0.38); cursor:pointer; position:relative; border-bottom:2px solid transparent; transition:color .2s; white-space:nowrap; text-decoration:none; }
.trv2-htab:hover { color:rgba(255,255,255,0.72); }
.trv2-htab.trv2-active { color:#00e5ff; border-bottom-color:#00e5ff; text-shadow:0 0 10px rgba(0,229,255,0.3); }
.trv2-htab.trv2-active::after { content:''; position:absolute; bottom:-2px; left:0; right:0; height:2px; box-shadow:0 0 8px #00e5ff,0 0 16px rgba(0,229,255,0.35); }
.trv2-pill { font-size:7px; font-weight:700; letter-spacing:.8px; text-transform:uppercase; background:rgba(255,255,255,0.05); border-radius:3px; padding:1px 5px; color:rgba(255,255,255,0.28); }
.trv2-htab.trv2-active .trv2-pill { background:rgba(0,229,255,0.1); color:rgba(0,229,255,0.55); }
.trv2-hnav-right { display:flex; align-items:center; gap:14px; }
.trv2-hnav-right a { font-size:11px; color:rgba(255,255,255,0.3); text-decoration:none; }
.trv2-hnav-right a:hover { color:rgba(255,255,255,0.65); }
.trv2-pipe { color:rgba(255,255,255,0.08); }
`;

// ── Build HTML ───────────────────────────────────────────────────────────────
const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const now = new Date();
const dateStr = months[now.getMonth()]+' '+now.getDate()+', '+now.getFullYear();

const tabsHTML = tabs.map(t => {
  const active = !t.soon && isActive(t.keys) ? 'trv2-active' : '';
  const dimStyle = t.soon ? 'style="color:rgba(255,255,255,0.2);cursor:default"' : '';
  const pillHTML = t.pill ? `<span class="trv2-pill"${t.soon?' style="background:rgba(139,92,246,0.1);color:rgba(139,92,246,0.45);border:1px dashed rgba(139,92,246,0.25)"':''}>${t.pill}</span>` : '';
  return `<a href="${t.href}" class="trv2-htab ${active}" ${dimStyle}>${t.label}${pillHTML}</a>`;
}).join('');

const shell = `
<div id="trv2-shell">
  <div id="trv2-topbar">
    <a href="v2.html" class="trv2-logo-block" style="text-decoration:none">
      <span class="trv2-logo-text">Training Run</span>
      <span class="trv2-logo-sub">Your Weekly AI Conditioning</span>
    </a>
    <span class="trv2-date">${dateStr}</span>
    <div class="trv2-topright">
      <a href="about.html" class="trv2-toplink">About</a>
      <a href="trsmethodology.html" class="trv2-toplink">Methodology</a>
      <a href="https://www.youtube.com/watch?v=7rZEPc6vXZo" target="_blank" class="trv2-watchpill">
        <span style="font-size:9px;color:#a78bfa">▶</span> Watch Latest Episode
      </a>
    </div>
  </div>
  <div class="trv2-glow"></div>
  <div class="trv2-wglow"></div>
  <div id="trv2-ticker">
    <div class="trv2-track" id="trv2-track">
      <div class="trv2-ti"><span style="font-size:11px;color:rgba(255,255,255,0.3)">Loading scores…</span></div>
    </div>
  </div>
  <div class="trv2-wglow"></div>
  <div id="trv2-hnav">
    <div class="trv2-htabs">${tabsHTML}</div>
    <div class="trv2-hnav-right">
      <a href="sources.html">Verify Sources</a><span class="trv2-pipe">|</span>
      <a href="https://www.youtube.com/@trainingrun" target="_blank">The Show</a><span class="trv2-pipe">|</span>
      <a href="about.html">About</a>
    </div>
  </div>
  <div class="trv2-glow"></div>
</div>`;

// ── Inject ───────────────────────────────────────────────────────────────────
const styleEl = document.createElement('style');
styleEl.textContent = css;
document.head.appendChild(styleEl);

document.body.insertAdjacentHTML('afterbegin', shell);

// ── Populate ticker from trs-data.json ───────────────────────────────────────
function getLatest(m){ const s=m.scores.filter(v=>v!==null&&v>0); return s.length?s[s.length-1]:null; }
function getChg(m){ const s=m.scores.filter(v=>v!==null&&v>0); return s.length>=2?+(s[s.length-1]-s[s.length-2]).toFixed(2):0; }
function get7(m){ return m.scores.filter(v=>v!==null&&v>0).slice(-7); }

fetch('trs-data.json?v='+Date.now())
  .then(r=>r.json())
  .then(data=>{
    const ranked = [...data.models]
      .filter(m=>getLatest(m)!==null)
      .sort((a,b)=>(getLatest(b)||0)-(getLatest(a)||0));
    const top5 = ranked.slice(0,5);

    let mover={name:'',company:'',change:-999}, loser={name:'',company:'',change:999};
    data.models.forEach(m=>{
      const pts=get7(m); if(pts.length<2) return;
      const chg=pts[pts.length-1]-pts[0];
      if(chg>mover.change) mover={name:m.name,company:m.company,change:chg};
      if(chg<loser.change) loser={name:m.name,company:m.company,change:chg};
    });

    let items = top5.map((m,i)=>{
      const score=getLatest(m), c=getChg(m), l=lc(m.company);
      const chgHTML=Math.abs(c)<0.005?'':(c>0?`<span class="trv2-up" style="margin-left:3px">↑${c.toFixed(2)}</span>`:`<span class="trv2-dn" style="margin-left:3px">↓${Math.abs(c).toFixed(2)}</span>`);
      return `<div class="trv2-ti"><span class="trv2-tl">#${i+1}</span><span class="trv2-tc">TRSbench</span>${logoImg(m.company,18)}<span class="trv2-tn">${m.name}</span><span class="trv2-ts">${score.toFixed(2)}</span>${chgHTML}</div>`;
    });
    if(mover.name&&mover.change>0.5){
      const l=lc(mover.company);
      items.push(`<div class="trv2-ti"><span style="font-size:12px">🔥</span><span style="font-size:9px;color:rgba(255,255,255,0.35)">On Fire</span>${logoImg(mover.company,18)}<span class="trv2-tn">${mover.name}</span><span class="trv2-up">+${mover.change.toFixed(2)}</span></div>`);
    }
    if(loser.name&&loser.change<-0.5){
      const l=lc(loser.company);
      items.push(`<div class="trv2-ti"><span style="font-size:9px;color:rgba(255,255,255,0.35)">Biggest Drop</span>${logoImg(loser.company,18)}<span class="trv2-tn">${loser.name}</span><span class="trv2-dn">${loser.change.toFixed(2)}</span></div>`);
    }

    const track = document.getElementById('trv2-track');
    track.innerHTML = items.join('') + items.join('');
    track.classList.add('go');
  })
  .catch(()=>{
    document.getElementById('trv2-track').innerHTML = '<div class="trv2-ti"><span style="font-size:11px;color:rgba(255,255,255,0.3)">trainingrun.ai — daily AI benchmark rankings</span></div>';
  });

})();
