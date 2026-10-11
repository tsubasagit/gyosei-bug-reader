// 作品トップ：episodes.json からエピソードの一覧を作る。並びは「新しい話から」が標準で、ボタンで逆にできる
// - 一覧の上に、ことばで探す欄と、ジャンル（genres）で絞り込む札。?q=・?tag= を付けたリンクでも開ける
// - 公開予定（upcoming.json の schedule）を一覧の下に。公開された話は自動で外れる
// - ニコニコ漫画・pixiv のボタンの「1〜N話」は、episodes.json の links から数える（公開のたびに書き換えなくてよい）
// 文言と、英語の題名・あらすじは i18n.js から取る（英語のときだけ差し替わる）
(async () => {
  'use strict';
  const list = document.getElementById('episodes');
  const T = window.I18N.t;
  const F = window.I18N.field;          // 英語のときは title_en などを読む
  const link = window.I18N.withLang;    // 英語のときはリンクに ?lang=en を付ける
  const isEn = window.I18N.isEn;
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  try {
    const res = await fetch('episodes.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    const published = data.episodes.filter(e => e.pages && e.pages.length).sort((a, b) => a.number - b.number);
    if (!published.length) { list.replaceChildren(el('li', 'episode-empty', T.listEmpty())); return; }
    // 並び順は、開くたびに「新しい話から」。切り替えると1話が上に来る（覚えない。前に覚えた順も使わない）
    try { localStorage.removeItem('gyosei-episode-order'); } catch { /* 消せなくても動く */ }
    let order = 'desc';
    const eps = published;
    const count = document.getElementById('episode-count');

    // 大きな「読む」ボタンと表紙は最新話へ。1話からは横に小さく
    const first = eps[0], latest = eps[eps.length - 1];   // eps は話数の小さい順
    document.querySelectorAll('[data-first-link]').forEach(a => { a.href = link(`ep/${latest.id}/`); });
    document.getElementById('cta-label').textContent = T.ctaLatest(latest.number);
    const firstLink = document.getElementById('cta-latest');
    firstLink.href = link(`ep/${first.id}/`);
    firstLink.textContent = T.fromFirst(F(first, 'title'));
    firstLink.hidden = latest === first;

    // ---- ニコニコ漫画・pixiv：1話から続けて載っている話の数 ----
    const upTo = key => { let n = 0; for (const ep of eps) { if (ep.number === n + 1 && ep.links && ep.links[key]) n = ep.number; } return n; };
    for (const [key, id] of [['niconico', 'nico-note'], ['pixiv', 'pixiv-note']]) {
      const n = upTo(key), small = document.getElementById(id);
      if (small && n) small.textContent = T.elsewhereNote(key, n);
    }

    // ---- 探す欄とジャンルの札 ----
    const params = new URLSearchParams(location.search);
    let query = params.get('q') || '';
    let genre = params.get('tag') || '';
    const genreCount = new Map();
    eps.forEach(ep => (ep.genres || []).forEach(g => genreCount.set(g, (genreCount.get(g) || 0) + 1)));
    if (genre && !genreCount.has(genre)) genre = '';
    const norm = s => String(s || '').normalize('NFKC').toLowerCase();
    const haystack = ep => norm([F(ep, 'title'), F(ep, 'subtitle'), F(ep, 'summary'), ep.title, ep.subtitle, ...(ep.tags || []), ...(ep.genres || []), `第${ep.number}話`].join(' '));
    const matches = ep => (!genre || (ep.genres || []).includes(genre))
      && norm(query).split(/\s+/).filter(Boolean).every(w => haystack(ep).includes(w));

    const filterBox = el('div', 'ep-filter');
    const search = el('input', 'ep-search');
    search.type = 'search'; search.value = query; search.placeholder = T.searchPlaceholder();
    search.setAttribute('aria-label', T.searchPlaceholder());
    const chips = el('div', 'ep-genres');
    chips.setAttribute('role', 'group'); chips.setAttribute('aria-label', T.genreLabel());
    const chip = (value, label) => {
      const b = el('button', 'genre-chip', label);
      b.type = 'button'; b.dataset.genre = value;
      b.addEventListener('click', () => { genre = genre === value ? '' : value; renderList(); });
      return b;
    };
    chips.append(chip('', T.genreAll()), ...[...genreCount].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ja')).map(([g, n]) => chip(g, `#${g} ${n}`)));
    filterBox.append(search);
    if (!isEn && genreCount.size) filterBox.append(chips);   // ジャンルは日本語の言葉なので、英語では出さない
    list.before(filterBox);
    let typing;
    search.addEventListener('input', () => { clearTimeout(typing); typing = setTimeout(() => { query = search.value; renderList(); }, 150); });

    function syncUrl() {
      const p = new URLSearchParams(location.search);
      if (query.trim()) p.set('q', query.trim()); else p.delete('q');
      if (genre) p.set('tag', genre); else p.delete('tag');
      const qs = p.toString();
      try { history.replaceState(null, '', location.pathname + (qs ? `?${qs}` : '') + location.hash); } catch { /* 書けなくても絞り込みは動く */ }
    }

    function renderList() {
      const shown = (order === 'asc' ? eps : eps.slice().reverse()).filter(matches);
      const filtering = !!(genre || query.trim());
      if (shown.length) list.replaceChildren(...shown.map(episodeItem));
      else {
        const li = el('li', 'episode-empty', T.noMatch());
        const clear = el('button', 'text-btn', T.clearFilter());
        clear.type = 'button';
        clear.addEventListener('click', () => { genre = ''; query = ''; search.value = ''; renderList(); });
        li.append(' ', clear);
        list.replaceChildren(li);
      }
      if (count) count.textContent = filtering ? T.epFiltered(shown.length, eps.length) : T.epCount(eps.length);
      [...sortBox.children].forEach(b => b.setAttribute('aria-pressed', String(b.dataset.order === order)));
      [...chips.children].forEach(b => b.setAttribute('aria-pressed', String(b.dataset.genre === genre)));
      syncUrl();
    }
    const sortBox = document.getElementById('ep-sort');
    for (const [key, label] of [['desc', T.sortDesc()], ['asc', T.sortAsc()]]) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'sort-btn'; b.textContent = label; b.dataset.order = key;
      b.addEventListener('click', () => {
        order = key;
        renderList();
      });
      sortBox.append(b);
    }

    // ジャンル（太字）のあとに、題材のことば
    function tagList(ep) {
      const ul = el('ul', 'ep-tags');
      ul.append(...(ep.genres || []).map(t => el('li', 'is-genre', `#${t}`)), ...(ep.tags || []).map(t => el('li', null, `#${t}`)));
      return ul;
    }

    function episodeItem(ep) {
      const li = el('li');
      const a = el('a', 'episode');
      a.href = link(`ep/${ep.id}/`);
      const img = el('img');
      img.src = `ep/${ep.id}/thumb.webp`;
      img.alt = T.thumbAlt(ep.number, F(ep, 'title'));
      img.loading = 'lazy';
      const body = el('div', 'episode-body');
      const pages = ep.pages.length - (ep.hasCover ? 1 : 0);
      body.append(
        ...(ep === latest ? [el('span', 'ep-pick', T.pick())] : []),
        el('span', 'ep-num', T.epNum(ep.number)),
        // 言語の札：日本語で見ているときは英語版がある話に、英語で見ているときは英語版が無い話にだけ付ける
        ...(T.langTag(!!ep.pagesEn) ? [el('span', 'ep-lang' + (ep.pagesEn ? ' has-en' : ''), T.langTag(!!ep.pagesEn))] : []),
        el('h3', 'ep-title', F(ep, 'title')),
        el('p', 'ep-sub', T.epSub(F(ep, 'subtitle'))),
        el('p', 'ep-summary', F(ep, 'summary')),
        // タグは日本語の検索向け。英語で見ているときは出さない
        ...(!isEn && ((ep.tags && ep.tags.length) || (ep.genres && ep.genres.length)) ? [tagList(ep)] : []),
        el('p', 'ep-meta', T.epMeta(pages, ep.published.replace(/-/g, '.'))),
        el('span', 'read-btn', T.readBtn()),
      );
      a.append(img, body);
      li.append(a);
      return li;
    }
    renderList();
    if (isEn) document.title = `${data.series.title_en} — ${data.series.subtitle_en}`;

    // ---- 公開予定（公開された話は自動で外れる） ----
    const up = await fetch('upcoming.json', { cache: 'no-cache' }).then(r => (r.ok ? r.json() : {})).catch(() => ({}));
    const done = new Set(eps.map(e => e.number));
    const plan = (up.schedule || []).filter(u => !done.has(u.number));
    const section = document.getElementById('upcoming');
    if (section && plan.length) {
      document.getElementById('upcoming-list').replaceChildren(...plan.map(u => {
        const li = el('li', 'upcoming-item');
        if (u.cover) {
          const img = el('img');
          img.src = u.cover; img.alt = T.thumbAlt(u.number, u.title); img.loading = 'lazy';
          li.append(img);
        } else {
          li.append(el('div', 'upcoming-noimg', T.coverSoon()));
        }
        const body = el('div', 'upcoming-body');
        const md = (u.date || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
        const when = md ? T.releaseDay(Number(md[2]), Number(md[3]), new Date(Number(md[1]), Number(md[2]) - 1, Number(md[3])).getDay()) : T.comingSoon();
        body.append(el('span', 'upcoming-date', when), el('span', 'ep-num', T.epNum(u.number)), el('h3', 'ep-title', u.title));
        if (u.subtitle) body.append(el('p', 'ep-sub', T.epSub(u.subtitle)));
        if (!isEn && u.genres && u.genres.length) {
          const tags = el('ul', 'ep-tags');
          tags.append(...u.genres.map(g => el('li', 'is-genre', `#${g}`)));
          body.append(tags);
        }
        li.append(body);
        return li;
      }));
      section.hidden = false;
    }
  } catch {
    list.replaceChildren(el('li', 'episode-empty', T.listError()));
  }
})();
