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
│   ├── main.py                # FastAPI app, routes, middleware stack
│   ├── net.py                 # outbound policy: host allowlist, pacing, CDN client
│   ├── security.py            # inbound policy: auth, rate limit, security headers
│   ├── extractor.py           # yt-dlp wrapper + URL validation
│   ├── playwright_extractor.py# headless-Chromium fallback, session cookie harvest
│   ├── formats.py             # format selection
│   ├── download_manager.py    # queue + background worker
│   ├── database.py            # SQLite queue store
│   ├── cookies.py             # Netscape cookie file handling
│   └── static/                # BUILD OUTPUT (committed) — vite writes here
├── frontend/                  # React 19 + Vite source
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/        # Navbar, SearchBar, VideoResult, QueuePanel,
│   │   │                      # ResultSkeleton, CommandPalette, SettingsModal, NotFound
│   │   ├── hooks/             # useModifierHeld
│   │   └── styles/            # tokens.css, base.css
│   └── public/favicon.svg
├── tests/                     # pytest suite
├── docs/screenshots/          # images used by the README
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh
└── architecture.md
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

### Security model
Two modules hold the policy, and both are enforced at the edges rather than sprinkled
through handlers.

`app/net.py` — **outbound**. Every outbound URL reaches the server as a request parameter,
so none is fetched before `check_outbound_url()` passes: scheme must be http(s), the host
must be on the TikTok allowlist (label-boundary match, so `eviltiktok.com` fails), and the
name must resolve only to public addresses (rejecting loopback, link-local and RFC1918, which
also blunts DNS rebinding). Enforced in `/download`, in `/queue`, and again in the queue
worker. Without it the download endpoint is a general-purpose fetcher — it would return the
body of any address the server can reach.

The same module owns the shared `curl_cffi` session and the token bucket that paces
outbound TikTok traffic (`SAVETOK_OUTBOUND_RPS`, default 1/s). Pacing is deliberate latency:
faster increases the odds of an IP block.

`app/security.py` — **inbound**. `BasicAuthMiddleware` (active only when `SAVETOK_PASSWORD`
is set; username ignored, password compared with `hmac.compare_digest`), `RateLimitMiddleware`
(sliding window per IP, static assets excluded so the budget is spent on API calls), and
`SecurityHeadersMiddleware` (nosniff, frame-deny, no-referrer, and a CSP that allows no inline
or eval'd script). Middleware is added innermost-first, so CORS ends up outermost and answers
preflights before auth can challenge them.

Also: cookie payloads are capped at 256 KiB before parsing, and `/queue/{id}/file` refuses any
stored path that resolves outside the queue directory. The container runs as uid 10001.

| Env var | Default | Effect |
|---|---|---|
| `SAVETOK_PASSWORD` | unset | Auth gate; unset disables it |
| `SAVETOK_RATE_LIMIT` | 240 | Inbound requests/min per IP |
| `SAVETOK_OUTBOUND_RPS` | 1 | Outbound TikTok requests/sec |
| `SAVETOK_OUTBOUND_BURST` | 3 | Allowance above the steady rate |
| `SAVETOK_TRUST_PROXY` | unset | Honour `X-Forwarded-For` (only behind a proxy) |

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
