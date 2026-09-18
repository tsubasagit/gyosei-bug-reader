# 行政バグります！ Webリーダー

梨ヶ坂市役所の地下にある「特務トレンド係」を舞台にした、1話完結のギャグ漫画をWebで読むためのサイトです。

- 右開き（日本の漫画と同じ）：`←` キー・画面の左クリック・右へスワイプで次のページ、`→` で前のページ
- 横長の画面では見開き（右が若いページ）、スマホの縦持ちでは1ページずつ
- `#p=5` を付けたリンクで、そのページから開ける

## 構成

```
index.html            作品トップ（エピソード一覧。episodes.json から作る）
episodes.json         作品とエピソードの情報、各話のページ画像の一覧
ep/<話ID>/index.html  読む画面（話ごとに1枚。中身は assets/reader.js）
ep/<話ID>/pages/      ページ画像（p00.webp が扉絵、p01.webp〜 が本編）
ep/<話ID>/thumb.webp  一覧に出す小さい絵
ep/<話ID>/og.jpg      SNS で共有したときの絵（1200×630）
assets/               CSS・JavaScript・favicon
tools/build_pages.py  name-maker の話フォルダからページ画像を作るツール
```

ビルドの仕組みはありません。ファイルをそのまま GitHub Pages で配信します。

## 話を足す

1. `episodes.json` の `episodes` に、話の情報（id・number・title・subtitle・summary・published）を足す
2. ページ画像を作る

   ```
   python tools/build_pages.py "<name-maker の話フォルダ>" <話ID> --cover "<扉絵の画像>" --og-panel P1-コマ1
   ```

   ネーム.json のコマの位置と、採用済みの絵（作画/）でページを組みます。全コマが採用済みでないと止まります。
3. `ep/22/index.html` を `ep/<話ID>/index.html` に写し、`data-episode`・タイトル・説明・OGP の URL を書き換える
4. 手元で確かめる：`python -m http.server 8976` → http://localhost:8976/
5. push すると GitHub Pages に反映される

## ライセンス

作品（画像・文章）の著作権は株式会社AppTalentHubに帰属します。無断転載を禁じます。
