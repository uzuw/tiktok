"""FastAPI application for TikTok video downloader."""

import asyncio
import os
import tempfile
from pathlib import Path

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.cookies import clear_cookies, has_cookies, load_cookies, save_cookies
from app.download_manager import (
    QUEUE_DIR,
    clear_queue,
    enqueue,
    get_item,
    list_items,
    remove_item,
)
from app.extractor import extract_info, is_video_url
from app.formats import pick_best_format
from app.net import BlockedTarget, cdn_get, check_outbound_url, pace_outbound, stream_to_file
from app.playwright_extractor import get_session_cookies, playwright_extract
from app.security import BasicAuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware


app = FastAPI(title="TikTok Downloader")

# Innermost first: the outermost added is the one that sees a request first, so
# CORS goes last and therefore answers preflights before auth can challenge them.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    limit=int(os.getenv("SAVETOK_RATE_LIMIT", "240")),
)
_auth_password = os.getenv("SAVETOK_PASSWORD", "")
if _auth_password:
    app.add_middleware(BasicAuthMiddleware, password=_auth_password)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    with open(os.path.join(static_dir, "index.html")) as f:
        SPA_HTML = f.read()
else:
    SPA_HTML = None


class ResolveRequest(BaseModel):
    url: str


class QueueRequest(BaseModel):
    url: str
    format_id: str = ""


class CookieRequest(BaseModel):
    # A Netscape cookie file is a few KB. Capped so an oversized paste is
    # rejected before it is parsed or written to disk.
    cookies: str = Field(max_length=256 * 1024)


@app.get("/", response_class=HTMLResponse)
async def index():
    if SPA_HTML:
        return HTMLResponse(SPA_HTML)
    return HTMLResponse(open("app/templates/index.html").read())


@app.get("/favicon.svg", include_in_schema=False)
async def favicon():
    """Vite emits public/favicon.svg to the static root, but only /assets is
    mounted through StaticFiles — serve the icon explicitly."""
    path = os.path.join(static_dir, "favicon.svg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, media_type="image/svg+xml")


@app.post("/resolve")
async def resolve_endpoint(req: ResolveRequest):
    """Resolve a TikTok URL into metadata + best-quality format_id."""
    url = req.url.strip()
    cookiefile = load_cookies()
    loop = asyncio.get_event_loop()

    if not is_video_url(url):
        raise HTTPException(status_code=400, detail="Not a valid TikTok video URL")

    info = None
    try:
        info = await loop.run_in_executor(None, extract_info, url, cookiefile)
    except Exception:
        info = None

    if info is None:
        try:
            info = await playwright_extract(url, cookiefile)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Extraction failed: {e}")

    formats = info.get("formats") or []
    caption = info.get("description") or info.get("title") or ""
    is_playwright = info.get("_source") == "playwright"

    if is_playwright:
        # Prefer play_addr: download_addr is signed for a session token the CDN
        # rejects for server-side fetches, so it 403s even with the cookie jar.
        format_id = ""
        for f in formats:
            if f.get("format_id") == "play_addr":
                format_id = f["url"]
                break
        if not format_id:
            for f in formats:
                if f.get("format_id") == "download_addr":
                    format_id = f["url"]
                    break
        return {
            "id": info.get("id", ""),
            "thumbnail": info.get("thumbnail", ""),
            "author": info.get("uploader") or info.get("channel", ""),
            "caption": caption[:500],
            "duration": info.get("duration", 0),
            "format_id": format_id,
        }

    best = pick_best_format(formats)
    return {
        "id": info.get("id", ""),
        "thumbnail": info.get("thumbnail", ""),
        "author": info.get("uploader") or info.get("channel", ""),
        "caption": caption[:500],
        "duration": info.get("duration", 0),
        "format_id": best["format_id"] if best else "",
    }


@app.get("/auth/status")
async def auth_status():
    return {"authenticated": has_cookies()}


@app.post("/auth/cookies")
async def set_cookies(req: CookieRequest):
    text = req.cookies.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Cookie text is empty")
    # Basic format check: should look like Netscape cookie file
    if not any("\t" in line for line in text.splitlines() if line.strip() and not line.startswith("#")):
        raise HTTPException(
            status_code=400,
            detail="Invalid cookie format. Export using a 'cookies.txt' extension (Netscape format).",
        )
    save_cookies(text)
    return {"authenticated": True}


@app.delete("/auth/cookies")
async def remove_cookies():
    clear_cookies()
    return {"authenticated": False}


@app.post("/queue")
async def queue_add(req: QueueRequest):
    """Add a video URL to the download queue."""
    url = req.url.strip()
    if not is_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid TikTok URL")
    fmt = req.format_id.strip() or ""
    if fmt.startswith("http"):
        try:
            check_outbound_url(fmt)
        except BlockedTarget as exc:
            raise HTTPException(status_code=400, detail=f"Blocked target: {exc}") from exc
    item = enqueue(url, fmt, title="")
    return item


@app.get("/queue")
async def queue_list():
    """List all queue items."""
    return {"items": list_items()}


@app.get("/queue/{item_id}")
async def queue_item(item_id: str):
    """Get single queue item status."""
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@app.delete("/queue")
async def queue_clear():
    """Clear all queue items."""
    count = clear_queue()
    return {"ok": True, "cleared": count}


@app.delete("/queue/{item_id}")
async def queue_delete(item_id: str):
    """Remove a queue item."""
    if not remove_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@app.get("/queue/{item_id}/file")
async def queue_file(item_id: str):
    """Serve a completed queue item's file."""
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    if item["status"] != "completed" or not item.get("file_path"):
        raise HTTPException(status_code=400, detail="File not ready")
    # The path comes from our own database, but confine it to the queue
    # directory anyway so no stored value can serve an arbitrary file.
    try:
        path = Path(item["file_path"]).resolve()
        path.relative_to(Path(QUEUE_DIR).resolve())
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="File not found on disk") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk")
    fname = path.name
    return FileResponse(path, filename=fname, media_type="video/mp4",
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.get("/download")
async def download_endpoint(url: str, format_id: str, bg: BackgroundTasks):
    """Download a TikTok video."""
    direct_url = format_id if format_id.startswith("http") else ""

    # Both targets arrive as request parameters, so neither is fetched until it
    # passes the TikTok allowlist. This is what stops the endpoint being used as
    # a general-purpose fetcher.
    for candidate in filter(None, (direct_url, url if url.startswith("http") else "")):
        try:
            check_outbound_url(candidate)
        except BlockedTarget as exc:
            raise HTTPException(status_code=400, detail=f"Blocked target: {exc}") from exc

    if not direct_url and not is_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid TikTok URL")

    loop = asyncio.get_event_loop()

    def download_direct(src: str) -> tuple[str, str]:
        fd, tmp = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        # The CDN URL is signed for the browser session that produced it, so it
        # needs that session's cookies plus the usual Referer/UA.
        resp = cdn_get(src, cookies=get_session_cookies(), stream=True)
        resp.raise_for_status()
        stream_to_file(resp, tmp)
        return tmp, "video"

    def download_ytdlp() -> tuple[str, str]:
        fd, tmp = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        os.unlink(tmp)  # yt-dlp resume would see 0-byte file as done
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": format_id,
            "outtmpl": tmp,
        }
        cookiefile = load_cookies()
        if cookiefile:
            opts["cookiefile"] = cookiefile
        pace_outbound()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        return tmp, info.get("id", "video")

    async def try_playwright() -> tuple[str, str]:
        info = await playwright_extract(url, load_cookies())
        pw_url = next(
            (f["url"] for f in info.get("formats", [])
             if f.get("format_id") in ("download_addr", "play_addr")),
            "",
        )
        if not pw_url:
            raise ValueError("No playable URL from Playwright")
        return await loop.run_in_executor(None, download_direct, pw_url)

    tmp = None
    try:
        if format_id.startswith("http"):
            tmp, video_id = await loop.run_in_executor(None, download_direct, format_id)
        else:
            try:
                tmp, video_id = await loop.run_in_executor(None, download_ytdlp)
            except Exception:
                tmp, video_id = await try_playwright()
    except Exception as e:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
        # Last resort: Playwright with fresh URL
        if not format_id.startswith("http") or not isinstance(e, HTTPException):
            try:
                tmp, video_id = await try_playwright()
            except Exception:
                if tmp and os.path.exists(tmp):
                    os.unlink(tmp)
                raise HTTPException(status_code=502, detail=f"Download failed: {e}")
        else:
            raise HTTPException(status_code=502, detail=f"Download failed: {e}")

    bg.add_task(os.unlink, tmp)
    filename = f"tiktok_{video_id}.mp4"
    return FileResponse(tmp, filename=filename, media_type="video/mp4",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# Paths that must stay JSON so API clients get a machine-readable 404.
API_PREFIXES = {"resolve", "download", "queue", "auth", "assets"}


@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str):
    """Unknown paths get the app shell so it can render its own 404 view.

    Registered last, so it only sees paths nothing else matched. The response
    carries a real 404 status either way — this is not a catch-all rewrite.
    """
    if path.split("/", 1)[0] in API_PREFIXES:
        raise HTTPException(status_code=404, detail="Not Found")
    if SPA_HTML:
        return HTMLResponse(SPA_HTML, status_code=404)
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
