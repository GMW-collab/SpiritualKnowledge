/* Harkhowal Online. One script, no dependencies.
   - A persistent audio player that keeps playing while you move between pages
     (links are followed in-page; every page also works fully without this script).
   - Components found by data-attributes, initialised on each page: video facades,
     continue-listening, series order, filters, theme chips, the theme map, search, review. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var BASE = document.body.getAttribute("data-base") || "/";
  var AUDIO_BASE = document.body.getAttribute("data-audio-base") || "";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function fdate(d) { if (!d) return ""; var p = d.split("-"); return +p[2] + " " + MONTHS[+p[1] - 1] + " " + p[0]; }
  function clock(s) { s = Math.max(0, Math.floor(s || 0)); var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(x).padStart(2, "0"); }
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    clear: function () { try { Object.keys(localStorage).forEach(function (k) { if (/^(pos:|recent|last|speed)/.test(k)) localStorage.removeItem(k); }); } catch (e) {} }
  };

  /* Same folding as scripts/knowledge.py fold(): lower-case, Gurmukhi variants folded, words only. */
  var FOLD = { "ਸ਼": "ਸ", "ਖ਼": "ਖ", "ਗ਼": "ਗ", "ਜ਼": "ਜ", "ਫ਼": "ਫ", "ਲ਼": "ਲ", "ੰ": "ਂ", "਼": "", "ੱ": "", "ੑ": "" };
  function fold(t) {
    t = (t || "").normalize("NFC").toLowerCase().replace(/[ਸ਼ਖ਼ਗ਼ਜ਼ਫ਼ਲ਼ੰ਼ੱੑ]/g, function (c) { return FOLD[c]; });
    return t.split(/[^਀-੿a-z0-9]+/).filter(Boolean).join(" ");
  }
  window.HK = { fold: fold };

  /* ------------------------------------------------------------ player */
  var A = $("audio"), Q = { list: [], cur: null }, SPEEDS = [1, 1.25, 1.5, 0.75], sp = store.get("speed", 1);
  function enc(p) { return p.split("/").map(function (x) { return encodeURIComponent(x).replace(/\(/g, "%28").replace(/\)/g, "%29"); }).join("/"); }
  function trackFrom(node) { return { p: node.dataset.p, t: node.dataset.t, s: node.dataset.s, sg: node.dataset.sg || "", sid: node.dataset.sid, d: node.dataset.d || "" }; }
  function queueFor(node) {
    var scope = node.closest("[data-queue]") || node.parentNode;
    return [].map.call(scope.querySelectorAll("[data-p]"), trackFrom);
  }
  function play(t, list, keepPaused) {
    Q.list = list && list.length ? list : [t]; Q.cur = t;
    $("p-err").hidden = true;
    A.src = AUDIO_BASE + enc(t.p); A.playbackRate = sp;
    var pos = store.get("pos:" + t.p, null);
    A.addEventListener("loadedmetadata", function () { if (pos && pos.t && pos.t < pos.d - 20) A.currentTime = pos.t; A.playbackRate = sp; }, { once: true });
    if (!keepPaused) A.play().catch(function () {});
    $("player").hidden = false; document.body.classList.add("playing");
    $("p-title").textContent = t.t; $("p-series").textContent = t.s;
    $("p-mark").textContent = t.sg || "ਕਥਾ"; $("p-series-link").href = BASE + "listen/" + t.sid + "/";
    var rec = store.get("recent", []).filter(function (r) { return r.p !== t.p; }); rec.unshift(t); store.set("recent", rec.slice(0, 12)); store.set("last", t);
    if ("mediaSession" in navigator) { try { navigator.mediaSession.metadata = new MediaMetadata({ title: t.t, artist: "Sant Baba Jagjit Singh Ji Harkhowal Wale", album: t.s }); } catch (e) {} }
    refresh();
  }
  function toggle() { if (!Q.cur) return; if (A.paused) A.play().catch(function () {}); else A.pause(); }
  function step(d) { if (!Q.cur) return; var i = Q.list.map(function (x) { return x.p; }).indexOf(Q.cur.p) + d; if (i >= 0 && i < Q.list.length) play(Q.list[i], Q.list); }
  function refresh() {
    var playing = Q.cur && !A.paused;
    $("p-play").querySelector("use").setAttribute("href", playing ? "#i-pause" : "#i-play");
    $("p-play").setAttribute("aria-label", playing ? "Pause" : "Play");
    document.querySelectorAll("#main .row[data-p]").forEach(function (r) {
      var on = Q.cur && r.dataset.p === Q.cur.p; r.classList.toggle("on", !!on);
      r.setAttribute("aria-pressed", on && playing ? "true" : "false");
      var u = r.querySelector(".pp use"); if (u) u.setAttribute("href", on && playing ? "#i-pause" : "#i-play");
      var pos = store.get("pos:" + r.dataset.p, null), bar = r.querySelector(".bar");
      if (bar && pos && pos.d && pos.t > 5) { bar.hidden = false; bar.firstChild.style.width = Math.min(100, pos.t / pos.d * 100) + "%"; }
    });
  }
  A.addEventListener("play", refresh); A.addEventListener("pause", refresh);
  A.addEventListener("ended", function () { if (Q.cur) store.set("pos:" + Q.cur.p, { t: 0, d: A.duration, at: Date.now() }); step(1); });
  var lastSave = 0, dragging = false;
  A.addEventListener("timeupdate", function () {
    var d = A.duration || 0, t = A.currentTime || 0;
    $("p-cur").textContent = clock(t); $("p-dur").textContent = clock(d);
    if (d && !dragging) $("p-seek").value = Math.round(t / d * 1000);
    $("p-mini").style.width = (d ? t / d * 100 : 0) + "%";
    if (Q.cur && d && Date.now() - lastSave > 5000) { lastSave = Date.now(); store.set("pos:" + Q.cur.p, { t: t, d: d, at: Date.now() }); }
  });
  A.addEventListener("error", function () { if (Q.cur && A.getAttribute("src")) { var m = $("p-err"); m.hidden = false; m.textContent = "This recording could not be loaded from Gurmatveechar. Try the next one, or check your connection."; } });
  $("p-seek").addEventListener("input", function () { dragging = true; if (A.duration) $("p-cur").textContent = clock(this.value / 1000 * A.duration); });
  $("p-seek").addEventListener("change", function () { if (A.duration) A.currentTime = this.value / 1000 * A.duration; dragging = false; });
  $("p-play").onclick = toggle; $("p-next").onclick = function () { step(1); };
  $("p-prev").onclick = function () { if (A.currentTime > 5) A.currentTime = 0; else step(-1); };
  $("p-back").onclick = function () { A.currentTime = Math.max(0, A.currentTime - 15); };
  $("p-fwd").onclick = function () { A.currentTime = Math.min(A.duration || 0, A.currentTime + 30); };
  function showSpeed() { $("p-speed").textContent = String(sp).replace(/^0/, "") + "×"; } showSpeed();
  $("p-speed").onclick = function () { sp = SPEEDS[(SPEEDS.indexOf(sp) + 1) % SPEEDS.length]; A.playbackRate = sp; store.set("speed", sp); showSpeed(); };
  $("p-close").onclick = function () { A.pause(); $("player").hidden = true; $("player").classList.remove("open"); document.body.classList.remove("playing"); };
  $("p-np").onclick = function () { if (matchMedia("(max-width:900px)").matches) $("player").classList.toggle("open"); else if (Q.cur) go(BASE + "listen/" + Q.cur.sid + "/"); };
  if ("mediaSession" in navigator) { try {
    navigator.mediaSession.setActionHandler("play", function () { A.play(); }); navigator.mediaSession.setActionHandler("pause", function () { A.pause(); });
    navigator.mediaSession.setActionHandler("previoustrack", function () { step(-1); }); navigator.mediaSession.setActionHandler("nexttrack", function () { step(1); });
    navigator.mediaSession.setActionHandler("seekbackward", function () { A.currentTime = Math.max(0, A.currentTime - 15); });
    navigator.mediaSession.setActionHandler("seekforward", function () { A.currentTime += 30; });
  } catch (e) {} }
  document.addEventListener("keydown", function (ev) {
    var typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    if (ev.key === "Escape" && $("player").classList.contains("open")) $("player").classList.remove("open");
    else if (ev.key === "/" && !typing) { var q = $("hq"); if (q) { ev.preventDefault(); q.focus(); } }
    else if (ev.key === " " && !typing && Q.cur && !/BUTTON|A|SUMMARY/.test(document.activeElement.tagName)) { ev.preventDefault(); toggle(); }
  });
  (function restore() { var t = store.get("last", null); if (t && t.p && t.sid) play(t, [t], true); })();

  document.addEventListener("click", function (ev) {
    var r = ev.target.closest("[data-p]");
    if (r && r.closest("#main")) { ev.preventDefault(); var t = trackFrom(r); if (Q.cur && Q.cur.p === t.p) toggle(); else play(t, queueFor(r)); }
  });

  /* ------------------------------------------------------------ in-page navigation (keeps audio playing) */
  function sameSite(a) {
    if (!a || a.target || a.hasAttribute("download") || a.origin !== location.origin) return false;
    if (a.pathname.indexOf(BASE) !== 0 || /\.(json|xml|txt|mp3|pdf)$/i.test(a.pathname)) return false;
    return !(a.pathname === location.pathname && a.hash);
  }
  var loading = null;
  function go(url, push) {
    if (loading) loading.abort && loading.abort();
    var ctl = window.AbortController ? new AbortController() : null; loading = ctl;
    fetch(url, ctl ? { signal: ctl.signal } : {}).then(function (r) { if (!r.ok && r.status !== 404) throw 0; return r.text(); }).then(function (txt) {
      var doc = new DOMParser().parseFromString(txt, "text/html"), main = doc.getElementById("main");
      if (!main) throw 0;
      document.getElementById("main").replaceWith(main);
      document.title = doc.title;
      ["description", "robots"].forEach(function (n) { var a = doc.querySelector('meta[name="' + n + '"]'), b = document.querySelector('meta[name="' + n + '"]'); if (b) b.remove(); if (a) document.head.appendChild(a.cloneNode()); });
      var nav = doc.querySelector(".top nav"); if (nav) document.querySelector(".top nav").innerHTML = nav.innerHTML;
      if (push !== false) history.pushState({}, "", url);
      var h = location.hash && document.getElementById(location.hash.slice(1));
      if (h) h.scrollIntoView(); else window.scrollTo(0, 0);
      main.focus({ preventScroll: true });
      init(main);
    }).catch(function (err) { if (err && err.name === "AbortError") return; location.href = url; });
  }
  document.addEventListener("click", function (ev) {
    if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var a = ev.target.closest("a[href]");
    if (a && sameSite(a)) { ev.preventDefault(); go(a.href); }
  });
  window.addEventListener("popstate", function () { go(location.href, false); });
  var hs = document.querySelector(".hsearch");
  if (hs) hs.addEventListener("submit", function (ev) { ev.preventDefault(); var q = $("hq").value.trim(); go(BASE + "search/?q=" + encodeURIComponent(q)); $("hq").blur(); });

  /* ------------------------------------------------------------ components */
  function embed(target, id, title) {
    var f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0";
    f.title = title || "YouTube video"; f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen"; f.allowFullscreen = true;
    target.replaceWith(f); if (!A.paused) A.pause();
  }
  function initVideos(root) {
    root.querySelectorAll("[data-video]").forEach(function (b) { b.onclick = function () { embed(b, b.dataset.video, b.getAttribute("aria-label")); }; });
    root.querySelectorAll("[data-video-target]").forEach(function (b) { b.onclick = function () { var t = $(b.dataset.videoTarget), th = t && t.querySelector("[data-video]"); if (th) { th.click(); t.scrollIntoView({ block: "center" }); } }; });
  }
  function rowFor(t) {
    var b = el("button", "row"); b.type = "button";
    ["p", "t", "s", "sg", "sid", "d"].forEach(function (k) { b.dataset[k] = t[k] || ""; });
    var pp = el("span", "pp"); pp.innerHTML = '<svg><use href="#i-play"/></svg>'; b.appendChild(pp);
    var tx = el("span", "t"); tx.appendChild(el("b", null, t.t)); tx.appendChild(el("span", null, t.s));
    var bar = el("i", "bar"); bar.hidden = true; bar.appendChild(el("i")); tx.appendChild(bar); b.appendChild(tx); b.appendChild(el("span", "d", t.d ? fdate(t.d) : ""));
    return b;
  }
  function initContinue(root) {
    root.querySelectorAll("[data-continue]").forEach(function (box) {
      var rec = store.get("recent", []).filter(function (t) { var x = store.get("pos:" + t.p, null); return t && t.p && x && x.d && x.t > 5 && x.t < x.d - 20; }).slice(0, 4);
      var rows = box.querySelector(".rows"); rows.textContent = ""; box.hidden = !rec.length; box.setAttribute("data-queue", "");
      rec.forEach(function (t) { rows.appendChild(rowFor(t)); });
    });
  }
  function initSeries(root) {
    root.querySelectorAll("[data-series]").forEach(function (box) {
      var rows = box.querySelector(".rows"), original = [].slice.call(rows.children);
      box.querySelectorAll("[data-order]").forEach(function (b) {
        b.onclick = function () {
          box.querySelectorAll("[data-order]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
          var list = original.slice();
          if (b.dataset.order === "new") list = list.filter(function (n) { return n.dataset.p; }).sort(function (a, c) { return (c.dataset.d || "").localeCompare(a.dataset.d || ""); });
          rows.textContent = ""; list.forEach(function (n) { rows.appendChild(n); });
        };
      });
      var aj = box.querySelector("[data-angjump]");
      if (aj) aj.onsubmit = function (ev) {
        ev.preventDefault(); var n = +aj.querySelector("input").value, msg = aj.querySelector(".angmsg");
        var hit = [].filter.call(rows.querySelectorAll("[data-a1]"), function (r) { return +r.dataset.a1 <= n && n <= +r.dataset.a2; })[0];
        if (!hit) { msg.textContent = n ? "No recording here is titled with Ang " + n + "." : ""; return; }
        msg.textContent = ""; hit.scrollIntoView({ block: "center" }); hit.classList.add("flash"); hit.focus(); setTimeout(function () { hit.classList.remove("flash"); }, 2000);
      };
      var pb = box.querySelector("[data-play-series]");
      if (pb) {
        var all = function () { return [].map.call(rows.querySelectorAll("[data-p]"), trackFrom); };
        var resume = all().filter(function (t) { var x = store.get("pos:" + t.p, null); return x && x.d && x.t > 5 && x.t < x.d - 20; })
          .sort(function (a, b) { return (store.get("pos:" + b.p, {}).at || 0) - (store.get("pos:" + a.p, {}).at || 0); })[0];
        if (resume) pb.querySelector("span").textContent = "Resume: " + resume.t;
        pb.onclick = function () { var l = all(); if (resume) play(resume, l); else if (l[0]) play(l[0], l); };
      }
    });
  }
  function initFilter(root) {
    var inp = root.querySelector("[data-filter-input]"), scope = root.querySelector("[data-filter-scope]");
    if (!inp || !scope) return;
    inp.oninput = function () {
      var q = fold(inp.value);
      scope.querySelectorAll("[data-filter]").forEach(function (n) { n.hidden = !!q && n.dataset.filter.indexOf(q) < 0; });
      scope.querySelectorAll(".shelf").forEach(function (s) { s.hidden = !s.querySelector("[data-filter]:not([hidden])"); });
    };
  }
  function initChips(root) {
    var grid = root.querySelector("[data-video-grid]"); if (!grid) return;
    var chips = root.querySelectorAll("[data-theme-chip]");
    function apply(slug) {
      chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c.dataset.themeChip === slug)); });
      grid.querySelectorAll("[data-themes]").forEach(function (c) { c.hidden = !!slug && (" " + c.dataset.themes + " ").indexOf(" " + slug + " ") < 0; });
    }
    chips.forEach(function (c) { c.onclick = function () { var on = c.getAttribute("aria-pressed") === "true"; apply(on ? "" : c.dataset.themeChip); }; });
    var p = new URLSearchParams(location.search).get("theme"); if (p) apply(p);
  }
  function initMap(root) {
    root.querySelectorAll(".constellation").forEach(function (svg) {
      svg.querySelectorAll(".node").forEach(function (n) {
        function on() { var s = n.dataset.slug; svg.classList.add("hl");
          svg.querySelectorAll(".edge").forEach(function (e) { var hit = e.dataset.a === s || e.dataset.b === s; e.classList.toggle("hl", hit); if (hit) { svg.querySelector('[data-slug="' + (e.dataset.a === s ? e.dataset.b : e.dataset.a) + '"]').classList.add("hl"); } });
          n.classList.add("hl"); }
        function off() { svg.classList.remove("hl"); svg.querySelectorAll(".hl").forEach(function (x) { x.classList.remove("hl"); }); }
        n.addEventListener("mouseenter", on); n.addEventListener("focus", on); n.addEventListener("mouseleave", off); n.addEventListener("blur", off);
      });
    });
  }
  function initRail(root) {
    var links = root.querySelectorAll(".rail a[href^='#']"); if (!links.length || !window.IntersectionObserver) return;
    var io = new IntersectionObserver(function (es) { es.forEach(function (en) { if (en.isIntersecting) links.forEach(function (a) { a.classList.toggle("cur", a.getAttribute("href") === "#" + en.target.id); }); }); }, { rootMargin: "-30% 0px -60% 0px" });
    links.forEach(function (a) { var s = root.querySelector(a.getAttribute("href")); if (s) io.observe(s); });
  }
  function initForget(root) {
    var b = root.querySelector("[data-forget]"); if (!b) return;
    b.onclick = function () { store.clear(); b.textContent = "Listening history forgotten on this device"; b.disabled = true; };
  }

  /* ------------------------------------------------------------ search */
  var INDEX = null;
  function loadIndex(src) { return INDEX ? Promise.resolve(INDEX) : fetch(src).then(function (r) { return r.json(); }).then(function (d) { INDEX = d; return d; }); }
  function search(d, raw, kind) {
    var q = fold(raw); if (q.length < 2) return null;
    var words = q.split(" "), nospace = q.replace(/ /g, "");
    // themes the query names, in any language (ego -> haumai, ਹੰਕਾਰ -> haumai)
    var hitThemes = Object.keys(d.themes).filter(function (s) { return d.themes[s].some(function (term) { return term && (term === q || (q.length > 2 && term.indexOf(q) === 0) || (term.length > 3 && q.indexOf(term) >= 0)); }); });
    var res = [];
    d.items.forEach(function (it) {
      if (kind && it[0] !== kind) return;
      var text = it[4], score = 0;
      if (words.every(function (w) { return text.indexOf(w) >= 0; })) score = 10 + (text.indexOf(q) >= 0 ? 5 : 0);
      else if (nospace.length > 3 && text.replace(/ /g, "").indexOf(nospace) >= 0) score = 8;
      var th = it[5] ? it[5].split(" ") : [], via = null;
      hitThemes.forEach(function (s) { if (th.indexOf(s) >= 0) { if (!score) via = s; score = Math.max(score, 4) + 2; } });
      if (it[0] === "theme" && hitThemes.indexOf(th[0]) >= 0) score += 40;
      if (it[0] === "theme") score += 6; else if (it[0] === "series") score += 3;
      if (score > 6 || (score && it[0] !== "rec")) res.push({ it: it, score: score, via: via });
    });
    res.sort(function (a, b) { return b.score - a.score || ((b.it[6] && b.it[6].d) || "").localeCompare((a.it[6] && a.it[6].d) || ""); });
    return { res: res, themes: hitThemes };
  }
  function initSearch(root) {
    var box = root.querySelector("[data-search]"); if (!box) return;
    var inp = root.querySelector("#sq"), kind = "", form = root.querySelector("[data-search-form]");
    var q0 = new URLSearchParams(location.search).get("q") || ""; inp.value = q0;
    var hint = box.innerHTML;
    function render() {
      var q = inp.value.trim();
      history.replaceState({}, "", location.pathname + (q ? "?q=" + encodeURIComponent(q) : ""));
      loadIndex(box.dataset.src).then(function (d) {
        var r = search(d, q, kind); box.textContent = "";
        if (!r) { box.innerHTML = hint; return; }
        if (!r.res.length) { box.appendChild(el("p", "hint", "Nothing matches ‘" + q + "’. Try a shorter word, a different spelling, or the same idea in Gurmukhi or English.")); return; }
        var groups = { theme: "Themes", series: "Series and texts", video: "Videos", rec: "Recordings", external: "From other teachers and makers", page: "Pages" };
        Object.keys(groups).forEach(function (g) {
          var list = r.res.filter(function (x) { return x.it[0] === g; }); if (!list.length) return;
          var lim = g === "rec" ? 40 : 12;
          box.appendChild(el("h2", null, groups[g] + (list.length > lim ? " (" + lim + " of " + list.length + ")" : "")));
          var wrap = el("div", g === "rec" ? "rows" : null); if (g === "rec") wrap.setAttribute("data-queue", "");
          list.slice(0, lim).forEach(function (x) {
            var it = x.it;
            if (g === "theme") { var a = el("a", "res-theme"); a.href = it[3]; var s = el("span", "g", it[6]); s.lang = "pa"; a.appendChild(s); a.appendChild(el("b", null, it[1])); a.appendChild(el("span", null, it[2])); wrap.appendChild(a); }
            else if (g === "rec") { var m = it[6]; wrap.appendChild(rowFor({ p: m.p, t: it[1], s: it[2], sg: m.sg, sid: m.sid, d: m.d })); }
            else { var l = el("a", "res-link"); l.href = it[3]; if (/^https?:/.test(it[3]) && it[3].indexOf(location.origin) !== 0) { l.target = "_blank"; l.rel = "noopener"; } l.appendChild(el("b", null, it[1])); l.appendChild(el("span", null, it[2])); wrap.appendChild(l); }
          });
          box.appendChild(wrap);
        });
        if (r.themes.length) box.appendChild(el("p", "via", "Results include items linked to the theme" + (r.themes.length > 1 ? "s " : " ") + r.themes.map(function (s) { return d.names[s][0]; }).join(", ") + ", which your search names."));
        refresh();
      });
    }
    var tm; inp.oninput = function () { clearTimeout(tm); tm = setTimeout(render, 140); };
    form.onsubmit = function (ev) { ev.preventDefault(); render(); };
    root.querySelectorAll("[data-kind]").forEach(function (c) { c.onclick = function () { kind = c.dataset.kind; root.querySelectorAll("[data-kind]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === c)); }); render(); }; });
    if (q0) render(); inp.focus();
  }

  /* ------------------------------------------------------------ editorial review */
  function initReview(root) {
    var box = root.querySelector("[data-review]"); if (!box) return;
    fetch(box.dataset.src).then(function (r) { return r.json(); }).then(function (d) {
      var ov = JSON.parse(JSON.stringify(d.overrides || {}));
      ["theme_add", "theme_remove", "theme_confirmed", "theme_review"].forEach(function (k) { ov[k] = ov[k] || {}; });
      ["approve", "reject", "gurbani_confirmed"].forEach(function (k) { ov[k] = ov[k] || []; });
      box.textContent = "";
      var out = el("textarea"); out.readOnly = true; out.setAttribute("aria-label", "Updated overrides.json");
      function sync() { out.value = JSON.stringify(ov, null, 2); }
      function addTo(map, id, slug, on) { var l = map[id] = map[id] || []; var i = l.indexOf(slug); if (on && i < 0) l.push(slug); if (!on && i >= 0) l.splice(i, 1); if (!l.length) delete map[id]; sync(); }
      function sec(title, intro) { var s = el("section"); s.appendChild(el("h2", null, title)); if (intro) s.appendChild(el("p", "sub", intro)); box.appendChild(s); return s; }

      var s1 = sec("Sources", "From the last automatic run.");
      var t = el("table"); t.innerHTML = "<thead><tr><th>Source</th><th>State</th><th>Message</th><th>Last success</th></tr></thead>";
      var tb = el("tbody"); (d.sources || []).forEach(function (src) { var st = (d.sync.sources || {})[src.id] || {}; var tr = el("tr");
        [src.title, st.state || src.state || "not run", st.message || src.note || "", (st.last_success || "").slice(0, 10)].forEach(function (v, i) { var td = el("td", i === 1 ? (/ok|partial/.test(v) ? "ok" : /fail|kept/.test(v) ? "bad" : "") : null, v); tr.appendChild(td); }); tb.appendChild(tr); });
      t.appendChild(tb); s1.appendChild(t);

      var s2 = sec("Gurbani checks", "Lines are checked daily against BaniDB. A line that failed its check is hidden until the text or Ang is corrected in content/gurbani.json. Confirm a line by hand only after checking it in a printed saroop or a trusted source.");
      var t2 = el("table"); t2.innerHTML = "<thead><tr><th>Line</th><th>Ang</th><th>State</th><th>Shown</th><th></th></tr></thead>"; var tb2 = el("tbody");
      d.gurbani.forEach(function (g) { var tr = el("tr"); var c = el("td"); var s = el("span", "g", g.gurmukhi); s.lang = "pa"; c.appendChild(s); c.appendChild(el("div", "sub", g.id + (g.reason ? ": " + g.reason : ""))); tr.appendChild(c);
        tr.appendChild(el("td", null, g.ang || "")); tr.appendChild(el("td", g.state === "failed-check" ? "bad" : g.state === "verified" ? "ok" : null, g.state)); tr.appendChild(el("td", null, g.shown ? "yes" : "no"));
        var td = el("td"); if (g.state !== "verified") { var lb = el("label"); var cb = el("input"); cb.type = "checkbox"; cb.checked = ov.gurbani_confirmed.indexOf(g.id) >= 0;
          cb.onchange = function () { var i = ov.gurbani_confirmed.indexOf(g.id); if (cb.checked && i < 0) ov.gurbani_confirmed.push(g.id); if (!cb.checked && i >= 0) ov.gurbani_confirmed.splice(i, 1); sync(); };
          lb.appendChild(cb); lb.appendChild(document.createTextNode("Confirmed by hand")); td.appendChild(lb); } tr.appendChild(td); tb2.appendChild(tr); });
      t2.appendChild(tb2); s2.appendChild(t2);

      var s3 = sec("Theme essays", "Each essay is an AI-assisted draft until a learned reader has reviewed it. Record the review here.");
      d.themes.forEach(function (th) { var row = el("div"); row.style.padding = "8px 0";
        var lab = el("b", null, th.title + " "); row.appendChild(lab);
        var cur = ov.theme_review[th.slug] || {}; var sel = el("select"); ["awaiting-review", "reviewed", "needs-changes"].forEach(function (v) { var o = el("option", null, v); o.value = v; if ((cur.status || th.review.status) === v) o.selected = true; sel.appendChild(o); });
        var who = el("input"); who.placeholder = "Reviewer's name"; who.value = cur.reviewer || ""; who.style.marginLeft = "8px";
        function upd() { if (sel.value === "awaiting-review" && !who.value) delete ov.theme_review[th.slug]; else ov.theme_review[th.slug] = { status: sel.value, reviewer: who.value, date: new Date().toISOString().slice(0, 10) }; sync(); }
        sel.onchange = upd; who.onchange = upd; row.appendChild(sel); row.appendChild(who); s3.appendChild(row); });

      var s4 = sec("Automatic theme links", "Made from titles. Untick a link to remove it; tick ‘confirmed’ once you have checked it.");
      d.themes.forEach(function (th) { var list = d.auto[th.slug] || []; var det = el("details"); det.appendChild(el("summary", null, th.title + " (" + list.length + ")"));
        list.slice(0, 400).forEach(function (it) { var lb = el("label"); var keep = el("input"); keep.type = "checkbox"; keep.checked = !((ov.theme_remove[it.id] || []).indexOf(th.slug) >= 0);
          keep.onchange = function () { addTo(ov.theme_remove, it.id, th.slug, !keep.checked); };
          var conf = el("input"); conf.type = "checkbox"; conf.checked = it.confirmed; conf.title = "Confirmed";
          conf.onchange = function () { addTo(ov.theme_confirmed, it.id, th.slug, conf.checked); };
          lb.appendChild(keep); var a = el("a", null, it.kind + ": " + it.title); a.href = it.url; a.target = "_blank"; lb.appendChild(a); lb.appendChild(el("span", "sub", " (" + it.via + ") ")); lb.appendChild(conf); lb.appendChild(el("span", "sub", "confirmed")); det.appendChild(lb); });
        s4.appendChild(det); });

      var s5 = sec("Videos with no theme", "Add a theme to any recent video its title did not reveal.");
      d.untagged.forEach(function (v) { var lb = el("label"); var sel = el("select"); sel.appendChild(el("option", null, "Add a theme…"));
        d.themes.forEach(function (th) { var o = el("option", null, th.title); o.value = th.slug; sel.appendChild(o); });
        sel.onchange = function () { if (sel.value) addTo(ov.theme_add, v.id, sel.value, true); };
        lb.appendChild(sel); lb.appendChild(document.createTextNode(" " + v.title + " (" + v.date + ")")); s5.appendChild(lb); });

      var s6 = sec("Imported items awaiting approval", d.pending.length ? "From connected feeds. Nothing here is public until approved." : "No feed items are waiting. Connect a feed in config.json to import material from other sources.");
      d.pending.forEach(function (p) { var lb = el("label"); var sel = el("select"); ["", "approve", "reject"].forEach(function (v) { var o = el("option", null, v || "Decide…"); o.value = v; sel.appendChild(o); });
        sel.onchange = function () { ["approve", "reject"].forEach(function (k) { var i = ov[k].indexOf(p.id); if (i >= 0) ov[k].splice(i, 1); }); if (sel.value) ov[sel.value].push(p.id); sync(); };
        lb.appendChild(sel); var a = el("a", null, p.title); a.href = p.link; a.target = "_blank"; a.rel = "noopener"; lb.appendChild(a); lb.appendChild(el("span", "sub", " " + p.feed + ", " + p.date)); s6.appendChild(lb); });

      var s7 = sec("Save your changes", "Copy this text, open overrides.json on GitHub, replace its contents and commit. The site rebuilds within a few minutes.");
      sync(); s7.appendChild(out);
      var bar = el("p"); var cp = el("button", "btn plain", "Copy"); cp.type = "button";
      cp.onclick = function () { out.select(); try { navigator.clipboard.writeText(out.value).then(function () { cp.textContent = "Copied"; }); } catch (e) { document.execCommand("copy"); } };
      var ed = el("a", "btn sun", "Open overrides.json on GitHub"); ed.href = d.edit_url; ed.target = "_blank"; ed.rel = "noopener"; ed.style.marginLeft = "10px";
      bar.appendChild(cp); bar.appendChild(ed); s7.appendChild(bar);
    }).catch(function () { box.textContent = "The review queue could not be loaded."; });
  }

  function init(root) {
    initVideos(root); initContinue(root); initSeries(root); initFilter(root); initChips(root);
    initMap(root); initRail(root); initForget(root); initSearch(root); initReview(root); refresh();
  }
  init(document.getElementById("main"));
})();
