// また来てもらうための仕掛け（作品トップと、読む画面の両方で読み込む）
// - 次回予告：upcoming.json の「次の話」を、トップと読み終わりの画面に出す
// - NEW：前に来たときから増えた話に印を付ける（開いたら消える）
// - 続きから読む：途中でやめた話とページを覚えておき、トップに出す
// - X のフォロー：新しい話のお知らせ先として、トップと読み終わりの画面に出す
// 覚えるのはこのブラウザの中だけ（localStorage）。読めない・書けないときは、何も出さずに普通に動く
(() => {
  'use strict';
  const app = document.getElementById('reader');
  const isReader = !!app;
  const BASE = isReader ? (app.dataset.base || '../../') : '';
  const EP_ID = isReader ? app.dataset.episode : null;

  // 見た目は別ファイル。HTML を触らずに済むよう、ここで読み込む
  const css = document.createElement('link');
  css.rel = 'stylesheet';
  css.href = BASE + 'assets/revisit.css';
  document.head.append(css);

  const KEY = { known: 'gyosei-known-episodes', fresh: 'gyosei-new-episodes', progress: 'gyosei-reading' };
  const load = (k, fallback) => { try { const v = JSON.parse(localStorage.getItem(k)); return v ?? fallback; } catch { return fallback; } };
  const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* 覚えられなくても動く */ } };
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const getJson = url => fetch(url, { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

  const dataP = getJson(BASE + 'episodes.json');
  const upcomingP = getJson(BASE + 'upcoming.json').catch(() => ({}));

  // 「近日公開」と「X でお知らせ」のかたまり。トップと読み終わりの画面で同じものを使う
  function noticeBlock(up, where) {
    const box = el('div', `revisit-notice revisit-${where}`);
    const next = up.next;
    if (next && next.title) {
      const when = next.date ? `${next.date.replace(/^\d{4}-0?(\d+)-0?(\d+)$/, '$1月$2日')}ごろ公開予定` : '近日公開';
      box.append(
        el('p', 'revisit-kicker', when),
        el('p', 'revisit-next', `第${next.number}話「${next.title}」`),
      );
    }
    if (up.x && up.x.url) {
      const a = el('a', 'revisit-x', '');
      a.href = up.x.url;
      a.target = '_blank';
      a.rel = 'noopener';
      a.append(el('span', 'revisit-x-mark', '𝕏'), el('span', '', `新しい話はXでお知らせします${up.x.handle ? `（${up.x.handle}）` : ''}　フォローする`));
      box.append(a);
    }
    return box.childElementCount ? box : null;
  }

  // ---- 読む画面 ------------------------------------------------------------
  if (isReader) {
    // 開いた話は NEW から外す
    save(KEY.fresh, load(KEY.fresh, []).filter(id => id !== EP_ID));

    // 読み終わりのカードに、差し込み口を先に置く（縦につなげる表示は、このカードを複製して使うため）
    const card = document.querySelector('#end .end-card');
    if (card) card.insertBefore(el('div', 'revisit-slot'), card.querySelector(':scope > .text-btn'));

    // どこまで読んだか：読む画面は #p=3 のようにページを URL に書く。その書き換えを見張る
    let last = 0, title = '', number = 0;   // last は最後のページの番号（扉絵が 0、本編は 1 から）
    const pageNow = () => { const m = location.hash.match(/p=(\d+)/); return m ? Number(m[1]) : 0; };
    function remember() {
      if (!last) return;
      const page = pageNow();
      const done = page >= last || app.classList.contains('is-ended');
      save(KEY.progress, { id: EP_ID, number, title, page, last, done, at: Date.now() });
    }
    const replace = history.replaceState.bind(history);
    history.replaceState = function (...args) { const r = replace(...args); remember(); return r; };
    window.addEventListener('hashchange', remember);
    new MutationObserver(remember).observe(app, { attributes: true, attributeFilter: ['class'] });

    Promise.all([dataP, upcomingP]).then(([data, up]) => {
      const ep = data.episodes.find(e => e.id === EP_ID);
      if (ep) { last = ep.hasCover ? ep.pages.length - 1 : ep.pages.length; title = ep.title; number = ep.number; remember(); }
      // 次回予告は、まだ公開していない話のときだけ出す
      const up2 = { ...up };
      if (up.next && data.episodes.some(e => e.number === up.next.number && e.pages && e.pages.length)) delete up2.next;
      document.querySelectorAll('.revisit-slot').forEach(slot => {
        const box = noticeBlock(up2, 'end');
        if (box) slot.replaceChildren(box);
      });
    }).catch(() => { /* 出せなくても読むのには困らない */ });
    return;
  }

  // ---- 作品トップ ----------------------------------------------------------
  Promise.all([dataP, upcomingP]).then(([data, up]) => {
    const published = data.episodes.filter(e => e.pages && e.pages.length).sort((a, b) => a.number - b.number);
    const ids = published.map(e => e.id);

    // NEW：前に来たときに無かった話。初めて来た人には付けない（全部が NEW になってしまうため）
    const known = load(KEY.known, null);
    let fresh = load(KEY.fresh, []).filter(id => ids.includes(id));
    if (Array.isArray(known)) fresh = [...new Set([...fresh, ...ids.filter(id => !known.includes(id))])];
    save(KEY.known, ids);
    save(KEY.fresh, fresh);

    const list = document.getElementById('episodes');
    function markNew() {
      list.querySelectorAll('a.episode').forEach(a => {
        const id = (a.getAttribute('href') || '').match(/ep\/([^/]+)\//)?.[1];
        const body = a.querySelector('.episode-body');
        if (!id || !body || body.querySelector('.ep-new')) return;
        if (fresh.includes(id)) body.prepend(el('span', 'ep-new', 'NEW'));
      });
    }
    if (list) { markNew(); new MutationObserver(markNew).observe(list, { childList: true }); }

    // 続きから読む：途中でやめた話があれば、読むボタンの下に出す
    const p = load(KEY.progress, null);
    const cta = document.querySelector('.cta-row');
    if (cta && p && !p.done && ids.includes(p.id) && p.page > 0) {
      const a = el('a', 'revisit-resume');
      a.href = `ep/${p.id}/#p=${p.page}`;
      a.append(el('span', 'revisit-resume-label', '続きから読む'), el('span', '', `第${p.number}話「${p.title}」 ${p.page}ページ目から`));
      cta.after(a);
    }

    // 近日公開と X のフォロー：エピソード一覧の下と、フッターの導線に
    const up2 = { ...up };
    if (up.next && published.some(e => e.number === up.next.number)) delete up2.next;
    const section = document.querySelector('.episodes-section .wrap');
    const box = noticeBlock(up2, 'top');
    if (section && box) section.append(box);
    if (up.x && up.x.url) {
      const links = document.querySelector('.footer-cta-links');
      if (links && !links.querySelector('.footer-btn-x')) {
        const a = el('a', 'footer-btn ghost footer-btn-x', 'Xで新しい話を受け取る');
        a.href = up.x.url; a.target = '_blank'; a.rel = 'noopener';
        links.append(a);
      }
    }
  }).catch(() => { /* 出せなくても一覧はふつうに動く */ });
})();
