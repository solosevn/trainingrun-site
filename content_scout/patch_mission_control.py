#!/usr/bin/env python3
"""
Patches mission-control.html to add the Content Scout Intelligence section,
a NEW stories indicator, and a Stories count in the summary bar.
Handles both minified and pretty-printed HTML.
"""

import re
from pathlib import Path

MC_PATH = Path.home() / "trainingrun-site" / "mission-control.html"

# ─────────────────────────────────────────────────────────────────────────────
# 1. CSS  (injected before </style>)
# ─────────────────────────────────────────────────────────────────────────────
SCOUT_CSS = """
    /* ── SCOUT / INTELLIGENCE ── */
    .story-row { display:flex; align-items:flex-start; padding:8px 0; gap:10px; border-top:1px solid var(--border); }
    .story-rank { width:20px; font-size:11px; font-weight:700; color:var(--subtext); flex-shrink:0; padding-top:2px; }
    .story-body { flex:1; min-width:0; }
    .story-title { font-size:13px; font-weight:500; line-height:1.35; color:var(--text); text-decoration:none; display:block; }
    .story-title:active { color:#ffab00; }
    .story-meta { display:flex; align-items:center; gap:6px; margin-top:4px; flex-wrap:wrap; }
    .story-badge { font-size:9px; font-weight:700; letter-spacing:1px; padding:2px 6px; border-radius:10px; text-transform:uppercase; }
    .story-badge.verified { background:rgba(0,230,118,0.15);  color:var(--green);  }
    .story-badge.likely   { background:rgba(68,138,255,0.15);  color:var(--blue);   }
    .story-badge.caution  { background:rgba(255,145,0,0.15);   color:var(--orange); }
    .story-source { font-size:10px; color:var(--subtext); }
    .story-score  { font-size:11px; font-weight:700; color:#ffab00; flex-shrink:0; padding-top:2px; }
    .story-cat    { font-size:10px; color:var(--subtext); border-left:1px solid var(--border); padding-left:6px; }
    .scout-stats { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:14px; }
    .scout-stat  { background:var(--surface); border-radius:10px; padding:10px 12px; text-align:center; }
    .scout-stat-num   { font-size:20px; font-weight:700; color:#ffab00; }
    .scout-stat-label { font-size:9px;  color:var(--subtext); text-transform:uppercase; letter-spacing:1px; margin-top:2px; }
    .stories-list       { margin-top:10px; background:var(--surface); border-radius:10px; padding:10px 12px; }
    .stories-list-title { font-size:10px; color:var(--subtext); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; }
    .no-brief { text-align:center; padding:20px; color:var(--subtext); font-size:13px; }
    .scout-narrative { margin-top:10px; background:var(--surface); border-radius:10px; padding:10px 12px;
                       font-size:12px; color:var(--subtext); line-height:1.6; }
    .scout-narrative strong { color:var(--text); display:block; font-size:10px;
                              text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }
    .new-badge { display:inline-flex; align-items:center; gap:4px;
                 background:rgba(255,171,0,0.18); color:#ffab00;
                 font-size:9px; font-weight:800; letter-spacing:1.5px;
                 padding:3px 8px; border-radius:20px; text-transform:uppercase;
                 border:1px solid rgba(255,171,0,0.35); }
    .new-dot { width:6px; height:6px; border-radius:50%; background:#ffab00;
               animation:pulse 1.4s infinite; flex-shrink:0; }
"""

# ─────────────────────────────────────────────────────────────────────────────
# 2. Stories summary item HTML snippet
# ─────────────────────────────────────────────────────────────────────────────
STORIES_ITEM = ('<div class="summary-item">'
                '<div class="summary-num" id="sum-stories" style="color:#ffab00">—</div>'
                '<div class="summary-label">Stories</div>'
                '</div>')

# ─────────────────────────────────────────────────────────────────────────────
# 3. Scout JS (injected before last </script>)
# ─────────────────────────────────────────────────────────────────────────────
SCOUT_JS = r"""
    // ── CONTENT SCOUT ────────────────────────────────────────────────────────
    const SCOUT_SEEN_KEY = "scout_brief_seen";

    function scoutBadgeClass(v) {
      if (!v) return "likely";
      const u = v.toUpperCase();
      if (u.includes("VERIFIED")) return "verified";
      if (u.includes("LIKELY"))   return "likely";
      return "caution";
    }
    function scoutBadgeLabel(v) {
      if (!v) return "Unverified";
      const u = v.toUpperCase();
      if (u.includes("VERIFIED")) return "\u2705 Verified";
      if (u.includes("LIKELY"))   return "\uD83D\uDFE2 Likely True";
      return "\u26A0\uFE0F Caution";
    }
    function markScoutSeen(briefDate) {
      try { localStorage.setItem(SCOUT_SEEN_KEY, briefDate); } catch(e) {}
    }
    function isScoutSeen(briefDate) {
      try { return localStorage.getItem(SCOUT_SEEN_KEY) === briefDate; } catch(e) { return false; }
    }

    async function loadScout() {
      const wrap = document.getElementById("scout-wrap");
      if (!wrap) return;
      try {
        const res = await fetch("/scout-briefing.json?t=" + Date.now());
        if (!res.ok) throw new Error("No briefing yet");
        const data = await res.json();

        const stories      = data.top_10 || [];
        const briefDate    = data.brief_date || (data.generated_at || "").slice(0,10) || "—";
        const totalScraped = data.total_scraped || 0;
        const totalPassed  = data.total_passed_filter || stories.length;
        const today        = new Date().toISOString().slice(0,10);
        const isFresh      = briefDate === today;
        const isSeen       = isScoutSeen(briefDate);
        const isNew        = isFresh && !isSeen && stories.length > 0;
        const statusClass  = isFresh ? "success" : "disabled";
        const statusLabel  = isFresh ? "LIVE" : "STALE";
        const genTime      = data.generated_at
          ? new Date(data.generated_at).toLocaleTimeString("en-US",{hour:"numeric",minute:"2-digit"})
          : "—";

        const sumEl = document.getElementById("sum-stories");
        if (sumEl) sumEl.textContent = stories.length > 0 ? stories.length : "—";

        const newBadgeHTML = isNew
          ? `<span class="new-badge"><span class="new-dot"></span>NEW</span>`
          : "";

        const storiesHTML = stories.length > 0
          ? stories.map((s,i) => `
            <div class="story-row">
              <div class="story-rank">${i+1}</div>
              <div class="story-body">
                <a class="story-title" href="${s.url||'#'}" target="_blank" rel="noopener">${s.title||'Untitled'}</a>
                <div class="story-meta">
                  <span class="story-badge ${scoutBadgeClass(s.ai_verification)}">${scoutBadgeLabel(s.ai_verification)}</span>
                  <span class="story-source">${s.source||''}</span>
                  ${s.category?`<span class="story-cat">${s.category}</span>`:''}
                </div>
              </div>
              <div class="story-score">${s.truth_score!=null?Math.round(s.truth_score):'—'}</div>
            </div>`).join("")
          : `<div class="no-brief">No stories yet — brief generates at 5:30 AM CST</div>`;

        const narrativeHTML = data.narrative
          ? `<div class="scout-narrative"><strong>Scout's Summary</strong>${data.narrative}</div>`
          : "";

        wrap.innerHTML = `
          <div class="section-label" style="padding-top:24px">Intelligence</div>
          <div class="cards">
            <div class="card" id="card-scout" onclick="scoutCardClick('${briefDate}')">
              <div class="card-header">
                <div class="agent-icon ${statusClass}" style="background:rgba(255,171,0,0.12)">\uD83D\uDCE1</div>
                <div class="card-info">
                  <div class="card-name" style="display:flex;align-items:center;gap:8px;">
                    Content Scout ${newBadgeHTML}
                  </div>
                  <div class="card-label">Daily AI Intelligence Brief</div>
                </div>
                <div class="card-right">
                  <span class="status-badge ${statusClass}">${statusLabel}</span>
                  <div class="card-score" style="color:#ffab00">${stories.length}</div>
                  <span class="chevron">\u25BC</span>
                </div>
              </div>
              <div class="card-detail">
                <div class="scout-stats">
                  <div class="scout-stat">
                    <div class="scout-stat-num">${totalScraped.toLocaleString()}</div>
                    <div class="scout-stat-label">Scraped</div>
                  </div>
                  <div class="scout-stat">
                    <div class="scout-stat-num">${totalPassed}</div>
                    <div class="scout-stat-label">Passed Filter</div>
                  </div>
                  <div class="scout-stat">
                    <div class="scout-stat-num">${genTime}</div>
                    <div class="scout-stat-label">Brief Time</div>
                  </div>
                </div>
                <div class="stories-list">
                  <div class="stories-list-title">Top Stories — ${briefDate}</div>
                  ${storiesHTML}
                </div>
                ${narrativeHTML}
              </div>
            </div>
          </div>`;

      } catch(e) {
        wrap.innerHTML = `
          <div class="section-label" style="padding-top:24px">Intelligence</div>
          <div class="cards">
            <div class="card">
              <div class="card-header">
                <div class="agent-icon disabled" style="background:rgba(255,171,0,0.08)">\uD83D\uDCE1</div>
                <div class="card-info">
                  <div class="card-name">Content Scout</div>
                  <div class="card-label">Brief generates at 5:30 AM CST</div>
                </div>
                <div class="card-right">
                  <span class="status-badge disabled">PENDING</span>
                  <div class="card-score dim">—</div>
                </div>
              </div>
            </div>
          </div>`;
      }
    }

    function scoutCardClick(briefDate) {
      toggleCard("scout");
      markScoutSeen(briefDate);
      const nb = document.querySelector("#card-scout .new-badge");
      if (nb) nb.remove();
    }
    // ─────────────────────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────────────────────────────────────
def patch(html: str) -> str:

    # ── 1. CSS ────────────────────────────────────────────────────────────────
    assert "</style>" in html, "No </style> found"
    html = html.replace("</style>", SCOUT_CSS + "</style>", 1)

    # ── 2. Stories item in summary bar ────────────────────────────────────────
    # Anchor: the closing of the Errors item — find by unique id then work outward
    # Pattern: id="sum-errors" ... </div> (closes summary-item) </div> (closes summary-bar)
    # Insert Stories item BEFORE the summary-bar's closing </div>
    m = re.search(r'id="sum-errors"', html)
    assert m, 'Could not find id="sum-errors" in HTML'
    # Find the two </div> tags after sum-errors: first closes .summary-num, second closes .summary-item
    pos = m.end()
    for _ in range(2):
        pos = html.index("</div>", pos) + len("</div>")
    # pos now points right after the closing </div> of the Errors summary-item
    # Insert our Stories item here (before the closing </div> of summary-bar)
    html = html[:pos] + STORIES_ITEM + html[pos:]

    # ── 3. Scout HTML placeholder before footer ───────────────────────────────
    footer_anchor = 'class="footer"'
    assert footer_anchor in html, "No footer div found"
    idx = html.index(footer_anchor)
    # Walk back to find the opening < of the footer div
    open_idx = html.rindex("<", 0, idx)
    html = html[:open_idx] + '<div id="scout-wrap"></div>' + html[open_idx:]

    # ── 4. Scout JS before last </script> ────────────────────────────────────
    idx = html.rfind("</script>")
    assert idx != -1, "No </script> found"
    html = html[:idx] + SCOUT_JS + "</script>" + html[idx + len("</script>"):]

    # ── 5. Update init calls ──────────────────────────────────────────────────
    # Handle both "loadStatus();\n    setInterval" and "loadStatus(); setInterval"
    html = re.sub(
        r'loadStatus\(\);\s*setInterval\(loadStatus,\s*60000\);',
        'loadStatus(); loadScout(); setInterval(function(){ loadStatus(); loadScout(); }, 60000);',
        html
    )

    return html


if __name__ == "__main__":
    src = MC_PATH.read_text(encoding="utf-8")
    out = patch(src)
    MC_PATH.write_text(out, encoding="utf-8")
    print(f"✅  Patched: {MC_PATH}")
    print(f"    {len(src):,} chars  →  {len(out):,} chars (+{len(out)-len(src):,})")
    print()
    print("Now push it live:")
    print("  cd ~/trainingrun-site")
    print('  git add mission-control.html')
    print('  git commit -m "feat: Content Scout Intelligence section + NEW indicator"')
    print("  git push")
