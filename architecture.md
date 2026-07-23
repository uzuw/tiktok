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
│   ├── main.py          # FastAPI app, routes
│   ├── extractor.py     # yt-dlp wrapper (resolve, download helpers)
│   ├── formats.py       # Format normalization logic
│   └── templates/
│       └── index.html   # Single-page frontend
├── phase0_test.py       # Throwaway feasibility script
├── requirements.txt
├── docker-compose.yml   # Phase 6
├── Dockerfile           # Phase 6
├── AGENT.md
├── architecture.md
├── phases.md
└── plans.md
```

## Dependencies (current)
- `yt-dlp` + `curl_cffi` (for TikTok impersonation)
- `fastapi` + `uvicorn`
- `httpx` or `aiohttp` (for proxying download bytes)
