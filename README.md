# 行政バグります！ Webリーダー

梨ヶ坂市役所の地下にある「特務トレンド係」を舞台にした、1話完結のギャグ漫画をWebで読むためのサイトです。

- 右開き（日本の漫画と同じ）：`←` キー・画面の左クリック・右へフリック（スワイプ）で次のページ、`→` で前のページ
- PC・タブレットなど幅のある画面は、全ページを横幅に合わせて（最大 960px）縦につなげ、スクロールだけで最後まで読む。最後のページの下に「おわり」
- スマホの縦持ち（幅700px未満）は、1ページずつめくる
- 見開き（右が若いページ）は、上のバーの「⋯」メニューで選べる。操作のしかたもこのメニューに書いてある
- 進み具合は画面の上端の細い線。マウスで読む画面では、上のバーは上端にマウスを寄せたときだけ出る
- ページ画像は紙の白い余白を切り落としてある（`build_pages.py` が自動で切る）
- `#p=5` を付けたリンクで、そのページから開ける

## 構成

```
index.html            作品トップ（表紙と読むボタン → どんな漫画？ → 登場人物 → エピソード一覧。一覧は episodes.json から作る）
episodes.json         作品とエピソードの情報、各話のページ画像の一覧
ep/<話ID>/index.html  読む画面（話ごとに1枚。中身は assets/reader.js）
ep/<話ID>/pages/      ページ画像（p00.webp が扉絵、p01.webp〜 が本編）
ep/<話ID>/thumb.webp  一覧に出す小さい絵
ep/<話ID>/og.jpg      SNS で共有したときの絵（1200×630）
assets/               CSS・JavaScript・favicon
assets/cover.webp     表紙（元の画像はシリーズのフォルダの 表紙_梨ヶ坂版_20260919.png）
assets/og-top.jpg     作品トップを SNS で共有したときの絵（表紙＋題名）
assets/chara/         登場人物4人の絵（元の画像はシリーズの 設定/キャラクター/Web紹介用_20260919/）
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
3. `ep/22/index.html` を `ep/<話ID>/index.html` に写し（「おわり」の「次の話へ」は reader.js が episodes.json から自動で足す）、`data-episode`・タイトル・説明・OGP の URL を書き換える
4. 手元で確かめる：`python -m http.server 8976` → http://localhost:8976/
5. push すると GitHub Pages に反映される

## ライセンス

作品（画像・文章）の著作権は株式会社AppTalentHubに帰属します。無断転載を禁じます。
