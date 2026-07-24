"""FastAPI application for TikTok video downloader."""

import asyncio
import os
import tempfile
import urllib.request

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.cookies import clear_cookies, has_cookies, load_cookies, save_cookies
from app.download_manager import enqueue, get_item, list_items, remove_item
from app.extractor import extract_info, extract_profile, is_profile_url, is_video_url
from app.formats import pick_sd_hd
from app.playwright_extractor import playwright_extract


app = FastAPI(title="TikTok Downloader")


class ResolveRequest(BaseModel):
    url: str


class CookieRequest(BaseModel):
    cookies: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(open("app/templates/index.html").read())


@app.post("/resolve")
async def resolve_endpoint(req: ResolveRequest):
    """Resolve a TikTok URL into metadata + SD/HD format IDs."""
    url = req.url.strip()
    cookiefile = load_cookies()
    loop = asyncio.get_event_loop()

    if not is_video_url(url):
        if is_profile_url(url):
            try:
                result = await loop.run_in_executor(None, extract_profile, url, cookiefile)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Profile extraction failed: {e}")
            return result
        raise HTTPException(status_code=400, detail="Not a valid TikTok URL")

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
        sd_fmt = None
        hd_fmt = None
        for f in formats:
            if f.get("format_id") == "play_addr":
                sd_fmt = f
            elif f.get("format_id") == "download_addr":
                hd_fmt = f
        return {
            "id": info.get("id", ""),
            "thumbnail": info.get("thumbnail", ""),
            "author": info.get("uploader") or info.get("channel", ""),
            "caption": caption[:500],
            "duration": info.get("duration", 0),
            "formats": {
                "sd": {"format_id": sd_fmt["url"]} if sd_fmt else None,
                "hd": {"format_id": hd_fmt["url"]} if hd_fmt else None,
                "_direct": True,
            },
        }

    sd_hd = pick_sd_hd(formats)
    return {
        "id": info.get("id", ""),
        "thumbnail": info.get("thumbnail", ""),
        "author": info.get("uploader") or info.get("channel", ""),
        "caption": caption[:500],
        "duration": info.get("duration", 0),
        "formats": {
            "sd": {"format_id": sd_hd["sd"]["format_id"]} if sd_hd.get("sd") else None,
            "hd": {"format_id": sd_hd["hd"]["format_id"]} if sd_hd.get("hd") else None,
        },
    }


@app.get("/auth/status")
async def auth_status():
    return {"authenticated": has_cookies()}


class CookieRequest(BaseModel):
    cookies: str


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
async def queue_add(req: ResolveRequest):
    """Add a video URL to the download queue (uses format_id='download')."""
    url = req.url.strip()
    if not is_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid TikTok URL")
    item = enqueue(url, "download", title="")
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


@app.delete("/queue/{item_id}")
async def queue_delete(item_id: str):
    """Remove a pending queue item."""
    if not remove_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found or already processing")
    return {"ok": True}


@app.get("/download")
async def download_endpoint(url: str, format_id: str, bg: BackgroundTasks):
    """Download a TikTok video."""
    if not is_video_url(url) and not format_id.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid TikTok URL")

    loop = asyncio.get_event_loop()

    def download_direct(src: str) -> str:
        fd, tmp = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        urllib.request.urlretrieve(src, tmp)
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
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        return tmp, info.get("id", "video")

    try:
        if format_id.startswith("http"):
            tmp, video_id = await loop.run_in_executor(None, download_direct, format_id)
        else:
            tmp, video_id = await loop.run_in_executor(None, download_ytdlp)
    except Exception as e:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise HTTPException(status_code=502, detail=f"Download failed: {e}")

    bg.add_task(os.unlink, tmp)
    filename = f"tiktok_{video_id}.mp4"
    return FileResponse(tmp, filename=filename, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
