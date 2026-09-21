"""読み上げ原稿を、合成しやすい長さのかたまり（チャンク）に分ける。"""
import re

SENT_PAUSE = 0.30  # 同じ段落の中のチャンクのあとの無音（秒）
PARA_PAUSE = 0.90  # 段落の終わりのあとの無音（秒）
_SENTENCE_END = re.compile(r"(?<=[。！？!?])")


def _split_sentences(paragraph: str) -> list[str]:
    flat = paragraph.replace("\r", "").replace("\n", "")
    return [s for s in _SENTENCE_END.split(flat) if s]


def _split_long(sentence: str, max_chars: int) -> list[str]:
    if len(sentence) <= max_chars:
        return [sentence]
    pieces, buf = [], ""
    for part in re.split(r"(?<=、)", sentence):
        if buf and len(buf) + len(part) > max_chars:
            pieces.append(buf)
            buf = part
        else:
            buf += part
    if buf:
        pieces.append(buf)
    out = []
    for piece in pieces:
        while len(piece) > max_chars:
            out.append(piece[:max_chars])
            piece = piece[max_chars:]
        if piece:
            out.append(piece)
    return out


def make_chunks(text: str, max_chars: int = 120) -> list[tuple[str, float]]:
    chunks: list[tuple[str, float]] = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        buf, para_chunks = "", []
        for sentence in _split_sentences(paragraph):
            for piece in _split_long(sentence, max_chars):
                if buf and len(buf) + len(piece) > max_chars:
                    para_chunks.append(buf)
                    buf = piece
                else:
                    buf += piece
        if buf:
            para_chunks.append(buf)
        for i, chunk in enumerate(para_chunks):
            pause = PARA_PAUSE if i == len(para_chunks) - 1 else SENT_PAUSE
            chunks.append((chunk, pause))
    return chunks
