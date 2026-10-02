import pytest

from scripts.mp3info import mp3_duration_sec

# MPEG-1 Layer III, 128kbps, 44.1kHz, stereo → 1フレーム 417バイト・1152サンプル
MPEG1_HEADER = bytes([0xFF, 0xFB, 0x90, 0x00])
MPEG1_FRAME_BYTES = 417
# MPEG-2 Layer III, 48kbps, 24kHz, mono（build_episode が作る音声と同じ型）→ 1フレーム 144バイト・576サンプル
MPEG2_HEADER = bytes([0xFF, 0xF3, 0x64, 0xC0])
MPEG2_FRAME_BYTES = 144


def _frames(header, frame_bytes, count):
    return (header + b"\x00" * (frame_bytes - len(header))) * count


def _write(tmp_path, data):
    p = tmp_path / "a.mp3"
    p.write_bytes(data)
    return p


def test_mpeg1_constant_bitrate(tmp_path):
    # 1000フレーム = 417,000バイト。417000*8/128000 = 26.06秒
    p = _write(tmp_path, _frames(MPEG1_HEADER, MPEG1_FRAME_BYTES, 1000))
    assert mp3_duration_sec(p) == 26


def test_mpeg2_mono_uses_mpeg2_tables(tmp_path):
    # 1000フレーム = 144,000バイト。144000*8/48000 = 24.0秒
    # MPEG-1 の表で読むとビットレートを誤り、長さが大きくずれる
    p = _write(tmp_path, _frames(MPEG2_HEADER, MPEG2_FRAME_BYTES, 1000))
    assert mp3_duration_sec(p) == 24


def test_id3v2_tag_is_not_counted_as_audio(tmp_path):
    # 先頭の ID3 タグ（本体 100,000バイト。中にフレームヘッダに見える並びを含む）を
    # 読み飛ばさず音声に数えると 32秒になる
    id3 = b"ID3\x04\x00\x00" + bytes([0, 6, 13, 32]) + MPEG1_HEADER + b"\x00" * 99996
    p = _write(tmp_path, id3 + _frames(MPEG1_HEADER, MPEG1_FRAME_BYTES, 1000))
    assert mp3_duration_sec(p) == 26


def test_xing_frame_count_wins_over_file_size(tmp_path):
    # 実データは10フレームだけだが、先頭の Info ヘッダは 2000フレームと言っている。
    # 2000*1152/44100 = 52.2秒。ファイルサイズから推定すると 0秒になる
    first = bytearray(_frames(MPEG1_HEADER, MPEG1_FRAME_BYTES, 1))
    first[36:40] = b"Info"
    first[40:44] = (1).to_bytes(4, "big")
    first[44:48] = (2000).to_bytes(4, "big")
    rest = _frames(MPEG1_HEADER, MPEG1_FRAME_BYTES, 9)
    p = _write(tmp_path, bytes(first) + rest)
    assert mp3_duration_sec(p) == 52


@pytest.mark.parametrize(
    "data",
    [b"", b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 64, b"\x00" * 500],
    ids=["empty", "wav", "zeros"],
)
def test_non_mp3_is_rejected_not_reported_as_zero_seconds(tmp_path, data):
    p = _write(tmp_path, data)
    with pytest.raises(ValueError):
        mp3_duration_sec(p)
