"""name-maker の話フォルダ（ネーム.json）から、対訳スクリプトの台本を作る。

使い方:
    python tools/build_script.py <話フォルダ> <話ID> [--lang en]

- ネーム.json のナレーション（caption）とセリフ（speech）を、コマごと・読む順に並べて書き出す
- 出力は ep/<話ID>/script.<lang>.json。すでにある同じ id の訳文（en）は引き継ぐ
- 訳文は人が書く。書き出したあと、"en" の空いているところを埋める
- 読む順は、コマは readingOrder、コマの中は「右上から左下へ」で並べる
- 各ページのコマの位置を、ページ画像の上の割合（左・上・右・下を 0〜1）で panels に書く。
  読む画面が対訳をコマの横に並べるのに使う。episodes.json の crop（build_pages.py が書く）が要る
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def center(o):
    return o['x'] + o.get('w', 0) / 2, o['y'] + o.get('h', 0) / 2


def inside(o, panel):
    cx, cy = center(o)
    return panel['x'] <= cx <= panel['x'] + panel['w'] and panel['y'] <= cy <= panel['y'] + panel['h']


def nearest(o, panels):
    cx, cy = center(o)
    def d(p):
        px, py = p['x'] + p['w'] / 2, p['y'] + p['h'] / 2
        return (cx - px) ** 2 + (cy - py) ** 2
    return min(panels, key=d)


def collect(page):
    """1ページぶんのセリフを、コマごと・読む順に並べて返す。"""
    panels = [o for o in page['objects'] if o['type'] == 'panel']
    panels.sort(key=lambda p: p.get('readingOrder', 0))
    buckets = {id(p): [] for p in panels}
    for o in page['objects']:
        if o['type'] not in ('caption', 'speech') or not o.get('text'):
            continue
        hit = next((p for p in panels if inside(o, p)), None) or (nearest(o, panels) if panels else None)
        if hit is not None:
            buckets[id(hit)].append(o)
    lines = []
    for p in panels:
        # 吹き出しは右上から左下へ読む
        for o in sorted(buckets[id(p)], key=lambda o: o['y'] - (o['x'] + o.get('w', 0))):
            lines.append({'panel': p.get('readingOrder', 0), 'type': o['type'], 'text': o['text']})
    return lines


def panel_boxes(page, crop):
    """コマの位置を、切り取ったあとのページ画像の上の割合にする。"""
    if not crop:
        return {}
    k = crop['scale']
    x0, y0, x1, y1 = crop['box']
    w, h = x1 - x0, y1 - y0
    out = {}
    for o in page['objects']:
        if o['type'] != 'panel':
            continue
        box = [(o['x'] * k - x0) / w, (o['y'] * k - y0) / h,
               ((o['x'] + o['w']) * k - x0) / w, ((o['y'] + o['h']) * k - y0) / h]
        out[str(o.get('readingOrder', 0))] = [round(min(max(v, 0), 1), 4) for v in box]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('episode_id')
    ap.add_argument('--lang', default='en')
    args = ap.parse_args()

    name_json = json.load(open(os.path.join(args.folder, 'ネーム.json'), encoding='utf-8'))
    out_path = os.path.join(ROOT, 'ep', args.episode_id, f'script.{args.lang}.json')
    old = {}
    if os.path.exists(out_path):
        prev = json.load(open(out_path, encoding='utf-8'))
        for pg in prev.get('pages', []):
            for ln in pg.get('lines', []):
                old[ln['id']] = (ln.get(args.lang, ''), ln.get('note', ''))

    episodes = json.load(open(os.path.join(ROOT, 'episodes.json'), encoding='utf-8'))['episodes']
    crop = next((e.get('crop') for e in episodes if e['id'] == args.episode_id), None)
    if not crop:
        print('注意：episodes.json にこの話の crop がありません。先に build_pages.py を流すと、対訳をコマの横に並べられます')

    pages, total, filled = [], 0, 0
    for i, page in enumerate(name_json['pages'], 1):
        lines = []
        seen = {}
        for ln in collect(page):
            n = seen[ln['panel']] = seen.get(ln['panel'], 0) + 1
            lid = f"p{i}-{ln['panel']}-{n}"
            text, note = old.get(lid, ('', ''))
            total += 1
            if text:
                filled += 1
            row = {'id': lid, 'panel': ln['panel'], 'type': ln['type'], 'ja': ln['text'], args.lang: text}
            if note:
                row['note'] = note  # 制度のひとこと解説（人が書く。書き出し直しても残す）
            lines.append(row)
        pages.append({'page': i, 'panels': panel_boxes(page, crop), 'lines': lines})

    data = {'episode': args.episode_id, 'lang': args.lang, 'pages': pages}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'{os.path.relpath(out_path, ROOT)}: {len(pages)} ページ、{total} 行（訳あり {filled} 行）')


if __name__ == '__main__':
    main()
