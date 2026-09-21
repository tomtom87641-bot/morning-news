#!/usr/bin/env bash
# usage: publish_branch.sh BRANCH MP3 DATE TITLE DESCRIPTION DURATION_SEC [TRANSCRIPT_TXT]
# 公開ブランチへ回を追加して push する。環境変数 SITE（作業場所）と PYTHON（既定 python3）で上書きできる。
set -euo pipefail
BRANCH="$1"; MP3="$(realpath "$2")"; DATE="$3"; TITLE="$4"; DESC="$5"; DUR="$6"
TRANSCRIPT="${7:-}"
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
EXTRA=()
if [ -n "$TRANSCRIPT" ]; then EXTRA=(--transcript "$(realpath "$TRANSCRIPT")"); fi
"$PY" -m scripts.publish --site-dir "$SITE" --mp3 "$MP3" --date "$DATE" \
  --title "$TITLE" --description "$DESC" --duration-sec "$DUR" \
  --pub-date "$(TZ=Asia/Tokyo date +%Y-%m-%dT%H:%M:%S%:z)" "${EXTRA[@]}"
git -C "$SITE" add -A
git -C "$SITE" commit -m "Add episode $DATE"
# push は最大3回。表示が fatal でも、リモートに届いていれば成功とみなす（届いたかは ls-remote で確かめる）。
LOCAL="$(git -C "$SITE" rev-parse HEAD)"
for i in 1 2 3; do
  git -C "$SITE" push origin "$BRANCH" || true
  REMOTE="$(git ls-remote origin "refs/heads/$BRANCH" | cut -f1)"
  if [ "$REMOTE" = "$LOCAL" ]; then
    echo "published $DATE to $BRANCH ($LOCAL)"
    exit 0
  fi
  echo "push not confirmed (try $i)"; sleep 3
done
echo "ERROR: push to $BRANCH could not be confirmed" >&2
exit 1
