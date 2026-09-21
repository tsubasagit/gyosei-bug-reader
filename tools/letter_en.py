"""コマの絵の吹き出しの日本語を消して、対訳（script.en.json）の英語を書き入れる。絵そのものは変えない。

使い方:
    python tools/letter_en.py <話フォルダ> <話ID> [--pages 2,3] [--out <出力フォルダ>]

- 吹き出しは絵の中から探す：白い地が黒い線に囲まれていて、中に文字（小さな黒い塊）がいくつもある領域
- ネーム.json のセリフの位置に一番近い吹き出しに、そのセリフの英語を入れる（ネームの位置は目安で、絵とは少しずれる）
- 吹き出しの中を白で塗りつぶし、英語を横書きで、収まるいちばん大きな字で中央に置く
- 見つからなかったセリフは報告して、そのコマは日本語のまま残す（描き文字も残す）
- 出力は <出力フォルダ>/作画/P{n}-コマ{m}.png（build_pages.py と同じ並び）と、確認用のページ画像 page-P{n}.png
- 自動の割り当ては外れることがある（絵はネームの位置どおりに吹き出しを描かないため）。
  --candidates で、コマごとの吹き出しの候補に番号を振った確認画像 cand-P{n}.png を出し、それを見て
  ep/<話ID>/letter.en.json に割り当てを書く：{"p3-1-1": 2, "p4-2-1": [x, y], "p7-2-2": "skip"}
  （数字＝そのコマの候補の番号、[x, y]＝組んだページ page-P{n}.png の上で吹き出しの中の白い点、[x0, y0, x1, y1]＝吹き出しを囲む四角（点で取れないとき）、"skip"＝日本語のまま残す）。
  表にあるセリフは表のとおりに、無いセリフは自動で入れる
- --publish を付けると、組んだページを episodes.json の crop で切って ep/<話ID>/pages-en/p{nn}.webp に書き、
  本編が全部そろったら episodes.json の pagesEn を true にする（英語で読むとき、読む画面はこちらを出す。扉絵は日本語版のまま）
"""
import argparse
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.spatial import ConvexHull

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages   # noqa: E402  ページの組み方（コマ枠・倍率）をそろえる
import build_script  # noqa: E402  セリフの並び順をそろえる

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.environ.get('LETTER_FONT', r'C:\Windows\Fonts\comicbd.ttf')
MAX_COST = 0.9    # これより合わない吹き出ししか無いセリフは、無理に入れず日本語のまま残す
SFX = re.compile(r'[\u30A0-\u30FF\u3041-\u3096ー〜！!？?…・\s]+')   # カタカナ・ひらがなだけの描き文字（カチカチ、ドドド）は残す
PAGE_MIN_PX = 13   # これより小さくしないと入らない吹き出しは、読めないので入れない（別の吹き出しを試す）
PAGE_MAX_PX = 34   # 組んだページ（1588px 幅）の上での、英語の字のいちばん大きいサイズ


def find_balloons(img):
    """文字の入った吹き出しの候補を返す。[{mask, cx, cy, area, marks}]
    白の境目を2通りで探して合わせる：ゆるい方（200）は輪郭が細い吹き出しを、きびしい方（240）は
    薄い灰色の壁や紙とつながってしまう吹き出しを拾う。同じ吹き出しが両方で見つかったら1つにする"""
    out = []
    for th in (200, 240):
        for b in _find(img, th):
            if not any((b['mask'] & o['mask']).sum() > 0.5 * min(b['area'], o['area']) for o in out):
                out.append(b)
    return out


def _find(img, threshold):
    g = np.asarray(img.convert('L'))
    h, w = g.shape
    white = g > threshold
    lab, n = ndimage.label(white)
    out = []
    sizes = ndimage.sum(white, lab, range(1, n + 1))
    for k in range(1, n + 1):
        if sizes[k - 1] < h * w * 0.002 or sizes[k - 1] > h * w * 0.2:   # 小さすぎる白・背景ほど大きい白は吹き出しではない
            continue
        comp = lab == k
        ys, xs = np.nonzero(comp)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        sub = comp[y0:y1 + 1, x0:x1 + 1]
        filled = ndimage.binary_fill_holes(sub)
        holes = filled & ~sub
        area = filled.sum()
        if area == 0:
            continue
        ratio = holes.sum() / area
        _, nholes = ndimage.label(holes)
        # 背景の白（コマの端まで広がる地）は、端に大きく接する。吹き出しは端にほとんど接しない
        edge = comp[0].sum() + comp[-1].sum() + comp[:, 0].sum() + comp[:, -1].sum()
        if edge > (sub.shape[0] + sub.shape[1]) * 0.25:   # 吹き出しはコマの端にほとんど触れない（触れる白は背景や服）
            continue
        # 吹き出しの地は真っ白（網点の肌や服は白の中に灰色が混じる）。文字は小さな塊がいくつもあり、
        # 目や口のような大きな穴は無い（顔を吹き出しと取り違えないため）
        paper = np.percentile(g[y0:y1 + 1, x0:x1 + 1][sub], 5)
        hl, _ = ndimage.label(holes)
        maxhole = ndimage.sum(holes, hl, range(1, nholes + 1)).max() / area if nholes else 0
        if not (0.015 < ratio < 0.55 and nholes >= 8 and paper >= 246 and maxhole < 0.05):
            continue
        # 形：吹き出しもナレーション枠も、ふくらんだ閉じた形（凸）。服のしわや背景の白い切れ端は形がいびつ
        edge_px = np.argwhere(filled & ~ndimage.binary_erosion(filled))
        try:
            solidity = area / ConvexHull(edge_px).volume
        except Exception:
            continue
        if solidity < 0.72:   # しっぽ付き・ギザギザの吹き出しも拾えるよう、ゆるめにする
            continue
        rect = area / (sub.shape[0] * sub.shape[1])   # 四角いナレーション枠は 1 に近い。楕円の吹き出しは 0.8 前後
        mask = np.zeros_like(comp)
        mask[y0:y1 + 1, x0:x1 + 1] = filled
        out.append({'mask': mask, 'cx': (x0 + x1) / 2, 'cy': (y0 + y1) / 2, 'area': area, 'marks': nholes, 'rect': rect})
    return out


def to_image_xy(box, panel, img, scale=build_pages.SCALE):
    """ネームのセリフの位置（ページ座標）を、コマの絵の上の画素に直す（build_pages と同じ切り抜き方）"""
    sx, sy = box[0] + box[2] / 2, box[1] + box[3] / 2
    pw, ph = round(panel['w'] * scale), round(panel['h'] * scale)
    r = max(pw / img.width, ph / img.height)
    left, top = (img.width * r - pw) / 2, (img.height * r - ph) / 2
    return ((sx - panel['x']) * scale + left) / r, ((sy - panel['y']) * scale + top) / r


def splits(ws):
    if len(ws) == 1:
        yield [ws[0]]
        return
    for rest in splits(ws[1:]):
        yield [ws[0]] + rest
        yield [ws[0] + ' ' + rest[0]] + rest[1:]


def widen_caption(img, mask, avoid=None):
    """縦書き用の細長いナレーション枠を、同じ高さのまま横に広げて描き直す（横書きの英語が細切れにならないように）。
    元の枠はそっくり覆うので、縦書きの跡は残らない"""
    ys, xs = np.nonzero(mask)
    pad = 5                                  # 元の枠線の太さぶん
    x0, x1, y0, y1 = xs.min() - pad, xs.max() + pad, ys.min() - pad, ys.max() + pad
    w = x1 - x0
    nw = max(w, min(int(w * 2.2), int(img.width * 0.55)))
    cx = (x0 + x1) / 2
    nx0 = int(min(max(cx - nw / 2, 4), img.width - 4 - nw))
    nx1 = nx0 + nw
    if avoid is not None:                    # ほかの吹き出しに重なるなら、重ならないところまで縮める
        cols = avoid[max(y0, 0):y1 + 1].any(axis=0)
        left = [x for x in range(nx0, x0) if cols[x]]
        right = [x for x in range(x1 + 1, nx1 + 1) if x < cols.size and cols[x]]
        if left:
            nx0 = max(left) + 8
        if right:
            nx1 = min(right) - 8
    out = img.copy()
    d = ImageDraw.Draw(out)
    d.rectangle((nx0, y0, nx1, y1), fill=(255, 255, 255), outline=(0, 0, 0), width=4)
    inside = np.zeros(mask.shape, bool)
    inside[y0 + 10:y1 - 9, nx0 + 10:nx1 - 9] = True
    return out, inside


def grow_balloon(img, mask):
    """細い吹き出しを、中心と高さはそのまま、幅を広げた楕円に描き直す"""
    ys, xs = np.nonzero(mask)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    h = ys.max() - ys.min() + 12
    w = max(xs.max() - xs.min() + 12, min(h * 0.9, img.width * 0.45))
    x0, x1 = max(cx - w / 2, 4), min(cx + w / 2, img.width - 4)
    y0, y1 = cy - h / 2, cy + h / 2
    out = img.copy()
    d = ImageDraw.Draw(out)
    d.ellipse((x0, y0, x1, y1), fill=(255, 255, 255), outline=(0, 0, 0), width=4)
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).ellipse((x0 + 8, y0 + 8, x1 - 8, y1 - 8), fill=255)
    return out, np.asarray(m) > 0


def letter(img, mask, text, caption=False, max_size=None, min_size=12, avoid=None):
    """吹き出しの中を白にして、英語をいちばん大きく収まる字で書く（max_size より大きくはしない）"""
    if caption and (lambda ys, xs: (ys.max() - ys.min()) > (xs.max() - xs.min()) * 1.3)(*np.nonzero(mask)):
        out, inside = widen_caption(img, mask, avoid)
    else:
        inside = ndimage.binary_erosion(mask, iterations=2)
        a = np.asarray(img).copy()
        a[inside] = 255
        out = Image.fromarray(a)
    d = ImageDraw.Draw(out)
    dist = ndimage.distance_transform_edt(inside)
    ys, xs = np.nonzero(inside)
    cy, cx = int(ys.mean()), int(xs.mean())
    words = text.upper().split()
    if len(words) > 14:              # 長いセリフは組み合わせが増えすぎるので、2語ずつまとめて考える
        words = [' '.join(words[i:i + 2]) for i in range(0, len(words), 2)]

    def width_at(y, margin):
        return int((dist[y] > margin).sum()) if 0 <= y < dist.shape[0] else 0

    best = None
    for lines in splits(words):
        for size in range(int(max_size or min(img.size) * 0.09), int(min_size) - 1, -2):
            font = ImageFont.truetype(FONT, size)
            lh = int(size * 1.12)
            margin = size * 0.5
            top = cy - lh * len(lines) // 2
            if all(d.textlength(ln, font=font) <= width_at(y, margin)
                   for i, ln in enumerate(lines) for y in (top + i * lh + 3, top + i * lh + lh - 3)):
                # 大きい字を優先。同じ大きさなら、行が少なく、行の長さがそろっている改行を選ぶ
                lens = [d.textlength(ln, font=font) for ln in lines]
                key = (size, -len(lines), -(max(lens) - min(lens)))
                if not best or key > best[0]:
                    best = (key, lines, font, lh, top)
                break
    if not best:
        return None
    (size, _, _), lines, font, lh, top = best
    for i, ln in enumerate(lines):
        d.text((cx - d.textlength(ln, font=font) / 2, top + i * lh), ln, font=font, fill=(0, 0, 0))
    return out, size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('episode_id')
    ap.add_argument('--pages', default='')
    ap.add_argument('--out', default=os.path.join(ROOT, '_letter_en'))
    ap.add_argument('--publish', action='store_true')
    ap.add_argument('--candidates', action='store_true')
    args = ap.parse_args()

    name_json = json.load(open(os.path.join(args.folder, 'ネーム.json'), encoding='utf-8'))
    script = json.load(open(os.path.join(ROOT, 'ep', args.episode_id, 'script.en.json'), encoding='utf-8'))
    en = {ln['id']: ln['en'] for pg in script['pages'] for ln in pg['lines']}
    map_path = os.path.join(ROOT, 'ep', args.episode_id, 'letter.en.json')
    fixed = json.load(open(map_path, encoding='utf-8')) if os.path.exists(map_path) else {}
    fixed = {k: v for k, v in fixed.items() if not k.startswith('_')}
    want = {int(p) for p in args.pages.split(',') if p} or set(range(1, len(name_json['pages']) + 1))
    os.makedirs(os.path.join(args.out, '作画'), exist_ok=True)
    report = []

    for pno, page in enumerate(name_json['pages'], 1):
        if pno not in want:
            continue
        panels = {o.get('readingOrder'): o for o in page['objects'] if o['type'] == 'panel'}
        lines, seen = [], {}
        for ln in build_script.collect(page):
            n = seen[ln['panel']] = seen.get(ln['panel'], 0) + 1
            ln['id'] = f"p{pno}-{ln['panel']}-{n}"
            lines.append(ln)
        for ro, panel in sorted(panels.items()):
            cand = next(c for c in panel['candidates'] if c['id'] == panel['approvedCandidateId'])
            img = Image.open(os.path.join(args.folder, cand['image'])).convert('RGB')
            balloons = find_balloons(img)
            if args.candidates:
                c = img.copy()
                cd = ImageDraw.Draw(c)
                font = ImageFont.truetype(FONT, max(28, img.width // 14))
                for bi, b in enumerate(balloons):
                    edge = b['mask'] & ~ndimage.binary_erosion(b['mask'], iterations=4)
                    a = np.asarray(c).copy(); a[edge] = (230, 30, 30); c = Image.fromarray(a); cd = ImageDraw.Draw(c)
                    cd.text((b['cx'], b['cy']), str(bi), font=font, fill=(230, 30, 30), anchor='mm', stroke_width=3, stroke_fill=(255, 255, 255))
                dst = os.path.join(args.out, 'cand', cand['image'])
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                c.save(dst)
            mine = [ln for ln in lines if ln['panel'] == ro]
            for ln in mine:
                if ln['type'] == 'caption' and SFX.fullmatch(ln['text']):
                    ln['sfx'] = True
            mine_all, mine = mine, [ln for ln in mine if not ln.get('sfx')]
            # ネームの位置に近い順に、吹き出しを1つずつ割り当てる
            # 位置の近さ（コマの対角線で割る）に、文字の量の近さを足す。日本語1字は黒い塊3〜4個ほどになる。
            # 長いセリフと短いセリフが近くに並ぶコマで、取り違えないため
            # 絵はネームの位置どおりに吹き出しを描かないことがあるので、位置の近さは目安にとどめ、
            # コマの中で読む順番（右上から左下）の近さも足す
            diag = (img.width ** 2 + img.height ** 2) ** 0.5
            order_b = sorted(range(len(balloons)), key=lambda i: balloons[i]['cy'] - balloons[i]['cx'])
            rank_b = {bi: k / max(len(balloons) - 1, 1) for k, bi in enumerate(order_b)}
            pairs = []
            for k, ln in enumerate(mine):          # mine は読む順に並んでいる
                x, y = to_image_xy(ln['box'], panel, img)
                expect = 3.5 * len(ln['text']) + 3
                rank_l = k / max(len(mine) - 1, 1)
                for bi, b in enumerate(balloons):
                    near = ((b['cx'] - x) ** 2 + (b['cy'] - y) ** 2) ** 0.5 / diag
                    amount = abs(np.log((b['marks'] + 3) / expect))
                    order = abs(rank_b[bi] - rank_l) if len(mine) > 1 else 0
                    boxy = b['rect'] > 0.93
                    shape = 0 if boxy == (ln['type'] == 'caption') else 0.5   # ナレーションは四角い枠、セリフは丸い吹き出し
                    pairs.append((0.3 * near + 0.5 * amount + 0.6 * order + shape, ln['id'], bi))
            # 合う組から順に入れていく。英語が収まらない吹き出しだったら、そのセリフは次に合う吹き出しを試す
            # 字の大きさの上限は、組んだページの上で PAGE_MAX_PX になるように（コマごとに縮尺が違うため）
            r = max(panel['w'] * build_pages.SCALE / img.width, panel['h'] * build_pages.SCALE / img.height)
            done, used_b, tried = {}, set(), set()

            def target(at, lid):
                """表の指定（候補の番号か、ページの上の点）から、吹き出しの番号を返す"""
                if not isinstance(at, list):
                    return at
                if len(at) == 4:                 # [x0, y0, x1, y1]：吹き出しを囲む四角（ページの上の画素）。中の楕円を吹き出しとみなす
                    ax0, ay0 = to_image_xy((at[0] / build_pages.SCALE, at[1] / build_pages.SCALE, 0, 0), panel, img)
                    ax1, ay1 = to_image_xy((at[2] / build_pages.SCALE, at[3] / build_pages.SCALE, 0, 0), panel, img)
                    # 四角に内接する楕円を少し大きくして、四角で切る（角の文字まで消せるように）
                    ex, ey = (ax1 - ax0) * 0.1, (ay1 - ay0) * 0.1
                    mimg = Image.new('L', img.size, 0)
                    ImageDraw.Draw(mimg).ellipse((ax0 - ex, ay0 - ey, ax1 + ex, ay1 + ey), fill=255)
                    m = np.asarray(mimg) > 0
                    box = np.zeros_like(m)
                    box[max(int(ay0), 0):int(ay1), max(int(ax0), 0):int(ax1)] = True
                    m &= box
                    if m.sum() < 100:
                        report.append(f"P{pno}-コマ{ro} {lid}：指定の四角 {at} がコマの絵の外です（→ 絵の上では ({ax0:.0f},{ay0:.0f})-({ax1:.0f},{ay1:.0f})、絵は {img.size}）")
                        return None
                    balloons.append({'mask': m, 'cx': (ax0 + ax1) / 2, 'cy': (ay0 + ay1) / 2, 'area': m.sum(), 'marks': 0, 'rect': 0})
                    return len(balloons) - 1
                # 吹き出しの中の点（組んだページ page-P{n}.png の上の画素）から、白い地を塗りつぶすように取る
                x, y = to_image_xy((at[0] / build_pages.SCALE, at[1] / build_pages.SCALE, 0, 0), panel, img)
                g_ = np.asarray(img.convert('L'))
                lab_, _ = ndimage.label(g_ > 235)
                k_ = lab_[int(y), int(x)] if 0 <= int(y) < g_.shape[0] and 0 <= int(x) < g_.shape[1] else 0
                m = ndimage.binary_fill_holes(lab_ == k_) if k_ else None
                if m is None or m.sum() > img.width * img.height * 0.3:   # 白くない点・背景まで漏れた
                    report.append(f"P{pno}-コマ{ro} {lid}：指定の点 {at} から吹き出しを取れませんでした")
                    return None
                balloons.append({'mask': m, 'cx': x, 'cy': y, 'area': m.sum(), 'marks': 0, 'rect': 0})
                return len(balloons) - 1

            for ln in mine:
                v = fixed.get(ln['id'])
                if v is None:
                    continue
                tried.add(ln['id'])
                if v == 'skip':
                    done[ln['id']] = 'skip'
                    continue
                # 1つのセリフを2つ以上の吹き出しに分けるときは {"parts": [{"at": 番号か点, "text": "英文"}, ...]}
                parts = v['parts'] if isinstance(v, dict) else [{'at': v, 'text': en[ln['id']]}]
                sizes = []
                for part in parts:
                    bi = target(part['at'], ln['id'])
                    if bi is None:
                        continue
                    others = [b['mask'] for j, b in enumerate(balloons) if j != bi]
                    res = letter(img, balloons[bi]['mask'], part['text'], caption=ln['type'] == 'caption',
                                 max_size=PAGE_MAX_PX / r, min_size=11 / r,
                                 avoid=np.logical_or.reduce(others) if others else None)
                    if not res and v != 'skip':
                        # 細すぎて横書きが入らない吹き出しは、同じ位置で横に広い楕円に描き直してから入れる（まわりの絵を少し隠す）
                        grown, gmask = grow_balloon(img, balloons[bi]['mask'])
                        res = letter(grown, gmask, part['text'], max_size=PAGE_MAX_PX / r, min_size=11 / r)
                    if res:
                        img, size = res
                        used_b.add(bi)
                        sizes.append(size)
                if len(sizes) == len(parts):
                    done[ln['id']] = min(sizes)
            pairs = [p for p in pairs if p[1] not in fixed]
            for cost, lid, bi in sorted(pairs):
                if lid in done or bi in used_b or cost > MAX_COST or not en.get(lid):
                    continue
                tried.add(lid)
                ln = next(l for l in mine if l['id'] == lid)
                others = [b['mask'] for j, b in enumerate(balloons) if j != bi]
                avoid = np.logical_or.reduce(others) if others else None
                res = letter(img, balloons[bi]['mask'], en[lid], caption=ln['type'] == 'caption',
                             max_size=PAGE_MAX_PX / r, min_size=PAGE_MIN_PX / r, avoid=avoid)
                if os.environ.get('LETTER_DEBUG'):
                    ys_, xs_ = np.nonzero(balloons[bi]['mask'])
                    print(f"  try {lid} cost={cost:.2f} box=({xs_.min()},{ys_.min()},{xs_.max()},{ys_.max()}) marks={balloons[bi]['marks']} r={r:.2f} -> {'ok' if res else 'NG'}")
                if not res:
                    continue
                img, size = res
                used_b.add(bi)
                done[lid] = size
            for ln in mine_all:
                if ln.get('sfx'):
                    report.append(f"P{pno}-コマ{ro} {ln['id']}：描き文字なので日本語のまま「{ln['text']}」")
                elif done.get(ln['id']) == 'skip':
                    report.append(f"P{pno}-コマ{ro} {ln['id']}：表の指定で日本語のまま「{ln['text']}」")
                elif ln['id'] in done:
                    report.append(f"P{pno}-コマ{ro} {ln['id']}：{done[ln['id']]}px「{en[ln['id']]}」")
                elif ln['id'] in tried:
                    report.append(f"P{pno}-コマ{ro} {ln['id']}：英語が収まらず、日本語のまま「{ln['text']}」")
                else:
                    report.append(f"P{pno}-コマ{ro} {ln['id']}：吹き出しが見つからず、日本語のまま「{ln['text']}」")
            dst = os.path.join(args.out, cand['image'])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            img.save(dst)
        # 確認用に、英語のコマでページを組む
        page_en = json.loads(json.dumps(page))
        pimg, _ = build_pages.page_image(args.out, page_en)
        pimg.save(os.path.join(args.out, f'page-P{pno}.png'))
        if args.candidates:
            cimg, _ = build_pages.page_image(os.path.join(args.out, 'cand'), page_en)
            cimg.save(os.path.join(args.out, f'cand-P{pno}.png'))
        if args.publish:
            ep = next(e for e in json.load(open(os.path.join(ROOT, 'episodes.json'), encoding='utf-8'))['episodes'] if e['id'] == args.episode_id)
            dst_dir = os.path.join(ROOT, 'ep', args.episode_id, 'pages-en')
            os.makedirs(dst_dir, exist_ok=True)
            pimg.crop(tuple(ep['crop']['box'])).save(os.path.join(dst_dir, f'p{pno:02d}.webp'), 'WEBP', quality=build_pages.QUALITY, method=6)
    if args.publish:
        ep_path = os.path.join(ROOT, 'episodes.json')
        data = json.load(open(ep_path, encoding='utf-8'))
        ep = next(e for e in data['episodes'] if e['id'] == args.episode_id)
        done = sorted(int(f[1:3]) for f in os.listdir(os.path.join(ROOT, 'ep', args.episode_id, 'pages-en')) if f.endswith('.webp'))
        ep['pagesEn'] = done == list(range(1, len(name_json['pages']) + 1))   # 本編が全部そろったときだけ使う
        with open(ep_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f"pages-en: {len(done)} ページ。pagesEn = {ep['pagesEn']}")
    print('\n'.join(report))


if __name__ == '__main__':
    main()
