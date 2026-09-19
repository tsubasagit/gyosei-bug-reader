// 作品トップ：episodes.json からエピソードの一覧を作り、「読む」ボタンを第1話（いちばん若い話）と最新話へ向ける
(async () => {
  'use strict';
  const list = document.getElementById('episodes');
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  try {
    const res = await fetch('episodes.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    const eps = data.episodes.filter(e => e.pages && e.pages.length).sort((a, b) => b.number - a.number);
    if (!eps.length) { list.replaceChildren(el('li', 'episode-empty', 'まだ公開しているエピソードはありません。')); return; }

    // 大きな「読む」ボタンと表紙は、初めての人向けにいちばん若い話へ。最新話は横に小さく
    const first = eps[eps.length - 1], latest = eps[0];
    document.querySelectorAll('[data-first-link]').forEach(a => { a.href = `ep/${first.id}/`; });
    document.getElementById('cta-label').textContent = first.number === 1 ? '第1話から読む' : `第${first.number}話から読む`;
    const latestLink = document.getElementById('cta-latest');
    latestLink.href = `ep/${latest.id}/`;
    latestLink.textContent = `最新話：第${latest.number}話「${latest.title}」`;
    latestLink.hidden = latest === first;
    list.replaceChildren(...eps.map(ep => {
      const li = el('li');
      const a = el('a', 'episode');
      a.href = `ep/${ep.id}/`;
      const img = el('img');
      img.src = `ep/${ep.id}/thumb.webp`;
      img.alt = `第${ep.number}話の扉絵`;
      img.loading = 'lazy';
      const body = el('div');
      const pages = ep.pages.length - (ep.hasCover ? 1 : 0);
      body.append(
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
    }));
  } catch {
    list.replaceChildren(el('li', 'episode-empty', '一覧を読み込めませんでした。時間をおいて、もう一度開いてください。'));
  }
})();
