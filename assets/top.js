// 作品トップ：episodes.json からエピソードの一覧を作る（新しい話が上）
(async () => {
  'use strict';
  const list = document.getElementById('episodes');
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  try {
    const res = await fetch('episodes.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    document.getElementById('series-desc').textContent = data.series.description;
    const eps = data.episodes.filter(e => e.pages && e.pages.length).sort((a, b) => b.number - a.number);
    if (!eps.length) { list.replaceChildren(el('li', 'episode-empty', 'まだ公開しているエピソードはありません。')); return; }
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
