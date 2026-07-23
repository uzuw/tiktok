"""Format normalization — maps yt-dlp's raw format list to SD/HD choices."""

import re
from typing import Any


def pick_sd_hd(formats: list[dict[str, Any]]) -> dict[str, Any]:
    """Given yt-dlp's format list, return SD and HD format specs.

    Rules:
    - SD -> format_id "download" (watermarked, single stream).
    - HD -> the highest-resolution non-download format (720p+).
      If the format is chunked (-0/-1), combines all chunks with '+'.
    """
    sd_format = None
    hd_format = None

    for f in formats:
        fid = f.get("format_id", "")
        vcodec = f.get("vcodec", "none")
        if vcodec == "none":
            continue

        if fid == "download" and not sd_format:
            sd_format = f

        if fid != "download":
            height = f.get("height") or 0
            if height >= 720:
                if hd_format is None or (f.get("height") or 0) > (hd_format.get("height") or 0):
                    if hd_format is None or (
                        f.get("vcodec", "").startswith("h264")
                        and not hd_format.get("vcodec", "").startswith("h264")
                    ):
                        hd_format = f

    if not hd_format and not sd_format:
        for f in formats:
            if f.get("vcodec", "none") != "none" and f.get("format_id") != "download":
                if hd_format is None or (f.get("height") or 0) > (hd_format.get("height") or 0):
                    hd_format = f

    result = {
        "sd": {"format_id": sd_format["format_id"]} if sd_format else None,
        "hd": None,
    }

    if hd_format:
        fid = hd_format["format_id"]
        # Combine chunk-pair formats (-0/-1) into a merge string
        if re.search(r"-\d+$", fid):
            base = re.sub(r"-\d+$", "", fid)
            chunks = sorted(
                f.get("format_id", "")
                for f in formats
                if re.match(rf"^{re.escape(base)}-\d+$", f.get("format_id", ""))
                and f.get("vcodec", "none") != "none"
            )
            if chunks:
                fid = "+".join(chunks)
        result["hd"] = {"format_id": fid}

    return result
