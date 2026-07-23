#!/usr/bin/env python3
"""Phase 0 — Feasibility spike: verify yt-dlp extracts TikTok video & profile metadata.

Usage:
    python3 phase0_test.py <tiktok-video-url> [tiktok-profile-url]

If no URLs are given, uses hardcoded examples.
"""

import sys
import json
import yt_dlp


def extract(url: str, label: str) -> dict:
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  URL: {url}")
    print(f"{'='*70}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Top-level keys
    top_keys = list(info.keys())
    print(f"\n  Top-level keys ({len(top_keys)}):")
    for k in sorted(top_keys):
        v = info[k]
        if isinstance(v, str):
            print(f"    {k}: {v[:120]}")
        elif isinstance(v, (int, float, bool)):
            print(f"    {k}: {v}")
        elif isinstance(v, list):
            print(f"    {k}: list[{len(v)}]")
        elif isinstance(v, dict):
            print(f"    {k}: dict[{len(v)} keys]")
        elif v is None:
            print(f"    {k}: None")
        else:
            print(f"    {k}: {type(v).__name__}")

    # Format list
    formats = info.get("formats") or []
    # Also check if there's a direct URL at top level
    direct_url = info.get("url")
    print(f"\n  Direct URL at top level: {direct_url}")

    print(f"\n  Format entries: {len(formats)}")
    for i, f in enumerate(formats):
        fmt_id = f.get("format_id", "?")
        ext = f.get("ext", "?")
        resolution = f.get("resolution") or f"{f.get('width','?')}x{f.get('height','?')}"
        filesize = f.get("filesize") or f.get("filesize_approx", 0)
        tbr = f.get("tbr", 0)
        vcodec = f.get("vcodec", "?")
        acodec = f.get("acodec", "?")
        note = f.get("format_note", "")
        url_present = "URL" if f.get("url") else "no-URL"
        print(f"    [{fmt_id:>6}] {ext:4} {resolution:>12}  {filesize:>10} bytes  "
              f"{tbr:>5}kbps  v={vcodec:>8} a={acodec:>6}  {note:20}  {url_present}")

        # Detect watermark-related fields
        for wkey in ("watermark", "video_watermark", "has_watermark"):
            if wkey in f:
                print(f"           -> {wkey}={f[wkey]}")

    # Check requested_formats (sometimes yt-dlp splits audio/video)
    req_fmts = info.get("requested_formats")
    if req_fmts:
        print(f"\n  requested_formats ({len(req_fmts)}):")
        for rf in req_fmts:
            print(f"    {rf.get('format_id','?')}  {rf.get('ext','?')}  "
                  f"{rf.get('width','?')}x{rf.get('height','?')}  url={'yes' if rf.get('url') else 'no'}")

    return info


def main():
    # Default test URLs (public TikTok videos)
    single_url = "https://www.tiktok.com/@tiktok/video/7101878848238824750"
    profile_url = "https://www.tiktok.com/@tiktok"

    if len(sys.argv) > 1:
        single_url = sys.argv[1]
    if len(sys.argv) > 2:
        profile_url = sys.argv[2]

    print("Phase 0 — yt-dlp TikTok Extraction Feasibility Spike")
    print(f"yt_dlp version info: {yt_dlp.__file__}")

    # 1. Single video extraction
    info = extract(single_url, "SINGLE VIDEO")

    # Summarise SD / HD candidates
    formats = info.get("formats") or []
    print(f"\n  --- SD/HD CANDIDATES ---")
    candidates = []
    for f in formats:
        vid = f.get("format_id", "")
        height = f.get("height", 0) or 0
        url = f.get("url")
        note = f.get("format_note", "")
        filesize = f.get("filesize") or f.get("filesize_approx", 0) or 0
        vcodec = f.get("vcodec", "none")
        if url and vcodec != "none":
            label = "HD" if height >= 720 else "SD"
            has_wm = f.get("watermark") or "watermark" in vid.lower()
            candidates.append((height, label, has_wm, vid, note, filesize, url))

    candidates.sort(key=lambda x: -x[0])
    print(f"  {'Height':>7} {'Label':>6} {'Watermark?':>11}  {'Format ID':>10}  {'Note':20}  {'Size':>10}")
    print(f"  {'-'*7} {'-'*6} {'-'*11}  {'-'*10}  {'-'*20}  {'-'*10}")
    for h, lbl, wm, vid, note, size, url in candidates:
        print(f"  {h:>7} {lbl:>6} {str(bool(wm)):>11}  {vid:>10}  {note:20}  {size:>10}")

    # 2. Profile extraction (just first page)
    print(f"\n{'='*70}")
    print(f"  PROFILE: will attempt playlist extraction")
    print(f"{'='*70}")
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "playlistend": 5,  # just first 5 to limit damage
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            profile_info = ydl.extract_info(profile_url, download=False)
        print(f"\n  Playlist type: {profile_info.get('_type', '?')}")
        print(f"  Title: {profile_info.get('title', '?')}")
        print(f"  Uploader: {profile_info.get('uploader', '?')}")
        entries = profile_info.get("entries") or []
        print(f"  Entries (capped at 5): {len(entries)}")
        for i, entry in enumerate(entries):
            if entry is None:
                print(f"    [{i}] None (likely private/deleted)")
                continue
            eid = entry.get("id", "?")
            title = entry.get("title", "?")[:80]
            url = entry.get("url") or entry.get("webpage_url", "?")
            print(f"    [{i}] id={eid}  title={title}")
            print(f"          url={url}")
            # Check if this is a flat entry or full
            if entry.get("_type") == "url" or not entry.get("formats"):
                print(f"          (flat entry — need to extract individually for formats)")
    except Exception as e:
        print(f"\n  Profile extraction failed: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*70}")
    print("  Phase 0 complete.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
