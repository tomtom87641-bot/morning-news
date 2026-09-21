"""新しい回を site/ に足し、フィードを作り直し、古い回を消す。"""
import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from scripts.feed import Episode, build_feed

KEEP = 7
SITE_URL = "https://tomtom87641-bot.github.io/morning-news"
FEED_TITLE = "朝のニュース（自分用）"
FEED_DESCRIPTION = "毎朝、公開ニュースを自分用にまとめて読み上げる番組。"


def add_episode(episodes, new, keep=KEEP):
    others = [e for e in episodes if e.date != new.date]
    merged = sorted(others + [new], key=lambda e: e.date, reverse=True)
    return merged[:keep], [e.filename for e in merged[keep:]]


def load_episodes(path: Path):
    if not path.exists():
        return []
    return [Episode(**d) for d in json.loads(path.read_text(encoding="utf-8"))]


def _save_episodes(path: Path, episodes) -> None:
    path.write_text(
        json.dumps([asdict(e) for e in episodes], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def publish(site_dir: Path, mp3: Path, new: Episode, keep: int = KEEP) -> None:
    episodes_dir = site_dir / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mp3, episodes_dir / new.filename)
    kept, dropped = add_episode(load_episodes(site_dir / "episodes.json"), new, keep)
    for name in dropped:
        (episodes_dir / name).unlink(missing_ok=True)
    _save_episodes(site_dir / "episodes.json", kept)
    (site_dir / "feed.xml").write_text(
        build_feed(kept, title=FEED_TITLE, description=FEED_DESCRIPTION, site_url=SITE_URL),
        encoding="utf-8",
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--site-dir", required=True, type=Path)
    p.add_argument("--mp3", required=True, type=Path)
    p.add_argument("--date", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--duration-sec", required=True, type=int)
    p.add_argument("--pub-date", required=True)
    a = p.parse_args()
    ep = Episode(
        date=a.date,
        title=a.title,
        description=a.description,
        filename=f"{a.date}.mp3",
        length_bytes=a.mp3.stat().st_size,
        duration_sec=a.duration_sec,
        pub_date=a.pub_date,
    )
    publish(a.site_dir, a.mp3, ep)


if __name__ == "__main__":
    main()
