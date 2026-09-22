"""購読フィード（RSS 2.0 + iTunes拡張）を組み立てる。"""
from dataclasses import dataclass
from datetime import datetime
from email.utils import format_datetime
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class Episode:
    date: str          # "YYYY-MM-DD"（日本時間）
    title: str
    description: str
    filename: str      # "2026-09-23.mp3"
    length_bytes: int
    duration_sec: int
    pub_date: str      # "2026-09-23T05:30:00+09:00"


def _hms(seconds: int) -> str:
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def build_feed(
    episodes, *, title: str, description: str, site_url: str, language: str = "ja",
    image_url: str | None = None,
) -> str:
    items = []
    for ep in sorted(episodes, key=lambda e: e.date, reverse=True):
        url = f"{site_url}/episodes/{ep.filename}"
        pub = format_datetime(datetime.fromisoformat(ep.pub_date))
        items.append(
            "    <item>\n"
            f"      <title>{escape(ep.title)}</title>\n"
            f"      <description>{escape(ep.description)}</description>\n"
            f"      <pubDate>{pub}</pubDate>\n"
            f'      <guid isPermaLink="false">morning-news-{escape(ep.date)}</guid>\n'
            f'      <enclosure url="{_attr(url)}" length="{ep.length_bytes}" type="audio/mpeg"/>\n'
            f"      <itunes:duration>{_hms(ep.duration_sec)}</itunes:duration>\n"
            "    </item>"
        )
    body = "\n".join(items)
    image_block = ""
    if image_url:
        image_block = (
            f'    <itunes:image href="{_attr(image_url)}"/>\n'
            "    <image>\n"
            f"      <url>{escape(image_url)}</url>\n"
            f"      <title>{escape(title)}</title>\n"
            f"      <link>{escape(site_url)}</link>\n"
            "    </image>\n"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
        "  <channel>\n"
        f"    <title>{escape(title)}</title>\n"
        f"    <link>{escape(site_url)}</link>\n"
        f"    <description>{escape(description)}</description>\n"
        f"    <language>{escape(language)}</language>\n"
        "    <itunes:author>自分用</itunes:author>\n"
        "    <itunes:explicit>false</itunes:explicit>\n"
        f"{image_block}"
        f"{body}\n"
        "  </channel>\n"
        "</rss>\n"
    )
