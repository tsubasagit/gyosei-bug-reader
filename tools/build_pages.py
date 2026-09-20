"""name-maker の話フォルダ（ネーム.json と 作画/）から、Web リーダー用のページ画像を作る。

使い方:
    python tools/build_pages.py <話フォルダ> <話ID> [--cover <扉絵の画像>] [--og-panel P1-コマ1]

- ネーム.json のコマの位置と、採用済みの絵（作画/P{n}-コマ{m}.png）でページを組む（A4 縦・右開き）
- 紙の白い余白は切り落とす（本編は全ページ同じ範囲で切る）
- 出力は ep/<話ID>/pages/p01.webp〜。扉絵を渡すと p00.webp として先頭に置く
- 一覧用の小さい絵 ep/<話ID>/thumb.webp と、SNS 共有用の ep/<話ID>/og.jpg も作る
- episodes.json の該当する話の pages（ファイル名）と sizes（幅・高さ）を、書き出したもので更新する
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_W, PAGE_H = 794, 1123          # name-maker のページ座標（A4 @96dpi）
SCALE = 2.0                          # 出力は 1588×2246
BORDER = 3                           # コマ枠の太さ（ページ座標）
QUALITY = 82
TRIM_PAD = 12                        # 余白を切り落としたあとに残す白（ページ座標）


def page_image(folder, page, scale=SCALE):
    w, h = round(PAGE_W * scale), round(PAGE_H * scale)
    canvas = Image.new('RGB', (w, h), 'white')
    draw = ImageDraw.Draw(canvas)
    missing = []
    for o in page['objects']:
        if o['type'] != 'panel':
            continue
        x, y, pw, ph = [round(v * scale) for v in (o['x'], o['y'], o['w'], o['h'])]
        cand = next((c for c in o.get('candidates', []) if c['id'] == o.get('approvedCandidateId')), None)
        if cand:
            im = Image.open(os.path.join(folder, cand['image'])).convert('RGB')
            r = max(pw / im.width, ph / im.height)
            im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
            left, top = (im.width - pw) // 2, (im.height - ph) // 2
            canvas.paste(im.crop((left, top, left + pw, top + ph)), (x, y))
        else:
            missing.append(o.get('readingOrder'))
        draw.rectangle((x, y, x + pw - 1, y + ph - 1), outline='black', width=round(BORDER * scale))
    return canvas, missing


def cover_page(path, scale=SCALE):
    """扉絵をページと同じ大きさの白い紙に、縦いっぱいで中央に置く。"""
    w, h = round(PAGE_W * scale), round(PAGE_H * scale)
    im = Image.open(path).convert('RGB')
    r = min(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    canvas = Image.new('RGB', (w, h), 'white')
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def content_box(img, pad):
    """白い紙の上で、絵や枠がある範囲（白でないところ）を pad だけ広げて返す。"""
    gray = img.convert('L')
    box = ImageChops.difference(gray, Image.new('L', gray.size, 255)).point(lambda v: 255 if v > 24 else 0).getbbox()
    if not box:
        return (0, 0) + img.size
    return (max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, img.width), min(box[3] + pad, img.height))


def trim_margins(cover, pages, pad=round(TRIM_PAD * SCALE)):
    """紙の白い余白を切り落とす。本編は全ページ同じ範囲で切る（見開きで大きさがそろうように）。"""
    if pages:
        boxes = [content_box(p, pad) for p in pages]
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        pages = [p.crop(box) for p in pages]
    if cover is not None:
        cover = cover.crop(content_box(cover, pad))
    return cover, pages


def og_image(folder, name_json, panel_name):
    """共有用 1200×630。指定したコマの絵を中央で切り抜く。"""
    pn, ko = panel_name.split('-')
    page = name_json['pages'][int(pn[1:]) - 1]
    o = next(o for o in page['objects'] if o['type'] == 'panel' and o['readingOrder'] == int(ko.replace('コマ', '')))
    cand = next(c for c in o['candidates'] if c['id'] == o['approvedCandidateId'])
    im = Image.open(os.path.join(folder, cand['image'])).convert('RGB')
    tw, th = 1200, 630
    r = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    left, top = (im.width - tw) // 2, (im.height - th) // 2
    return im.crop((left, top, left + tw, top + th))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('episode_id')
    ap.add_argument('--cover')
    ap.add_argument('--og-panel', default='P1-コマ1')
    args = ap.parse_args()

    name_json = json.load(open(os.path.join(args.folder, 'ネーム.json'), encoding='utf-8'))
    out_dir = os.path.join(ROOT, 'ep', args.episode_id)
    pages_dir = os.path.join(out_dir, 'pages')
    os.makedirs(pages_dir, exist_ok=True)
    for f in os.listdir(pages_dir):
        if f.endswith('.webp'):
            os.remove(os.path.join(pages_dir, f))

    cover = cover_page(args.cover) if args.cover else None
    pages = []
    for i, page in enumerate(name_json['pages'], 1):
        img, missing = page_image(args.folder, page)
        if missing:
            raise SystemExit(f'P{i} に絵が採用されていないコマがあります: {missing}')
        pages.append(img)
    cover, pages = trim_margins(cover, pages)

    files = []
    for name, img in ([('p00.webp', cover)] if cover else []) + [(f'p{i:02d}.webp', img) for i, img in enumerate(pages, 1)]:
        p = os.path.join(pages_dir, name)
        img.save(p, 'WEBP', quality=QUALITY, method=6)
        files.append(name)
        print(name, img.size, os.path.getsize(p) // 1024, 'KB')

    # 一覧用の小さい絵（扉絵があれば扉絵、なければ1ページ目）
    thumb_src = os.path.join(pages_dir, files[0])
    t = Image.open(thumb_src)
    t.thumbnail((480, 680))
    t.save(os.path.join(out_dir, 'thumb.webp'), 'WEBP', quality=80, method=6)
    og_image(args.folder, name_json, args.og_panel).save(os.path.join(out_dir, 'og.jpg'), quality=85)

    # episodes.json の pages を更新
    ep_path = os.path.join(ROOT, 'episodes.json')
    data = json.load(open(ep_path, encoding='utf-8'))
    ep = next((e for e in data['episodes'] if e['id'] == args.episode_id), None)
    if ep is None:
        raise SystemExit(f'episodes.json に話 {args.episode_id} がありません。先に書き足してください。')
    ep['pages'] = files
    ep['sizes'] = [list(img.size) for img in ([cover] if cover else []) + pages]  # 読み込む前に高さを取っておくため
    ep['hasCover'] = bool(args.cover)
    with open(ep_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')  # 末尾の改行を残す（ないと毎回ここだけ差分になる）
    total = sum(os.path.getsize(os.path.join(pages_dir, f)) for f in files)
    print(f'{len(files)} 枚、合計 {total // 1024} KB。episodes.json を更新しました。')


if __name__ == '__main__':
    main()
