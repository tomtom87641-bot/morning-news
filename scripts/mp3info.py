"""MP3 の再生時間（秒）を、標準ライブラリだけで測る。Layer III（ふつうの MP3）のみ対応。"""
from pathlib import Path

_KBPS_MPEG1 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
_KBPS_MPEG2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def _parse_header(b):
    """4バイトが Layer III のフレームヘッダなら (MPEG-1か, ビット/秒, サンプル/秒, モノか) を返す。"""
    if len(b) < 4 or b[0] != 0xFF or (b[1] & 0xE0) != 0xE0:
        return None
    version = (b[1] >> 3) & 3
    layer = (b[1] >> 1) & 3
    bitrate_index = b[2] >> 4
    rate_index = (b[2] >> 2) & 3
    if version == 1 or layer != 1 or bitrate_index in (0, 15) or rate_index == 3:
        return None
    mpeg1 = version == 3
    kbps = (_KBPS_MPEG1 if mpeg1 else _KBPS_MPEG2)[bitrate_index]
    return mpeg1, kbps * 1000, _RATES[version][rate_index], (b[3] >> 6) == 3


def mp3_duration_sec(path) -> int:
    data = Path(path).read_bytes()
    pos = 0
    if data[:3] == b"ID3" and len(data) >= 10:
        pos = 10 + ((data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9])
    while pos + 4 <= len(data) and _parse_header(data[pos : pos + 4]) is None:
        pos += 1
    if pos + 4 > len(data):
        raise ValueError("MP3 のフレームが見つかりません（MP3 ではないか、壊れています）")
    mpeg1, bitrate, rate, mono = _parse_header(data[pos : pos + 4])

    offset = (21 if mono else 36) if mpeg1 else (13 if mono else 21)
    if data[pos + offset : pos + offset + 4] in (b"Xing", b"Info"):
        flags = int.from_bytes(data[pos + offset + 4 : pos + offset + 8], "big")
        if flags & 1:
            frames = int.from_bytes(data[pos + offset + 8 : pos + offset + 12], "big")
            return int(frames * (1152 if mpeg1 else 576) / rate)

    return int((len(data) - pos) * 8 / bitrate)
