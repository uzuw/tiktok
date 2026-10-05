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

    # No second pass is needed: the conditions that skip a format here are the
    # same ones that would have skipped it above, so `best is None` means the
    # list holds nothing usable.
    if best is None:
        return None

    fid: str = best["format_id"]

    fid = re.sub(r"-\d+$", "-0", fid)

    return {"format_id": fid}
