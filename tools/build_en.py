"""英語のページ（en/index.html と en/ep/<話ID>/index.html）を、日本語のページから書き出す。

使い方: python tools/build_en.py
build_seo.py の最後でも呼ばれるので、話を足したとき（build_pages.py）・タグを直したときは自動で作り直される。

- 日本語のページは ?lang=en で英語に切り替わるが、切り替えは JavaScript なので、検索エンジンには日本語しか見えない。
  英語のページは、題名・説明・画面の文言・構造化データを最初から英語で書いておき、海外の検索で見つかるようにする
- 画面の文言は assets/i18n.js の EN（data-i18n の印のところ）、話の題名・あらすじは episodes.json の *_en
- 各話の「おわり」に、英語の台本（ep/<話ID>/script.en.json）の全文を「Read the English script」として載せる
  （吹き出しの絵の中の英語は、検索エンジンには読めないため）
- 日本語のページと英語のページは hreflang で互いを指す（日本語側は build_seo.py が書く）
- 英語のページは <html data-lang="en">。i18n.js はこれを見て英語に固定し、データと絵はサイトのいちばん上から読む
  （作品トップは data-root="../"、読む画面は data-base="../../../"。ほかの話へのリンクは data-link-base="../../" で /en/ の中へ）
- en/ の下は書き出すたびに上書きする。手で直さない
"""
import html
import json
import os
import re
import sys

from bs4 import BeautifulSoup, Comment

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_seo import ANALYTICS, PUBLISHER, SITE, ld_json, replace_block, write  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIES_KEYWORDS_EN = ['City Hall Bug', 'manga', 'free manga', 'webcomic', 'gag manga', 'comedy manga',
                      'Japanese city hall', 'civil servant', 'Japan bureaucracy', 'English manga']
GENRE_EN = ['Gag manga', 'Workplace comedy']


def load_en_strings():
    """i18n.js の EN（'キー': '英語',）を読む"""
    src = open(os.path.join(ROOT, 'assets', 'i18n.js'), encoding='utf-8').read()
    block = src[src.index('const EN = {'):src.index('\n  };', src.index('const EN = {'))]
    out = {}
    for m in re.finditer(r"^\s*'([\w.]+)':\s*'((?:[^'\\]|\\.)*)',?\s*$", block, re.M):
        out[m.group(1)] = re.sub(r'\\(.)', r'\1', m.group(2))
    return out


def alternates(ja_url, en_url):
    return '\n'.join([
        f'  <link rel="alternate" hreflang="ja" href="{ja_url}">',
        f'  <link rel="alternate" hreflang="en" href="{en_url}">',
        f'  <link rel="alternate" hreflang="x-default" href="{ja_url}">',
    ])


def apply_strings(soup, EN):
    for el in soup.select('[data-i18n]'):
        v = EN.get(el['data-i18n'])
        if v is not None:
            el.string = v
    for el in soup.select('[data-i18n-html]'):
        v = EN.get(el['data-i18n-html'])
        if v is not None:
            el.clear()
            el.append(BeautifulSoup(v, 'html.parser'))
    for el in soup.select('[data-i18n-attr]'):
        for pair in el['data-i18n-attr'].split(','):
            attr, _, key = (s.strip() for s in pair.partition(':'))
            if attr and key in EN:
                el[attr] = EN[key]


def rewrite_urls(soup, fn):
    for el in soup.find_all(['a', 'link', 'script', 'img', 'source']):
        for attr in ('href', 'src'):
            v = el.get(attr)
            if not v or re.match(r'^([a-z]+:|//|#|/)', v):
                continue
            el[attr] = fn(v)


def set_meta(soup, title, desc, url, image=None):
    soup.title.string = title
    soup.find('meta', attrs={'name': 'description'})['content'] = desc
    for prop, val in (('og:title', title), ('og:description', desc), ('og:url', url)):
        tag = soup.find('meta', attrs={'property': prop})
        if tag:
            tag['content'] = val
    if image:
        tag = soup.find('meta', attrs={'property': 'og:image'})
        if tag:
            tag['content'] = image
    if not soup.find('meta', attrs={'property': 'og:locale'}):
        og = soup.find('meta', attrs={'property': 'og:type'})
        loc = soup.new_tag('meta', attrs={'property': 'og:locale', 'content': 'en_US'})
        og.insert_after(loc)
        og.insert_after('\n  ')
        alt = soup.new_tag('meta', attrs={'property': 'og:locale:alternate', 'content': 'ja_JP'})
        loc.insert_after(alt)
        loc.insert_after('\n  ')


def finish(soup, seo_block):
    text = soup.decode(formatter='html5')
    text = replace_block(text, 'seo', seo_block, r'<link rel="icon"')
    text = replace_block(text, 'analytics', ANALYTICS, r'</head>')
    return text


def script_section(ep):
    """英語の台本の全文（「おわり」の中に、開いて読む形で）。無ければ空"""
    path = os.path.join(ROOT, 'ep', ep['id'], 'script.en.json')
    if not os.path.exists(path):
        return ''
    script = json.load(open(path, encoding='utf-8'))
    parts = []
    for pg in script['pages']:
        lines = [ln for ln in pg['lines'] if ln.get('en')]
        if not lines:
            continue
        parts.append(f'<h3>Page {pg["page"]}</h3>')
        for ln in lines:
            cls = ' class="is-caption"' if ln.get('type') == 'caption' else ''
            parts.append(f'<p{cls}>{html.escape(ln["en"])}</p>')
            if ln.get('note'):
                parts.append(f'<p class="end-script-note">Note: {html.escape(ln["note"])}</p>')
    if not parts:
        return ''
    title = html.escape(ep['title_en'])
    return (f'<details class="end-script"><summary>Read the English script</summary>'
            f'<div class="end-script-body"><h2>Ep. {ep["number"]} “{title}” — English script</h2>'
            + ''.join(parts) + '</div></details>')


def build_episode(ep, series, EN):
    src = os.path.join(ROOT, 'ep', ep['id'], 'index.html')
    if not os.path.exists(src):
        return False
    soup = BeautifulSoup(open(src, encoding='utf-8').read(), 'html.parser')
    ja_url, en_url = f"{SITE}ep/{ep['id']}/", f"{SITE}en/ep/{ep['id']}/"
    n, title = ep['number'], ep['title_en']
    stitle = series['title_en']

    soup.html['lang'] = 'en'
    soup.html['data-lang'] = 'en'
    desc = ep.get('summary_en') or series['description_en']
    set_meta(soup, f'Ep. {n} “{title}” | {stitle} — free English manga', desc, en_url)
    apply_strings(soup, EN)

    lettered = ep.get('pagesEn')
    def url(v):
        if v.startswith('../../assets/'):
            return '../' + v
        if v.startswith('pages/'):
            return f"../../../ep/{ep['id']}/{'pages-en' if lettered and not (ep.get('hasCover') and v.endswith('p00.webp')) else 'pages'}/{v[6:]}"
        return v
    rewrite_urls(soup, url)

    main = soup.find(id='reader')
    main['data-base'] = '../../../'
    main['data-link-base'] = '../../'
    soup.find(id='title').string = f'Ep. {n}  {title}'
    soup.select_one('.end-sub').string = f'Ep. {n} “{title}”'
    # 日本語の検索向けのタグは英語のページには載せない
    for c in soup.find_all(string=lambda s: isinstance(s, Comment) and s.strip() in ('tags:start', 'tags:end')):
        c.extract()
    for ul in soup.select('.end-tags'):
        ul.decompose()
    sec = script_section(ep)
    if sec:
        soup.select_one('.end-actions').insert_after(BeautifulSoup(sec, 'html.parser'))

    data = {
        '@context': 'https://schema.org',
        '@type': 'ComicIssue',
        'name': title,
        'headline': f'Ep. {n} “{title}”',
        'alternativeHeadline': ep.get('subtitle_en', ''),
        'issueNumber': n,
        'url': en_url,
        'description': desc,
        'keywords': ','.join(SERIES_KEYWORDS_EN),
        'image': f'{ja_url}og.jpg',
        'thumbnailUrl': f'{ja_url}thumb.webp',
        'datePublished': ep['published'],
        'inLanguage': 'en',
        'genre': GENRE_EN,
        'isAccessibleForFree': True,
        'author': PUBLISHER,
        'publisher': PUBLISHER,
        'translationOfWork': {'@type': 'ComicIssue', 'name': ep['title'], 'inLanguage': 'ja', 'url': ja_url},
        'isPartOf': {'@type': 'ComicSeries', 'name': stitle, 'url': f'{SITE}en/'},
    }
    seo = '\n'.join([
        f'  <link rel="canonical" href="{en_url}">',
        alternates(ja_url, en_url),
        f'  <meta name="keywords" content="{html.escape(",".join(SERIES_KEYWORDS_EN))}">',
        '  <script type="application/ld+json">',
        ld_json(data),
        '  </script>',
    ])
    dst_dir = os.path.join(ROOT, 'en', 'ep', ep['id'])
    os.makedirs(dst_dir, exist_ok=True)
    write(os.path.join(dst_dir, 'index.html'), finish(soup, seo))
    return True


def build_top(series, eps, EN):
    soup = BeautifulSoup(open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read(), 'html.parser')
    stitle, sub = series['title_en'], series['subtitle_en']
    soup.html['lang'] = 'en'
    soup.html['data-lang'] = 'en'
    soup.html['data-root'] = '../'
    desc = series['description_en'] + ' Read it free in English on the web.'
    set_meta(soup, f'{stitle} — {sub} | Free English gag manga', desc, f'{SITE}en/')
    apply_strings(soup, EN)
    rewrite_urls(soup, lambda v: '../' + v if v.startswith('assets/') or v == 'feed.xml' else v)

    # 話の一覧を最初から書いておく（top.js が読み込んだら同じものに描き直す）
    latest = eps[-1]
    for a in soup.select('[data-first-link]'):
        a['href'] = f"ep/{latest['id']}/"
    lst = soup.find(id='episodes')
    lst.clear()
    for ep in reversed(eps):
        item = (f'<li><a class="episode" href="ep/{ep["id"]}/">'
                f'<img src="../ep/{ep["id"]}/thumb.webp" alt="Ep. {ep["number"]} {html.escape(ep["title_en"])}" loading="lazy">'
                f'<div class="episode-body"><span class="ep-num">Ep. {ep["number"]}</span>'
                f'<h3 class="ep-title">{html.escape(ep["title_en"])}</h3>'
                f'<p class="ep-sub">{html.escape(ep.get("subtitle_en", ""))}</p>'
                f'<p class="ep-summary">{html.escape(ep.get("summary_en", ""))}</p></div></a></li>')
        lst.append(BeautifulSoup(item, 'html.parser'))
    for ns in soup.find_all('noscript'):
        if ns.find(attrs={'data-i18n-html': 'ep.noscript'}):
            ns.decompose()
    count = soup.find(id='episode-count')
    if count:
        count.string = f'{len(eps)} chapters online. Start anywhere.'

    data = {
        '@context': 'https://schema.org',
        '@type': 'ComicSeries',
        'name': stitle,
        'alternateName': series['title'],
        'url': f'{SITE}en/',
        'description': series['description_en'],
        'image': f'{SITE}assets/og-top.jpg',
        'inLanguage': 'en',
        'genre': GENRE_EN,
        'keywords': ','.join(SERIES_KEYWORDS_EN),
        'isAccessibleForFree': True,
        'author': PUBLISHER,
        'publisher': PUBLISHER,
        'hasPart': [{
            '@type': 'ComicIssue',
            'name': e['title_en'],
            'issueNumber': e['number'],
            'url': f"{SITE}en/ep/{e['id']}/",
            'datePublished': e['published'],
        } for e in eps],
    }
    seo = '\n'.join([
        f'  <link rel="canonical" href="{SITE}en/">',
        alternates(SITE, f'{SITE}en/'),
        f'  <meta name="keywords" content="{html.escape(",".join(SERIES_KEYWORDS_EN))}">',
        '  <script type="application/ld+json">',
        ld_json(data),
        '  </script>',
    ])
    os.makedirs(os.path.join(ROOT, 'en'), exist_ok=True)
    write(os.path.join(ROOT, 'en', 'index.html'), finish(soup, seo))


def english_episodes(data):
    """英語のページを作る話（公開中で、英語の題名がある話）"""
    return sorted((e for e in data['episodes'] if e.get('pages') and e.get('title_en')), key=lambda e: e['number'])


def build():
    data = json.load(open(os.path.join(ROOT, 'episodes.json'), encoding='utf-8'))
    EN = load_en_strings()
    eps = [e for e in english_episodes(data) if build_episode(e, data['series'], EN)]
    build_top(data['series'], eps, EN)
    print(f'英語のページ：作品トップと {len(eps)} 話を en/ に書き出しました。')
    return eps


if __name__ == '__main__':
    build()
