"""新しい回を site/ に足し、フィードを作り直し、古い回を消す。"""
import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from scripts.channels import CHANNELS, channel_site_url, get_channel
from scripts.feed import Episode, build_feed

_NEWS = CHANNELS["news"]
KEEP = _NEWS.keep
SITE_URL = channel_site_url(_NEWS)
FEED_TITLE = _NEWS.title
FEED_DESCRIPTION = _NEWS.description


def add_episode(episodes, new, keep=KEEP):
    others = [e for e in episodes if e.date != new.date]
    merged = sorted(others + [new], key=lambda e: e.date, reverse=True)
    return merged[:keep], [e.filename for e in merged[keep:]]


def load_episodes(path: Path):
    if not path.exists():
        return []
    return [Episode(**d) for d in json.loads(path.read_text(encoding="utf-8"))]


def _save_episodes(path: Path, episodes) -> None:
    text = json.dumps([asdict(e) for e in episodes], ensure_ascii=False, indent=2) + "\n"
    path.write_bytes(text.encode("utf-8"))  # バイト列で書く（Windows でも改行を LF のままにするため）


def publish(
    site_dir: Path, mp3: Path, new: Episode, keep: int = KEEP,
    transcript: Path | None = None, cover_image: Path | None = None,
    site_url: str = SITE_URL, feed_title: str = FEED_TITLE,
    feed_description: str = FEED_DESCRIPTION,
) -> None:
    episodes_dir = site_dir / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mp3, episodes_dir / new.filename)
    if transcript is not None:
        shutil.copy2(transcript, episodes_dir / Path(new.filename).with_suffix(".txt"))
    if cover_image is not None:
        shutil.copy2(cover_image, site_dir / "cover.jpg")
    kept, dropped = add_episode(load_episodes(site_dir / "episodes.json"), new, keep)
    for name in dropped:
        (episodes_dir / name).unlink(missing_ok=True)
        (episodes_dir / Path(name).with_suffix(".txt")).unlink(missing_ok=True)
    _save_episodes(site_dir / "episodes.json", kept)
    _write_feed(site_dir, kept, site_url, feed_title, feed_description)


def _write_feed(site_dir, episodes, site_url, title, description) -> None:
    image_url = f"{site_url}/cover.jpg" if (site_dir / "cover.jpg").exists() else None
    feed = build_feed(
        episodes, title=title, description=description, site_url=site_url, image_url=image_url,
    )
    (site_dir / "feed.xml").write_bytes(feed.encode("utf-8"))


def publish_channel(
    site_root: Path, channel_id: str, mp3: Path, new: Episode,
    transcript: Path | None = None, cover_image: Path | None = None,
) -> None:
    channel = get_channel(channel_id)
    publish(
        Path(site_root) / channel.subdir, mp3, new, keep=channel.keep,
        transcript=transcript, cover_image=cover_image,
        site_url=channel_site_url(channel), feed_title=channel.title,
        feed_description=channel.description,
    )


def unpublish_channel(site_root: Path, channel_id: str, key: str) -> None:
    channel = get_channel(channel_id)
    site_dir = Path(site_root) / channel.subdir
    episodes = load_episodes(site_dir / "episodes.json")
    targets = [e for e in episodes if e.date == key]
    if not targets:
        raise ValueError(f"日付キー {key} の回は「{channel.title}」にありません。")
    kept = [e for e in episodes if e.date != key]
    _save_episodes(site_dir / "episodes.json", kept)
    for e in targets:
        (site_dir / "episodes" / e.filename).unlink(missing_ok=True)
        (site_dir / "episodes" / Path(e.filename).with_suffix(".txt")).unlink(missing_ok=True)
    _write_feed(site_dir, kept, channel_site_url(channel), channel.title, channel.description)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--site-dir", required=True, type=Path)
    p.add_argument("--mp3", required=True, type=Path)
    p.add_argument("--date", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--duration-sec", required=True, type=int)
    p.add_argument("--pub-date", required=True)
    p.add_argument("--transcript", type=Path, default=None)
    p.add_argument("--cover-image", type=Path, default=None)
    p.add_argument("--channel", default="news")
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
    publish_channel(
        a.site_dir, a.channel, a.mp3, ep, transcript=a.transcript, cover_image=a.cover_image
    )


if __name__ == "__main__":
    main()
