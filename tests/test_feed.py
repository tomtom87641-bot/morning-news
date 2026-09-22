import xml.etree.ElementTree as ET

from scripts.feed import Episode, build_feed

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"


def _ep(date, **kw):
    base = dict(
        date=date,
        title=f"朝のニュース {date}",
        description="要約",
        filename=f"{date}.mp3",
        length_bytes=7_000_000,
        duration_sec=1185,
        pub_date=f"{date}T05:30:00+09:00",
    )
    base.update(kw)
    return Episode(**base)


def _build(episodes):
    return build_feed(
        episodes,
        title="朝のニュース",
        description="自分用",
        site_url="https://example.github.io/morning-news",
    )


def test_items_are_newest_first():
    root = ET.fromstring(_build([_ep("2026-09-21"), _ep("2026-09-23"), _ep("2026-09-22")]))
    titles = [i.findtext("title") for i in root.iter("item")]
    assert titles == ["朝のニュース 2026-09-23", "朝のニュース 2026-09-22", "朝のニュース 2026-09-21"]


def test_enclosure_points_to_episode_file():
    root = ET.fromstring(_build([_ep("2026-09-23")]))
    enc = next(root.iter("enclosure"))
    assert enc.get("url") == "https://example.github.io/morning-news/episodes/2026-09-23.mp3"
    assert enc.get("length") == "7000000"
    assert enc.get("type") == "audio/mpeg"


def test_duration_is_hh_mm_ss():
    root = ET.fromstring(_build([_ep("2026-09-23")]))
    assert next(root.iter(ITUNES + "duration")).text == "00:19:45"


def test_special_characters_are_escaped():
    root = ET.fromstring(_build([_ep("2026-09-23", title="労使 & AI <速報>")]))
    assert next(root.iter("item")).findtext("title") == "労使 & AI <速報>"


def test_pubdate_is_rfc822():
    root = ET.fromstring(_build([_ep("2026-09-23")]))
    assert next(root.iter("item")).findtext("pubDate") == "Wed, 23 Sep 2026 05:30:00 +0900"


def test_no_image_tag_when_image_url_omitted():
    root = ET.fromstring(_build([_ep("2026-09-23")]))
    assert root.find(f"channel/{ITUNES}image") is None
    assert root.find("channel/image") is None


def test_image_tags_present_when_image_url_given():
    xml = build_feed(
        [_ep("2026-09-23")],
        title="朝のニュース",
        description="自分用",
        site_url="https://example.github.io/morning-news",
        image_url="https://example.github.io/morning-news/cover.jpg",
    )
    root = ET.fromstring(xml)
    itunes_image = root.find(f"channel/{ITUNES}image")
    assert itunes_image.get("href") == "https://example.github.io/morning-news/cover.jpg"
    assert root.findtext("channel/image/url") == "https://example.github.io/morning-news/cover.jpg"
    assert root.findtext("channel/image/title") == "朝のニュース"
