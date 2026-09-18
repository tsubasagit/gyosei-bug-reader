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
- UI の文言は日本語。会社名は「株式会社AppTalentHub」と書く（略称は使わない）
- localStorage は見開き／1ページの好みだけ。読めなくても動くように try/catch で包む

## 作品の正

作品の中身・キャラクターの正は `03_contents/01_stock/comics/漫画-行政バグります/` と、非公開リポジトリ `comic-gyosei-bug`。
