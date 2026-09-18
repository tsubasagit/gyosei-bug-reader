// 行政バグります！ Webリーダー
// 右開き（日本の漫画と同じ）：← キー・画面の左クリック・右へスワイプで次のページ、→ で前のページ。
// 横長の画面では見開き（右が若いページ）、縦長の画面では1ページずつ表示する。
(() => {
  'use strict';

  const app = document.getElementById('reader');
  const EP_ID = app.dataset.episode;
  const BASE = app.dataset.base || '../../';
  const $ = id => document.getElementById(id);
  const stage = $('stage');
  const MODE_KEY = 'gyosei-reader-mode'; // 'auto' | 'single' | 'spread'

  const state = {
    ep: null,
    pages: [],      // ページ画像の URL
    views: [],      // 表示の単位（1ページずつ、または見開きの2ページ）。中身はページ番号の配列
    view: 0,        // いま表示している views の位置
    mode: 'auto',
    ended: false,
  };

  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch { /* 保存できない環境では覚えない */ } },
  };

  // 扉絵は「扉」、本編は 1 から数える
  const pageLabel = i => (state.ep.hasCover ? (i === 0 ? '扉' : String(i)) : String(i + 1));
  const bodyCount = () => state.pages.length - (state.ep.hasCover ? 1 : 0);

  // 幅の狭い画面（スマホの縦持ち）は、見開きを選んでいても1ページずつ
  const isNarrow = () => window.innerWidth < 700;

  function isSpread() {
    if (isNarrow() || state.mode === 'single') return false;
    if (state.mode === 'spread') return true;
    return window.innerWidth >= 900 && window.innerWidth > window.innerHeight * 1.15;
  }

  function buildViews() {
    const n = state.pages.length;
    const views = [];
    if (!isSpread()) {
      for (let i = 0; i < n; i++) views.push([i]);
      return views;
    }
    let i = 0;
    if (state.ep.hasCover) { views.push([0]); i = 1; } // 扉絵は1枚で見せる
    for (; i < n; i += 2) views.push(i + 1 < n ? [i, i + 1] : [i]);
    return views;
  }

  // 見開きと1ページを切り替えても、読んでいたページを見失わない
  function relayout(keepPage) {
    const page = keepPage ?? currentPage();
    state.views = buildViews();
    state.view = Math.max(0, state.views.findIndex(v => v.includes(page)));
    render();
  }

  const currentPage = () => (state.views[state.view] || [0])[0];

  function makeImage(i) {
    const img = new Image();
    img.decoding = 'async';
    img.src = state.pages[i];
    img.alt = `第${state.ep.number}話「${state.ep.title}」 ${state.ep.hasCover && i === 0 ? '扉絵' : pageLabel(i) + 'ページ'}`;
    img.className = 'page';
    img.draggable = false;
    return img;
  }

  function render() {
    const view = state.views[state.view];
    stage.classList.toggle('is-spread', view.length === 2);
    stage.setAttribute('aria-busy', 'true');
    const imgs = view.map(makeImage);
    let pending = imgs.length;
    const done = () => { if (--pending <= 0) stage.setAttribute('aria-busy', 'false'); };
    imgs.forEach(img => (img.complete ? done() : img.addEventListener('load', done, { once: true })));
    imgs.forEach(img => img.addEventListener('error', done, { once: true }));
    stage.replaceChildren(...imgs); // 見開きは CSS の row-reverse で、若いページが右に来る

    const first = view[0], last = view[view.length - 1];
    const label = view.length === 2 ? `${pageLabel(first)}–${pageLabel(last)}` : pageLabel(first);
    $('indicator').textContent = state.ep.hasCover && first === 0 ? `扉 / ${bodyCount()}` : `${label} / ${bodyCount()}`;
    $('progress-fill').style.width = `${((last + 1) / state.pages.length) * 100}%`;
    $('prev').disabled = state.view === 0;
    $('mode').textContent = isSpread() ? '1ページで読む' : '見開きで読む';
    $('mode').hidden = isNarrow();

    const hash = `#p=${pageLabel(first) === '扉' ? 0 : pageLabel(first)}`;
    if (location.hash !== hash) history.replaceState(null, '', hash);
    preload();
  }

  // 前後2つ分の画像を先に読み込んで、めくりを速くする
  function preload() {
    for (const d of [1, 2, -1]) {
      const v = state.views[state.view + d];
      if (v) v.forEach(i => { const im = new Image(); im.src = state.pages[i]; });
    }
  }

  function next() {
    if (state.ended) return;
    if (state.view < state.views.length - 1) { state.view++; render(); }
    else showEnd(true);
  }
  function prev() {
    if (state.ended) { showEnd(false); return; }
    if (state.view > 0) { state.view--; render(); }
  }
  function goTo(view) { showEnd(false); state.view = Math.min(Math.max(view, 0), state.views.length - 1); render(); }

  function showEnd(on) {
    state.ended = on;
    $('end').hidden = !on;
    app.classList.toggle('is-ended', on);
    if (on) $('restart').focus();
  }

  function toggleUi(force) {
    app.classList.toggle('ui-hidden', force !== undefined ? !force : !app.classList.contains('ui-hidden'));
  }

  // ---- 操作 ---------------------------------------------------------------
  document.addEventListener('keydown', e => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    switch (e.key) {
      case 'ArrowLeft': case 'PageDown': next(); break;
      case 'ArrowRight': case 'PageUp': prev(); break;
      case ' ': (e.shiftKey ? prev : next)(); break;
      case 'Home': goTo(0); break;
      case 'End': goTo(state.views.length - 1); break;
      case 'Escape': if (state.ended) showEnd(false); else toggleUi(true); break;
      default: return;
    }
    e.preventDefault();
  });

  // 画面の左 4 割で次へ、右 4 割で前へ、真ん中はメニューの出し入れ。横に 50px 以上動かしたらスワイプ
  let down = null;
  stage.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    down = { x: e.clientX, y: e.clientY, t: Date.now() };
  });
  stage.addEventListener('pointerup', e => {
    if (!down) return;
    const dx = e.clientX - down.x, dy = e.clientY - down.y;
    down = null;
    if (window.visualViewport && window.visualViewport.scale > 1.05) return; // 拡大中はめくらない
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.2) { (dx > 0 ? next : prev)(); return; }
    if (Math.abs(dx) > 10 || Math.abs(dy) > 10) return;
    const x = e.clientX / window.innerWidth;
    if (x < 0.4) next(); else if (x > 0.6) prev(); else toggleUi();
  });
  stage.addEventListener('pointercancel', () => { down = null; });

  $('next').addEventListener('click', next);
  $('prev').addEventListener('click', prev);
  $('restart').addEventListener('click', () => goTo(0));
  $('end-back').addEventListener('click', () => showEnd(false));
  $('mode').addEventListener('click', () => {
    state.mode = isSpread() ? 'single' : 'spread';
    storage.set(MODE_KEY, state.mode);
    relayout();
  });
  const fsBtn = $('fullscreen');
  if (document.fullscreenEnabled) {
    fsBtn.addEventListener('click', () => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()).catch(() => {}));
  } else fsBtn.hidden = true;

  let resizeTimer = 0;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => relayout(), 120); });

  // #p=3 のようなリンクから、ページ番号（扉絵が 0）を読む
  function pageFromHash() {
    const m = location.hash.match(/p=(\d+)/);
    if (!m) return null;
    const page = Number(m[1]) - (state.ep.hasCover ? 0 : 1);
    return Math.min(Math.max(page, 0), state.pages.length - 1);
  }

  // ---- 読み込み -----------------------------------------------------------
  async function start() {
    try {
      const res = await fetch(BASE + 'episodes.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error(res.status);
      const data = await res.json();
      state.ep = data.episodes.find(e => e.id === EP_ID);
      if (!state.ep || !state.ep.pages.length) throw new Error('episode');
      state.pages = state.ep.pages.map(f => `${BASE}ep/${EP_ID}/pages/${f}`);
      state.mode = ['single', 'spread'].includes(storage.get(MODE_KEY)) ? storage.get(MODE_KEY) : 'auto';

      $('title').textContent = `第${state.ep.number}話　${state.ep.title}`;
      document.title = `第${state.ep.number}話「${state.ep.title}」｜${data.series.title}`;

      relayout(pageFromHash() ?? 0);
      app.classList.add('is-ready');
      // 開いたまま #p=5 のリンクを踏んだときも、そのページへ飛ぶ
      window.addEventListener('hashchange', () => {
        const page = pageFromHash();
        if (page !== null && page !== currentPage()) { showEnd(false); relayout(page); }
      });
    } catch {
      $('error').hidden = false;
    }
  }
  start();
})();
