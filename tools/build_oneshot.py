"""話数に入れない一話（読み切り・没案）を yomikiri/<id>/ に書き出す。

使い方:
    python tools/build_oneshot.py <話フォルダ> <id> [--cover <縦の表紙>]

- ページの組み方・余白の切り方・thumb.webp / og.jpg は build_pages.py と同じ（関数をそのまま使う）
- episodes.json の oneshots にある <id> の pages・sizes・hasCover を書き出したもので更新する
  （題名・あらすじなどは先に episodes.json に書いておく）
- 最後に build_seo で sitemap などを作り直す
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp

sys.stdout.reconfigure(encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('oneshot_id')
    ap.add_argument('--cover')
    args = ap.parse_args()

    ep_path = os.path.join(bp.ROOT, 'episodes.json')
    data = json.load(open(ep_path, encoding='utf-8'))
    one = next((o for o in data.get('oneshots', []) if o['id'] == args.oneshot_id), None)
    if one is None:
        raise SystemExit(f'episodes.json の oneshots に {args.oneshot_id} がありません。先に書き足してください。')

    out_dir = os.path.join(bp.ROOT, *one['dir'].split('/'))
    pages_dir = os.path.join(out_dir, 'pages')
    os.makedirs(pages_dir, exist_ok=True)
    for f in os.listdir(pages_dir):
        if f.endswith('.webp'):
            os.remove(os.path.join(pages_dir, f))

    name_json = json.load(open(os.path.join(args.folder, 'ネーム.json'), encoding='utf-8'))
    cover = bp.cover_page(args.cover) if args.cover else None
    pages = []
    for i, page in enumerate(name_json['pages'], 1):
        img, missing = bp.page_image(args.folder, page)
        if missing:
            raise SystemExit(f'P{i} に絵が採用されていないコマがあります: {missing}')
        pages.append(img)
    cover, pages, _ = bp.trim_margins(cover, pages)

    files = []
    for name, img in ([('p00.webp', cover)] if cover else []) + [(f'p{i:02d}.webp', img) for i, img in enumerate(pages, 1)]:
        p = os.path.join(pages_dir, name)
        img.save(p, 'WEBP', quality=bp.QUALITY, method=6)
        files.append(name)
        print(name, img.size, os.path.getsize(p) // 1024, 'KB')

    wide = bp.find_wide_cover(args.folder)
    if not wide:
        raise SystemExit('話フォルダに横の表紙（扉絵-横-〜.png）がありません。')
    bp.save_thumb_og(out_dir, *bp.cover_images(args.folder, wide))

    one['pages'] = files
    one['sizes'] = [list(img.size) for img in ([cover] if cover else []) + pages]
    one['hasCover'] = bool(args.cover)
    with open(ep_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'{len(files)} 枚。episodes.json の oneshots を更新しました。')

    import build_seo
    build_seo.build()


if __name__ == '__main__':
    main()
