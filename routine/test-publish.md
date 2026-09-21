これは動作確認です。ニュース・メール・カレンダー・Googleドライブには一切触れないでください。有料の音声ツールは使わないでください。

【守ること】
- 書き込みは、ブランチ `claude/feed` だけ（これが公開ブランチ）。`main` には push しない。
- 公開されるので、内容は下の固定のテスト原稿だけにする。
- 作業ファイル（原稿・ログ・mp3）は、リポジトリの中に作らず、`~/work/` に置く。
- 証明書の検証を無効にしない。プロキシの設定・認証情報・環境変数の中身を読まない。通信制限を迂回しない。通らなければ、事実とエラーの要点だけを報告して止まる。

次を順に実行し、最後に各段階の成功・失敗と実際の出力を日本語で報告してください。

1. `bash scripts/setup_cloud.sh` を実行する（2〜3分）。
2. `mkdir -p ~/work/out` を実行し、`TODAY=$(TZ=Asia/Tokyo date +%F)` を求め、次の内容を `~/work/test_script.txt` に保存する（リポジトリの中には作らない。段落の間は空行）。

```
おはようございます。これは、朝のニュース音声の公開テストです。

購読の登録と、自動ダウンロードの確認のための、短い回です。以上、テストでした。
```

3. `~/work/venv/bin/python -m scripts.build_episode --script ~/work/test_script.txt --out ~/work/out/ep.mp3` を実行し、JSONを報告する。
4. `bash scripts/publish_branch.sh claude/feed ~/work/out/ep.mp3 "$TODAY" "朝のニュース ${TODAY}（テスト）" "公開テスト用の短い回です。" <3のduration_sec>` を実行する。
5. 公開を確認する。最大5分、15秒おきに `curl -s https://tomtom87641-bot.github.io/morning-news/feed.xml` を実行し、`morning-news-${TODAY}` が含まれるかを確かめる。含まれた時点で終了し、結果を報告する。
