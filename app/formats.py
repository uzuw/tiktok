"""Format normalization — picks the best-quality format from yt-dlp's output."""

import re
from typing import Any


def pick_best_format(formats: list[dict[str, Any]]) -> dict[str, str] | None:
    """Return the best-quality format_id from yt-dlp's format list.

    Skips the watermarked ``download`` format.  Chooses the highest-resolution
    format, preferring h264 at the same resolution.  If the chosen format is
    chunked (``foo-N``) returns the first chunk only — each chunk is a
    complete copy, not a DASH segment.
    """
    best = None
    for f in formats:
        fid = f.get("format_id", "")
        vcodec = f.get("vcodec", "none")
        if vcodec == "none" or fid == "download":
            continue

        if best is None:
            best = f
            continue

        bh = best.get("height") or 0
        fh = f.get("height") or 0
        if fh > bh:
            best = f
        elif fh == bh:
            # At the same resolution prefer h264
            if f.get("vcodec", "").startswith("h264") and not best.get("vcodec", "").startswith("h264"):
                best = f

    # Fallback: pick any video format at all
    if best is None:
        for f in formats:
            if f.get("vcodec", "none") != "none" and f.get("format_id") != "download":
                best = f
                break

    if best is None:
        return None

    fid: str = best["format_id"]

    fid = re.sub(r"-\d+$", "-0", fid)

    return {"format_id": fid}
