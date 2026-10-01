"""episodes.json のタグと話の情報を、検索エンジン向けに各 HTML とサイトマップへ書き出す。

使い方: python tools/build_seo.py
build_pages.py の最後でも呼ばれるので、話を足したときは自動で作り直される。

- ep/<話ID>/index.html の <head>：正規 URL（canonical）・キーワード・構造化データ（schema.org の ComicIssue）
- ep/<話ID>/index.html の「おわり」：この話のタグ（画面に出る文字。Google が読む本文にもなる）
- index.html の <head>：作品の構造化データ（ComicSeries と、公開中の話の一覧）
- sitemap.xml：作品トップと公開中の話（Search Console に登録して使う）

書き込む場所は <!-- seo:start --> 〜 <!-- seo:end -->、<!-- tags:start --> 〜 <!-- tags:end --> の印の間。
印が無い HTML には、<link rel="icon"> の前・「おわり」の .end-sub の後に印ごと足す。
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://tsubasagit.github.io/gyosei-bug-reader/'
PUBLISHER = {'@type': 'Organization', 'name': '株式会社AppTalentHub', 'url': 'https://apptalenthub.co.jp/'}
# どの話にも付ける言葉（作品そのものを探す人向け）
SERIES_KEYWORDS = ['行政バグります', '漫画', '無料漫画', 'Web漫画', 'ギャグ漫画', 'お役所', '公務員', '市役所']


def ld_json(obj):
    """<script type="application/ld+json"> の中身。</script> で途切れないよう < を逃がす"""
    return json.dumps(obj, ensure_ascii=False, indent=2).replace('<', '\\u003c')


def replace_block(text, name, block, anchor_re, before=True):
    """印の間を block に差し替える。印が無ければ anchor_re の前（または後）に印ごと足す"""
    start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
    marked = re.compile(r'^([ \t]*)' + re.escape(start) + r'.*?' + re.escape(end), re.S | re.M)
    if marked.search(text):
        return marked.sub(lambda m: f'{m.group(1)}{start}\n{block}\n{m.group(1)}{end}', text, count=1)
    m = re.search(anchor_re, text, re.M)
    if not m:
        raise SystemExit(f'差し込む場所が見つかりません: {anchor_re}')
    indent = re.match(r'[ \t]*', text[text.rfind('\n', 0, m.start()) + 1:]).group(0)
    chunk = f'{indent}{start}\n{block}\n{indent}{end}\n'
    if before:
        pos = text.rfind('\n', 0, m.start()) + 1
    else:
        pos = text.find('\n', m.end()) + 1
    return text[:pos] + chunk + text[pos:]


def episode_head(ep, series):
    url = f"{SITE}ep/{ep['id']}/"
    tags = ep.get('tags', [])
    data = {
        '@context': 'https://schema.org',
        '@type': 'ComicIssue',
        'name': ep['title'],
        'headline': f"第{ep['number']}話「{ep['title']}」",
        'alternativeHeadline': ep.get('subtitle', ''),
        'issueNumber': ep['number'],
        'url': url,
        'description': ep.get('summary', ''),
        'keywords': ','.join(tags + SERIES_KEYWORDS),
        'image': f'{url}og.jpg',
        'thumbnailUrl': f'{url}thumb.webp',
        'datePublished': ep['published'],
        'inLanguage': 'ja',
        'genre': ['ギャグ漫画', 'お役所コメディ'],
        'isAccessibleForFree': True,
        'author': PUBLISHER,
        'publisher': PUBLISHER,
        'isPartOf': {'@type': 'ComicSeries', 'name': series['title'], 'url': SITE},
    }
    keywords = html.escape(','.join(tags + SERIES_KEYWORDS))
    return '\n'.join([
        f'  <link rel="canonical" href="{url}">',
        f'  <meta name="keywords" content="{keywords}">',
        '  <script type="application/ld+json">',
        ld_json(data),
        '  </script>',
    ])


def episode_tags(ep):
    items = ''.join(f'<li>#{html.escape(t)}</li>' for t in ep.get('tags', []))
    return f'        <ul class="end-tags" aria-label="この話のタグ">{items}</ul>'


def series_head(series, eps):
    data = {
        '@context': 'https://schema.org',
        '@type': 'ComicSeries',
        'name': series['title'],
        'alternateName': series.get('title_en', ''),
        'url': SITE,
        'description': series.get('description', ''),
        'image': f'{SITE}assets/og-top.jpg',
        'inLanguage': 'ja',
        'genre': ['ギャグ漫画', 'お役所コメディ'],
        'keywords': ','.join(SERIES_KEYWORDS),
        'isAccessibleForFree': True,
        'author': PUBLISHER,
        'publisher': PUBLISHER,
        'hasPart': [{
            '@type': 'ComicIssue',
            'name': e['title'],
            'issueNumber': e['number'],
            'url': f"{SITE}ep/{e['id']}/",
            'datePublished': e['published'],
            'keywords': ','.join(e.get('tags', [])),
        } for e in eps],
    }
    return '\n'.join([
        f'  <link rel="canonical" href="{SITE}">',
        f'  <meta name="keywords" content="{html.escape(",".join(SERIES_KEYWORDS))}">',
        '  <script type="application/ld+json">',
        ld_json(data),
        '  </script>',
    ])


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def build():
    data = json.load(open(os.path.join(ROOT, 'episodes.json'), encoding='utf-8'))
    series = data['series']
    eps = sorted((e for e in data['episodes'] if e.get('pages')), key=lambda e: e['number'])

    for ep in eps:
        path = os.path.join(ROOT, 'ep', ep['id'], 'index.html')
        if not os.path.exists(path):
            continue
        text = open(path, encoding='utf-8').read()
        text = replace_block(text, 'seo', episode_head(ep, series), r'<link rel="icon"')
        text = replace_block(text, 'tags', episode_tags(ep), r'<p class="end-sub">.*</p>', before=False)
        write(path, text)

    top = os.path.join(ROOT, 'index.html')
    text = open(top, encoding='utf-8').read()
    write(top, replace_block(text, 'seo', series_head(series, eps), r'<link rel="icon"'))

    latest = max((e['published'] for e in eps), default='')
    urls = [(SITE, latest)] + [(f"{SITE}ep/{e['id']}/", e['published']) for e in eps]
    body = ''.join(f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{d}</lastmod>\n  </url>\n' for u, d in urls)
    write(os.path.join(ROOT, 'sitemap.xml'),
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '</urlset>\n')
    print(f'{len(eps)} 話のタグ・構造化データと sitemap.xml を書き出しました。')


if __name__ == '__main__':
    build()
