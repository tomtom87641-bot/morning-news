"""原稿（テキスト）→ mp3。クラウドで実行する。声は Kokoro の jf_alpha。"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np  # noqa: F401  (concat_with_pauses が返す配列の型)
import soundfile as sf

from scripts.audio import concat_with_pauses
from scripts.chunker import make_chunks

VOICE = "jf_alpha"
WORK = Path.home() / "work"


def synthesize(text, model_path, voices_path, speed=1.0):
    from kokoro_onnx import Kokoro
    from misaki import ja

    kokoro = Kokoro(model_path, voices_path)
    g2p = ja.JAG2P()
    chunks = make_chunks(text)
    waves, pauses, sample_rate = [], [], 24000
    for i, (chunk, pause) in enumerate(chunks, 1):
        phonemes, _ = g2p(chunk)
        samples, sample_rate = kokoro.create(phonemes, voice=VOICE, speed=speed, is_phonemes=True)
        waves.append(samples)
        pauses.append(pause)
        print(f"[{i}/{len(chunks)}] {len(chunk)}字", file=sys.stderr, flush=True)
    return concat_with_pauses(waves, pauses, sample_rate), sample_rate


def to_mp3(wav_path: Path, mp3_path: Path) -> None:
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", str(wav_path), "-ac", "1", "-b:a", "48k", str(mp3_path)],
        check=True,
        capture_output=True,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--script", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--model", default=str(WORK / "kokoro" / "kokoro-v1.0.onnx"))
    p.add_argument("--voices", default=str(WORK / "kokoro" / "voices-v1.0.bin"))
    p.add_argument("--speed", type=float, default=1.0)
    a = p.parse_args()

    started = time.time()
    audio, sample_rate = synthesize(a.script.read_text(encoding="utf-8"), a.model, a.voices, a.speed)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    wav = a.out.with_suffix(".wav")
    sf.write(str(wav), audio, sample_rate)
    to_mp3(wav, a.out)
    wav.unlink()
    print(json.dumps({
        "duration_sec": int(len(audio) / sample_rate),
        "bytes": a.out.stat().st_size,
        "synth_sec": round(time.time() - started, 1),
    }))


if __name__ == "__main__":
    main()
