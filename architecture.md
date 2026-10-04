# Architecture — TikTok Downloader

## System Overview

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐     ┌────────┐
│   Browser   │────▶│  FastAPI      │────▶│  yt-dlp   │────▶│ TikTok │
│ (HTML/JS)   │◀────│  Backend      │◀────│ Extractor │◀────│   API  │
└─────────────┘     └──────┬───────┘     └───────────┘     └────────┘
                           │
                    ┌──────┴───────┐
                    │  Redis/RQ    │  (Phase 4+)
                    │  Job Queue   │
                    └──────────────┘
```

## Data Flow

### Single Video Download
1. User pastes TikTok URL in frontend
2. Frontend sends `POST /resolve { "url": "..." }`
3. Backend calls yt-dlp `extract_info(url, download=False)`
4. Backend normalizes format list → SD/HD mapping
5. Returns JSON: `{ thumbnail, author, caption, formats: { sd, hd } }`
6. User clicks "Download SD" or "Download HD"
7. Frontend calls `GET /download?formatId=...`
8. Backend streams video bytes from TikTok CDN → browser with correct headers

### Profile / Batch Download (Phase 3-4)
1. Frontend sends `POST /resolve { "url": "..." }` (profile URL)
2. Backend detects `/@username`, starts playlist extraction
3. Returns paginated list of videos
4. User selects videos, clicks "Download Selected"
5. Frontend calls `POST /batch { "format_ids": [...] }`
6. Backend enqueues job → Redis worker processes → returns zip

## Key Design Decisions

### Why proxy the download?
TikTok CDN URLs expire quickly and require specific HTTP headers (User-Agent, Referer). If the browser hits the CDN directly, downloads often fail. The backend's proxy ensures reliable delivery.

### Why not expose CDN URLs?
They're time-limited and header-sensitive. Letting the browser handle them directly would mean:
- Stale URLs by the time the user clicks download
- Failed requests due to missing Referer header
- No download tracking (Phase 5)

### Format normalization
yt-dlp returns 6-9 formats per video. Most are chunk-split variants (-0, -1 suffixes). We normalize to two choices:
- **SD**: format_id=`download` (watermarked, always present, smallest)
- **HD**: best of remaining formats based on resolution (720p+)

## Project Structure (Phased)

```
tiktok/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, routes
│   ├── extractor.py          # yt-dlp wrapper (resolve, download helpers)
│   ├── formats.py            # Format normalization logic
│   ├── playwright_extractor.py  # headless-Chromium fallback extractor
│   ├── download_manager.py   # queue worker thread
│   ├── database.py           # SQLite queue store
│   ├── cookies.py            # TikTok cookie file handling
│   └── static/               # BUILD OUTPUT (committed) — vite writes here
├── frontend/                 # React 19 + Vite source
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/       # Navbar, SearchBar, VideoResult, QueuePanel, …
│   │   ├── styles/           # tokens.css, base.css
│   │   └── assets/           # generated halftone art (scripts/gen-art.mjs)
│   └── scripts/gen-art.mjs    # regenerates the dither SVGs
├── tests/                    # pytest suite
├── phase0_test.py            # Throwaway feasibility script
├── requirements.txt
├── requirements-dev.txt
├── docker-compose.yml        # Phase 6
├── Dockerfile                # Phase 6
├── AGENT.md
├── architecture.md
├── phases.md
└── plans.md
```

### Frontend build
`npm run build` inside `frontend/` writes to `app/static` (`emptyOutDir`). FastAPI reads
`app/static/index.html` **once at import**, so the server must be restarted after every
rebuild — the asset filenames are content-hashed and the old ones are deleted.

### Routing and 404s
There is no client router. `GET /` serves the app; every other path falls through to a
catch-all registered last in `app/main.py`, which serves the same shell **with a 404 status**
so deep links resolve and the client renders `components/NotFound.jsx`. Paths whose first
segment is an API prefix (`resolve`, `download`, `queue`, `auth`, `assets`) keep a JSON 404
instead, so API clients never receive HTML.

### Design system
Reference language: bencho.dev and obsidianui.dev. `frontend/src/styles/tokens.css` holds a
white canvas (`--bg`), grey-fill panels (`--panel`, `--panel-2`) used for depth instead of
shadows, and colour reserved strictly for status (`--ok`, `--bad`, `--busy`). Type is Inter
and Inter Tight (display) with Geist Mono for machine strings, all self-hosted through
`@fontsource-variable`.

There is deliberately **no animation library**. The micro-interactions live in
`styles/base.css`: the 0.97 press, the leading-icon nudge, key hints that depress while
⌘/Ctrl is held, a shimmer skeleton plus indeterminate bar instead of a spinner, and row
actions that fade in on hover. ⌘K opens `components/CommandPalette.jsx`, which is a view
over real app actions supplied by `App.jsx`.

## Dependencies (current)
- `yt-dlp` + `curl_cffi` (for TikTok impersonation)
- `fastapi` + `uvicorn` + `jinja2`
- `playwright` (headless Chromium fallback extractor)
- Frontend: `react`, `@phosphor-icons/react`, `@fontsource-variable/inter`, `@fontsource-variable/inter-tight`, `@fontsource-variable/geist-mono`
- Dev: `pytest` + `httpx` (see `requirements-dev.txt`)
