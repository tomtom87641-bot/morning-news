from datetime import datetime, timezone

import pytest

from scripts.channels import get_channel
from scripts.upload_special import (
    build_episode,
    default_key,
    ensure_key_is_free,
    ensure_special_channel,
    resolve_cover,
    validate_key,
)


@pytest.mark.parametrize("key", ["2026-10-03", "2026-10-03-demo", "2026-10-03-demo2-b"])
def test_valid_keys_are_accepted(key):
    validate_key(key)


@pytest.mark.parametrize(
    "key",
    ["demo", "2026-10-03-Demo", "2026-10-03-デモ", "2026-10-03 demo", "../2026-10-03",
     "2026-10-03/x", "", "2026-10-03-", "2026-10-03--x"],
    ids=["no-date", "upper", "japanese", "space", "parent-dir", "slash", "empty",
         "trailing-dash", "double-dash"],
)
def test_keys_that_could_break_file_names_are_rejected(key):
    with pytest.raises(ValueError):
        validate_key(key)


def test_default_key_is_the_japan_date_and_time():
    utc = datetime(2026, 10, 2, 22, 8, 9, tzinfo=timezone.utc)  # 日本時間では 10/3 07:08:09
    assert default_key(utc) == "2026-10-03-070809"


def test_build_episode_describes_the_uploaded_file(tmp_path):
    mp3 = tmp_path / "x.mp3"
    mp3.write_bytes(b"12345")
    now = datetime(2026, 10, 2, 22, 8, 9, tzinfo=timezone.utc)
    ep = build_episode("2026-10-03-demo", "題名", "説明", mp3, 123, now)
    assert (ep.date, ep.filename) == ("2026-10-03-demo", "2026-10-03-demo.mp3")
    assert (ep.length_bytes, ep.duration_sec) == (5, 123)
    assert ep.pub_date == "2026-10-03T07:08:09+09:00"
    assert (ep.title, ep.description) == ("題名", "説明")


def test_existing_key_is_refused_unless_replacing():
    # 別の音声を同じ名札で上げて、前の回を消してしまわないこと
    with pytest.raises(ValueError):
        ensure_key_is_free({"2026-10-03-demo"}, "2026-10-03-demo", replace=False)
    ensure_key_is_free({"2026-10-03-demo"}, "2026-10-03-demo", replace=True)
    ensure_key_is_free({"2026-10-03-demo"}, "2026-10-03-other", replace=False)


def test_news_channel_is_reserved_for_the_daily_routine():
    # 毎朝の7回の枠を、手動のアップロードで押し出してしまわないこと
    with pytest.raises(ValueError):
        ensure_special_channel("news")
    ensure_special_channel("annex")


def test_each_channel_uses_its_own_cover(tmp_path):
    (tmp_path / "cover.jpg").write_bytes(b"news")
    assert resolve_cover(get_channel("news"), tmp_path) == tmp_path / "cover.jpg"
    # 朝のニュースのカバーを別館に流用しない
    assert resolve_cover(get_channel("annex"), tmp_path) is None
    (tmp_path / "cover_annex.jpg").write_bytes(b"annex")
    assert resolve_cover(get_channel("annex"), tmp_path) == tmp_path / "cover_annex.jpg"
