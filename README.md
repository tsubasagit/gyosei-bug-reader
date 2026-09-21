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
index.html            作品トップ（表紙と読むボタン → エピソード一覧 → どんな漫画？ → 登場人物。一覧は episodes.json から作る）
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

## 英語で読む（試作）

- `?lang=en` を付けると英語になる（例：`ep/1/?lang=en`）。選んだ言語はブラウザに覚える。日本語に戻すときは右上（読む画面は右下）のボタンか `?lang=ja`
- 文言は `assets/i18n.js`。HTML の日本語はそのまま残し、英語のときだけ `data-i18n`（文字）・`data-i18n-html`（リンク入りの文）・`data-i18n-attr`（alt などの属性）の印が付いたところを差し替える。文言を足すときは HTML に印を付けて、`i18n.js` の `EN` に同じキーで英語を書く
- 題名・副題・あらすじの英語は `episodes.json` の `title_en`・`subtitle_en`・`summary_en`
- 対訳は `ep/<話ID>/script.en.json`。作り方：

  ```
  python tools/build_script.py "<name-maker の話フォルダ>" <話ID> --lang en
  ```

  ネーム.json のナレーションとセリフを、コマの順・吹き出しの順（右上から左下）に並べて書き出す。`en` に英訳、必要なら `note` に制度のひとこと解説を書く。書き出し直しても、同じ id の `en` と `note` は残る。対訳ファイルが無い話は、英語でも絵だけで読む
- 対訳は、幅 1100px 以上の画面ではページの右に、コマの上端の高さにそろえて並ぶ（対訳にマウスを載せると、そのコマに枠が出る）。狭い画面ではページの下、スマホは下のバーのボタン。コマの位置は `script.en.json` の `panels`（ページ画像の上の割合）で、`build_pages.py` が episodes.json に書く `crop` から計算する。**`build_pages.py` を流したあとに `build_script.py` を流す**
- CSS・JS を直したら、HTML の `?v=` を新しい値にする（古いファイルがブラウザに残って、新しい HTML と噛み合わなくなるのを防ぐ）

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
