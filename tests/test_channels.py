import json

import pytest

from scripts.channels import get_channel
from scripts.feed import Episode
from scripts.publish import publish, publish_channel, unpublish_channel


def _txt(tmp_path):
    p = tmp_path / "src.txt"
    p.write_text("原稿", encoding="utf-8")
    return p


def _ep(date):
    return Episode(
        date=date,
        title=f"回 {date}",
        description="要約",
        filename=f"{date}.mp3",
        length_bytes=1,
        duration_sec=100,
        pub_date=f"{date[:10]}T05:30:00+09:00",
    )


def _mp3(tmp_path):
    p = tmp_path / "src.mp3"
    p.write_bytes(b"x")
    return p


def _episode_count(episodes_json):
    return len(json.loads(episodes_json.read_text(encoding="utf-8")))


def test_unknown_channel_is_rejected_and_nothing_is_written(tmp_path):
    # 綴りを間違えたとき、朝のニュースのフィードに書き込んでしまわないこと
    with pytest.raises(ValueError):
        publish_channel(tmp_path, "nwes", _mp3(tmp_path), _ep("2026-10-03"))
    assert [p.name for p in tmp_path.iterdir()] == ["src.mp3"]


def test_news_feed_keeps_its_title_and_audio_urls(tmp_path):
    # すでに購読しているアプリが使う番組名と配信URL。変わると購読が壊れる
    publish_channel(tmp_path, "news", _mp3(tmp_path), _ep("2026-10-01"))
    feed = (tmp_path / "feed.xml").read_text(encoding="utf-8")
    assert "<title>朝のニュース（自分用）</title>" in feed
    assert "https://tomtom87641-bot.github.io/morning-news/episodes/2026-10-01.mp3" in feed


def test_annex_feed_points_at_annex_urls_and_carries_annex_title(tmp_path):
    publish_channel(tmp_path, "annex", _mp3(tmp_path), _ep("2026-10-03-demo"))
    feed = (tmp_path / "annex" / "feed.xml").read_text(encoding="utf-8")
    # 配信URLが朝のニュース側を向くと、購読アプリで音声が再生できなくなる
    assert "https://tomtom87641-bot.github.io/morning-news/annex/episodes/2026-10-03-demo.mp3" in feed
    assert "morning-news/episodes/" not in feed
    assert f"<title>{get_channel('annex').title}</title>" in feed


def test_annex_leaves_the_news_feed_files_alone(tmp_path):
    (tmp_path / "feed.xml").write_text("NEWS-FEED", encoding="utf-8")
    publish_channel(tmp_path, "annex", _mp3(tmp_path), _ep("2026-10-03-demo"))
    assert (tmp_path / "feed.xml").read_text(encoding="utf-8") == "NEWS-FEED"
    assert not (tmp_path / "episodes.json").exists()
    assert not (tmp_path / "episodes").exists()


def test_files_are_written_with_lf_even_when_run_on_windows(tmp_path):
    # Windows のPCから公開しても、フィードと一覧の改行が CRLF に変わって全行が差分にならないこと
    publish_channel(tmp_path, "news", _mp3(tmp_path), _ep("2026-10-01"))
    for name in ("feed.xml", "episodes.json"):
        assert b"\r\n" not in (tmp_path / name).read_bytes()


def test_news_channel_still_keeps_only_seven_episodes(tmp_path):
    for d in range(1, 26):
        publish_channel(tmp_path, "news", _mp3(tmp_path), _ep(f"2026-10-{d:02d}"))
    assert _episode_count(tmp_path / "episodes.json") == 7


def test_annex_keeps_more_than_seven_episodes(tmp_path):
    for d in range(1, 26):
        publish_channel(tmp_path, "annex", _mp3(tmp_path), _ep(f"2026-10-{d:02d}-x"))
    assert _episode_count(tmp_path / "annex" / "episodes.json") > 7


def _publish_three(tmp_path, channel):
    for d in ("2026-10-01-a", "2026-10-02-b", "2026-10-03-c"):
        publish_channel(tmp_path, channel, _mp3(tmp_path), _ep(d), transcript=_txt(tmp_path))


def test_unpublish_removes_audio_text_index_and_feed_entry_of_that_episode_only(tmp_path):
    _publish_three(tmp_path, "annex")
    unpublish_channel(tmp_path, "annex", "2026-10-02-b")
    base = tmp_path / "annex"
    assert not (base / "episodes" / "2026-10-02-b.mp3").exists()
    assert not (base / "episodes" / "2026-10-02-b.txt").exists()
    assert (base / "episodes" / "2026-10-01-a.mp3").exists()
    assert (base / "episodes" / "2026-10-03-c.txt").exists()
    keys = [e["date"] for e in json.loads((base / "episodes.json").read_text(encoding="utf-8"))]
    assert keys == ["2026-10-03-c", "2026-10-01-a"]
    feed = (base / "feed.xml").read_text(encoding="utf-8")
    assert "2026-10-02-b" not in feed
    assert "2026-10-01-a" in feed and "2026-10-03-c" in feed


def test_unpublish_keeps_the_channel_url_and_title_in_the_rebuilt_feed(tmp_path):
    _publish_three(tmp_path, "annex")
    unpublish_channel(tmp_path, "annex", "2026-10-02-b")
    feed = (tmp_path / "annex" / "feed.xml").read_text(encoding="utf-8")
    assert "https://tomtom87641-bot.github.io/morning-news/annex/episodes/2026-10-01-a.mp3" in feed
    assert f"<title>{get_channel('annex').title}</title>" in feed


def test_unpublish_of_an_unknown_key_changes_nothing(tmp_path):
    _publish_three(tmp_path, "annex")
    files = [tmp_path / "annex" / "episodes.json", tmp_path / "annex" / "feed.xml"]
    before = [f.read_bytes() for f in files]
    with pytest.raises(ValueError):
        unpublish_channel(tmp_path, "annex", "2026-10-09-nope")
    assert [f.read_bytes() for f in files] == before
    assert (tmp_path / "annex" / "episodes" / "2026-10-02-b.mp3").exists()


def test_unpublishing_the_last_episode_leaves_a_valid_empty_feed(tmp_path):
    publish_channel(tmp_path, "annex", _mp3(tmp_path), _ep("2026-10-01-a"))
    unpublish_channel(tmp_path, "annex", "2026-10-01-a")
    base = tmp_path / "annex"
    assert json.loads((base / "episodes.json").read_text(encoding="utf-8")) == []
    feed = (base / "feed.xml").read_text(encoding="utf-8")
    assert "<item>" not in feed and "</rss>" in feed


def test_news_channel_output_is_identical_to_the_legacy_publish_call(tmp_path):
    # 毎朝の自動実行は従来の呼び方（publish）のまま。チャンネル対応で出力が変わらないこと
    legacy, via_channel = tmp_path / "legacy", tmp_path / "via_channel"
    for d in range(1, 4):
        publish(legacy, _mp3(tmp_path), _ep(f"2026-10-{d:02d}"))
        publish_channel(via_channel, "news", _mp3(tmp_path), _ep(f"2026-10-{d:02d}"))
    for name in ("feed.xml", "episodes.json"):
        assert (via_channel / name).read_bytes() == (legacy / name).read_bytes()
