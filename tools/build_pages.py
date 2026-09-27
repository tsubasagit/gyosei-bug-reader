"""name-maker の話フォルダ（ネーム.json と 作画/）から、Web リーダー用のページ画像を作る。

使い方:
    python tools/build_pages.py <話フォルダ> <話ID> [--cover <扉絵の画像>] [--og-panel P1-コマ1]
    python tools/build_pages.py <話フォルダ> <話ID> --covers-only    # 一覧の絵と共有の絵だけ作り直す

- ネーム.json のコマの位置と、採用済みの絵（作画/P{n}-コマ{m}.png）でページを組む（A4 縦・右開き）
- 紙の白い余白は切り落とす（本編は全ページ同じ範囲で切る）
- 出力は ep/<話ID>/pages/p01.webp〜。扉絵を渡すと p00.webp として先頭に置く
- 一覧用の小さい絵 ep/<話ID>/thumb.webp と、SNS 共有用の ep/<話ID>/og.jpg も作る。
  話フォルダに横のカラー表紙（扉絵-横-〜.png）があれば、どちらもそこから作る（thumb は 640×360）。
  og.jpg（1200×630）は表紙より横長なので、ロゴなしの原画（_backups/扉絵-横-カラー表紙_ロゴなし.png）の下を切り、
  シリーズの 設定/ロゴ/ のロゴを表紙と同じ付け方で右下に重ね直す（題名もロゴも切れないように）。
  横の表紙が無い話は、これまでどおり thumb は先頭のページ、og.jpg は --og-panel のコマから作る
- episodes.json の該当する話の pages（ファイル名）と sizes（幅・高さ）を、書き出したもので更新する
"""
import argparse
import json
import os
import re
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_W, PAGE_H = 794, 1123          # name-maker のページ座標（A4 @96dpi）
SCALE = 2.0                          # 出力は 1588×2246
BORDER = 3                           # コマ枠の太さ（ページ座標）
QUALITY = 82
TRIM_PAD = 12                        # 余白を切り落としたあとに残す白（ページ座標）
THUMB_W, THUMB_H = 640, 360          # 一覧の絵（横の表紙から作るとき）
OG_W, OG_H = 1200, 630               # SNS で共有したときの絵
WIDE_COVER = re.compile(r'^扉絵[-_ ]?横.*\.(png|jpe?g|webp)$', re.I)   # name-maker と同じ決め方
PLAIN_COVER = os.path.join('_backups', '扉絵-横-カラー表紙_ロゴなし.png')
LOGO = os.path.join('設定', 'ロゴ', '行政バグります_ロゴ_透過.png')      # シリーズのフォルダから見た場所


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
    box = None
    if pages:
        boxes = [content_box(p, pad) for p in pages]
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        pages = [p.crop(box) for p in pages]
    if cover is not None:
        cover = cover.crop(content_box(cover, pad))
    return cover, pages, box


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


def find_wide_cover(folder):
    """話フォルダの横の表紙。「扉絵-横…」の名前順で最初の1枚。無ければ None。"""
    names = sorted(n for n in os.listdir(folder) if WIDE_COVER.match(n))
    return os.path.join(folder, names[0]) if names else None


def fill(im, tw, th, top=None):
    """tw×th をすき間なく埋めるように縮め、はみ出した分を切る。top=0 なら上をそろえて下を切る。"""
    r = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    left = (im.width - tw) // 2
    top = (im.height - th) // 2 if top is None else top
    return im.crop((left, top, left + tw, top + th))


def put_logo(im, logo_path):
    """ロゴを右下に重ねる。カラー表紙（幅1672）と同じ付け方：幅600、白ふち11px、右下へずらした薄い影。"""
    cov = im.convert('RGBA')
    k = cov.width / 1672
    lw = round(600 * k)
    logo = Image.open(logo_path).convert('RGBA')
    lh = round(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    a = logo.split()[3]
    grow = max(3, round(11 * k) | 1)                                     # MaxFilter は奇数だけ
    outline = a.filter(ImageFilter.MaxFilter(grow)).filter(ImageFilter.GaussianBlur(1))
    shadow = a.filter(ImageFilter.MaxFilter(grow)).filter(ImageFilter.GaussianBlur(8 * k))
    px, py = cov.width - lw - round(14 * k), cov.height - lh - round(8 * k)
    sh = Image.new('RGBA', (lw, lh), (0, 0, 0, 0))
    sh.putalpha(shadow.point(lambda v: int(v * 0.55)))
    cov.alpha_composite(sh, (px + round(6 * k), py + round(8 * k)))
    wh = Image.new('RGBA', (lw, lh), (255, 255, 255, 0))
    wh.putalpha(outline)
    cov.alpha_composite(wh, (px, py))
    cov.alpha_composite(logo, (px, py))
    return cov.convert('RGB')


def cover_images(folder, wide):
    """横の表紙から、一覧の絵（thumb）と共有の絵（og）を作る。"""
    im = Image.open(wide).convert('RGB')
    thumb = fill(im, THUMB_W, THUMB_H)
    plain = os.path.join(folder, PLAIN_COVER)
    logo = os.path.join(folder, '..', '..', LOGO)
    if os.path.exists(plain) and os.path.exists(logo):
        src = Image.open(plain).convert('RGB')
        h = round(src.width * OG_H / OG_W)                                # 表紙の幅のまま 1200:630 にする高さ
        og = put_logo(src.crop((0, 0, src.width, min(h, src.height))), logo).resize((OG_W, OG_H), Image.LANCZOS)
    else:
        print(f'ロゴなしの原画（{PLAIN_COVER}）かロゴが無いので、og.jpg は表紙の上下を切って作ります（ロゴの下が少し切れます）。')
        og = fill(im, OG_W, OG_H)
    return thumb, og


def save_thumb_og(out_dir, thumb, og):
    thumb.save(os.path.join(out_dir, 'thumb.webp'), 'WEBP', quality=80, method=6)
    og.save(os.path.join(out_dir, 'og.jpg'), quality=85)
    print('thumb.webp', thumb.size, '/ og.jpg', og.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('episode_id')
    ap.add_argument('--cover')
    ap.add_argument('--og-panel', default='P1-コマ1')
    ap.add_argument('--covers-only', action='store_true', help='ページは作らず、横の表紙から thumb.webp と og.jpg だけ作り直す')
    args = ap.parse_args()

    wide = find_wide_cover(args.folder)
    if args.covers_only:
        if not wide:
            raise SystemExit('話フォルダに横の表紙（扉絵-横-〜.png）がありません。')
        out_dir = os.path.join(ROOT, 'ep', args.episode_id)
        if not os.path.isdir(out_dir):
            raise SystemExit(f'ep/{args.episode_id}/ がありません。先にページを作ってください。')
        save_thumb_og(out_dir, *cover_images(args.folder, wide))
        return

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
    cover, pages, crop = trim_margins(cover, pages)

    files = []
    for name, img in ([('p00.webp', cover)] if cover else []) + [(f'p{i:02d}.webp', img) for i, img in enumerate(pages, 1)]:
        p = os.path.join(pages_dir, name)
        img.save(p, 'WEBP', quality=QUALITY, method=6)
        files.append(name)
        print(name, img.size, os.path.getsize(p) // 1024, 'KB')

    # 一覧用の小さい絵と共有の絵。横のカラー表紙があればそこから、無ければ先頭のページと --og-panel のコマから
    if wide:
        save_thumb_og(out_dir, *cover_images(args.folder, wide))
    else:
        t = Image.open(os.path.join(pages_dir, files[0]))
        t.thumbnail((480, 680))
        save_thumb_og(out_dir, t, og_image(args.folder, name_json, args.og_panel))

    # episodes.json の pages を更新
    ep_path = os.path.join(ROOT, 'episodes.json')
    data = json.load(open(ep_path, encoding='utf-8'))
    ep = next((e for e in data['episodes'] if e['id'] == args.episode_id), None)
    if ep is None:
        raise SystemExit(f'episodes.json に話 {args.episode_id} がありません。先に書き足してください。')
    ep['pages'] = files
    ep['sizes'] = [list(img.size) for img in ([cover] if cover else []) + pages]  # 読み込む前に高さを取っておくため
    ep['hasCover'] = bool(args.cover)
    # 本編を切り取った範囲（ページ座標 794×1123 を SCALE 倍した画素）。対訳をコマの横に並べるのに使う
    ep['crop'] = {'scale': SCALE, 'box': list(crop)} if crop else None
    with open(ep_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')  # 末尾の改行を残す（ないと毎回ここだけ差分になる）
    total = sum(os.path.getsize(os.path.join(pages_dir, f)) for f in files)
    print(f'{len(files)} 枚、合計 {total // 1024} KB。episodes.json を更新しました。')

    # 新しい話のお知らせ（feed.xml）も作り直す
    import build_feed
    build_feed.build()


if __name__ == '__main__':
    main()
