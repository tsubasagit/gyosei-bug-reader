"""episodes.json から、新しい話のお知らせ用の RSS（feed.xml）を作る。

使い方: python tools/build_feed.py
build_pages.py の最後でも呼ばれるので、話を足したときは自動で作り直される。
公開済み（pages がある）の話だけを、新しい順に載せる。
"""
import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://tsubasagit.github.io/gyosei-bug-reader/'
JST = timezone(timedelta(hours=9))


def build():
    data = json.load(open(os.path.join(ROOT, 'episodes.json'), encoding='utf-8'))
    series = data['series']
    eps = [e for e in data['episodes'] if e.get('pages')]
    eps.sort(key=lambda e: (e.get('published', ''), e['number']), reverse=True)

    def pub(e):
        d = datetime.strptime(e['published'], '%Y-%m-%d').replace(hour=9, tzinfo=JST)
        return format_datetime(d)

    items = []
    for e in eps:
        url = f"{SITE}ep/{e['id']}/"
        title = f"第{e['number']}話「{e['title']}」"
        desc = f"～{e.get('subtitle', '')}～ {e.get('summary', '')}".strip()
        items.append(
            '    <item>\n'
            f'      <title>{escape(title)}</title>\n'
            f'      <link>{url}</link>\n'
            f'      <guid isPermaLink="true">{url}</guid>\n'
            f'      <pubDate>{pub(e)}</pubDate>\n'
            f'      <description>{escape(desc)}</description>\n'
            f'      <enclosure url="{url}thumb.webp" type="image/webp" length="0"/>\n'
            '    </item>'
        )

    last = pub(eps[0]) if eps else format_datetime(datetime.now(JST))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '  <channel>\n'
        f"    <title>{escape(series['title'])} ～{escape(series['subtitle'])}～</title>\n"
        f'    <link>{SITE}</link>\n'
        f'    <atom:link href="{SITE}feed.xml" rel="self" type="application/rss+xml"/>\n'
        f"    <description>{escape(series['description'])}</description>\n"
        '    <language>ja</language>\n'
        f'    <lastBuildDate>{last}</lastBuildDate>\n'
        + '\n'.join(items) + '\n'
        '  </channel>\n'
        '</rss>\n'
    )
    with open(os.path.join(ROOT, 'feed.xml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(xml)
    print(f'feed.xml を作りました（{len(eps)} 話）')


if __name__ == '__main__':
    build()
