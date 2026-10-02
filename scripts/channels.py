"""ポッドキャストのチャンネル（番組）の定義。配信は同じ GitHub Pages の中で、番組ごとにフォルダを分ける。"""
from dataclasses import dataclass

SITE_ROOT = "https://tomtom87641-bot.github.io/morning-news"


@dataclass(frozen=True)
class Channel:
    id: str
    subdir: str  # 配信ブランチ内のフォルダ。"" は最上位（朝のニュース）
    title: str
    description: str
    keep: int  # 一覧に残す回数
    cover: str  # assets/ にある、番組のカバー画像のファイル名


CHANNELS = {
    c.id: c
    for c in (
        Channel("news", "", "朝のニュース（自分用）", "毎朝、公開ニュースを自分用にまとめて読み上げる番組。", 7, "cover.jpg"),
        Channel("annex", "annex", "別館", "朝のニュースとは別の、いろいろな音声を置く場所。", 20, "cover_annex.jpg"),
    )
}


def get_channel(channel_id: str) -> Channel:
    try:
        return CHANNELS[channel_id]
    except KeyError:
        raise ValueError(f"不明なチャンネル: {channel_id}（{' / '.join(CHANNELS)} のどれか）") from None


def channel_site_url(channel: Channel) -> str:
    return f"{SITE_ROOT}/{channel.subdir}" if channel.subdir else SITE_ROOT
