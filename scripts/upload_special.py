"""すでにある音声（MP3）を、別のチャンネル（既定は「別館」）に1回分として公開する／取り消す。

使い方は docs/ポッドキャスト別館_アップロード指示書.md を見る。
  python -m scripts.upload_special upload --mp3 音声.mp3 --title 題名 --description 説明
  python -m scripts.upload_special list
  python -m scripts.upload_special remove --key 日付キー
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.channels import channel_site_url, get_channel
from scripts.feed import Episode
from scripts.mp3info import mp3_duration_sec
from scripts.publish import load_episodes, publish_channel, unpublish_channel

JST = timezone(timedelta(hours=9))
REPO = Path(__file__).resolve().parent.parent
BRANCH = "claude/feed"
_KEY = re.compile(r"^\d{4}-\d{2}-\d{2}(-[a-z0-9]+)*$")


def validate_key(key: str) -> None:
    if not _KEY.fullmatch(key):
        raise ValueError(
            f"日付キー {key!r} は使えません。「2026-10-03」または「2026-10-03-demo」のように、"
            "日付のあとに英小文字・数字をハイフンでつないだ形にしてください。"
        )


def default_key(now) -> str:
    return now.astimezone(JST).strftime("%Y-%m-%d-%H%M%S")


def build_episode(key, title, description, mp3, duration_sec, now) -> Episode:
    return Episode(
        date=key,
        title=title,
        description=description,
        filename=f"{key}.mp3",
        length_bytes=Path(mp3).stat().st_size,
        duration_sec=duration_sec,
        pub_date=now.astimezone(JST).isoformat(timespec="seconds"),
    )


def ensure_key_is_free(existing_keys, key, replace) -> None:
    if key in existing_keys and not replace:
        raise ValueError(
            f"日付キー {key} の回がすでにあります。上書きしてよければ --replace を付けてください。"
        )


def ensure_special_channel(channel_id: str) -> None:
    get_channel(channel_id)  # 不明な名前はここで ValueError
    if channel_id == "news":
        raise ValueError(
            "朝のニュース（news）は毎朝の自動実行専用です。別の番組（annex など）を指定してください。"
        )


def resolve_cover(channel, assets_dir):
    path = Path(assets_dir) / channel.cover
    return path if path.exists() else None


def _git(*args, cwd=None, check=True):
    r = subprocess.run(
        ["git", *args], cwd=str(cwd or REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} に失敗しました: {(r.stderr or r.stdout).strip()}")
    return r


def _remote_head() -> str:
    out = _git("ls-remote", "origin", f"refs/heads/{BRANCH}").stdout.split()
    return out[0] if out else ""


def _change_feed_branch(message, mutate, dry_run):
    """配信ブランチの最新を別の場所に取り出し、mutate(site) で書き換え、コミットしてプッシュする。"""
    for _ in range(3):
        tmp = Path(tempfile.mkdtemp(prefix="feed-"))
        site = tmp / "site"
        try:
            _git("fetch", "origin", BRANCH)
            _git("worktree", "add", "--detach", str(site), f"origin/{BRANCH}")
            mutate(site)
            _git("add", "-A", cwd=site)
            _git("commit", "-m", message, cwd=site)
            commit = _git("rev-parse", "HEAD", cwd=site).stdout.strip()
            if dry_run:
                return commit, False
            push = _git("push", "origin", f"HEAD:{BRANCH}", cwd=site, check=False)
            if push.returncode == 0 or _remote_head() == commit:
                return commit, True
            # 毎朝の自動実行など、ほかの更新と重なった。最新を取り直してやり直す
        finally:
            _git("worktree", "remove", "--force", str(site), check=False)
            shutil.rmtree(tmp, ignore_errors=True)
    raise RuntimeError("3回試しても公開できませんでした。少し待ってからもう一度実行してください。")


def upload(
    *, channel_id, mp3, title, description, key=None, transcript=None,
    duration_sec=None, replace=False, dry_run=False,
) -> dict:
    ensure_special_channel(channel_id)
    channel = get_channel(channel_id)
    mp3 = Path(mp3).resolve()
    if not mp3.is_file():
        raise ValueError(f"音声ファイルが見つかりません: {mp3}")
    now = datetime.now(JST)
    key = key or default_key(now)
    validate_key(key)
    duration = duration_sec if duration_sec is not None else mp3_duration_sec(mp3)
    episode = build_episode(key, title, description, mp3, duration, now)
    cover = resolve_cover(channel, REPO / "assets")
    transcript = Path(transcript).resolve() if transcript else None

    def mutate(site):
        existing = {e.date for e in load_episodes(site / channel.subdir / "episodes.json")}
        ensure_key_is_free(existing, key, replace)
        publish_channel(site, channel_id, mp3, episode, transcript=transcript, cover_image=cover)

    commit, pushed = _change_feed_branch(f"Add episode {key} to {channel_id}", mutate, dry_run)
    base = channel_site_url(channel)
    return {
        "channel": channel_id, "key": key, "title": title, "duration_sec": duration,
        "commit": commit[:7], "pushed": pushed,
        "feed_url": f"{base}/feed.xml", "audio_url": f"{base}/episodes/{key}.mp3",
    }


def remove(*, channel_id, key, dry_run=False) -> dict:
    ensure_special_channel(channel_id)
    commit, pushed = _change_feed_branch(
        f"Remove episode {key} from {channel_id}",
        lambda site: unpublish_channel(site, channel_id, key),
        dry_run,
    )
    return {"channel": channel_id, "key": key, "commit": commit[:7], "pushed": pushed}


def list_episodes(channel_id) -> list:
    channel = get_channel(channel_id)
    _git("fetch", "origin", BRANCH)
    prefix = f"{channel.subdir}/" if channel.subdir else ""
    r = _git("show", f"origin/{BRANCH}:{prefix}episodes.json", check=False)
    if r.returncode != 0:
        return []  # まだ1回も公開していない
    return [
        {"key": e["date"], "title": e["title"], "duration_sec": e["duration_sec"], "published": e["pub_date"]}
        for e in json.loads(r.stdout)
    ]


def wait_for_feed(feed_url: str, key: str, present: bool = True, timeout_sec: int = 240) -> bool:
    """公開側（GitHub Pages）の反映を待つ。反映まで通常1〜2分。"""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{feed_url}?t={int(time.time())}", timeout=15) as r:
                if (f"morning-news-{key}" in r.read().decode("utf-8", "replace")) == present:
                    return True
        except Exception:
            pass
        time.sleep(10)
    return False


def _build_parser():
    p = argparse.ArgumentParser(description="別のポッドキャストチャンネル（既定: 別館）に音声を公開する／取り消す")
    sub = p.add_subparsers(dest="command", required=True)

    u = sub.add_parser("upload", help="音声（MP3）を1回分として公開する")
    u.add_argument("--mp3", required=True, type=Path, help="音声ファイル（MP3）")
    u.add_argument("--title", required=True, help="アプリの一覧に出る題名")
    u.add_argument("--description", required=True, help="回の説明文")
    u.add_argument("--channel", default="annex", help="チャンネル（既定: annex＝別館）")
    u.add_argument("--key", help="日付キー（回の名札）。例: 2026-10-03-demo。省略すると現在の日時から自動で付く")
    u.add_argument("--transcript", type=Path, help="原稿テキスト（任意）")
    u.add_argument("--duration-sec", type=int, help="再生時間（秒）。省略するとMP3から自動で測る")
    u.add_argument("--replace", action="store_true", help="同じ日付キーの回があるとき上書きする")
    u.add_argument("--dry-run", action="store_true", help="公開せずに、できあがりの確認だけする")
    u.add_argument("--no-verify", action="store_true", help="公開後の反映確認を省く")

    r = sub.add_parser("remove", help="公開済みの回を取り消す")
    r.add_argument("--key", required=True, help="取り消す回の日付キー")
    r.add_argument("--channel", default="annex")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--no-verify", action="store_true", help="取り消し後の反映確認を省く")

    ls = sub.add_parser("list", help="いま公開されている回の一覧を見る")
    ls.add_argument("--channel", default="annex")
    return p


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    a = _build_parser().parse_args(argv)
    try:
        if a.command == "list":
            print(json.dumps(list_episodes(a.channel), ensure_ascii=False, indent=2))
            return 0
        if a.command == "upload":
            result = upload(
                channel_id=a.channel, mp3=a.mp3, title=a.title, description=a.description,
                key=a.key, transcript=a.transcript, duration_sec=a.duration_sec,
                replace=a.replace, dry_run=a.dry_run,
            )
            present = True
        else:
            result = remove(channel_id=a.channel, key=a.key, dry_run=a.dry_run)
            result["feed_url"] = f"{channel_site_url(get_channel(a.channel))}/feed.xml"
            present = False
    except (ValueError, RuntimeError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["pushed"] and not a.no_verify:
        ok = wait_for_feed(result["feed_url"], result["key"], present=present)
        print(
            "公開側に反映されました。" if ok
            else "プッシュはできましたが、公開側の反映は確認できませんでした（通常1〜2分かかります。"
                 "この環境から公開側に接続できないだけかもしれません）。",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
