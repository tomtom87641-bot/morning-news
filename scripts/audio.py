"""合成した波形を、間（無音）をはさんでつなげる。"""
import numpy as np


def concat_with_pauses(waves: list, pauses: list, sample_rate: int) -> np.ndarray:
    if len(waves) != len(pauses):
        raise ValueError("waves and pauses must have the same length")
    parts = []
    for i, (wave, pause) in enumerate(zip(waves, pauses)):
        parts.append(np.asarray(wave, dtype=np.float32))
        if i < len(waves) - 1:
            parts.append(np.zeros(int(round(pause * sample_rate)), dtype=np.float32))
    if not parts:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(parts)
