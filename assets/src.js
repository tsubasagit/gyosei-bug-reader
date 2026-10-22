/* 媒体別の流入を数えるための小さな仕掛け。
   リンクに ?src=pixiv のような印が付いていたら、Cloudflare Web Analytics に「_src/pixiv/」というページ表示を1回だけ送り、
   アドレスをすぐ元に戻す（history.back）。Cloudflare の「パス」の表に、媒体ごとの訪問が並ぶ（見た目は何も変わらない） */
(function () {
  try {
    var q = new URLSearchParams(location.search);
    var s = (q.get('src') || '').toLowerCase().replace(/[^a-z0-9_-]/g, '').slice(0, 20);
    if (!s) return;
    var key = 'gb_src_sent';
    try { if (sessionStorage.getItem(key) === s) return; sessionStorage.setItem(key, s); } catch (e) {}
    var orig = location.pathname + location.search + location.hash;
    var root = location.pathname.replace(/(\/en)?(\/ep\/[^\/]+)?\/?$/, '/');
    // Cloudflare の計測は pushState を拾うので、いったん別のアドレスへ進めて、すぐ戻る（履歴は元どおりになる）
    var at = history.length;
    history.pushState(null, '', root + '_src/' + s + '/');
    setTimeout(function () {
      if (location.pathname.indexOf('/_src/') !== -1) history.back();
      setTimeout(function () { if (location.pathname + location.search + location.hash !== orig) history.replaceState(history.state, '', orig); }, 300);
    }, 500);
  } catch (e) {}
})();
