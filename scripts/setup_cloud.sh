#!/usr/bin/env bash
# クラウドで Kokoro 一式を入れる。所要 2〜3 分。
set -euo pipefail
WORK="${WORK:-$HOME/work}"
mkdir -p "$WORK/kokoro"
python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install --upgrade pip
"$WORK/venv/bin/pip" install "setuptools==59.6.0" wheel
"$WORK/venv/bin/pip" install kokoro-onnx "misaki[ja]" soundfile numpy imageio-ffmpeg
"$WORK/venv/bin/python" -m unidic download
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
curl -fsSL -o "$WORK/kokoro/kokoro-v1.0.onnx" "$BASE/kokoro-v1.0.onnx"
curl -fsSL -o "$WORK/kokoro/voices-v1.0.bin" "$BASE/voices-v1.0.bin"
echo "setup done"
