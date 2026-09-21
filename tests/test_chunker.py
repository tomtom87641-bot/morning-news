from scripts.chunker import make_chunks, SENT_PAUSE, PARA_PAUSE


def test_single_sentence_gets_paragraph_pause():
    assert make_chunks("おはようございます。") == [("おはようございます。", PARA_PAUSE)]


def test_sentences_are_merged_up_to_limit():
    text = "一つ目です。二つ目です。三つ目です。"
    assert make_chunks(text, max_chars=14) == [
        ("一つ目です。二つ目です。", SENT_PAUSE),
        ("三つ目です。", PARA_PAUSE),
    ]


def test_blank_line_starts_new_paragraph():
    assert make_chunks("前半です。\n\n後半です。") == [
        ("前半です。", PARA_PAUSE),
        ("後半です。", PARA_PAUSE),
    ]


def test_single_newline_is_joined():
    assert make_chunks("前半です。\n後半です。") == [("前半です。後半です。", PARA_PAUSE)]


def test_long_sentence_is_split_at_reading_marks():
    sentence = "あ" * 10 + "、" + "い" * 10 + "、" + "う" * 10 + "。"
    chunks = make_chunks(sentence, max_chars=15)
    assert all(len(c) <= 15 for c, _ in chunks)
    assert "".join(c for c, _ in chunks) == sentence


def test_unbroken_long_text_is_hard_split():
    chunks = make_chunks("あ" * 40, max_chars=15)
    assert [len(c) for c, _ in chunks] == [15, 15, 10]
