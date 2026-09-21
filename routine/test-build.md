これは動作確認です。ニュース・メール・カレンダー・Googleドライブには一切触れないでください。有料の音声ツールは使わないでください。

【守ること】
- 書き込みは、ブランチ `claude/feed-test` だけ。`main` と `claude/feed` には push しない。
- 証明書の検証を無効にしない。プロキシの設定・認証情報・環境変数の中身を読まない。通信制限を迂回しない。通らなければ、事実とエラーの要点だけを報告して止まる。

次を順に実行し、最後に各段階の成功・失敗と実際の出力を日本語で報告してください。

1. `bash scripts/setup_cloud.sh` を実行する（2〜3分）。終了コードと最後の5行を報告する。
2. 次の内容を `test_script.txt` に保存する（段落の間は空行）。

```
おはようございます。これは、朝のニュース音声の動作確認です。三つの段落を読み上げます。

一つ目の段落です。労働、エーアイ、経済、パチンコ業界、マダミスと謎解き、東京のイベントの順に、お伝えする予定です。

二つ目の段落です。文章はできるだけ短く区切って、聞き取りやすくします。以上、テストでした。
```

3. `~/work/venv/bin/python -m scripts.build_episode --script test_script.txt --out out/test.mp3` を実行し、標準出力のJSON（duration_sec, bytes, synth_sec）を報告する。
4. `git fetch origin && git checkout -b claude/feed-test origin/main` を実行し、`out/test.mp3` を `episodes/test.mp3` としてコピーして `git add episodes/test.mp3` → `git commit -m "Add test episode"` → `git push -u origin claude/feed-test` を実行する。push の結果を報告する。
