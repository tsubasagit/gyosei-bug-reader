// 作品トップ：episodes.json からエピソードの一覧を作る。並びは「1話から」が標準で、ボタンで逆にできる
(async () => {
  'use strict';
  const list = document.getElementById('episodes');
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  try {
    const res = await fetch('episodes.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    const published = data.episodes.filter(e => e.pages && e.pages.length).sort((a, b) => a.number - b.number);
    if (!published.length) { list.replaceChildren(el('li', 'episode-empty', 'まだ公開しているエピソードはありません。')); return; }
    // 並び順は「1話から」が標準。切り替えると新しい話が上に来る。選んだ順はこのブラウザに覚える
    const SORT_KEY = 'gyosei-episode-order';
    let order = 'asc';
    try { if (localStorage.getItem(SORT_KEY) === 'desc') order = 'desc'; } catch { /* 読めなくても標準のまま */ }
    const eps = published;
    const count = document.getElementById('episode-count');
    if (count) count.textContent = `公開中の${eps.length}話。どの話からでも楽しめます。`;

    // 大きな「読む」ボタンと表紙は、初めての人向けにいちばん若い話へ。最新話は横に小さく
    const first = eps[0], latest = eps[eps.length - 1];   // eps は話数の小さい順
    document.querySelectorAll('[data-first-link]').forEach(a => { a.href = `ep/${first.id}/`; });
    document.getElementById('cta-label').textContent = first.number === 1 ? '第1話から読む' : `第${first.number}話から読む`;
    const latestLink = document.getElementById('cta-latest');
    latestLink.href = `ep/${latest.id}/`;
    latestLink.textContent = `最新話：第${latest.number}話「${latest.title}」`;
    latestLink.hidden = latest === first;
    function renderList() {
      const sorted = order === 'asc' ? eps : eps.slice().reverse();
      list.replaceChildren(...sorted.map(episodeItem));
      [...sortBox.children].forEach(b => b.setAttribute('aria-pressed', String(b.dataset.order === order)));
    }
    const sortBox = document.getElementById('ep-sort');
    for (const [key, label] of [['asc', '1話から'], ['desc', '新しい話から']]) {
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
      a.href = `ep/${ep.id}/`;
      const img = el('img');
      img.src = `ep/${ep.id}/thumb.webp`;
      img.alt = `第${ep.number}話「${ep.title}」の扉絵`;
      img.loading = 'lazy';
      const body = el('div', 'episode-body');
      const pages = ep.pages.length - (ep.hasCover ? 1 : 0);
      body.append(
        ...(ep === first ? [el('span', 'ep-pick', 'はじめてならここ')] : []),
        el('span', 'ep-num', `第${ep.number}話`),
        el('h3', 'ep-title', ep.title),
        el('p', 'ep-sub', `～${ep.subtitle}～`),
        el('p', 'ep-summary', ep.summary),
        el('p', 'ep-meta', `${pages}ページ・${ep.published.replace(/-/g, '.')} 公開`),
        el('span', 'read-btn', '読む ▶'),
      );
      a.append(img, body);
      li.append(a);
      return li;
    }
    renderList();
  } catch {
    list.replaceChildren(el('li', 'episode-empty', '一覧を読み込めませんでした。時間をおいて、もう一度開いてください。'));
  }
})();
