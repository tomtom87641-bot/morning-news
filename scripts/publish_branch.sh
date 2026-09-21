#!/usr/bin/env bash
# usage: publish_branch.sh BRANCH MP3 DATE TITLE DESCRIPTION DURATION_SEC
# 公開ブランチへ回を追加して push する。環境変数 SITE（作業場所）と PYTHON（既定 python3）で上書きできる。
set -euo pipefail
BRANCH="$1"; MP3="$(realpath "$2")"; DATE="$3"; TITLE="$4"; DESC="$5"; DUR="$6"
REPO="$(git rev-parse --show-toplevel)"
SITE="${SITE:-$HOME/work/site}"
PY="${PYTHON:-python3}"
cd "$REPO"
rm -rf "$SITE"
git worktree prune
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  git fetch origin "$BRANCH"
  git worktree add -B "$BRANCH" "$SITE" "origin/$BRANCH"
else
  git worktree add --detach "$SITE"
  git -C "$SITE" checkout --orphan "$BRANCH"
  git -C "$SITE" rm -rf --quiet .
fi
"$PY" -m scripts.publish --site-dir "$SITE" --mp3 "$MP3" --date "$DATE" \
  --title "$TITLE" --description "$DESC" --duration-sec "$DUR" \
  --pub-date "$(TZ=Asia/Tokyo date +%Y-%m-%dT%H:%M:%S%:z)"
git -C "$SITE" add -A
git -C "$SITE" commit -m "Add episode $DATE"
git -C "$SITE" push origin "$BRANCH"
echo "published $DATE to $BRANCH"
