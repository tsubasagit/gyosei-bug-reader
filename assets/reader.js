// 行政バグります！ Webリーダー
// 右開き（日本の漫画と同じ）：← キー・画面の左クリック・右へフリック（スワイプ）で次のページ、→ で前のページ。
// 表示は3通り。
// - 縦につなげる（幅のある画面の標準）：全ページを横幅に合わせて縦に並べ、スクロールだけで最後まで読む
// - 1ページずつめくる（スマホの縦持ち）：画面に1ページを収めて、めくる
// - 見開き（幅のある画面でメニューから選んだとき）：2ページを並べてめくる。右が若いページ
(() => {
  'use strict';

  const app = document.getElementById('reader');
  const EP_ID = app.dataset.episode;
  const BASE = app.dataset.base || '../../';
  const $ = id => document.getElementById(id);
  const stage = $('stage');
  const MODE_KEY = 'gyosei-reader-mode'; // 'auto' | 'spread'
  const T = window.I18N.t;               // 文言（日本語・英語）
  const F = window.I18N.field;           // 英語のときは title_en などを読む
  const link = window.I18N.withLang;

  const state = {
    ep: null,
    pages: [],      // ページ画像の URL
    views: [],      // めくるときの表示の単位（1ページか見開きの2ページ）。中身はページ番号の配列
    view: 0,        // いま表示している views の位置
    page: 0,        // 縦につなげる表示で、いま読んでいるページ
    mode: 'auto',
    ended: false,
    script: null,   // 対訳（英語で読むときだけ読み込む）
  };

  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch { /* 保存できない環境では覚えない */ } },
  };

  // 扉絵は「扉」、本編は 1 から数える
  const pageLabel = i => (state.ep.hasCover ? (i === 0 ? T.coverLabel() : String(i)) : String(i + 1));
  const bodyCount = () => state.pages.length - (state.ep.hasCover ? 1 : 0);

  // 幅の狭い画面（スマホの縦持ち）は、1ページずつめくる
  const isNarrow = () => window.innerWidth < 700;
  const isSpread = () => !isNarrow() && state.mode === 'spread';
  const isFlow = () => !isNarrow() && !isSpread();

  const hasMouse = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const smooth = () => (window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth');

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

  const currentPage = () => (isFlow() ? state.page : (state.views[state.view] || [0])[0]);

  // 表示を切り替えても、読んでいたページを見失わない
  function relayout(keepPage) {
    const page = keepPage ?? currentPage();
    showEnd(false);
    state.views = buildViews();
    state.view = Math.max(0, state.views.findIndex(v => v.includes(page)));
    app.classList.toggle('is-flow', isFlow());
    stage.classList.toggle('is-flow', isFlow());
    if (state.script) {                    // 対訳は、縦につなげる表示ではページの下に、めくる表示ではボタンで出す
      ensureSheet();
      if (isFlow()) openSheet(false);
      if (sheetBtn) sheetBtn.hidden = isFlow();
    }
    if (isFlow()) renderFlow(page); else render();
    updateMenu();
  }

  function makeImage(i, lazy) {
    const img = new Image();
    img.decoding = 'async';
    if (lazy) img.loading = 'lazy';
    const size = state.ep.sizes && state.ep.sizes[i];
    if (size) { img.width = size[0]; img.height = size[1]; } // 読み込む前から高さを取っておく
    img.src = state.pages[i];
    img.alt = T.pageAlt(state.ep.number, F(state.ep, 'title'),
      state.ep.hasCover && i === 0 ? T.coverAltPart() : T.pageAltPart(pageLabel(i)));
    img.className = 'page';
    img.draggable = false;
    img.dataset.page = i;
    return img;
  }

  // ---- めくる表示（スマホ・見開き） ------------------------------------------
  function render() {
    const view = state.views[state.view];
    stage.classList.toggle('is-spread', view.length === 2);
    stage.setAttribute('aria-busy', 'true');
    const imgs = view.map(i => makeImage(i, false));
    let pending = imgs.length;
    const done = () => { if (--pending <= 0) stage.setAttribute('aria-busy', 'false'); };
    imgs.forEach(img => (img.complete ? done() : img.addEventListener('load', done, { once: true })));
    imgs.forEach(img => img.addEventListener('error', done, { once: true }));
    stage.replaceChildren(...imgs); // 見開きは CSS の row-reverse で、若いページが右に来る

    const first = view[0], last = view[view.length - 1];
    const label = view.length === 2 ? `${pageLabel(first)}–${pageLabel(last)}` : pageLabel(first);
    showPosition(first, label, (last + 1) / state.pages.length);
    $('prev').disabled = state.view === 0;
    if (sheetBtn) sheetBtn.disabled = !view.some(hasLines);
    if (sheet && !sheet.hidden) {              // 対訳を開いたままページをめくったとき
      if (sheetBtn.disabled) openSheet(false); else fillSheet();
    }
    preload();
  }

  // 前後2つ分の画像を先に読み込んで、めくりを速くする
  function preload() {
    for (const d of [1, 2, -1]) {
      const v = state.views[state.view + d];
      if (v) v.forEach(i => { const im = new Image(); im.src = state.pages[i]; });
    }
  }

  // ---- 縦につなげる表示（PC・タブレット） ------------------------------------
  function renderFlow(page) {
    stage.classList.remove('is-spread');
    stage.setAttribute('aria-busy', 'false');
    // 最初の2ページはすぐ読み込み、残りは近づいたら読み込む
    const imgs = [];
    state.pages.forEach((_, i) => {
      imgs.push(makeImage(i, i > page + 1));
      const sc = scriptBlock(i);           // 英語で読むときは、ページの下に対訳を挟む
      if (sc) imgs.push(sc);
    });
    stage.replaceChildren(...imgs, flowEnd());
    state.page = page;
    stage.scrollTop = page === 0 ? 0 : pageTop(page);
    onFlowScroll();
  }

  // 最後のページの下に置く「おわり」
  function flowEnd() {
    const end = document.createElement('section');
    end.className = 'flow-end';
    end.setAttribute('aria-label', 'おわり');
    const card = $('end').querySelector('.end-card').cloneNode(true);
    card.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
    card.querySelector(':scope > .text-btn')?.remove(); // 「最後のページに戻る」は縦につなげる表示では要らない
    card.querySelector('.end-actions .text-btn').addEventListener('click', () => stage.scrollTo({ top: 0, behavior: smooth() })); // 最初から読む
    end.append(card);
    return end;
  }

  const pageEls = () => stage.querySelectorAll('.page');
  const pageTop = i => { const el = pageEls()[i]; return el ? el.offsetTop - 8 : 0; };

  // いま画面の上から 4 割のところにあるページを「読んでいるページ」にする
  function onFlowScroll() {
    const line = stage.scrollTop + stage.clientHeight * 0.4;
    let page = 0;
    pageEls().forEach((el, i) => { if (el.offsetTop <= line) page = i; });
    state.page = page;
    const max = stage.scrollHeight - stage.clientHeight;
    showPosition(page, pageLabel(page), max > 0 ? stage.scrollTop / max : 1);
  }
  let scrollTick = 0;
  stage.addEventListener('scroll', () => {
    if (!isFlow() || scrollTick) return;
    scrollTick = requestAnimationFrame(() => { scrollTick = 0; onFlowScroll(); });
  }, { passive: true });

  function flowGo(dir) {
    const n = state.pages.length;
    let target;
    if (dir > 0) target = state.page + 1;
    // ページの途中まで読んでいたら、まずそのページの頭に戻る
    else target = stage.scrollTop > pageTop(state.page) + 24 ? state.page : state.page - 1;
    if (target < 0) return;
    const top = target >= n ? stage.scrollHeight : pageTop(target);
    stage.scrollTo({ top, behavior: smooth() });
  }

  // ---- 対訳（英語で読むときだけ） ---------------------------------------------
  async function loadScript() {
    if (!window.I18N.isEn) return;
    try {
      const res = await fetch(`${BASE}ep/${EP_ID}/script.${window.I18N.lang}.json`, { cache: 'no-cache' });
      if (!res.ok) return;                       // 対訳がまだ無い話は、絵だけで読む
      const data = await res.json();
      if (data && data.pages && data.pages.length) {
        state.script = data;
        app.classList.add('has-script');
      }
    } catch { /* 読めなければ出さない */ }
  }

  // ページの順番（扉絵が 0）から、その本編ページの対訳を組み立てる
  function scriptBlock(i) {
    if (!state.script) return null;
    const num = state.ep.hasCover ? i : i + 1;
    if (num < 1) return null;                    // 扉絵にはセリフが無い
    const page = state.script.pages.find(p => p.page === num);
    if (!page || !page.lines.length) return null;
    const box = document.createElement('aside');
    box.className = 'script';
    const head = document.createElement('p');
    head.className = 'script-head';
    head.textContent = `${T.scriptTitle()} · ${T.pageAltPart(pageLabel(i))}`;
    const ol = document.createElement('ol');
    ol.className = 'script-lines';
    for (const ln of page.lines) {
      const li = document.createElement('li');
      li.className = ln.type === 'caption' ? 'script-line is-caption' : 'script-line';
      const en = document.createElement('p');
      en.className = 'sc-en';
      en.textContent = ln[state.script.lang] || ln.ja;
      const ja = document.createElement('p');
      ja.className = 'sc-ja';
      ja.lang = 'ja';
      ja.textContent = ln.ja;
      li.append(en, ja);
      if (ln.note) {                             // 制度のひとこと解説
        const note = document.createElement('p');
        note.className = 'sc-note';
        note.textContent = ln.note;
        li.append(note);
      }
      ol.append(li);
    }
    box.append(head, ol);
    return box;
  }

  // めくる表示（スマホ・見開き）では、下のバーのボタンで対訳を出す
  let sheet = null, sheetBtn = null;
  function ensureSheet() {
    if (!state.script || sheet) return;
    sheetBtn = document.createElement('button');
    sheetBtn.type = 'button';
    sheetBtn.className = 'nav-btn script-btn';
    sheetBtn.textContent = T.scriptTitle();
    sheetBtn.addEventListener('click', () => openSheet(sheet.hidden));
    document.querySelector('.controls').append(sheetBtn);
    sheet = document.createElement('div');
    sheet.className = 'script-sheet';
    sheet.hidden = true;
    sheet.addEventListener('click', e => { if (e.target === sheet) openSheet(false); });
    app.append(sheet);
  }
  function openSheet(on) {
    if (!sheet) return;
    sheet.hidden = !on;
    app.classList.toggle('sheet-open', on);
    if (on) fillSheet();
  }
  function fillSheet() {
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'text-btn script-close';
    close.textContent = '×';
    close.setAttribute('aria-label', 'Close');
    close.addEventListener('click', () => openSheet(false));
    const view = state.views[state.view] || [currentPage()];   // 見開きなら2ページぶん
    sheet.replaceChildren(close, ...view.map(scriptBlock).filter(Boolean));
  }
  // そのページに対訳があるか（扉絵にはセリフが無い）
  function hasLines(i) {
    if (!state.script) return false;
    const page = state.script.pages.find(p => p.page === (state.ep.hasCover ? i : i + 1));
    return !!(page && page.lines.length);
  }

  // ---- 共通 ---------------------------------------------------------------
  function showPosition(first, label, progress) {
    const text = T.counter(label, bodyCount());
    $('indicator').textContent = text;
    $('top-indicator').textContent = text;
    $('progress-fill').style.width = `${Math.min(progress, 1) * 100}%`;
    const hash = `#p=${state.ep.hasCover && first === 0 ? 0 : pageLabel(first)}`;
    if (location.hash !== hash) history.replaceState(null, '', hash);
  }

  function next() {
    if (isFlow()) { flowGo(1); return; }
    if (state.ended) return;
    if (state.view < state.views.length - 1) { state.view++; render(); }
    else showEnd(true);
  }
  function prev() {
    if (isFlow()) { flowGo(-1); return; }
    if (state.ended) { showEnd(false); return; }
    if (state.view > 0) { state.view--; render(); }
  }
  function goTo(where) { // 'first' | 'last'
    if (isFlow()) { stage.scrollTo({ top: where === 'first' ? 0 : stage.scrollHeight, behavior: smooth() }); return; }
    showEnd(false);
    state.view = where === 'first' ? 0 : state.views.length - 1;
    render();
  }

  function showEnd(on) {
    state.ended = on;
    $('end').hidden = !on;
    app.classList.toggle('is-ended', on);
    if (on) $('restart').focus();
  }

  function toggleUi(force) {
    app.classList.toggle('ui-hidden', force !== undefined ? !force : !app.classList.contains('ui-hidden'));
  }

  // ---- メニュー（表示の切り替えと操作のしかた） -------------------------------
  const menu = $('menu'), menuBtn = $('menu-btn');
  function openMenu(on) {
    menu.hidden = !on;
    menuBtn.setAttribute('aria-expanded', String(on));
    app.classList.toggle('menu-open', on);
  }
  function updateMenu() {
    $('mode').hidden = isNarrow();
    $('mode').textContent = isSpread() ? T.modeToFlow() : T.modeToSpread();
    $('menu-hint').textContent = isNarrow() ? T.hintNarrow() : isFlow() ? T.hintFlow() : T.hintSpread();
  }
  menuBtn.addEventListener('click', e => { e.stopPropagation(); openMenu(menu.hidden); });
  document.addEventListener('click', e => { if (!menu.hidden && !e.target.closest('.menu-wrap')) openMenu(false); });
  $('mode').addEventListener('click', () => {
    state.mode = isSpread() ? 'auto' : 'spread';
    storage.set(MODE_KEY, state.mode);
    openMenu(false);
    relayout();
  });

  // ---- 操作 ---------------------------------------------------------------
  document.addEventListener('keydown', e => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === 'Escape' && !menu.hidden) { openMenu(false); menuBtn.focus(); e.preventDefault(); return; }
    if (e.key === 'Escape' && sheet && !sheet.hidden) { openSheet(false); e.preventDefault(); return; }
    if (isFlow() && [' ', 'ArrowDown', 'ArrowUp', 'PageDown', 'PageUp'].includes(e.key)) {
      // 縦につなげる表示では、スクロールはブラウザにまかせる（ページ全体ではなく stage を動かす）
      const step = { ' ': 0.85, PageDown: 0.85, PageUp: -0.85, ArrowDown: 0.15, ArrowUp: -0.15 }[e.key] * (e.shiftKey && e.key === ' ' ? -1 : 1);
      stage.scrollBy({ top: step * stage.clientHeight, behavior: smooth() });
      e.preventDefault();
      return;
    }
    switch (e.key) {
      case 'ArrowLeft': case 'PageDown': next(); break;
      case 'ArrowRight': case 'PageUp': prev(); break;
      case ' ': (e.shiftKey ? prev : next)(); break;
      case 'Home': goTo('first'); break;
      case 'End': goTo('last'); break;
      case 'Escape': if (state.ended) showEnd(false); else toggleUi(true); break;
      default: return;
    }
    e.preventDefault();
  });

  // 画面の左 4 割で次へ、右 4 割で前へ、真ん中はメニューの出し入れ。
  // 横に払ったら（指のフリック・マウスのドラッグ）、右へ払うと次、左へ払うと前
  function gesture(dx, dy, clientX, target, swipe) {
    if (window.visualViewport && window.visualViewport.scale > 1.05) return; // 拡大中はめくらない
    if (target.closest('.flow-end')) return; // 「おわり」のボタンを押したとき
    if (Math.abs(dx) > swipe && Math.abs(dx) > Math.abs(dy) * 1.2) { (dx > 0 ? next : prev)(); return; }
    if (Math.abs(dx) > 10 || Math.abs(dy) > 10) return;
    const x = clientX / window.innerWidth;
    if (x < 0.4) next(); else if (x > 0.6) prev(); else toggleUi();
  }

  // マウス・ペン
  let down = null;
  stage.addEventListener('pointerdown', e => {
    if (e.pointerType === 'touch' || e.button !== 0) return;
    down = { x: e.clientX, y: e.clientY };
  });
  stage.addEventListener('pointerup', e => {
    if (!down || e.pointerType === 'touch') return;
    const dx = e.clientX - down.x, dy = e.clientY - down.y;
    down = null;
    gesture(dx, dy, e.clientX, e.target, 50);
  });
  stage.addEventListener('pointercancel', () => { down = null; });

  // 指は touch イベントで拾う。iPhone の Safari は touch-action: pinch-zoom を知らないので、
  // 横に払うとブラウザが操作を引き取って pointercancel になり、pointer イベントではフリックを取りこぼす
  let touch = null;
  stage.addEventListener('touchstart', e => {
    touch = e.touches.length === 1 ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null; // 2本指はピンチ
  }, { passive: true });
  stage.addEventListener('touchmove', e => { if (e.touches.length > 1) touch = null; }, { passive: true });
  stage.addEventListener('touchend', e => {
    if (!touch || e.touches.length) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touch.x, dy = t.clientY - touch.y;
    touch = null;
    if (e.target.closest('.flow-end')) return; // 「おわり」のボタンはふつうに押せるように
    if (e.cancelable) e.preventDefault(); // タップのあとに来るマウスの真似イベントを止める
    gesture(dx, dy, t.clientX, e.target, 30);
  });
  stage.addEventListener('touchcancel', () => { touch = null; });

  $('next').addEventListener('click', next);
  $('prev').addEventListener('click', prev);
  $('restart').addEventListener('click', () => goTo('first'));
  $('end-back').addEventListener('click', () => showEnd(false));
  const fsBtn = $('fullscreen');
  if (document.fullscreenEnabled) {
    fsBtn.addEventListener('click', () => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()).catch(() => {}));
  } else fsBtn.hidden = true;

  // マウスで読む画面では、バーはページに重ねて出し入れする。
  // 上端（めくる表示では下端も）にマウスを寄せると出て、離れて 2.5 秒経つと隠れる
  if (hasMouse) {
    app.classList.add('autohide');
    let idle = 0, overBar = false;
    const hideLater = () => {
      clearTimeout(idle);
      idle = setTimeout(() => { if (!overBar && !state.ended && menu.hidden) toggleUi(false); }, 2500);
    };
    document.querySelectorAll('.bar').forEach(bar => {
      bar.addEventListener('mouseenter', () => { overBar = true; clearTimeout(idle); });
      bar.addEventListener('mouseleave', () => { overBar = false; hideLater(); });
    });
    document.addEventListener('mousemove', e => {
      const nearBottom = !isFlow() && e.clientY > window.innerHeight - 120;
      if (e.clientY < 80 || nearBottom) { toggleUi(true); hideLater(); }
    });
    menu.addEventListener('mouseleave', hideLater);
    hideLater(); // 開いた直後はバーを見せて、どこで操作するかを知らせる
  }

  let resizeTimer = 0, lastNarrow = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      // 縦につなげる表示のまま幅だけ変わったときは、組み直さない（ブラウザが自然に並べ直す）
      if (isFlow() && lastNarrow === false) { onFlowScroll(); return; }
      lastNarrow = isNarrow();
      relayout();
    }, 120);
  });

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
      state.mode = storage.get(MODE_KEY) === 'spread' ? 'spread' : 'auto';

      const epTitle = F(state.ep, 'title');
      $('title').textContent = T.readerTitle(state.ep.number, epTitle);
      $('end').querySelector('.end-sub').textContent = T.endSub(state.ep.number, epTitle);
      // 「おわり」の X で感想を書く：話の題名と、この話の URL（ページ番号は付けない）
      const shareText = T.shareText(state.ep.number, epTitle);
      $('share-x').href = `https://x.com/intent/post?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(location.href.split('#')[0])}`;
      // 次に公開されている話があれば、「おわり」のいちばん上に「次の話へ」を出す（感想ボタンは控えめに）
      const nextEp = data.episodes.filter(e => e.pages && e.pages.length && e.number > state.ep.number).sort((a, b) => a.number - b.number)[0];
      if (nextEp) {
        const a = document.createElement('a');
        a.className = 'btn btn-primary';
        a.href = link(`${BASE}ep/${nextEp.id}/`);
        a.textContent = T.nextEp(nextEp.number, F(nextEp, 'title'));
        $('share-x').className = 'btn btn-ghost';
        $('end').querySelector('.end-actions').prepend(a);
      }
      document.title = T.docTitle(state.ep.number, epTitle, F(data.series, 'title'));
      await loadScript();

      lastNarrow = isNarrow();
      relayout(pageFromHash() ?? 0);
      app.classList.add('is-ready');
      // 開いたまま #p=5 のリンクを踏んだときも、そのページへ飛ぶ
      window.addEventListener('hashchange', () => {
        const page = pageFromHash();
        if (page !== null && page !== currentPage()) relayout(page);
      });
    } catch {
      $('error').hidden = false;
    }
  }
  start();
})();
