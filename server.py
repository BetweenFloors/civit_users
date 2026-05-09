"""
Local web UI for civitai-user reporter.

Run:  python server.py
      python server.py --port 8080
"""

from __future__ import annotations

import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import argparse

from fetch import fetch_all
from report import generate_html

_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Civitai User Reporter</title>
<style>
  :root {
    --bg:#0d0d1a; --surface:#16213e; --border:#2a2a4a;
    --accent:#e879f9; --accent2:#818cf8; --text:#e2e8f0; --muted:#64748b;
    --input-bg:#0d0d1a; --btn:#7c3aed; --btn-hover:#6d28d9;
    --error:#f87171; --success:#4ade80;
  }
  [data-theme="light"] {
    --bg:#f8fafc; --surface:#fff; --border:#e2e8f0;
    --accent:#9333ea; --accent2:#6366f1; --text:#1e293b; --muted:#94a3b8;
    --input-bg:#fff; --btn:#7c3aed; --btn-hover:#6d28d9;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text); font-family:system-ui,sans-serif;
         min-height:100vh; display:flex; flex-direction:column; align-items:center;
         justify-content:center; padding:24px; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:14px;
          padding:36px 40px; width:100%; max-width:480px; box-shadow:0 8px 40px #0006; }
  h1 { font-size:1.5rem; font-weight:700; margin-bottom:6px;
       background:linear-gradient(90deg,var(--accent),var(--accent2));
       -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .subtitle { color:var(--muted); font-size:0.85rem; margin-bottom:28px; }
  label { display:block; font-size:0.8rem; font-weight:600; color:var(--muted);
          text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px; }
  input[type=text], input[type=password], select {
    width:100%; background:var(--input-bg); border:1px solid var(--border);
    border-radius:8px; color:var(--text); font-size:0.95rem;
    padding:10px 12px; outline:none; transition:border-color .15s;
  }
  input:focus, select:focus { border-color:var(--accent2); }
  .field { margin-bottom:18px; }
  .row { display:flex; gap:12px; }
  .row .field { flex:1; }
  .hint { font-size:0.72rem; color:var(--muted); margin-top:5px; }
  .hint a { color:var(--accent2); }
  .warning { margin-top:12px; padding:9px 12px; background:#ca8a0418;
    border:1px solid #ca8a0455; border-radius:8px; font-size:0.78rem;
    color:#fbbf24; line-height:1.4; }

  button[type=submit] {
    width:100%; padding:12px; background:var(--btn); color:#fff;
    border:none; border-radius:8px; font-size:1rem; font-weight:600;
    cursor:pointer; transition:background .15s; margin-top:4px;
    display:flex; align-items:center; justify-content:center; gap:8px;
  }
  button[type=submit]:hover { background:var(--btn-hover); }
  button[type=submit]:disabled { opacity:.5; cursor:not-allowed; }

  .spinner { width:18px; height:18px; border:2px solid #ffffff44;
             border-top-color:#fff; border-radius:50%; animation:spin .7s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }

  .msg { margin-top:16px; padding:10px 14px; border-radius:8px;
         font-size:0.88rem; display:none; }
  .msg.error { background:#f8717122; border:1px solid var(--error); color:var(--error); }
  .msg.success { background:#4ade8022; border:1px solid var(--success); color:var(--success); }

  .theme-toggle { position:fixed; top:18px; right:18px; background:var(--surface);
    border:1px solid var(--border); border-radius:20px; padding:6px 14px;
    cursor:pointer; font-size:0.8rem; color:var(--muted); }
  .theme-toggle:hover { color:var(--text); }

  .token-row { display:flex; gap:8px; }
  .token-row input { flex:1; }
  .eye-btn { background:none; border:1px solid var(--border); border-radius:8px;
    color:var(--muted); cursor:pointer; padding:0 12px; font-size:1rem; }
  .eye-btn:hover { color:var(--text); }
  .toggle-row { display:flex; gap:8px; }
  .toggle-btn { flex:1; padding:9px; background:none; border:1px solid var(--border);
    border-radius:8px; color:var(--muted); cursor:pointer; font-size:0.88rem;
    transition:all .15s; }
  .toggle-btn:hover { border-color:var(--accent2); color:var(--text); }
  .toggle-btn.active { background:var(--btn); border-color:var(--btn); color:#fff; }
</style>
</head>
<body>

<button class="theme-toggle" onclick="toggleTheme()">🌙 / ☀️</button>

<div class="card">
  <h1>Civitai User Reporter</h1>
  <p class="subtitle">Generate a full HTML report for any Civitai user — based on the official API.</p>

  <form id="form" onsubmit="handleSubmit(event)">
    <div class="field">
      <label>API Token</label>
      <div class="token-row">
        <input type="password" id="token" placeholder="ab12cd34…" autocomplete="off" required>
        <button type="button" class="eye-btn" onclick="toggleToken()" title="Show/hide">👁</button>
      </div>
      <div class="hint">
        Generate a token at
        <a href="https://civitai.red/user/account" target="_blank">civitai.red → account settings</a>.
        Stored only in your browser (localStorage).
      </div>
    </div>

    <div class="row">
      <div class="field">
        <label>Username</label>
        <input type="text" id="username" placeholder="BetweenFloors" required>
      </div>
      <div class="field">
        <label>Theme</label>
        <select id="theme_sel">
          <option value="dark">🌙 Dark</option>
          <option value="light">☀️ Light</option>
        </select>
      </div>
    </div>

    <div class="field">
      <label>Content</label>
      <div class="toggle-row">
        <button type="button" class="toggle-btn active" id="btn-all" onclick="setContent('all')">🔞 All content</button>
        <button type="button" class="toggle-btn" id="btn-sfw" onclick="setContent('sfw')">🟢 SFW only</button>
      </div>
      <input type="hidden" id="browsing_level" value="31">
    </div>

    <button type="submit" id="btn">
      <span id="btn-text">Generate report</span>
    </button>
    <div class="warning">
      ⚠️ Large profiles (1000+ images) may take 30–60 seconds — please wait.
    </div>
  </form>

  <div class="msg error" id="err"></div>
  <div class="msg success" id="ok"></div>
</div>

<script>
const LS_TOKEN = 'civitai_user_token';
const LS_THEME = 'civitai_ui_theme';

const saved = localStorage.getItem(LS_TOKEN);
if (saved) document.getElementById('token').value = saved;

const savedTheme = localStorage.getItem(LS_THEME) || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem(LS_THEME, next);
}

function setContent(val) {
  document.getElementById('browsing_level').value = val === 'sfw' ? '1' : '31';
  document.getElementById('btn-all').classList.toggle('active', val === 'all');
  document.getElementById('btn-sfw').classList.toggle('active', val === 'sfw');
}

function toggleToken() {
  const el = document.getElementById('token');
  el.type = el.type === 'password' ? 'text' : 'password';
}

async function handleSubmit(e) {
  e.preventDefault();
  const token          = document.getElementById('token').value.trim();
  const username       = document.getElementById('username').value.trim();
  const theme          = document.getElementById('theme_sel').value;
  const browsing_level = parseInt(document.getElementById('browsing_level').value);

  localStorage.setItem(LS_TOKEN, token);

  const btn     = document.getElementById('btn');
  const btnText = document.getElementById('btn-text');
  btn.disabled  = true;
  btnText.innerHTML = '<span class="spinner"></span> Loading…';
  document.getElementById('err').style.display = 'none';
  document.getElementById('ok').style.display  = 'none';

  try {
    const resp = await fetch('/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token, username, theme, browsing_level}),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);

    const blob = new Blob([data.html], {type: 'text/html'});
    const url  = URL.createObjectURL(blob);
    window.open(url, '_blank');

    const ok = document.getElementById('ok');
    ok.textContent = `✓ Report for @${username} generated — opened in a new tab`;
    ok.style.display = 'block';
  } catch(err) {
    const el = document.getElementById('err');
    el.textContent = '✗ ' + err.message;
    el.style.display = 'block';
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Generate report';
  }
}
</script>
</body>
</html>"""


class _Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        self._respond(200, "text/html; charset=utf-8", _UI.encode())

    def do_POST(self):
        if urlparse(self.path).path != "/generate":
            self._respond(404, "text/plain", b"Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        try:
            payload  = json.loads(body)
            token          = payload.get("token", "").strip()
            username       = payload.get("username", "").strip()
            theme          = payload.get("theme", "dark")
            browsing_level = int(payload.get("browsing_level", 31))

            data     = fetch_all(token, username, browsing_level)
            html_out = generate_html(data, username, theme=theme)
            self._json(200, {"html": html_out})

        except Exception:
            self._json(500, {"error": traceback.format_exc().splitlines()[-1]})

    def _respond(self, code: int, ctype: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self._respond(code, "application/json; charset=utf-8", body)


def main():
    parser = argparse.ArgumentParser(description="Civitai User Reporter")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), _Handler)
    url    = f"http://localhost:{args.port}"
    print(f"  Civitai User Reporter  →  {url}")
    print("  Ctrl+C to stop\n")

    if not args.no_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
