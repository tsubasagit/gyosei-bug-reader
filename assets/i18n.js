// 表示する言語を決めて、英語のときだけ文言を差し替える。
// - 日本語が標準。`?lang=en` を付けると英語になり、選んだ言語はこのブラウザに覚える
// - HTML に書いてある日本語はそのまま。英語のときだけ data-i18n の印を頼りに置き換える
// - top.js / reader.js が作る文言は I18N.t の辞書から取る
// このファイルは top.js・reader.js より先に読み込む。
(() => {
  'use strict';
  const KEY = 'gyosei-lang';
  const SUPPORTED = ['ja', 'en'];

  const asked = new URLSearchParams(location.search).get('lang');
  let lang = 'ja';
  if (SUPPORTED.includes(asked)) {
    lang = asked;
    try { localStorage.setItem(KEY, lang); } catch { /* 覚えられなくても動く */ }
  } else {
    try { const saved = localStorage.getItem(KEY); if (SUPPORTED.includes(saved)) lang = saved; } catch { /* 標準のまま */ }
  }
  const isEn = lang === 'en';

  // ---- 英語の文言（HTML に data-i18n="キー" を付けたところと対応する） ----------
  const EN = {
    'topbar.note': 'Tech and IT background for this comic comes from the <a href="https://apptalenthub.co.jp/category/column-posts/" target="_blank" rel="noopener">AppTalentHub column</a>.',

    'hero.coverAlt': 'Cover of City Hall Bug! Tetsu Genda, Rena Akamine, Shota Suzuki and Go Gotokuji.',
    'hero.kicker': 'Standalone chapters · city hall gag manga',
    'hero.logo': 'City Hall Bug!',
    'hero.logoSub': 'Nashigasaka City Hall, Special Trends Unit',
    'hero.catch': 'Selfish motives.<br>Citizens somehow helped.',
    'hero.lead': 'Tetsu Genda is a civil servant who wants money and an easy life. He crams public rules and new tech overnight — and strange solutions come out of the basement of City Hall.',
    'hero.ctaNote': 'Free · no sign-up · 11 pages',
    'hero.linkEpisodes': 'Chapters',
    'hero.linkStory': 'What is this?',
    'hero.linkChars': 'Characters',

    'ep.eyebrow': 'Pick the case that sounds fun',
    'ep.title': 'Chapters online',
    'ep.sortLabel': 'Sort order',
    'ep.loading': 'Loading…',
    'ep.noscript': 'Read <a href="ep/1/?lang=en">The Gym That Vanished in Seconds</a> / <a href="ep/3/?lang=en">We’ll Take the Problem Home</a> / <a href="ep/4/?lang=en">We’ll Invent a Local Specialty</a>',

    'story.eyebrow': 'Set one floor below City Hall',
    'story.title': 'Welcome to the Special Trends Unit',
    'story.lead1': 'In the basement of Nashigasaka City Hall sits a unit with no budget and no authority. Every time a citizen’s problem lands there, <strong>Tetsu Genda</strong> — a civil servant who thinks about nothing but money and naps — smells profit and starts moving.',
    'story.lead2': 'His methods are mostly outrageous. And yet the problems keep getting solved.',
    'story.point1': '<strong>About 5 minutes each</strong>Every chapter stands alone. Start anywhere.',
    'story.point2': '<strong>Laugh, learn one thing</strong>How public rules actually work, delivered inside the chaos.',
    'story.point3': '<strong>Free</strong>No account, no login.',

    'chara.eyebrow': 'Four difficult people',
    'chara.title': 'The team downstairs',
    'chara.tetsu.alt': 'Tetsu Genda, a man in a work vest holding a thick book, pointing at you with a grin.',
    'chara.tetsu.role': 'Lead · staff',
    'chara.tetsu.name': 'Tetsu Genda<small>38</small>',
    'chara.tetsu.line': '“This... this could be money!”',
    'chara.tetsu.desc': 'Driven entirely by cash and the urge to slack off. When he smells a profit he can learn any rule or any technology overnight. Helping people is a side effect.',
    'chara.rena.alt': 'Rena Akamine, a woman with long blonde hair holding up a palm to stop someone.',
    'chara.rena.role': 'Team leader · Tetsu’s boss',
    'chara.rena.name': 'Rena Akamine',
    'chara.rena.line': '“Tetsu. Is that actually legal?”',
    'chara.rena.desc': 'Logical, sharp, and the only person who tries to stop Tetsu. She is usually right, and usually one step too late.',
    'chara.shota.alt': 'Shota Suzuki, a high schooler in a white T-shirt showing the calculator on his phone.',
    'chara.shota.role': 'High-school part-timer',
    'chara.shota.name': 'Shota Suzuki<small>16</small>',
    'chara.shota.line': '“If it pays, I’ll do it. No overtime.”',
    'chara.shota.desc': 'Does the math before he does anything. He joins Tetsu’s schemes strictly by the numbers — and his refusal to work late is backed by actual labor law.',
    'chara.gotokuji.alt': 'Go Gotokuji, a man in glasses and a suit holding a giant approval stamp with a quiet smile.',
    'chara.gotokuji.role': 'Section chief',
    'chara.gotokuji.name': 'Go Gotokuji<small>46</small>',
    'chara.gotokuji.line': '“Genda. ...I mean, Mr. Genda.”',
    'chara.gotokuji.desc': 'Never raises his voice. The angrier he gets, the more polite he becomes, and the brighter his glasses shine. If he calls you “Mr.”, run.',

    'footer.credit1': 'This comic is produced with <strong>name-maker</strong>, an in-house tool by <a href="https://apptalenthub.co.jp/" target="_blank" rel="noopener">AppTalentHub</a> that carries a chapter from storyboard to finished pages.',
    'footer.credit2': 'Made at <a href="https://momosta.com/event/" target="_blank" rel="noopener">Momosta</a>, Okayama, summer 2026.',
    'footer.rapitAlt': 'Rapit, a white rabbit character in goggles, drawing a storyboard at a desk.',
    'footer.ctaLead': 'How is this comic drawn?',
    'footer.ctaBody': 'One line of premise comes back as panel layout, dialogue and a punchline. We wrote up how it works in <a href="https://apptalenthub.co.jp/case-posts/4525/" target="_blank" rel="noopener">What is name-maker?</a>',
    'footer.ctaArticle': 'What is name-maker?',
    'footer.ctaContact': 'Talk to us about your project',
    'footer.disclaimer': 'This is a work of fiction. Nashigasaka City is invented, and nothing here reflects the real operation of any person, organization or public office. It is not an official publication of any government body.',
    'footer.copy': '© 2026 AppTalentHub Inc.',

    'reader.back': '‹ Chapters',
    'reader.menuAria': 'Display options and how to read',
    'reader.menuTitle': 'Display',
    'reader.fullscreenAria': 'Read full screen',
    'reader.fullscreenTitle': 'Full screen',
    'reader.nextAria': 'Next page (← key)',
    'reader.next': '◀ Next',
    'reader.prevAria': 'Previous page (→ key)',
    'reader.prev': 'Back ▶',
    'reader.endTitle': 'The End',
    'reader.shareX': 'Post about it on X',
    'reader.seeChars': 'Meet the characters',
    'reader.toList': 'All chapters',
    'reader.restart': 'Read from the start',
    'reader.endBack': 'Back to the last page',
    'reader.error': 'The pages could not be loaded. Please try again in a little while.',
    'reader.noscript': 'JavaScript is required to read this page.',
  };

  // ---- top.js / reader.js が使う文言 ------------------------------------------
  const STR = {
    ja: {
      epCount: n => `公開中の${n}話。どの話からでも楽しめます。`,
      ctaFirst: n => (n === 1 ? '第1話から読む' : `第${n}話から読む`),
      latest: (n, title) => `最新話：第${n}話「${title}」`,
      pick: () => 'はじめてならここ',
      epNum: n => `第${n}話`,
      epSub: s => `～${s}～`,
      epMeta: (pages, date) => `${pages}ページ・${date} 公開`,
      readBtn: () => '読む ▶',
      sortAsc: () => '1話から',
      sortDesc: () => '新しい話から',
      listEmpty: () => 'まだ公開しているエピソードはありません。',
      listError: () => '一覧を読み込めませんでした。時間をおいて、もう一度開いてください。',
      thumbAlt: (n, title) => `第${n}話「${title}」の扉絵`,

      readerTitle: (n, title) => `第${n}話　${title}`,
      docTitle: (n, title, series) => `第${n}話「${title}」｜${series}`,
      coverLabel: () => '扉',
      pageAlt: (n, title, label) => `第${n}話「${title}」 ${label}`,
      coverAltPart: () => '扉絵',
      pageAltPart: label => `${label}ページ`,
      counter: (label, total) => `${label} / ${total}`,
      modeToSpread: () => '見開きで読む',
      modeToFlow: () => '縦につなげて読む',
      hintNarrow: () => '右へフリック・画面の左をタップで次のページ。真ん中をタップでメニュー',
      hintFlow: () => 'スクロールで読み進めます。← で次のページ、→ で前のページ',
      hintSpread: () => '← で次のページ、→ で前のページ。画面の左クリックでも次へ',
      shareText: (n, title) => `『行政バグります！』第${n}話「${title}」を読んだ #行政バグります`,
      nextEp: (n, title) => `次の話へ：第${n}話「${title}」`,
      endSub: (n, title) => `第${n}話「${title}」`,
      readMoreLabel: () => 'もっと深く知りたい人へ',
      readMoreNote: () => '解説記事を読む（別のページが開きます）',
      comingSoon: () => '近日公開',
      releaseOn: (m, d) => `${m}月${d}日ごろ公開予定`,
      xFollow: handle => `新しい話はXでお知らせします${handle ? `（${handle}）` : ''}　フォローする`,
      xFooter: () => 'Xで新しい話を受け取る',
      resume: () => '続きから読む',
      resumeFrom: (n, title, page) => `第${n}話「${title}」 ${page}ページ目から`,
      scriptTitle: () => '対訳',
      scriptToggle: () => '対訳を見る',
      langName: () => '日本語',
      otherLang: () => 'English',
    },
    en: {
      epCount: n => `${n} chapters online. Start with any of them.`,
      ctaFirst: n => `Start with chapter ${n}`,
      latest: (n, title) => `Latest: Ep. ${n} “${title}”`,
      pick: () => 'Start here',
      epNum: n => `Ep. ${n}`,
      epSub: s => `— ${s}`,
      epMeta: (pages, date) => `${pages} pages · published ${date}`,
      readBtn: () => 'Read ▶',
      sortAsc: () => 'Oldest first',
      sortDesc: () => 'Newest first',
      listEmpty: () => 'No chapters are online yet.',
      listError: () => 'The chapter list could not be loaded. Please try again in a little while.',
      thumbAlt: (n, title) => `Title page of Ep. ${n} “${title}”`,

      readerTitle: (n, title) => `Ep. ${n}  ${title}`,
      docTitle: (n, title, series) => `Ep. ${n} “${title}” | ${series}`,
      coverLabel: () => 'Title',
      pageAlt: (n, title, label) => `Ep. ${n} “${title}” ${label}`,
      coverAltPart: () => 'title page',
      pageAltPart: label => `page ${label}`,
      counter: (label, total) => `${label} / ${total}`,
      modeToSpread: () => 'Two-page spread',
      modeToFlow: () => 'Single column',
      hintNarrow: () => 'Swipe right or tap the left side for the next page. Tap the middle for this menu.',
      hintFlow: () => 'Scroll to read. ← for the next page, → to go back.',
      hintSpread: () => '← for the next page, → to go back. Clicking the left side also goes forward.',
      shareText: (n, title) => `Read “City Hall Bug!” Ep. ${n}: ${title}`,
      nextEp: (n, title) => `Next chapter: Ep. ${n} “${title}”`,
      endSub: (n, title) => `Ep. ${n} “${title}”`,
      readMoreLabel: () => 'Want to go deeper?',
      readMoreNote: () => 'Read the explainer (opens in a new page)',
      comingSoon: () => 'Coming soon',
      releaseOn: (m, d) => `Coming around ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1]} ${d}`,
      xFollow: handle => `New chapters are announced on X${handle ? ` (${handle})` : ''} \u2014 follow`,
      xFooter: () => 'Get new chapters on X',
      resume: () => 'Continue reading',
      resumeFrom: (n, title, page) => `Ep. ${n} \u201c${title}\u201d from page ${page}`,
      scriptTitle: () => 'English script',
      scriptToggle: () => 'Show the English script',
      langName: () => 'English',
      otherLang: () => '日本語',
    },
  };

  // episodes.json の項目を、いまの言語で読む（英語が無ければ日本語のまま）
  const field = (obj, name) => (isEn ? (obj[`${name}_en`] || obj[name]) : obj[name]);

  // 同じサイトの中のリンクに ?lang= を引き継ぐ
  function withLang(href) {
    if (!isEn || !href) return href;
    if (/^(https?:)?\/\//.test(href) || href.startsWith('mailto:')) return href;
    const [path, hash = ''] = href.split('#');
    if (!path) return href;                        // 「#characters」のような同じページの中のリンク
    const join = path.includes('?') ? '&' : '?';
    return `${path}${join}lang=en${hash ? '#' + hash : ''}`;
  }

  function localizeLinks(root = document) {
    if (!isEn) return;
    root.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href');
      if (/^(https?:)?\/\//.test(href) || href.startsWith('#') || href.includes('lang=')) return;
      a.setAttribute('href', withLang(href));
    });
  }

  // data-i18n="キー"（文字だけ）、data-i18n-html="キー"（リンクなどを含む文）、
  // data-i18n-attr="alt:キー, aria-label:キー"（属性）
  function apply(root = document) {
    if (!isEn) return;
    root.querySelectorAll('[data-i18n]').forEach(el => {
      const v = EN[el.dataset.i18n];
      if (v != null) el.textContent = v;
    });
    root.querySelectorAll('[data-i18n-html]').forEach(el => {
      const v = EN[el.dataset.i18nHtml];
      if (v != null) el.innerHTML = v;
    });
    root.querySelectorAll('[data-i18n-attr]').forEach(el => {
      el.dataset.i18nAttr.split(',').forEach(pair => {
        const [attr, key] = pair.split(':').map(s => s.trim());
        const v = EN[key];
        if (attr && v != null) el.setAttribute(attr, v);
      });
    });
    localizeLinks(root);
  }

  // 右上に言語の切り替えを出す
  function mountSwitch() {
    const a = document.createElement('a');
    a.className = 'lang-switch';
    a.textContent = STR[lang].otherLang();
    a.setAttribute('lang', isEn ? 'ja' : 'en');
    const url = new URL(location.href);
    url.searchParams.set('lang', isEn ? 'ja' : 'en');
    a.href = url.pathname + url.search + url.hash;
    a.title = isEn ? '日本語で読む' : 'Read in English';
    document.body.append(a);
  }

  window.I18N = { lang, isEn, t: STR[lang], field, withLang, apply, localizeLinks };

  document.documentElement.lang = lang;
  apply();
  mountSwitch();
})();
