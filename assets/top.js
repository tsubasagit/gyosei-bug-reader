// 作品トップ：episodes.json からエピソードの一覧を作る。並びは「1話から」が標準で、ボタンで逆にできる
// 文言と、英語の題名・あらすじは i18n.js から取る（英語のときだけ差し替わる）
(async () => {
  'use strict';
  const list = document.getElementById('episodes');
  const T = window.I18N.t;
  const F = window.I18N.field;          // 英語のときは title_en などを読む
  const link = window.I18N.withLang;    // 英語のときはリンクに ?lang=en を付ける
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  try {
    const res = await fetch('episodes.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    const published = data.episodes.filter(e => e.pages && e.pages.length).sort((a, b) => a.number - b.number);
    if (!published.length) { list.replaceChildren(el('li', 'episode-empty', T.listEmpty())); return; }
    // 並び順は「1話から」が標準。切り替えると新しい話が上に来る。選んだ順はこのブラウザに覚える
    const SORT_KEY = 'gyosei-episode-order';
    let order = 'asc';
    try { if (localStorage.getItem(SORT_KEY) === 'desc') order = 'desc'; } catch { /* 読めなくても標準のまま */ }
    const eps = published;
    const count = document.getElementById('episode-count');
    if (count) count.textContent = T.epCount(eps.length);

    // 大きな「読む」ボタンと表紙は、初めての人向けにいちばん若い話へ。最新話は横に小さく
    const first = eps[0], latest = eps[eps.length - 1];   // eps は話数の小さい順
    document.querySelectorAll('[data-first-link]').forEach(a => { a.href = link(`ep/${first.id}/`); });
    document.getElementById('cta-label').textContent = T.ctaFirst(first.number);
    const latestLink = document.getElementById('cta-latest');
    latestLink.href = link(`ep/${latest.id}/`);
    latestLink.textContent = T.latest(latest.number, F(latest, 'title'));
    latestLink.hidden = latest === first;
    function renderList() {
      const sorted = order === 'asc' ? eps : eps.slice().reverse();
      list.replaceChildren(...sorted.map(episodeItem));
      [...sortBox.children].forEach(b => b.setAttribute('aria-pressed', String(b.dataset.order === order)));
    }
    const sortBox = document.getElementById('ep-sort');
    for (const [key, label] of [['asc', T.sortAsc()], ['desc', T.sortDesc()]]) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'sort-btn'; b.textContent = label; b.dataset.order = key;
      b.addEventListener('click', () => {
        order = key;
        try { localStorage.setItem(SORT_KEY, key); } catch { /* 覚えられなくても動く */ }
        renderList();
      });
      sortBox.append(b);
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
        ...(ep === first ? [el('span', 'ep-pick', T.pick())] : []),
        el('span', 'ep-num', T.epNum(ep.number)),
        el('h3', 'ep-title', F(ep, 'title')),
        el('p', 'ep-sub', T.epSub(F(ep, 'subtitle'))),
        el('p', 'ep-summary', F(ep, 'summary')),
        el('p', 'ep-meta', T.epMeta(pages, ep.published.replace(/-/g, '.'))),
        el('span', 'read-btn', T.readBtn()),
      );
      a.append(img, body);
      li.append(a);
      return li;
    }
    renderList();
    if (window.I18N.isEn) document.title = `${data.series.title_en} — ${data.series.subtitle_en}`;
  } catch {
    list.replaceChildren(el('li', 'episode-empty', T.listError()));
  }
})();
