"""Generate an HTML user profile report from official API data."""

from __future__ import annotations
import html
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

_USER_BASE = "https://civitai.red/user"
_POST_BASE = "https://civitai.red/posts"

_STOP = {
    "a","an","the","and","or","of","in","to","with","for","on","at","by","from",
    "is","it","its","as","be","was","are","were","has","have","that","this",
    "not","but","so","if","no","yes","up","do","my","me","you","we","he","she",
    "they","his","her","our","your","their","what","which","who","how","when",
    "where","why","all","any","more","most","some","such","than","then","now",
    "quality","best","high","low","score","masterpiece","detailed","ultra",
    "realistic","photorealistic","photo","style","art","beautiful","anime","digital","painting",
    "portrait","background","dark","light","white","black","image","render",
    "woman","man","girl","boy","face","hair","eyes","skin","body","wearing",
    "slightly","visible","shallow","depth","lighting","looking","small","long",
    "natural","texture","young","expression","field","soft","warm","golden",
}


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return iso[:10]


def _month(iso: str) -> str:
    return iso[:7]


def _img_rx(stats: dict) -> int:
    return sum(stats.get(k, 0) for k in
               ("likeCount", "heartCount", "laughCount", "cryCount", "dislikeCount"))


def _rx_badges(stats: dict) -> str:
    parts = []
    for key, emoji in [("likeCount","👍"),("heartCount","❤️"),
                        ("laughCount","😂"),("cryCount","😢"),
                        ("commentCount","💬")]:
        v = stats.get(key, 0)
        if v:
            parts.append(f'<span class="rx-chip">{emoji} {v}</span>')
    return " ".join(parts)


def _tokens(meta: dict | None) -> list[str]:
    if not meta:
        return []
    prompt = meta.get("prompt", "") or ""
    tokens = re.split(r"[,\s]+", prompt.lower())
    return [t for t in tokens if len(t) >= 3 and t not in _STOP and t.isalpha()]


def generate_html(data: dict, username: str,
                  output_path: str | Path | None = None, theme: str = "dark") -> str:
    profile        = data["profile"]
    images         = data["images"]
    images_by_post = data["images_by_post"]
    truncated      = data.get("truncated", False)

    # Sort images newest first (default view)
    sorted_images = sorted(images, key=lambda i: i.get("createdAt", ""), reverse=True)

    # --- aggregate stats ---
    total_rx  = sum(_img_rx(img.get("stats", {})) for img in images)
    n_posts   = len(images_by_post)
    avg_rx    = round(total_rx / len(images), 2) if images else 0

    # --- timeline (images per month) ---
    month_counts: Counter = Counter(
        _month(img.get("createdAt", "")) for img in images if img.get("createdAt")
    )
    sorted_months = sorted(month_counts.items())
    max_m = max((v for _, v in sorted_months), default=1)
    bars_html = "".join(
        f'<div class="bar-group">'
        f'<div class="bar" style="height:{max(2,round(n/max_m*100))}%" title="{m}: {n} images">'
        f'<span class="bar-val">{n}</span></div>'
        f'<div class="bar-label">{m[5:]}</div></div>'
        for m, n in sorted_months
    )

    # --- image cards ---
    img_cards = ""
    for img in sorted_images:
        url     = img.get("url", "")
        date    = _fmt_date(img.get("createdAt", ""))
        iso     = img.get("createdAt", "")
        pid     = img.get("postId", "")
        stats   = img.get("stats") or {}
        rx      = _img_rx(stats)
        rx_html = _rx_badges(stats)
        bm      = html.escape(img.get("baseModel") or "")
        img_tag = f'<img src="{html.escape(url)}" loading="lazy" alt="">' if url else '<div class="no-img">—</div>'
        link    = f"{_POST_BASE}/{pid}" if pid else "#"

        img_cards += f"""
        <div class="img-card" data-date="{html.escape(iso)}" data-rx="{rx}">
          <a href="{link}" target="_blank" class="img-thumb">{img_tag}</a>
          <div class="img-info">
            <div class="img-meta">{date}{f' · <span class="bm">{bm}</span>' if bm else ''}</div>
            <div class="img-rx">{rx_html or '<span class="no-rx">—</span>'}</div>
          </div>
        </div>"""

    # --- models used ---
    model_counts: Counter = Counter(
        img.get("baseModel", "Unknown") for img in images if img.get("baseModel")
    )
    top_models = model_counts.most_common(10)
    max_mc = top_models[0][1] if top_models else 1
    model_rows = "".join(
        f'<tr><td>{html.escape(m)}</td>'
        f'<td><div class="inline-bar" style="width:{max(2,round(n/max_mc*100))}%"></div><br>{n}</td></tr>'
        for m, n in top_models
    )

    # --- prompt keywords ---
    all_tokens: list[str] = []
    for img in images:
        all_tokens.extend(_tokens(img.get("meta")))
    top_words = Counter(all_tokens).most_common(60)
    max_wc = top_words[0][1] if top_words else 1
    word_cloud = " ".join(
        f'<span class="tag" style="font-size:{min(1.2,0.72+c/max_wc*0.5):.2f}rem">'
        f'{html.escape(w)} <sup>{c}</sup></span>'
        for w, c in top_words
    ) or '<span style="color:var(--muted)">No prompts found</span>'

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = f"""<!DOCTYPE html>
<html lang="en" data-theme="{theme}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@{html.escape(username)} — Civitai Profile Report</title>
<style>
:root,[data-theme="dark"]{{
  --bg:#0d0d1a;--surface:#16213e;--surface2:#1a1a2e;--border:#2a2a4a;
  --accent:#e879f9;--accent2:#818cf8;--text:#e2e8f0;--muted:#64748b;--r:10px;
}}
[data-theme="light"]{{
  --bg:#f1f5f9;--surface:#fff;--surface2:#f8fafc;--border:#e2e8f0;
  --accent:#9333ea;--accent2:#6366f1;--text:#1e293b;--muted:#94a3b8;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif;padding:20px 24px;max-width:1400px;margin:0 auto}}
a{{color:var(--accent2);text-decoration:none}}a:hover{{text-decoration:underline}}

.page-header{{background:linear-gradient(135deg,var(--surface),var(--surface2));border:1px solid var(--border);border-radius:var(--r);padding:24px 28px;margin-bottom:20px}}
.page-header h1{{font-size:1.6rem;font-weight:700}}
.page-header h1 a{{color:var(--accent)}}
.header-meta{{color:var(--muted);font-size:.85rem;margin-top:5px}}

.fetch-warning{{margin-bottom:16px;padding:10px 14px;background:#ca8a0418;border:1px solid #ca8a0455;border-radius:8px;font-size:0.85rem;color:#fbbf24}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:20px}}
.stat{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:14px 12px;text-align:center}}
.stat-val{{font-size:1.9rem;font-weight:700;color:var(--accent);line-height:1}}
.stat-label{{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-top:4px}}

.section{{margin-bottom:28px}}
.section-title{{font-size:1rem;font-weight:600;color:var(--accent2);padding-bottom:6px;border-bottom:1px solid var(--border);margin-bottom:14px;display:flex;align-items:center;justify-content:space-between}}

.chart{{display:flex;align-items:flex-end;gap:6px;height:130px;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:14px;overflow-x:auto}}
.bar-group{{min-width:28px;flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;height:100%;justify-content:flex-end}}
.bar{{background:linear-gradient(180deg,var(--accent),var(--accent2));width:100%;border-radius:4px 4px 0 0;display:flex;align-items:flex-start;justify-content:center;min-height:3px}}
.bar-val{{font-size:.65rem;font-weight:700;color:#fff;padding:2px 0}}
.bar-label{{font-size:.6rem;color:var(--muted);white-space:nowrap}}

.imgs-grid{{display:grid;grid-template-columns:repeat(8,1fr);gap:10px}}
@media(max-width:900px){{.imgs-grid{{grid-template-columns:repeat(4,1fr)}}}}
.img-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;transition:border-color .15s,transform .15s}}
.img-card:hover{{border-color:var(--accent2);transform:translateY(-2px)}}
.img-thumb{{display:block;aspect-ratio:1;overflow:hidden;background:#0a0a1a}}
.img-thumb img{{width:100%;height:100%;object-fit:cover;display:block}}
.no-img{{display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:.8rem}}
.img-info{{padding:7px 9px}}
.img-meta{{font-size:.68rem;color:var(--muted);margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bm{{color:var(--accent2)}}
.img-rx{{display:flex;gap:4px;flex-wrap:wrap}}
.rx-chip{{font-size:.72rem;background:#ffffff0a;border:1px solid var(--border);border-radius:10px;padding:1px 6px}}
.no-rx{{font-size:.68rem;color:var(--muted)}}

table{{width:100%;border-collapse:collapse;background:var(--surface);border-radius:var(--r);overflow:hidden;border:1px solid var(--border)}}
th{{background:var(--surface2);color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;padding:9px 14px;text-align:left}}
td{{padding:9px 14px;border-top:1px solid var(--border);font-size:.88rem}}
tr:hover td{{background:#ffffff06}}
.inline-bar{{display:inline-block;height:8px;background:linear-gradient(90deg,var(--accent2),var(--accent));border-radius:4px;vertical-align:middle;margin-right:6px;min-width:2px}}

.global-tags{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:14px 16px;line-height:2.2}}
.tag{{display:inline-block;background:#818cf811;border:1px solid #818cf833;border-radius:6px;padding:1px 7px;font-size:.72rem;color:var(--accent2);margin:2px}}

.sort-btn{{background:var(--btn,#7c3aed);border:none;border-radius:8px;color:#fff;cursor:pointer;padding:5px 13px;font-size:.8rem;font-weight:600;transition:opacity .15s}}
.sort-btn:hover{{opacity:.85}}
.img-card.hidden{{display:none}}
.pagination{{display:flex;align-items:center;justify-content:center;gap:10px;margin-top:18px;flex-wrap:wrap}}
.pg-btn{{background:var(--surface);border:1px solid var(--border);border-radius:8px;color:var(--text);cursor:pointer;padding:6px 14px;font-size:.85rem;transition:border-color .15s}}
.pg-btn:hover{{border-color:var(--accent2)}}
.pg-btn:disabled{{opacity:.35;cursor:not-allowed}}
.pg-info{{font-size:.82rem;color:var(--muted)}}
.pg-input{{width:54px;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.82rem;padding:5px 8px;text-align:center}}

.footer{{text-align:center;color:var(--muted);font-size:.72rem;margin-top:40px;padding-top:14px;border-top:1px solid var(--border)}}
</style>
</head>
<body>

<div class="page-header">
  <h1><a href="{_USER_BASE}/{html.escape(username)}" target="_blank">@{html.escape(username)}</a></h1>
  <div class="header-meta">{profile.get("modelCount",0)} models &nbsp;·&nbsp; <a href="{_USER_BASE}/{html.escape(username)}" target="_blank">civitai.red</a></div>
</div>
{'<div class="fetch-warning">⚠️ Fetch stopped early due to an API error — results may be incomplete (' + str(len(images)) + ' images retrieved).</div>' if truncated else ''}
<div class="stats-grid">
  <div class="stat"><div class="stat-val">{n_posts}</div><div class="stat-label">Posts</div></div>
  <div class="stat"><div class="stat-val">{len(images):,}</div><div class="stat-label">Images</div></div>
  <div class="stat"><div class="stat-val">{total_rx:,}</div><div class="stat-label">Total reactions</div></div>
  <div class="stat"><div class="stat-val">{avg_rx}</div><div class="stat-label">Avg rx/image</div></div>
  <div class="stat"><div class="stat-val">{len(top_models)}</div><div class="stat-label">Models used</div></div>
</div>

<div class="section">
  <div class="section-title">Base models used</div>
  <table><thead><tr><th>Model</th><th>Images</th></tr></thead>
  <tbody>{model_rows}</tbody></table>
</div>

<div class="section">
  <div class="section-title">Most used prompt keywords</div>
  <div class="global-tags">{word_cloud}</div>
</div>

<div class="section">
  <div class="section-title">Images per month</div>
  <div class="chart">{bars_html}</div>
</div>

<div class="section">
  <div class="section-title">
    <span id="gallery-title">Images — chronological ({len(images)})</span>
    <button class="sort-btn" onclick="toggleSort()">⭐ Sort by reactions</button>
  </div>
  <div class="imgs-grid" id="gallery">{img_cards}</div>
  <div class="pagination" id="pagination">
    <button class="pg-btn" id="pg-prev" onclick="changePage(-1)">← Prev</button>
    <span class="pg-info">Page <input class="pg-input" id="pg-input" type="number" min="1" onchange="goToPage(this.value)"> / <span id="pg-total"></span></span>
    <button class="pg-btn" id="pg-next" onclick="changePage(1)">Next →</button>
  </div>
</div>

<div class="footer">Generated {now} · <a href="{_USER_BASE}/{html.escape(username)}" target="_blank">@{html.escape(username)}</a> · civitai.com/api/v1 · <a href="https://github.com/BetweenFloors/civit_users" target="_blank">GitHub</a></div>

<script>
const PAGE_SIZE = 64;
let byRx = false;
let currentPage = 1;
let allCards = [];

function initGallery() {{
  allCards = Array.from(document.querySelectorAll('.img-card'));
  renderPage(1);
}}

function renderPage(page) {{
  const total = Math.ceil(allCards.length / PAGE_SIZE);
  currentPage = Math.max(1, Math.min(page, total));
  const start = (currentPage - 1) * PAGE_SIZE;
  const end = start + PAGE_SIZE;
  allCards.forEach((c, i) => c.classList.toggle('hidden', i < start || i >= end));
  document.getElementById('pg-input').value = currentPage;
  document.getElementById('pg-total').textContent = total;
  document.getElementById('pg-prev').disabled = currentPage === 1;
  document.getElementById('pg-next').disabled = currentPage === total;
  window.scrollTo({{top: document.getElementById('gallery').offsetTop - 80, behavior: 'smooth'}});
}}

function changePage(dir) {{ renderPage(currentPage + dir); }}
function goToPage(val) {{ renderPage(parseInt(val)); }}

function toggleSort() {{
  byRx = !byRx;
  const grid = document.getElementById('gallery');
  const title = document.getElementById('gallery-title');
  const btn = event.target;
  allCards.sort((a, b) => byRx
    ? parseInt(b.dataset.rx) - parseInt(a.dataset.rx)
    : b.dataset.date.localeCompare(a.dataset.date)
  );
  allCards.forEach(c => grid.appendChild(c));
  title.textContent = byRx
    ? 'Images — by reactions ({len(images)})'
    : 'Images — chronological ({len(images)})';
  btn.textContent = byRx ? '🕐 Sort by date' : '⭐ Sort by reactions';
  renderPage(1);
}}

window.addEventListener('DOMContentLoaded', initGallery);
</script>
</body>
</html>"""

    if output_path:
        Path(output_path).write_text(doc, encoding="utf-8")
    return doc
