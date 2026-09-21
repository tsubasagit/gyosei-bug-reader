# CLAUDE.md — gyosei-bug-reader

漫画「行政バグります！」の Web リーダー。静的サイト（HTML/CSS/素の JavaScript）で、GitHub Pages で配信する。仕様は SERVICE_SPEC.md、話の足し方は README.md。

## 手元で確かめる

```
python -m http.server 8976
```

`.claude/launch.json`（AppTalentHub 直下）に `gyosei-bug-reader` の設定がある。

## 決まりごと

- **右開き**：← が次のページ。見開きは `.stage` の `flex-direction: row-reverse` で若いページを右に置く。逆にしない
- ページ画像は `tools/build_pages.py` で作る。制作データ（設定資料・プロンプト・ネーム.json）はこのリポジトリに入れない（公開リポジトリのため）
- パスは相対パスで書く（GitHub Pages ではサイトが `/gyosei-bug-reader/` の下に置かれる）
- UI の文言は日本語が標準。会社名は「株式会社AppTalentHub」と書く（略称は使わない）
- 英語表示（`?lang=en`）の文言は `assets/i18n.js` に集める。HTML の日本語は書き換えず、`data-i18n` の印で差し替える。JS が作る文言は `I18N.t` から取り、日本語を JS に直書きしない
- 漫画の絵の中に話数を入れない。話数はサイトの表示（一覧・見出し）で出す
- CSS・JS を直したら、各 HTML の読み込みの `?v=` を上げる
- 表示は3通り：縦につなげる（幅700px以上の標準）・めくる（幅700px未満）・見開き（メニューで選択）。`episodes.json` の `sizes` で読み込み前に高さを取るので、ページ画像を差し替えたら `sizes` も直す（`build_pages.py` なら自動）
- localStorage に置くのは、見開きの好み・一覧の並び順・言語だけ。読めなくても動くように try/catch で包む

## 作品の正

作品の中身・キャラクターの正は `03_contents/01_stock/comics/漫画-行政バグります/` と、非公開リポジトリ `comic-gyosei-bug`。
