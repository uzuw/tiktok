"""FastAPI application for TikTok video downloader."""

import asyncio
import os
import tempfile

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.extractor import extract_info, is_profile_url, is_video_url
from app.formats import pick_sd_hd


app = FastAPI(title="TikTok Downloader")


class ResolveRequest(BaseModel):
    url: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(open("app/templates/index.html").read())


@app.post("/resolve")
async def resolve_endpoint(req: ResolveRequest):
    """Resolve a TikTok URL into metadata + SD/HD format IDs."""
    url = req.url.strip()

    if not is_video_url(url):
        if is_profile_url(url):
            raise HTTPException(
                status_code=400, detail="Profile URLs not supported yet (Phase 3)"
            )
        raise HTTPException(status_code=400, detail="Not a valid TikTok video URL")

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, extract_info, url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Extraction failed: {e}")

    formats = info.get("formats") or []
    sd_hd = pick_sd_hd(formats)
    caption = info.get("description") or info.get("title") or ""

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


@app.get("/download")
async def download_endpoint(url: str, format_id: str, bg: BackgroundTasks):
    """Download a TikTok video using yt-dlp (handles chunk merging, cookies, headers)."""
    if not is_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid TikTok URL")

    loop = asyncio.get_event_loop()
    # Use mkstemp for safe unique name, then remove the empty file
    # so yt-dlp doesn't think it's already downloaded (resume feature)
    fd, tmp = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    os.unlink(tmp)

    def download():
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": format_id,
            "outtmpl": tmp,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        return info.get("id", "video")

    try:
        video_id = await loop.run_in_executor(None, download)
    except Exception as e:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise HTTPException(status_code=502, detail=f"Download failed: {e}")

    bg.add_task(os.unlink, tmp)
    filename = f"tiktok_{video_id}_{format_id}.mp4"
    return FileResponse(tmp, filename=filename, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
