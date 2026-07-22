"""The boot splash shown while the server starts and the Hub reconnects.

It must not depend on the embedded server (that's the whole point — the server
isn't up yet), so the design PNG is inlined as a data URI and the whole page is
a self-contained HTML string. A small loader and a status line are drawn in the
strip the design left empty at the bottom; the status text is updated from
Python via `window.evaluate_js`.
"""

from __future__ import annotations

import base64

from paths import resource

_SPLASH_PNG = resource("desktop/assets/nestdeck-splash@2x.png")


def splash_html() -> str:
    data = base64.b64encode(_SPLASH_PNG.read_bytes()).decode()
    return _TEMPLATE.replace("__IMG__", f"data:image/png;base64,{data}")


# `setStatus` is called from Python during boot to update the line.
_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      html, body {
        margin: 0; height: 100%; overflow: hidden;
        background: #FAF9F7;
        font-family: 'Manrope', system-ui, sans-serif;
      }
      .art {
        position: fixed; inset: 0;
        background: #FAF9F7 url('__IMG__') center / contain no-repeat;
      }
      /* The design leaves ~140px clear at the bottom; the loader sits there. */
      .loader {
        position: fixed; left: 0; right: 0; bottom: 76px;
        display: flex; flex-direction: column; align-items: center; gap: 14px;
      }
      .dots { display: flex; gap: 8px; }
      .dots span {
        width: 9px; height: 9px; border-radius: 999px; background: #007AFF;
        animation: pulse 1.1s ease-in-out infinite;
      }
      .dots span:nth-child(2) { animation-delay: 0.16s; }
      .dots span:nth-child(3) { animation-delay: 0.32s; }
      @keyframes pulse {
        0%, 100% { opacity: 0.28; transform: scale(0.82); }
        40% { opacity: 1; transform: scale(1); }
      }
      #status {
        font-size: 14px; font-weight: 500; color: #8E8E93;
        letter-spacing: 0.01em;
      }
      @media (prefers-reduced-motion: reduce) {
        .dots span { animation: none; opacity: 0.7; }
      }
    </style>
  </head>
  <body>
    <div class="art"></div>
    <div class="loader">
      <div class="dots"><span></span><span></span><span></span></div>
      <div id="status">Démarrage…</div>
    </div>
    <script>
      function setStatus(text) {
        var el = document.getElementById('status');
        if (el) el.textContent = text;
      }
    </script>
  </body>
</html>"""
