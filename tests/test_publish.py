from scripts.feed import Episode
from scripts.publish import add_episode, load_episodes, publish


def _ep(date, **kw):
    base = dict(
        date=date,
        title=f"朝のニュース {date}",
        description="要約",
        filename=f"{date}.mp3",
        length_bytes=10,
        duration_sec=1000,
        pub_date=f"{date}T05:30:00+09:00",
    )
    base.update(kw)
    return Episode(**base)


def test_add_episode_keeps_newest_seven():
    existing = [_ep(f"2026-09-{d:02d}") for d in range(10, 19)]  # 10〜18日の9件
    kept, dropped = add_episode(existing, _ep("2026-09-19"), keep=7)
    assert [e.date for e in kept] == [f"2026-09-{d:02d}" for d in range(19, 12, -1)]
    assert dropped == ["2026-09-12.mp3", "2026-09-11.mp3", "2026-09-10.mp3"]


def test_same_date_replaces_instead_of_duplicating():
    kept, dropped = add_episode([_ep("2026-09-22")], _ep("2026-09-22", title="差し替え"), keep=7)
    assert len(kept) == 1 and kept[0].title == "差し替え" and dropped == []


def test_publish_copies_transcript_and_prunes_old_ones(tmp_path):
    site = tmp_path / "site"
    for d in range(10, 18):  # 10〜17日の8回
        mp3 = tmp_path / f"{d}.mp3"
        mp3.write_bytes(b"x")
        txt = tmp_path / f"{d}.txt"
        txt.write_text(f"原稿{d}", encoding="utf-8")
        publish(site, mp3, _ep(f"2026-09-{d:02d}"), transcript=txt)
    names = sorted(p.name for p in (site / "episodes").iterdir())
    expected = sorted(
        [f"2026-09-{d:02d}.mp3" for d in range(11, 18)]
        + [f"2026-09-{d:02d}.txt" for d in range(11, 18)]
    )
    assert names == expected
    assert (site / "episodes" / "2026-09-17.txt").read_text(encoding="utf-8") == "原稿17"


def test_publish_copies_cover_image_and_references_it_in_feed(tmp_path):
    site = tmp_path / "site"
    mp3 = tmp_path / "a.mp3"
    mp3.write_bytes(b"x")
    cover = tmp_path / "cover_source.jpg"
    cover.write_bytes(b"fake-jpeg-bytes")
    publish(site, mp3, _ep("2026-09-22"), cover_image=cover)
    assert (site / "cover.jpg").read_bytes() == b"fake-jpeg-bytes"
    assert "cover.jpg" in (site / "feed.xml").read_text(encoding="utf-8")


def test_publish_without_cover_image_keeps_existing_one(tmp_path):
    site = tmp_path / "site"
    mp3 = tmp_path / "a.mp3"
    mp3.write_bytes(b"x")
    cover = tmp_path / "cover_source.jpg"
    cover.write_bytes(b"fake-jpeg-bytes")
    publish(site, mp3, _ep("2026-09-22"), cover_image=cover)
    publish(site, mp3, _ep("2026-09-23"))  # cover_image を渡さない2回目
    assert (site / "cover.jpg").read_bytes() == b"fake-jpeg-bytes"
    assert "cover.jpg" in (site / "feed.xml").read_text(encoding="utf-8")


def test_publish_writes_files_and_prunes(tmp_path):
    site = tmp_path / "site"
    for d in range(10, 18):  # 10〜17日の8回
        mp3 = tmp_path / f"{d}.mp3"
        mp3.write_bytes(b"x" * d)
        publish(site, mp3, _ep(f"2026-09-{d:02d}", length_bytes=d))
    names = sorted(p.name for p in (site / "episodes").iterdir())
    assert names == [f"2026-09-{d:02d}.mp3" for d in range(11, 18)]
    assert (site / "feed.xml").exists()
    assert load_episodes(site / "episodes.json")[0].date == "2026-09-17"
