"""公開予定.json（制作側の予定表）から、Web リーダーの表示に要る分だけを写す。

- episodes.json の各話に `genres`（ジャンルのタグ。一覧の絞り込みに使う）と `links`（ニコニコ漫画・pixiv の各話の URL）
- upcoming.json の `schedule`（まだ公開していない話を、予約日の早い順に --count 本）と `next`（その先頭）
- 公開予定の話の横のカラー表紙を assets/upcoming/<話数>.webp に（表紙が無い話は絵なしで出す）

話を公開したとき・予約日や話数を付け替えたときに流す。予定表は非公開のフォルダにあるので、中身はこのリポジトリに入れず、
表示に要る題名・日付・タグ・URL だけを写す。

    python tools/sync_schedule.py ["<シリーズの 各話 フォルダ>"] [--count 3]
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SERIES = r'G:\マイドライブ\AppTalentHub\03_contents\01_stock\comics\行政バグります！ ～梨ヶ坂市役所・特務トレンド係～\各話'
NAME = re.compile(r'^(\d+)話-(.+?)(?:\s*～(.*))?$')
COVER = '扉絵-横-カラー表紙.png'
PLATFORMS = ('niconico', 'pixiv')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('series', nargs='?', default=DEFAULT_SERIES)
    ap.add_argument('--count', type=int, default=3, help='公開予定に出す話の数')
    args = ap.parse_args()
    series = Path(args.series)
    schedule = load(series / '公開予定.json')

    # 話数 → 予定表の行（フォルダ名の「N話-」で引く）
    by_number = {}
    for entry in schedule['entries'].values():
        m = NAME.match(entry.get('name', ''))
        if m:
            by_number[int(m.group(1))] = entry

    episodes_path = ROOT / 'episodes.json'
    data = load(episodes_path)
    published = set()
    for ep in data['episodes']:
        if not ep.get('pages'):
            continue
        published.add(ep['number'])
        entry = by_number.get(ep['number'])
        if not entry:
            continue
        ep['genres'] = list(entry.get('tags', []))
        links = {p: entry['platforms'][p]['url'] for p in PLATFORMS
                 if entry.get('platforms', {}).get(p, {}).get('url')}
        if links:
            ep['links'] = links
        else:
            ep.pop('links', None)
    dump(episodes_path, data)

    # 公開予定：未公開で予約日のある話を、日付の早い順に
    today = date.today().isoformat()
    upcoming = []
    for number, entry in sorted(by_number.items(), key=lambda kv: (kv[1].get('date') or '9999', kv[0])):
        if number in published or not entry.get('date') or entry['date'] < today:
            continue
        m = NAME.match(entry['name'])
        folder = series / entry['name']
        item = {'number': number, 'title': m.group(2).strip(), 'subtitle': (m.group(3) or '').strip(),
                'date': entry['date'], 'genres': list(entry.get('tags', []))}
        if (folder / COVER).exists():
            out = ROOT / 'assets' / 'upcoming' / f'{number}.webp'
            out.parent.mkdir(exist_ok=True)
            img = Image.open(folder / COVER).convert('RGB')
            img.thumbnail((640, 640 * img.height // img.width))
            img.save(out, 'WEBP', quality=82)
            item['cover'] = f'assets/upcoming/{number}.webp'
        upcoming.append(item)
        if len(upcoming) >= args.count:
            break

    # 出さなくなった話の表紙は消す
    keep = {f'{u["number"]}.webp' for u in upcoming}
    for f in (ROOT / 'assets' / 'upcoming').glob('*.webp'):
        if f.name not in keep:
            f.unlink()

    up_path = ROOT / 'upcoming.json'
    up = load(up_path)
    old_next = up.get('next') or {}
    up['schedule'] = upcoming
    if upcoming:
        first = upcoming[0]
        nxt = {'number': first['number'], 'title': first['title'], 'date': first['date']}
        if old_next.get('number') == first['number'] and old_next.get('title_en'):
            nxt['title_en'] = old_next['title_en']
        up['next'] = nxt
    dump(up_path, up)

    sys.stdout.reconfigure(encoding='utf-8')
    for ep in data['episodes']:
        if ep.get('pages'):
            print(f"{ep['number']:>3}話 genres={ep.get('genres')} links={sorted(ep.get('links', {}))}")
    for u in upcoming:
        print(f"予定 {u['number']}話 {u['date']} {u['title']} cover={'cover' in u}")


if __name__ == '__main__':
    main()
