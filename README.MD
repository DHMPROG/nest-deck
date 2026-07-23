# Nest Deck

Turn a Google Nest Hub — or any tablet with a browser, like an iPad — into a
colourful, tactile control surface: a self-hosted "Stream Deck" you configure
from a desktop app and cast (or simply open) over your LAN.

Tap a tile to fire an action: a keyboard macro, launch an app, an OBS scene, a
Spotify/media key, a meeting shortcut, a webhook… Design your pages in a visual
editor; the Hub updates live.

> **Status:** functional. The desktop app runs, casts to the Hub, and every
> action type works. Grab `NestDeck.exe` from the
> [Releases](../../releases) page, or run from source (below).

---

## Features

- **iOS-home-screen feel** — pastel tiles, springy motion, light & dark themes.
- **Cast to the Nest Hub** — finds the device on your network and remembers it,
  reconnecting automatically on launch.
- **No Hub? No problem** — open the deck URL on an iPad or any tablet for the
  same touch deck in the browser.
- **Visual editor** — drag actions onto a grid (3×5 up to 6×6 per page),
  organise pages and profiles, all changes live-sync to the Hub over SSE.
- **Real, pre-configured actions** out of the box:
  - Media / volume via system media keys — works with Spotify, YouTube, VLC…
    with zero setup
  - Keyboard macros and app launchers (with an installed-app picker)
  - OBS scenes & controls (OBS WebSocket)
  - Spotify Web API
  - Meet / Zoom / Teams shortcuts
  - Plain HTTP webhooks
- **Make your own** — define custom macros, launchers and categories, pick any
  Phosphor icon.
- **First-launch wizard** that walks you through casting and building your deck.

---

## How it works

Everything runs on your PC. A small web server hosts two views — the **Deck**
(what the Hub shows) and the **Editor** (the desktop window) — and translates tile
taps into keystrokes, app launches, OBS/Spotify calls, etc. The Deck is cast to
the Hub as a web page; the Hub stores nothing.

Because macros and launchers act on the machine running the backend, the backend
must run **natively on your PC** for those to work — which is exactly what the
desktop app does.

---

## Run it (users)

### From a release (once published)

1. Download `NestDeck.exe` from the [Releases](../../releases) page.
2. Run it. On first launch, the setup wizard helps you find your Hub and cast.
3. Optionally enable *Start with Windows* from the editor.

### From source (works today)

Requires **Python 3.11+** and **Node 18+**.

```bash
# 1. Build the frontend
cd frontend
npm install
npm run build
cd ..

# 2. Install the desktop app's Python deps
python -m venv .venv
# Windows:
.\.venv\Scripts\pip install -r desktop/requirements.txt
# macOS/Linux:
# ./.venv/bin/pip install -r desktop/requirements.txt

# 3. Launch the desktop app (window + embedded server + auto-cast)
.\.venv\Scripts\python desktop/nestdeck.py
```

The window shows the Editor. Use the **Cast** button (top right) to pick your Hub
— it's remembered for next time.

### No Nest Hub? Use an iPad (or any tablet)

The Deck is just a web page, so any device on your Wi-Fi can be the control
surface. On your iPad or Android tablet, open:

```
http://<your-PC-IP>:8770/
```

(The exact address is shown in the editor's cast panel as the deck URL.) In
Safari, use **Share → Add to Home Screen** to get a fullscreen, app-like deck.
Tiles still trigger everything on the PC — macros, launches, OBS — exactly as
they would from a Hub.

> A deeper guide (firewall, OBS/Spotify setup, Docker, troubleshooting) lives in
> [`RUNNING.md`](RUNNING.md).

---

## Which actions work where

| Action type | Needs |
| --- | --- |
| Media / volume | Nothing — system media keys |
| Keyboard macros, launchers | The backend running natively on the PC you want to control |
| OBS | OBS running with its WebSocket server enabled |
| Spotify | A one-off OAuth setup (see `RUNNING.md`) |
| Meet / Zoom / Teams | The meeting window focused on the PC |
| HTTP webhook | A reachable URL |

Running the backend in Docker (a Linux container) means **macros, launchers and
the app picker won't work** — the container has no keyboard or installed apps.
Docker is best when you only use OBS / Spotify / HTTP actions.

---

## Contributing

Contributions are welcome. The project is a monorepo with three parts:

```
backend/    FastAPI + SQLModel (SQLite). REST + SSE. Action handlers.
frontend/   SvelteKit + Svelte 5 + Tailwind 4. Deck (/) and Editor (/editor).
desktop/    The .exe launcher: serves the build + backend, opens a pywebview
            window, handles casting (pychromecast).
```

### Dev setup

Run the two dev servers in separate terminals:

```bash
# Backend (auto-reload) — http://127.0.0.1:8000, docs at /docs
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# Frontend (hot reload) — http://127.0.0.1:5173, proxies /api to the backend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/` for the Deck and `/editor` for the Editor.

### Before you push

- **Type-check the frontend:** `npm run check` (must be 0 errors).
- **Keep colours in the design tokens.** `frontend/src/lib/theme.ts` is the
  single source of truth; use the Tailwind utilities it generates (`bg-cat-*`,
  `bg-app-*`, …) rather than hardcoding hex.
- **Action handlers must never raise** — catch and return
  `{"status": "error", "message": ...}` so an offline service degrades to an
  error tile instead of a 500.
- **Respect `prefers-reduced-motion`** for any new animation.

### Adding an action type

1. Add a handler in `backend/app/services/` — `async def handle(action) -> dict`.
2. Register it in `backend/app/services/registry.py`.
3. Add its form fields to `frontend/src/lib/components/editor/ActionEditorModal.svelte`.

Issues and ideas are welcome on the tracker. Please keep PRs focused and describe
what you verified.

---

## Tech stack

Svelte 5 · SvelteKit · Tailwind CSS 4 · TypeScript · FastAPI · SQLModel · SQLite ·
pychromecast · pywebview · Phosphor Icons · Manrope.

## License

MIT.
