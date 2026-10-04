"""Tests for app.formats.pick_best_format."""

from app.formats import pick_best_format

WATERMARKED = {"format_id": "download", "vcodec": "h264", "height": 480}


def fmt(format_id, vcodec="h264", height=720):
    return {"format_id": format_id, "vcodec": vcodec, "height": height}


def test_empty_list_returns_none():
    assert pick_best_format([]) is None


def test_only_watermarked_format_returns_none():
    assert pick_best_format([WATERMARKED]) is None


def test_audio_only_formats_return_none():
    assert pick_best_format([fmt("audio", vcodec="none", height=0)]) is None


def test_picks_highest_resolution():
    formats = [
        fmt("bytevc1_540p_x", height=540),
        fmt("h264_720p_x", height=720),
        fmt("bytevc1_1080p_x", height=1080),
    ]
    assert pick_best_format(formats) == {"format_id": "bytevc1_1080p_x"}


def test_prefers_h264_at_equal_resolution():
    formats = [fmt("bytevc1_720p_x", vcodec="bytevc1", height=720), fmt("h264_720p_y", height=720)]
    assert pick_best_format(formats) == {"format_id": "h264_720p_y"}


def test_keeps_first_on_equal_resolution_and_codec():
    formats = [
        fmt("bytevc1_720p_a", vcodec="bytevc1", height=720),
        fmt("bytevc1_720p_b", vcodec="bytevc1", height=720),
    ]
    assert pick_best_format(formats) == {"format_id": "bytevc1_720p_a"}


def test_watermarked_format_is_ignored_even_when_largest():
    formats = [WATERMARKED, fmt("h264_720p_x", height=720)]
    assert pick_best_format(formats) == {"format_id": "h264_720p_x"}


def test_missing_height_treated_as_zero():
    formats = [{"format_id": "h264_a", "vcodec": "h264"}, fmt("h264_b", height=0)]
    assert pick_best_format(formats) == {"format_id": "h264_a"}


def test_chunk_suffix_normalized_to_first_chunk():
    formats = [fmt("bytevc1_1080p_abc-3")]
    assert pick_best_format(formats) == {"format_id": "bytevc1_1080p_abc-0"}


def test_format_id_without_chunk_suffix_unchanged():
    assert pick_best_format([fmt("h264_720p_plain")]) == {"format_id": "h264_720p_plain"}
