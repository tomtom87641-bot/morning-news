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
