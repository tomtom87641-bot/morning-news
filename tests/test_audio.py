import numpy as np
import pytest

from scripts.audio import concat_with_pauses


def test_pause_is_inserted_between_but_not_after_last():
    a = np.ones(10, dtype=np.float32)
    b = np.ones(20, dtype=np.float32)
    out = concat_with_pauses([a, b], [0.5, 9.9], sample_rate=100)
    assert len(out) == 10 + 50 + 20
    assert out[10:60].sum() == 0


def test_empty_input_gives_empty_array():
    assert len(concat_with_pauses([], [], 24000)) == 0


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        concat_with_pauses([np.ones(1)], [], 24000)
