#!/usr/bin/env python3
"""Build the static website into _site/.

  python scripts/build.py                 # base path "/" (for harkhowal.com)
  BASE_PATH=/SpiritualKnowledge/ python scripts/build.py   # for a project Pages URL

Standard library only. Reads content/ and data/; never touches the network.
"""
import hashlib
import html
import json
import os
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knowledge as K  # noqa: E402

ROOT = K.ROOT
OUT = Path(os.environ.get("OUT_DIR", ROOT / "_site"))
BASE = "/" + os.environ.get("BASE_PATH", "/").strip("/") + "/"
BASE = "/" if BASE == "//" else BASE
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SGGS = "sri-guru-granth-sahib-ji-di-lareevar-katha"

e = lambda s: html.escape(str(s or ""), quote=True)  # noqa: E731


def u(path=""):
    return BASE + path.lstrip("/")


def fdate(d):
    try:
        y, m, dd = d[:10].split("-")
        return f"{int(dd)} {MONTHS[int(m) - 1]} {y}"
    except Exception:
        return ""


# ------------------------------------------------------------------ light Markdown
def inline(s):
    s = e(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)",
               lambda m: f'<a href="{m.group(2) if m.group(2).startswith("http") else u(m.group(2))}">{m.group(1)}</a>', s)
    return s


def md(text, ctx=None):
    """Paragraphs, '- ' lists, '### ' headings, [[gurbani:id]] blocks and ':::' compare/tension blocks."""
    out, para, items = [], [], []
    lines = text.splitlines()
    i = 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            items.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        m = re.match(r"^\[\[gurbani:([a-z0-9-]+)\]\]$", line.strip())
        if m:
            flush()
            out.append(gurbani_block(m.group(1), ctx))
        elif line.startswith(":::"):
            flush()
            m = re.match(r"^:::\s*(compare|tension)\s+(.*)$", line)
            kind, rest = (m.group(1), m.group(2)) if m else ("note", "")
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                body.append(lines[i])
                i += 1
            out.append(aside_block(kind, rest, "\n".join(body), ctx))
        elif line.startswith("### "):
            flush()
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("- "):
            if para:
                flush()
            items.append(line[2:])
        elif not line.strip():
            flush()
        else:
            if items:
                flush()
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def aside_block(kind, head, body, ctx):
    if kind == "compare":
        tradition, _, source = head.partition("|")
        return (f'<aside class="compare" aria-label="Comparative note: {e(tradition.strip())}">'
                f'<p class="gloss"><b>Comparative note</b>{e(tradition.strip())}'
                f'{"<span>Source: " + e(source.strip()) + "</span>" if source.strip() else ""}'
                f'<span>Editorial, with Gurmat as the frame. Awaiting review.</span></p>'
                f'<div class="aside-body">{md(body, ctx)}</div></aside>')
    return (f'<aside class="tension" aria-label="Where views differ"><p class="gloss"><b>Where views differ</b>{e(head.strip())}</p>'
            f'<div class="aside-body">{md(body, ctx)}</div></aside>')


# ------------------------------------------------------------------ Gurbani
VERIFY_TEXT = {
    "verified": "Checked against BaniDB",
    "editor-confirmed": "Confirmed by an editor",
    "unchecked": "Not yet machine-checked against BaniDB",
}


def pangtis(text):
    """One verse line (pangti) per line, broken after each ॥ (keeping verse numbers like ॥੧॥ with it)."""
    parts = re.findall(r"[^॥]+॥(?:[੦-੯]+॥)?", text) or [text]
    return "".join(f'<span class="pangti">{e(p.strip())}</span>' for p in parts)


def gurbani_block(gid, ctx):
    k = ctx["k"]
    line = k["gurbani"].get(gid)
    if not line:
        raise SystemExit(f"Unknown Gurbani id: {gid}")
    show, state = K.gurbani_state(line, k["verification"], k["overrides"])
    ctx.setdefault("gurbani_used", []).append((gid, state))
    if not show:
        return f"<!-- gurbani:{gid} hidden until checked ({state}) -->"
    src = line["source"]
    ang = src.get("ang")
    katha = K.katha_for_line(line, ctx["katha_idx"])
    rows = "".join(track_row(t, s, sub=f"{s['title']}") for t, s in katha)
    note = f'<p class="tnote"><b>About the translation.</b> {e(line["translation_note"])}</p>' if line.get("translation_note") else ""
    read = (f'<a href="https://www.sikhitothemax.org/ang?ang={ang}&amp;source=G" rel="noopener" target="_blank">Read Ang {ang} in full</a>'
            if ang else "")
    return f"""<figure class="bani" id="g-{e(gid)}">
  <blockquote lang="pa" class="g">{pangtis(line['gurmukhi'])}</blockquote>
  <p class="translit" lang="pa-Latn"><span class="lbl">Transliteration</span> {e(line['translit'])}</p>
  <p class="render"><span class="lbl">Translation, editorial</span> {e(line['rendering'])}</p>
  {note}
  <figcaption><cite>{e(src.get('granth'))}{', Ang ' + str(ang) if ang else ''}</cite>. {e(src.get('bani'))}. {e(src.get('author'))}.
    <span class="vstate v-{state}">{VERIFY_TEXT.get(state, '')}</span> {read}</figcaption>
  {f'<div class="bani-katha" data-queue><p class="lbl">Babaji’s katha of this {"pauri" if line.get("japji_pauri") is not None else "Ang"}</p><div class="rows">{rows}</div></div>' if rows else ''}
</figure>"""


# ------------------------------------------------------------------ shared fragments
def track_attrs(t, s):
    m = K.ANG_RE.search(t["t"])
    ang = f' data-a1="{int(m.group(1))}" data-a2="{int(m.group(2) or m.group(1))}"' if m else ""
    return (ang + ' ' + f'data-p="{e(t["p"])}" data-t="{e(t["t"])}" data-s="{e(s["title"])}" data-sg="{e(s.get("gurmukhi", ""))}" '
            f'data-sid="{e(s["id"])}" data-d="{e(t.get("d", ""))}"')


def track_row(t, s, sub="", date_shown=True):
    sub = sub if sub is not None else ""
    d = (f'<span class="d" title="Date the recording was added to Gurmatveechar">Added {fdate(t.get("d"))}</span>'
         if date_shown and t.get("d") else '<span class="d"></span>')
    return (f'<button type="button" class="row" {track_attrs(t, s)}><span class="pp" aria-hidden="true">'
            f'<svg><use href="#i-play"/></svg></span><span class="t"><b>{e(t["t"])}</b>'
            f'{"<span>" + e(sub) + "</span>" if sub else ""}<i class="bar" hidden><i></i></i></span>{d}</button>')


def video_card(v, small=False, label=None):
    title = v["title"].replace(" || ", ". ").replace("||", ". ")
    when = fdate(v.get("published"))
    return (f'<article class="vc{" small" if small else ""}"><button type="button" class="thumb" data-video="{e(v["id"])}" '
            f'aria-label="Play video: {e(title)}"><img loading="lazy" decoding="async" alt="" '
            f'src="https://i.ytimg.com/vi/{e(v["id"])}/hqdefault.jpg" width="480" height="360">'
            f'<span class="mini" aria-hidden="true"><svg><use href="#i-play"/></svg></span></button>'
            f'<h3 lang="{"pa" if re.search("[਀-੿]", title) else "en"}">{e(title)}</h3>'
            f'<p class="meta">{e(label) + ", " if label else ""}{when}'
            f' <a href="https://www.youtube.com/watch?v={e(v["id"])}" target="_blank" rel="noopener">Open on YouTube</a></p></article>')


def provenance(kind, extra=""):
    labels = {
        "editorial": ("Editorial introduction", "Drafted with AI assistance for this site. Not Gurbani and not Babaji’s words."),
        "babaji": ("Babaji’s katha", "Linked by the titles of the recordings and videos."),
        "reflect": ("Questions for reflection", "Editorial, offered for your own enquiry."),
        "deeper": ("Primary sources", "Gurbani, and the texts Babaji has given katha on."),
    }
    t, d = labels[kind]
    return f'<p class="gloss"><b>{t}</b><span>{d}</span>{extra}</p>'


ICONS = """<svg width="0" height="0" class="sprite" aria-hidden="true">
<symbol id="i-play" viewBox="0 0 12 14"><path d="M1 0.6l10.4 6.4L1 13.4z"/></symbol>
<symbol id="i-pause" viewBox="0 0 12 14"><path d="M1 0h3.4v14H1zM7.6 0H11v14H7.6z"/></symbol>
<symbol id="i-next" viewBox="0 0 24 24"><path d="M5 5l10 7-10 7zM17 5h2v14h-2z"/></symbol>
<symbol id="i-prev" viewBox="0 0 24 24"><path d="M19 5L9 12l10 7zM5 5h2v14H5z"/></symbol>
<symbol id="i-back" viewBox="0 0 24 24"><path d="M12 5V1L7 6l5 5V7a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8z"/></symbol>
<symbol id="i-fwd" viewBox="0 0 24 24"><path d="M12 5V1l5 5-5 5V7a6 6 0 1 0 6 6h2a8 8 0 1 1-8-8z"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="M5.3 3.9L12 10.6l6.7-6.7 1.4 1.4-6.7 6.7 6.7 6.7-1.4 1.4-6.7-6.7-6.7 6.7-1.4-1.4 6.7-6.7-6.7-6.7z"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><path d="M10 3a7 7 0 0 1 5.6 11.2l5.1 5.1-1.4 1.4-5.1-5.1A7 7 0 1 1 10 3zm0 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10z"/></symbol>
</svg>"""


def page(ctx, path, title, body, desc, *, section="", noindex=False, jsonld=None, og_image=None, lang="en"):
    k = ctx["k"]
    site = k["config"].get("site_name", "Harkhowal Online")
    full = title if title == site else f"{title} | {site}"
    canonical = k["config"].get("site_url", "").rstrip("/") + "/" + path.lstrip("/")
    nav = [("latest/", "Latest", "latest"), ("topics/", "Topics", "topics"), ("journey/", "Journey", "journey"), ("listen/", "Listen", "listen"), ("watch/", "Watch", "watch"), ("about/", "About", "about")]
    navh = "".join(f'<a href="{u(p)}"{" aria-current=\"page\"" if section == s else ""}>{t}</a>' for p, t, s in nav)
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    img = og_image or "https://i.ytimg.com/vi/" + (k["videos"][0]["id"] if k["videos"] else "") + "/hqdefault.jpg"
    social = " ".join(f'<a href="{e(v)}" rel="noopener" target="_blank">{n}</a>'
                      for n, v in (("YouTube", k["config"].get("social", {}).get("youtube")),
                                   ("Facebook", k["config"].get("social", {}).get("facebook"))) if v)
    doc = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(full)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
{'<meta name="robots" content="noindex, nofollow">' if noindex else ''}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(site)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(img)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#161A33">
<link rel="icon" href="{u('assets/icon.svg')}" type="image/svg+xml">
<link rel="apple-touch-icon" href="{u('assets/apple-touch-icon.png')}">
<link rel="manifest" href="{u('manifest.webmanifest')}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Alegreya:ital,wght@0,400;0,500;0,700;1,400&family=Alegreya+Sans:wght@400;500;700&family=Mukta+Mahee:wght@400;500;700&family=Noto+Serif+Gurmukhi:wght@500;700&display=swap">
<link rel="stylesheet" href="{u('assets/site.css')}?v={ctx['ver']}">
{ld}
</head>
<body data-base="{e(BASE)}" data-audio-base="{e(k['audio'].get('base', ''))}">
{ICONS}
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="wrap">
    <a class="brand" href="{u()}"><span class="g" lang="pa">ਹਰਖੋਵਾਲ</span><span>Harkhowal</span></a>
    <nav aria-label="Main">{navh}</nav>
    <form class="hsearch" action="{u('search/')}" role="search"><label class="sr" for="hq">Search</label>
      <svg class="icon" aria-hidden="true"><use href="#i-search"/></svg><input id="hq" name="q" type="search" placeholder="Search" autocomplete="off"></form>
  </div>
</header>
<main id="main" tabindex="-1" data-path="{e(path)}">
{body}
</main>
<footer class="foot">
  <div class="wrap">
    <div>
      <p class="g fateh" lang="pa">ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖ਼ਾਲਸਾ, ਵਾਹਿਗੁਰੂ ਜੀ ਕੀ ਫ਼ਤਿਹ</p>
      <p>Sant Ashram, Sultanpur Lodhi, Punjab. <a href="mailto:{e(k['config'].get('contact_email'))}">{e(k['config'].get('contact_email'))}</a></p>
      <p>Audio is hosted by <a href="https://www.gurmatveechar.com" rel="noopener" target="_blank">Gurmatveechar.com</a>. Videos are from Babaji’s YouTube channel. {social}</p>
    </div>
    <div class="foot-links">
      <a href="{u('sources/')}">Sources and how this site works</a>
      <a href="{u('search/')}">Search</a>
      <span>Updated {e(ctx['updated'])}</span>
    </div>
  </div>
</footer>
<div class="player" id="player" hidden>
  <div class="ptop" aria-hidden="true"><i id="p-mini"></i></div>
  <div class="pl">
    <button class="np" id="p-np" type="button" aria-label="Show player controls"><span class="np-mark g" id="p-mark" aria-hidden="true"></span><span class="np-t"><b id="p-title"></b><span id="p-series"></span></span></button>
    <div class="ctl">
      <button class="ib opt" id="p-prev" type="button" aria-label="Previous recording"><svg class="icon"><use href="#i-prev"/></svg></button>
      <button class="ib opt" id="p-back" type="button" aria-label="Back 15 seconds"><svg class="icon"><use href="#i-back"/></svg><small>15</small></button>
      <button class="ib main" id="p-play" type="button" aria-label="Play"><svg class="icon"><use href="#i-play"/></svg></button>
      <button class="ib opt" id="p-fwd" type="button" aria-label="Forward 30 seconds"><svg class="icon"><use href="#i-fwd"/></svg><small>30</small></button>
      <button class="ib" id="p-next" type="button" aria-label="Next recording"><svg class="icon"><use href="#i-next"/></svg></button>
    </div>
    <div class="seek"><span id="p-cur">0:00</span><input id="p-seek" type="range" min="0" max="1000" value="0" aria-label="Seek"><span id="p-dur">0:00</span></div>
    <div class="ext">
      <button class="speed" id="p-speed" type="button" aria-label="Playback speed">1×</button>
      <a class="ib" id="p-series-link" href="{u('listen/')}" aria-label="Open this series"><svg class="icon"><use href="#i-search"/></svg></a>
      <button class="ib" id="p-close" type="button" aria-label="Close player"><svg class="icon"><use href="#i-x"/></svg></button>
    </div>
  </div>
  <p class="perr" id="p-err" hidden></p>
  <audio id="audio" preload="metadata"></audio>
</div>
<script src="{u('assets/site.js')}?v={ctx['ver']}" defer></script>
</body>
</html>
"""
    write(path, doc)
    if not noindex:
        ctx["sitemap"].append(path)


def write(path, text):
    p = OUT / path.lstrip("/")
    if path.endswith("/") or path == "":
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------ pages
def theme_items(ctx, slug):
    """Everything linked to a theme, split by kind, newest first."""
    k, links = ctx["k"], ctx["links"]
    vids = [v for v in k["videos"] if slug in links.get("yt:" + v["id"], {})]
    recs = []
    for s in k["audio"].get("series", []):
        for t in s["tracks"]:
            if slug in links.get(t["id"], {}):
                recs.append((t, s))
    recs.sort(key=lambda ts: (ts[0].get("d") or "", ts[0]["t"]), reverse=True)
    series = [s for s in k["audio"].get("series", []) if slug in links.get("s:" + s["id"], {})]
    ext = [x for x in k["external"].get("items", []) if x.get("status") == "published" and slug in links.get(x["id"], {})]
    return vids, recs, series, ext


def constellation(ctx, current=None, size=520):
    """An SVG map of the themes and their stated relationships. Each node links to its theme."""
    import math
    k = ctx["k"]
    th = k["themes"]
    n = len(th)
    cx = cy = size / 2
    r = size / 2 - 70
    pos = {}
    for i, t in enumerate(th):
        a = -math.pi / 2 + 2 * math.pi * i / n
        pos[t["slug"]] = (cx + r * math.cos(a), cy + r * math.sin(a))
    edges = []
    for ed in k["graph"]:
        (x1, y1), (x2, y2) = pos[ed["a"]], pos[ed["b"]]
        cls = "edge" + (" tension" if ed.get("tension") else "") + (" on" if current in (ed["a"], ed["b"]) else "")
        edges.append(f'<path class="{cls}" data-a="{ed["a"]}" data-b="{ed["b"]}" d="M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}"/>')
    nodes = []
    for t in th:
        x, y = pos[t["slug"]]
        anchor = "middle"
        dy = 4
        on = " on" if t["slug"] == current else ""
        nodes.append(f'<a href="{u("themes/" + t["slug"] + "/")}" class="node{on}" data-slug="{t["slug"]}">'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5"/>'
                     f'<text x="{x:.1f}" y="{y - 14:.1f}" text-anchor="{anchor}" class="g" lang="pa">{e(t["gurmukhi"])}</text>'
                     f'<text x="{x:.1f}" y="{y + 22 + dy:.1f}" text-anchor="{anchor}" class="en">{e(t["title"].split(":")[0].split(",")[0])}</text></a>')
    return (f'<svg class="constellation" viewBox="0 0 {size} {size}" role="group" aria-label="Map of the themes and how they connect">'
            f'<g class="edges">{"".join(edges)}</g><g>{"".join(nodes)}</g></svg>')


def journey_path(ctx, on_night=False, link_base=""):
    """The seven stops from manmukh to sach khand, warming from night to dawn."""
    stages = ctx["k"]["journey"]["stages"]
    stops = "".join(f'<li class="s{i + 1}"><a href="{link_base}#{e(st["id"])}"><span class="dot" aria-hidden="true"></span>'
                    f'<span class="g" lang="pa">{e(st["gurmukhi"])}</span><span class="en">{e(st["title"])}</span></a></li>'
                    for i, st in enumerate(stages))
    return f'<ol class="path{" on-night" if on_night else ""}" aria-label="The seven steps of the journey">{stops}</ol>'


def journey_katha(ctx):
    """Babaji's katha of Japji Sahib pauris 34 to 38, in order: the five khands and the mint."""
    out, seen = [], set()
    for a, b, t, s in sorted(ctx["katha_idx"]["pauris"], key=lambda x: (x[3]["id"] != "jap-ji-sahib-katha", x[0], x[2]["i"])):
        if b >= 34 and a <= 38 and t["p"] not in seen:
            seen.add(t["p"])
            out.append((t, s))
    return out


def build_journey(ctx):
    k = ctx["k"]
    j = k["journey"]
    sec = j["sections"]
    ctx_local = {**ctx, "gurbani_used": []}
    review = j.get("review", {})
    reviewed = review.get("status") == "reviewed"
    review_note = (f'Reviewed by {e(review.get("reviewer", "an editor"))}.' if reviewed else "Awaiting review by a learned reader.")
    n = len(j["stages"])
    rail = "".join(f'<li><a href="#{st["id"]}"><span class="g" lang="pa">{e(st["gurmukhi"])}</span> {e(st["short"])}</a></li>' for st in j["stages"])
    layers = [f'<section id="intro" class="layer">{provenance("editorial", "<span class=rv>" + review_note + "</span>")}<h2>Two ways of facing</h2>{md(sec.get("intro", ""), ctx_local)}</section>']
    for i, st in enumerate(j["stages"]):
        chips = []
        for tid in st.get("topics", []):
            tp = k["topic_by_id"].get(tid)
            if tp:
                chips.append(f'<a class="tag" href="{topic_url(tp)}"><span class="g" lang="pa">{e(tp["gurmukhi"])}</span> {e(tp["title"].split(":")[0])}</a>')
        gloss = (f'<p class="gloss"><b>Step {i + 1} of {n}</b><span>Drawn from {e(st["source"])}.</span>'
                 f'<span>Editorial guide; Gurbani is quoted with its source.</span></p>')
        layers.append(f'<section id="{st["id"]}" class="layer stage s{i + 1}">{gloss}'
                      f'<h2><span class="g" lang="pa">{e(st["gurmukhi"])}</span><span class="en">{e(st["title"])}</span></h2>'
                      f'{md(sec.get(st["id"], ""), ctx_local)}'
                      f'{("<p class=tags><span class=tags-lbl>In Babaji’s katha:</span> " + "".join(chips) + "</p>") if chips else ""}</section>')
    mint = "".join(f'<div><dt><span class="g" lang="pa">{e(g)}</span> {e(q)}</dt><dd>{e(tool)}</dd></div>' for g, q, tool in j.get("mint", []))
    layers.append(f'<section id="mint" class="layer">{provenance("editorial")}<h2><span class="g" lang="pa">ਸਚੀ ਟਕਸਾਲ</span><span class="en">The true mint</span></h2>'
                  + "".join(md(part, ctx_local) + (f'<dl class="mint" aria-label="The tools of the mint">{mint}</dl>' if i == 0 else "")
                            for i, part in enumerate(sec.get("mint", "").split("[[mint-table]]")))
                  + '</section>')
    jk = journey_katha(ctx)
    rows = "".join(track_row(t, s, sub=s["title"]) for t, s in jk)
    layers.append(f'<section id="gurmukh" class="layer">{provenance("editorial")}<h2><span class="g" lang="pa">ਗੁਰਮੁਖ</span><span class="en">The gurmukh</span></h2>'
                  f'{md(sec.get("gurmukh", ""), ctx_local)}'
                  f'<h3 id="katha">Babaji’s katha of the five khands and the mint</h3><p class="sub">Japji Sahib, pauris 34 to 38, in order. Press one to listen; the next follows on.</p>'
                  f'<div class="rows" data-queue>{rows}</div>'
                  f'<p class="tags"><span class="tags-lbl">Further:</span> <a class="tag" href="{u("topics/sidh-gosht/")}"><span class="g" lang="pa">ਸਿਧ ਗੋਸਟਿ</span> Sidh Gosht</a>'
                  f'<a class="tag" href="{u("topics/japji/")}"><span class="g" lang="pa">ਜਪੁਜੀ ਸਾਹਿਬ</span> Japji Sahib</a></p></section>')
    body = f"""
<article class="journey">
  <header class="theme-head journey-head">
    <div class="wrap">
      <p class="crumbs"><a href="{u('topics/')}">Topics</a>, the journey</p>
      <h1><span class="g" lang="pa">{e(j['gurmukhi'])}</span><span class="en">{e(j['title'])}</span></h1>
      <p class="sub">{e(j['subtitle'])}</p>
      {journey_path(ctx, on_night=True)}
      <p class="journey-listen"><a href="#katha">Listen to Babaji’s katha of these pauris</a></p>
    </div>
  </header>
  <div class="wrap tika">
    <nav class="rail" aria-label="Steps of the journey"><ol>{rail}</ol>
      <p class="rail-extra"><a href="#mint">The true mint</a><a href="#gurmukh">The gurmukh</a></p></nav>
    <div class="col">{''.join(layers)}</div>
  </div>
</article>"""
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": f"{j['title']} ({j['gurmukhi']})", "description": j["summary"],
          "inLanguage": "en", "publisher": {"@type": "Organization", "name": k["config"].get("site_name")}}
    page(ctx, "journey/", f"{j['title']}: {j['subtitle']}", body, j["summary"], section="journey", jsonld=ld)
    ctx["gurbani_log"]["journey"] = ctx_local["gurbani_used"]


def build_theme(ctx, th):
    k = ctx["k"]
    slug = th["slug"]
    ctx_local = {**ctx, "gurbani_used": []}
    sec = th["sections"]
    review = K.theme_review(k, slug)
    vids, recs, series, ext = theme_items(ctx, slug)
    reviewed = review.get("status") == "reviewed"
    review_note = (f'Reviewed by {e(review.get("reviewer", "an editor"))}{", " + fdate(review.get("date")) if review.get("date") else ""}.'
                   if reviewed else "Awaiting review by a learned reader.")
    discover = md(sec.get("discover", ""), ctx_local)
    understand = md(sec.get("understand", ""), ctx_local)

    # Explore: Babaji's own katha first
    vh = "".join(video_card(v, small=True) for v in vids[:6])
    more_v = f'<p class="more"><a href="{u("watch/")}?theme={slug}">All {len(vids)} videos on this theme</a></p>' if len(vids) > 6 else ""
    rh = "".join(track_row(t, s, sub=s["title"] + (", " + t["g"] if t.get("g") else "")) for t, s in recs[:12])
    rest = "".join(track_row(t, s, sub=s["title"]) for t, s in recs[12:60])
    more_r = (f'<details class="morerows"><summary>Show {len(recs) - 12} more</summary><div class="rows">{rest}</div></details>'
              if len(recs) > 12 else "")
    sh = "".join(series_line(ctx, s) for s in series)
    exh = "".join(f'<li><a href="{e(ext_url(x))}" target="_blank" rel="noopener">{e(x["title"])}</a>'
                  f'<span>{e(x["creator"])}. From another channel; curated by the Dera.</span></li>' for x in ext)
    explore_parts = []
    shown_lines = [g for g, st in ctx_local["gurbani_used"] if st in VERIFY_TEXT]
    seen_p, bk = set(), []
    for g in shown_lines:
        for t, s in K.katha_for_line(k["gurbani"][g], ctx["katha_idx"], limit=2):
            if t["p"] not in seen_p:
                seen_p.add(t["p"])
                src = k["gurbani"][g]["source"]
                bk.append(track_row(t, s, sub=f"Katha of {src.get('bani')}, Ang {src.get('ang')}"))
    if bk:
        explore_parts.append(f'<h3>Katha of the Gurbani quoted here</h3><div class="rows" data-queue>{"".join(bk)}</div>')
    if vids:
        explore_parts.append(f'<h3>Videos</h3><div class="vgrid">{vh}</div>{more_v}')
    if recs:
        explore_parts.append(f'<h3>Recordings with this in their title</h3><div class="rows" data-queue>{rh}</div>{more_r}')
    if series:
        explore_parts.append(f'<h3>Series on this theme</h3><ul class="serieslist">{sh}</ul>')
    if ext:
        explore_parts.append(f'<h3>From other teachers and makers</h3><ul class="extlist">{exh}</ul>')
    if not explore_parts:
        explore_parts.append('<p class="empty">No recordings are linked to this theme by title yet. Editors can link recordings on the Review page, and new videos are linked automatically when their titles mention the theme.</p>')

    # Connections
    conns = []
    for ed in k["graph"]:
        if slug not in (ed["a"], ed["b"]):
            continue
        other = k["theme_by_slug"][ed["b"] if ed["a"] == slug else ed["a"]]
        refs = "".join(f'<a href="#g-{g}" class="gref">Ang {k["gurbani"][g]["source"].get("ang")}</a>' for g in ed.get("gurbani", [])
                       if g in k["gurbani"] and any(g == x for x, st in ctx_local["gurbani_used"] if st in VERIFY_TEXT))
        conns.append(f'<li><a class="cn" href="{u("themes/" + other["slug"] + "/")}"><span class="g" lang="pa">{e(other["gurmukhi"])}</span> {e(other["title"])}</a>'
                     f'<p>{e(ed["why"])} {refs}</p>{"<p class=tension-line><b>Where they pull apart.</b> " + e(ed["tension"]) + "</p>" if ed.get("tension") else ""}</li>')

    reflect = md(sec.get("reflect", ""), ctx_local)
    practise = md(sec.get("practise", ""), ctx_local)

    # Go deeper: texts and Angs
    deeper_series = [k["series_by_id"][sid] for sid in
                     sorted({sid for sid, p in k["texts"]["profiles"].items() if slug in p.get("themes", [])})
                     if sid in k["series_by_id"]]
    angs = sorted({(k["gurbani"][g]["source"].get("ang"), k["gurbani"][g]["source"].get("bani"), k["gurbani"][g]["source"].get("author"))
                   for g, st in ctx_local["gurbani_used"] if st in VERIFY_TEXT and k["gurbani"][g]["source"].get("ang")})
    angh = "".join(f'<li><a href="https://www.sikhitothemax.org/ang?ang={a}&amp;source=G" target="_blank" rel="noopener">Ang {a}</a>'
                   f'<span>{e(b)}</span></li>' for a, b, au in angs)
    dsh = "".join(series_line(ctx, s) for s in deeper_series)

    layers = [("discover", "Discover"), ("understand", "Understand"), ("explore", "Explore"), ("reflect", "Reflect"), ("deeper", "Go deeper")]
    rail = "".join(f'<li><a href="#{a}">{t}</a></li>' for a, t in layers)
    body = f"""
<article class="theme">
  <header class="theme-head">
    <div class="wrap">
      <p class="crumbs"><a href="{u('topics/')}">Topics</a>, in depth</p>
      <h1><span class="g" lang="pa">{e(th['gurmukhi'])}</span><span class="en">{e(th['title'])}</span></h1>
      <p class="sub">{e(th['subtitle'])}</p>
      <p class="q">{e(th['question'])}</p>
    </div>
  </header>
  <div class="wrap tika">
    <nav class="rail" aria-label="On this page"><ol>{rail}</ol>
      <div class="rail-map">{constellation(ctx, slug, 360)}</div></nav>
    <div class="col">
      <section id="discover" class="layer">{provenance('editorial', '<span class="rv">' + review_note + '</span>')}<h2>Discover</h2>{discover}</section>
      <section id="understand" class="layer">{provenance('editorial')}<h2>Understand</h2>{understand}</section>
      <section id="explore" class="layer">{provenance('babaji')}<h2>Explore Babaji’s katha</h2>{''.join(explore_parts)}</section>
      <section id="connections" class="layer">{provenance('editorial')}<h2>How this connects</h2><ul class="conns">{''.join(conns)}</ul></section>
      <section id="reflect" class="layer">{provenance('reflect')}<h2>Reflect</h2>{reflect}<h3>A practice for this week</h3>{practise}</section>
      <section id="deeper" class="layer">{provenance('deeper')}<h2>Go deeper</h2>
        {('<h3>Gurbani on this page</h3><ul class="anglist">' + angh + '</ul>') if angh else ''}
        {('<h3>Texts Babaji has taught on this theme</h3><ul class="serieslist">' + dsh + '</ul>') if dsh else ''}
        <p class="sub">Found something mistaken or missing? Write to <a href="mailto:{e(k['config'].get('contact_email'))}">{e(k['config'].get('contact_email'))}</a>.</p>
      </section>
    </div>
  </div>
</article>"""
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": f"{th['title']} ({th['gurmukhi']})",
          "description": th["summary"], "inLanguage": "en", "about": th["title"],
          "publisher": {"@type": "Organization", "name": k["config"].get("site_name")}}
    page(ctx, f"themes/{slug}/", f"{th['title']}: {th['subtitle']}", body, th["summary"], section="topics", jsonld=ld)
    ctx["gurbani_log"][slug] = ctx_local["gurbani_used"]


def series_line(ctx, s):
    k = ctx["k"]
    prof = k["texts"]["profiles"].get(s["id"], {})
    return (f'<li><a href="{u("listen/" + s["id"] + "/")}"><span class="g" lang="pa">{e(s.get("gurmukhi") or "")}</span> '
            f'{e(prof.get("text") or s["title"])}</a><span>{len(s["tracks"]):,} recordings</span></li>')


def reason(via):
    """How a link was made, in plain words for readers."""
    m = re.match(r"(title|description|series title): ‘(.*)’$", via)
    if m:
        return {"title": "title names", "description": "description names", "series title": "series title names"}[m.group(1)] + f" ‘{m.group(2)}’"
    if via.startswith("covers"):
        return f"katha {via}"
    return {"editor": "linked by an editor", "curated": "chosen by the Dera"}.get(via, "part of a series on this topic")


def topic_url(tp):
    return u(f"themes/{tp['theme']}/") if tp["kind"] == "theme" else u(f"topics/{tp['id']}/")


def topic_items(ctx, tid):
    """Everything linked to a topic: videos, recordings (with why), series."""
    k, links = ctx["k"], ctx["links"]
    vids = [(v, links["yt:" + v["id"]][tid]["via"]) for v in k["videos"] if tid in links.get("yt:" + v["id"], {})]
    recs, series = [], []
    for s in k["audio"].get("series", []):
        if tid in links.get("s:" + s["id"], {}):
            series.append(s)
            continue
        for t in s["tracks"]:
            if tid in links.get(t["id"], {}):
                recs.append((t, s, links[t["id"]][tid]["via"]))
    return vids, recs, series


def related_topics(ctx, tid, limit=6):
    """Topics that share katha with this one, most shared first."""
    k, links = ctx["k"], ctx["links"]
    counts = {}
    for iid, tps in links.items():
        if tid in tps:
            for other in tps:
                if other != tid and other in k["topic_by_id"]:
                    counts[other] = counts.get(other, 0) + 1
    return [k["topic_by_id"][t] for t, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]


def topic_count(ctx, tid):
    vids, recs, series = topic_items(ctx, tid)
    seen = {t["p"] for t, s, via in recs} | {t["p"] for s in series for t in s["tracks"]}
    th = ctx["k"]["theme_by_slug"].get(tid)
    if th:  # an in-depth theme also offers the katha of each Gurbani line it quotes
        for g in set(K.gurbani_refs("\n".join(th["sections"].values())) + [th["anchor"]]):
            line = ctx["k"]["gurbani"][g]
            if K.gurbani_state(line, ctx["k"]["verification"], ctx["k"]["overrides"])[0]:
                seen |= {t["p"] for t, s in K.katha_for_line(line, ctx["katha_idx"], limit=2)}
    return len(vids) + len(seen)


def build_topics(ctx):
    k = ctx["k"]
    kinds = k["topics_file"].get("kinds", {})
    # In-depth themes, as questions, with the map of how they connect
    qs = "".join(f'<li><a href="{u("themes/" + t["slug"] + "/")}"><span class="g" lang="pa">{e(t["gurmukhi"])}</span>'
                 f'<span class="en">{e(t["title"])}</span><span class="q">{e(t["question"])}</span></a></li>' for t in k["themes"])
    groups = []
    for kind, meta in kinds.items():
        rows = []
        for tp in [t for t in k["topics"] if t["kind"] == kind]:
            n = topic_count(ctx, tp["id"])
            if not n:
                continue
            terms = K.fold(" ".join([tp["title"], tp["gurmukhi"]] + tp.get("aliases", [])))
            rows.append(f'<a class="ix" href="{topic_url(tp)}" data-filter="{e(terms)}"><span class="gn" lang="pa">{e(tp["gurmukhi"])}</span>'
                        f'<span class="en">{e(tp["title"])}</span><span class="n">{n:,}</span></a>')
        groups.append(f'<section class="shelf"><div class="shelf-head"><h2><span class="g" lang="pa">{e(meta["gurmukhi"])}</span> {e(meta["title"])}</h2></div>'
                      f'<div class="index">{"".join(rows)}</div></section>')
    j = k["journey"]
    journey_row = (f'<a class="ix" href="{u("journey/")}" data-filter="{e(K.fold(" ".join([j["title"], j["gurmukhi"], j["subtitle"]] + j.get("terms", []))))}">'
                   f'<span class="gn" lang="pa">{e(j["gurmukhi"])}</span><span class="en">The journey, in seven steps</span><span class="n">{len(journey_katha(ctx)):,}</span></a>')
    theme_rows = journey_row + "".join(f'<a class="ix" href="{u("themes/" + t["slug"] + "/")}" data-filter="{e(K.fold(" ".join([t["title"], t["gurmukhi"], t["question"]] + t.get("terms", []))))}">'
                         f'<span class="gn" lang="pa">{e(t["gurmukhi"])}</span><span class="en">{e(t["title"])}: in depth</span><span class="n">{topic_count(ctx, t["slug"]):,}</span></a>' for t in k["themes"])
    body = f"""
<section class="page-head"><div class="wrap">
  <h1>Topics</h1>
  <p class="lede">Find a topic, then the katha that speaks to it. Topics are drawn from Babaji’s own titles and from the Gurbani he has expounded: Gurbani topics gather the katha of their Angs, others gather recordings and videos whose titles name them.</p>
  <label class="filter"><svg class="icon" aria-hidden="true"><use href="#i-search"/></svg><input id="tq" type="search" data-filter-input placeholder="Find a topic: ego, ਨਾਮ, Sukhmani, Sangrand" aria-label="Find a topic" autocomplete="off"></label>
</div></section>
<div class="wrap shelves" data-filter-scope>
  <section class="shelf"><div class="shelf-head"><h2><span class="g" lang="pa">ਵਿਸਥਾਰ</span> In depth</h2><p>Eleven themes with an introduction, Gurbani, Babaji’s katha and questions for reflection.</p></div>
  <div class="index">{theme_rows}</div></section>
  {"".join(groups)}
</div>
<section class="wrap band themes-index">
  <ol class="qlist">{qs}</ol>
  <figure class="mapfig">{constellation(ctx)}<figcaption>How the in-depth themes connect. Dashed lines mark connections where the two ideas also pull in different directions.</figcaption></figure>
</section>"""
    page(ctx, "topics/", "Topics", body,
         "A knowledge base of Gurmat topics from Babaji's katha: ideas, Gurbani, Gurus and Gurmukhs, and occasions, each with the katha that refers to it.",
         section="topics")
    for tp in k["topics"]:
        if tp["kind"] != "theme":
            build_topic(ctx, tp)


def build_topic(ctx, tp):
    k = ctx["k"]
    tid = tp["id"]
    vids, recs, series = topic_items(ctx, tid)
    total = len(vids) + len(recs) + sum(len(s["tracks"]) for s in series)
    angs = tp.get("match", {}).get("angs", [])
    by_ang = bool(angs)
    if by_ang:
        recs.sort(key=lambda x: (x[1]["id"] != SGGS, x[1]["title"], x[0]["i"]))
    else:
        recs.sort(key=lambda x: (x[0].get("d") or "", x[0]["i"]), reverse=True)
    parts = []
    if angs:
        al = "".join(f'<li><a href="https://www.sikhitothemax.org/ang?ang={a}&amp;source=G" target="_blank" rel="noopener">Ang {a} to {b}</a>'
                     f'<span>Sri Guru Granth Sahib Ji</span></li>' for a, b in angs)
        parts.append(f'<h2>Where it is in the Granth</h2><ul class="anglist">{al}</ul>')
    if vids:
        parts.append(f'<h2>Videos</h2><div class="vgrid">{"".join(video_card(v, small=True, label=reason(via).capitalize()) for v, via in vids)}</div>')
    if recs:
        rows = "".join(track_row(t, s, sub=f"{s['title']}. Linked: {reason(via)}") for t, s, via in recs[:200])
        parts.append(f'<h2>Recordings{" in Ang order" if by_ang else ", newest first"}</h2><div class="rows" data-queue>{rows}</div>')
    if series:
        parts.append(f'<h2>Whole series</h2><ul class="serieslist">{"".join(series_line(ctx, s) for s in series)}</ul>')
    if not parts:
        parts.append('<p class="empty">No katha is linked to this topic yet.</p>')
    rel = related_topics(ctx, tid)
    relh = "".join(f'<a class="tag" href="{topic_url(r)}"><span class="g" lang="pa">{e(r["gurmukhi"])}</span> {e(r["title"])}</a>' for r in rel)
    theme = k["theme_by_slug"].get(tp.get("theme", ""))
    deep = (f'<p class="deeper-link">Go deeper: <a href="{u("themes/" + theme["slug"] + "/")}"><span class="g" lang="pa">{e(theme["gurmukhi"])}</span> '
            f'{e(theme["title"])}</a>, with Gurbani, comparisons and questions for reflection.</p>') if theme else ""
    if tp.get("journey"):
        deep += (f'<p class="deeper-link">The journey: <a href="{u("journey/")}"><span class="g" lang="pa">{e(k["journey"]["gurmukhi"])}</span> '
                 f'{e(k["journey"]["title"])}</a>, step by step.</p>')
    kind = k["topics_file"]["kinds"].get(tp["kind"], {}).get("title", "")
    body = f"""
<section class="page-head topic-head"><div class="wrap">
  <p class="crumbs"><a href="{u('topics/')}">Topics</a>, {e(kind)}</p>
  <h1><span class="g" lang="pa">{e(tp['gurmukhi'])}</span><span class="en">{e(tp['title'])}</span></h1>
  <p class="lede">{e(tp.get('about', ''))}</p>
  <p class="gloss solo"><b>How this page is made</b><span>{total:,} {'recording or video' if total == 1 else 'recordings and videos'} linked {'by the Angs their titles cover, and ' if by_ang else ''}by their titles; each says why. The note above is editorial.</span></p>
  {deep}
  {('<p class="tags">Related topics: ' + relh + '</p>') if relh else ''}
</div></section>
<div class="wrap topic-body">{"".join(parts)}</div>"""
    page(ctx, f"topics/{tid}/", f"{tp['title']}: Babaji’s katha", body,
         f"{tp.get('about', '')} Katha by Sant Baba Jagjit Singh Ji Harkhowal Wale on {tp['title']}.", section="topics",
         noindex=total < 3)


def build_listen(ctx):
    k = ctx["k"]
    shelves = []
    for sh in k["texts"]["shelves"]:
        rows = []
        for sid in sh["series"]:
            s = k["series_by_id"].get(sid)
            if not s:
                continue
            prof = k["texts"]["profiles"].get(sid, {})
            rows.append(f'<a class="ix" href="{u("listen/" + sid + "/")}" data-filter="{e(K.fold(s["title"] + " " + s.get("gurmukhi", "") + " " + prof.get("text", "")))}">'
                        f'<span class="gn{"" if s.get("gurmukhi") else " en"}" lang="{"pa" if s.get("gurmukhi") else "en"}">{e(s.get("gurmukhi") or prof.get("text") or s["title"])}</span>'
                        f'<span class="en">{e(prof.get("text") or s["title"])}</span><span class="n">{len(s["tracks"]):,}</span></a>')
        listed = set(sh["series"])
        shelves.append(f'<section class="shelf" id="{sh["id"]}"><div class="shelf-head"><h2><span class="g" lang="pa">{e(sh["gurmukhi"])}</span> {e(sh["title"])}</h2>'
                       f'<p>{e(sh["intro"])}</p></div><div class="index">{"".join(rows)}</div></section>')
    # anything not on a shelf
    shelved = {sid for sh in k["texts"]["shelves"] for sid in sh["series"]}
    loose = [s for s in k["audio"].get("series", []) if s["id"] not in shelved]
    if loose:
        rows = "".join(f'<a class="ix" href="{u("listen/" + s["id"] + "/")}" data-filter="{e(K.fold(s["title"]))}"><span class="gn en">{e(s["title"])}</span>'
                       f'<span class="en">New series</span><span class="n">{len(s["tracks"]):,}</span></a>' for s in loose)
        shelves.append(f'<section class="shelf"><div class="shelf-head"><h2>Newly added</h2><p>Series that appeared on Gurmatveechar since this list was last arranged.</p></div><div class="index">{rows}</div></section>')
    total = sum(len(s["tracks"]) for s in k["audio"].get("series", []))
    dated = sorted([(t, s) for s in k["audio"].get("series", []) for t in s["tracks"] if t.get("d")], key=lambda ts: ts[0]["d"], reverse=True)[:8]
    newest = ("<section class='wrap newest'><h2>Recently added</h2><div class='rows' data-queue>"
              + "".join(track_row(t, s, sub=s["title"]) for t, s in dated) + "</div></section>") if dated else ""
    els = [x for x in k["external"]["items"] if x.get("collection") == "elsewhere" and x.get("status") == "published"]
    col = k["external"]["collections"].get("elsewhere", {})
    elsewhere = (f'<section class="wrap extcol"><h2>{e(col.get("title"))}</h2><p class="sub">{e(col.get("intro"))}</p><ul class="extlist">'
                 + "".join(f'<li><a href="{e(ext_url(x))}" target="_blank" rel="noopener">{e(x["title"])}</a><span>{e(x["source_note"])}</span></li>' for x in els)
                 + '</ul></section>') if els else ""
    body = f"""
<section class="page-head"><div class="wrap">
  <h1>Listen</h1>
  <p class="lede">{total:,} recordings of Babaji’s katha in {len(k['audio'].get('series', []))} series, streamed from Gurmatveechar.com. Your place in each recording is remembered on this device.</p>
  <label class="filter"><svg class="icon" aria-hidden="true"><use href="#i-search"/></svg><input type="search" data-filter-input placeholder="Filter series, in English or Gurmukhi" aria-label="Filter series"></label>
</div></section>
<div data-continue class="wrap continue" hidden><h2>Continue listening</h2><div class="rows"></div></div>
{newest}
<div class="wrap shelves" data-filter-scope>{''.join(shelves)}</div>
{elsewhere}"""
    page(ctx, "listen/", "Listen to Babaji’s katha", body,
         f"Listen to {total:,} katha recordings by Sant Baba Jagjit Singh Ji Harkhowal Wale: Sri Guru Granth Sahib Ji, Suraj Parkash, Bhai Gurdas Ji, Vedanta and more.",
         section="listen")
    for s in k["audio"].get("series", []):
        build_series(ctx, s)


def build_series(ctx, s):
    k = ctx["k"]
    prof = k["texts"]["profiles"].get(s["id"], {})
    links = ctx["links"].get("s:" + s["id"], {})
    themes = [k["theme_by_slug"][t] for t in sorted(set(links) | set(prof.get("themes", []))) if t in k["theme_by_slug"]]
    rows, g = [], None
    for t in s["tracks"]:
        if t.get("g") and t["g"] != g:
            g = t["g"]
            rows.append(f'<h3 class="grp">{e(g)}</h3>')
        rows.append(track_row(t, s, sub=""))
    about = ""
    if prof:
        facts = []
        if prof.get("author") and prof["author"] != "unknown":
            facts.append(f"<div><dt>By</dt><dd>{e(prof['author'])}</dd></div>")
        if prof.get("tradition") and prof["tradition"] != "unknown":
            facts.append(f"<div><dt>Tradition</dt><dd>{e(prof['tradition'])}</dd></div>")
        about = (f'<div class="profile">{provenance("editorial")}'
                 f'{"<p>" + e(prof["about"]) + "</p>" if prof.get("about") else "<p class=empty>Background on this text has not been written yet.</p>"}'
                 f'{"<p class=uncertain><b>Uncertain.</b> " + e(prof["uncertainty"]) + "</p>" if prof.get("uncertainty") else ""}'
                 f'<dl>{"".join(facts)}</dl></div>')
    tl = "".join(f'<a class="tag" href="{u("themes/" + t["slug"] + "/")}"><span class="g" lang="pa">{e(t["gurmukhi"])}</span> {e(t["title"])}</a>' for t in themes)
    has_dates = any(t.get("d") for t in s["tracks"])
    has_angs = sum(1 for t in s["tracks"] if K.ANG_RE.search(t["t"])) > 20
    title_txt = prof.get("text") or s["title"]
    body = f"""
<section class="page-head series-head"><div class="wrap">
  <p class="crumbs"><a href="{u('listen/')}">Listen</a></p>
  <h1>{'<span class="g" lang="pa">' + e(s['gurmukhi']) + '</span>' if s.get('gurmukhi') else ''}<span class="en">{e(title_txt)}</span></h1>
  <p class="sub">{len(s['tracks']):,} recordings{', last added ' + fdate(s.get('latest')) if s.get('latest') else ''}. <a href="{e(s['page'])}" rel="noopener" target="_blank">Folder on Gurmatveechar</a></p>
  {('<p class="tags">' + tl + '</p>') if tl else ''}
</div></section>
<div class="wrap series-body">
  {about}
  <div class="tracks" data-queue data-series="{e(s['id'])}">
    <div class="tools"><button class="btn sun" type="button" data-play-series><svg class="icon"><use href="#i-play"/></svg><span>Play from the start</span></button>
    {'<form class="angjump" data-angjump><label for="angn">Go to Ang</label><input id="angn" type="number" min="1" max="1430" inputmode="numeric"><button class="btn plain" type="submit">Find</button><span class="angmsg" aria-live="polite"></span></form>' if has_angs else ''}
    {'<div class="seg" role="group" aria-label="Order"><button type="button" aria-pressed="true" data-order="part">In order</button><button type="button" aria-pressed="false" data-order="new">Newest first</button></div>' if has_dates else ''}</div>
    <div class="rows">{''.join(rows)}</div>
  </div>
</div>"""
    ld = {"@context": "https://schema.org", "@type": "PodcastSeries", "name": f"{title_txt}: katha by Sant Baba Jagjit Singh Ji Harkhowal Wale",
          "url": k["config"].get("site_url", "") + "/listen/" + s["id"] + "/", "inLanguage": "pa",
          "author": {"@type": "Person", "name": "Sant Baba Jagjit Singh Ji Harkhowal Wale"}}
    desc = (prof.get("about") or f"{len(s['tracks'])} katha recordings") + " Katha by Sant Baba Jagjit Singh Ji Harkhowal Wale."
    page(ctx, f"listen/{s['id']}/", f"{title_txt} katha", body, desc[:300], section="listen", jsonld=ld)


def ext_url(x):
    return x.get("url") or f"https://www.youtube.com/watch?v={x['youtube']}"


def build_watch(ctx):
    k, links = ctx["k"], ctx["links"]
    chips = "".join(f'<button type="button" class="chip" data-theme-chip="{t["slug"]}" aria-pressed="false"><span class="g" lang="pa">{e(t["gurmukhi"])}</span> {e(t["title"].split(":")[0])}</button>'
                    for t in k["themes"] if any(t["slug"] in links.get("yt:" + v["id"], {}) for v in k["videos"]))
    cards = []
    for v in k["videos"]:
        th = " ".join(links.get("yt:" + v["id"], {}).keys())
        cards.append(f'<div data-themes="{e(th)}">{video_card(v)}</div>')
    ext = []
    for cid, col in k["external"].get("collections", {}).items():
        items = [x for x in k["external"]["items"] if x.get("collection") == cid and x.get("status") == "published"]
        if not items:
            continue
        lis = "".join(f'<li><a href="{e(ext_url(x))}" target="_blank" rel="noopener">{e(x["title"])}</a>'
                      f'<span>{e(x["creator"])}</span></li>' for x in items)
        ext.append(f'<section class="extcol"><h2>{e(col["title"])}</h2><p class="sub">{e(col["intro"])}</p><ul class="extlist">{lis}</ul></section>')
    feeds = K.published_feed_items(k)
    if feeds:
        lis = "".join(f'<li><a href="{e(i["link"])}" target="_blank" rel="noopener">{e(i["title"])}</a><span>{e(i.get("creator") or i.get("author"))}, {fdate(i.get("published"))}</span></li>' for i in feeds[:30])
        ext.append(f'<section class="extcol"><h2>From connected feeds</h2><p class="sub">Approved by an editor. Each opens at its source.</p><ul class="extlist">{lis}</ul></section>')
    yt = k["config"].get("youtube_url", "")
    body = f"""
<section class="page-head"><div class="wrap">
  <h1>Watch</h1>
  <p class="lede">Babaji’s divans from the Dera’s YouTube channel, newest first. New videos appear here the morning after they are published.</p>
  {('<div class="chips" role="group" aria-label="Show videos on a theme">' + chips + '</div>') if chips else ''}
</div></section>
<section class="wrap"><div class="vgrid big" data-video-grid>{''.join(cards)}</div>
<p class="more"><a class="btn plain" href="{e(yt)}" target="_blank" rel="noopener">Open the YouTube channel</a></p></section>
<div class="wrap ext">{''.join(ext)}</div>"""
    page(ctx, "watch/", "Watch Babaji’s divans", body, "Latest katha videos by Sant Baba Jagjit Singh Ji Harkhowal Wale, with jeevan katha and Sikh history from other channels.", section="watch")


def build_home(ctx):
    k = ctx["k"]
    v = k["videos"][0] if k["videos"] else None
    hero_video = ""
    if v:
        title = v["title"].replace(" || ", ". ").replace("||", ". ")
        parts = [p.strip() for p in re.split(r"[।|]|\bl\b", title) if p.strip()]
        lead = parts[0] if parts else title
        rest = " · ".join(parts[1:4])
        theme_hits = [k["topic_by_id"][s] for s in ctx["links"].get("yt:" + v["id"], {}) if s in k["topic_by_id"]]
        hero_video = f"""
    <div class="hero-text">
      <p class="when"><span class="live" aria-hidden="true"></span>Newest katha, {fdate(v.get('published'))}</p>
      <h1 class="g" lang="pa">{e(lead)}</h1>
      {'<p class="also g" lang="pa">' + e(rest.replace(' · ', '। ')) + '</p>' if rest else ''}
      <div class="acts">
        <button class="btn sun" type="button" data-video-target="hero-screen"><svg class="icon"><use href="#i-play"/></svg>Watch now</button>
        <a class="btn ghost" href="{u('listen/')}">Browse {sum(len(s['tracks']) for s in k['audio'].get('series', [])):,} recordings</a>
      </div>
      {('<p class="hthemes">Topics: ' + ', '.join(f'<a href="{topic_url(t)}">{e(t["title"].split(":")[0])}</a>' for t in theme_hits[:5]) + '</p>') if theme_hits else ''}
    </div>
    <div class="hero-screen" id="hero-screen">
      <button type="button" class="thumb" data-video="{e(v['id'])}" aria-label="Play video: {e(title)}">
        <img alt="" src="https://i.ytimg.com/vi/{e(v['id'])}/hqdefault.jpg" width="480" height="360" fetchpriority="high">
        <span class="mini big" aria-hidden="true"><svg><use href="#i-play"/></svg></span></button>
    </div>"""
    qs = "".join(f'<li><a href="{u("themes/" + t["slug"] + "/")}"><span class="g" lang="pa">{e(t["gurmukhi"])}</span><span class="q">{e(t["question"])}</span></a></li>' for t in k["themes"])
    vids = "".join(video_card(x, small=True) for x in k["videos"][1:7])
    shelves = []
    for sh in k["texts"]["shelves"]:
        n = sum(len(k["series_by_id"][sid]["tracks"]) for sid in sh["series"] if sid in k["series_by_id"])
        shelves.append(f'<li><a href="{u("listen/")}#{sh["id"]}"><span class="g" lang="pa">{e(sh["gurmukhi"])}</span><b>{e(sh["title"])}</b><span>{n:,} recordings</span></a></li>')
    today = date.today().isoformat()
    progs = [p for p in k["programmes"] if (p.get("end") or p.get("date", "")) >= today][:4]
    progh = ""
    if progs:
        cards = "".join(f'<li><b>{fdate(p["date"]) or e(p["date"])}</b><span>{e(p.get("title") or p.get("place"))}</span>'
                        f'{"<span>" + e(p["place"]) + "</span>" if p.get("title") and p.get("place") else ""}'
                        f'{"<a href=" + chr(34) + e(p["link"]) + chr(34) + " target=_blank rel=noopener>Details</a>" if p.get("link") else ""}</li>' for p in progs)
        progh = f'<section class="wrap band progs"><h2>Upcoming programmes</h2><ul>{cards}</ul></section>'
    body = f"""
<section class="hero">
  <div class="wrap hero-grid">{hero_video}</div>
  <div class="horizon" aria-hidden="true"></div>
</section>
<section class="wrap band journey-band">
  <div class="h-row"><h2>The journey from manmukh to gurmukh</h2><a href="{u('journey/')}">Begin the journey</a></div>
  <p>Seven steps, from life facing the self to the realm of truth, following the map Guru Nanak Dev Ji gives in Japji Sahib, with Babaji’s katha of each pauri.</p>
  {journey_path(ctx, link_base=u('journey/'))}
</section>
<section class="wrap band begin">
  <div class="begin-head"><h2>Begin with a question</h2>
  <p>Each theme starts from a question, then opens into Gurbani, Babaji’s katha and your own reflection. Or <a href="{u('topics/')}">find a topic</a> and the katha that speaks to it.</p></div>
  <ul class="qlist">{qs}</ul>
</section>
<div data-continue class="wrap band continue" hidden><h2>Continue listening</h2><div class="rows"></div></div>
<section class="wrap band"><div class="h-row"><h2>Recent divans</h2><a href="{u('latest/')}">All audio and video, newest first</a></div><div class="vgrid">{vids}</div></section>
<section class="wrap band library-teaser"><div class="h-row"><h2>The katha library</h2><a href="{u('listen/')}">Open the library</a></div><ul class="shelfnav">{''.join(shelves)}</ul></section>
{progh}
<section class="wrap band lineage-teaser">
  {portrait("babaji", "Sant Baba Jagjit Singh Ji, seated cross-legged in white", "", sizes="(max-width: 760px) 60vw, 240px")}
  <div><h2>Sant Ashram, Sultanpur Lodhi</h2>
  <p>Sant Baba Jagjit Singh Ji is based at the Sant Ashram in Sultanpur Lodhi, Punjab, and gives katha of Gurbani in Punjab and abroad. He stands in the lineage of Sant Jawala Singh Ji, who founded Dera Sant Ghar, Harkhowal, in 1918, and of the mahapurakhs of Hoti Mardan.</p>
  <p><a href="{u('about/')}">About Babaji and the Dera</a></p></div>
</section>"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": k["config"].get("site_name"), "url": k["config"].get("site_url"),
          "potentialAction": {"@type": "SearchAction", "target": k["config"].get("site_url", "") + "/search/?q={q}", "query-input": "required name=q"}}
    page(ctx, "", k["config"].get("site_name", "Harkhowal Online"), body,
         "Katha and Gurmat vichar by Sant Baba Jagjit Singh Ji Harkhowal Wale: thousands of recordings, the latest divans, and themes that connect Gurbani with everyday life.",
         jsonld=ld)


def portrait(name, alt, caption, sizes="(max-width: 900px) 92vw, 400px", lazy=True):
    small, large = PHOTOS[name]
    return (f'<figure class="portrait"><img src="{u(f"assets/images/{name}-{small[0]}.jpg")}" '
            f'srcset="{u(f"assets/images/{name}-{small[0]}.jpg")} {small[0]}w, {u(f"assets/images/{name}-{large[0]}.jpg")} {large[0]}w" '
            f'sizes="{sizes}" width="{small[0]}" height="{small[1]}" alt="{e(alt)}"{" loading=\"lazy\"" if lazy else ""} decoding="async">'
            f'{"<figcaption>" + e(caption) + "</figcaption>" if caption else ""}</figure>')


# (width, height) of the prepared sizes in assets/images
PHOTOS = {"babaji": ((440, 471), (800, 856)), "babaji-standing": ((440, 587), (800, 1067)), "sant-jawala-singh-ji": ((400, 485), (720, 873))}


def build_about(ctx):
    k = ctx["k"]
    a = k["about"]
    s = a["sections"]
    lineage = """<ol class="lineage">
      <li><b>Bhai Daya Singh Ji</b><span>First of the Panj Pyare</span></li>
      <li><b>Sant Karam Singh Ji</b><span>Hoti Mardan</span></li>
      <li><b>Sant Aiya Singh Ji</b><span>Hoti Mardan</span></li>
      <li><b>Sant Jawala Singh Ji</b><span>Harkhowal, 1889 to 1957</span></li>
      <li><b>Sant Baba Jagjit Singh Ji</b><span>Harkhowal Wale</span></li></ol>"""
    jkatha = [(t, sr) for sr in k["audio"].get("series", []) for t in sr["tracks"] if re.search(r"Jawala|Karam Singh Ji Hoti", t["t"])]
    jk = "".join(track_row(t, sr, sub=sr["title"]) for t, sr in jkatha)
    rv = K.theme_review({"theme_by_slug": {"about": a}, "overrides": {}}, "about")
    body = f"""
<section class="page-head"><div class="wrap"><h1>About Babaji and the Dera</h1></div></section>
<div class="wrap about">
  <div class="col">
    {portrait("babaji-standing", "Sant Baba Jagjit Singh Ji standing outdoors in white, with a white turban, a fawn cardigan and a red garland", "Sant Baba Jagjit Singh Ji Harkhowal Wale", lazy=False)}
    {md(s.get('babaji', ''), ctx)}
    <h2>Dera Sant Ghar</h2>{md(s.get('dera', ''), ctx)}
    <h2>Sant Jawala Singh Ji</h2>
    {portrait("sant-jawala-singh-ji", "Painted portrait of Sant Jawala Singh Ji seated in meditation, wearing a garland", "Sant Jawala Singh Ji (1889 to 1957), founder of Dera Sant Ghar. A painted portrait.")}
    {md(s.get('jawala-singh', ''), ctx)}
    {('<div class="rows" data-queue>' + jk + '</div>') if jk else ''}
    <p class="gloss solo"><b>About this page</b><span>{e(rv.get('by', ''))}. Corrections are welcome at {e(k['config'].get('contact_email'))}.</span></p>
    <h2>Contact</h2>{md(s.get('contact', ''), ctx)}
  </div>
  <aside class="side"><h2>Lineage</h2>{md(s.get('lineage', ''), ctx)}{lineage}</aside>
</div>"""
    ld = {"@context": "https://schema.org", "@type": "Person", "name": "Sant Baba Jagjit Singh Ji Harkhowal Wale",
          "url": k["config"].get("site_url", "") + "/about/", "sameAs": [v for v in k["config"].get("social", {}).values() if v]}
    page(ctx, "about/", "About Babaji and the Dera", body, a["summary"], section="about", jsonld=ld)


STATE_TEXT = {"ok": "Working", "partial": "Working, with a problem", "kept-previous": "Unreachable, kept previous data",
              "failed": "Failed", "not-configured": "Not set up", "needs-credentials": "Needs permission", "disabled": "Turned off"}


def build_sources(ctx):
    k = ctx["k"]
    sync = k["sync"].get("sources", {})
    rows = []
    for src in k["config"].get("sources", []):
        st = sync.get(src["id"], {})
        state = st.get("state") or src.get("state") or "not-run"
        rows.append(f'<tr><th scope="row">{e(src.get("title"))}<span>{e(src.get("kind", ""))}</span></th>'
                    f'<td><span class="state s-{e(state)}">{e(STATE_TEXT.get(state, "Not run yet"))}</span>'
                    f'{"<span>Last success " + fdate(st.get("last_success", "")[:10]) + "</span>" if st.get("last_success") else ""}</td>'
                    f'<td>{e(src.get("method", ""))}{" " + e(src.get("note", "")) if src.get("note") else ""}</td></tr>')
    feeds = [s for s in k["config"].get("sources", []) if s.get("adapter") == "feed"]
    body = f"""
<section class="page-head"><div class="wrap"><h1>Sources and how this site works</h1>
<p class="lede">What comes from where, how it gets here, and how to tell Gurbani, Babaji’s katha and our own writing apart.</p></div></section>
<div class="wrap prose">
  <h2>Where the material comes from</h2>
  <div class="tablewrap" tabindex="0" role="region" aria-label="Sources, scrollable"><table class="srctable"><thead><tr><th scope="col">Source</th><th scope="col">Status</th><th scope="col">How it is connected</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
  <p>A source is shown as working only when its last automatic run succeeded. {('Status last checked ' + e(fdate(k['sync'].get('updated', '')[:10])) + '.') if k['sync'].get('updated') else 'The automatic update has not run on this copy of the site yet.'}{'' if feeds else ' No outside feeds are connected yet.'}</p>

  <h2>What each kind of text is</h2>
  <dl class="kinds">
    <div><dt><span class="kind k-gurbani">Gurbani</span></dt><dd>The Guru’s Word, shown in Gurmukhi with its Ang, bani and author. Each line is checked against BaniDB; lines not yet confirmed say so, and lines we are less sure of stay hidden until they pass.</dd></div>
    <div><dt><span class="kind k-translation">Translation, editorial</span></dt><dd>Our own English renderings and transliterations, written for this site. They are not published translations; where a line is read in more than one way, we say so.</dd></div>
    <div><dt><span class="kind k-babaji">Babaji’s katha</span></dt><dd>Recordings and videos of Babaji. We link them to themes using their titles and the Angs they cover. We have not transcribed them, so we never summarise what Babaji said in them.</dd></div>
    <div><dt><span class="kind k-editorial">Editorial introduction</span></dt><dd>Introductions, comparisons and reflections written for this site with AI assistance. They are labelled on every page and held as awaiting review until a learned reader has checked them.</dd></div>
    <div><dt><span class="kind k-external">Other teachers and makers</span></dt><dd>Material by others, chosen by the Dera’s sevadars, always credited and linked rather than copied.</dd></div>
  </dl>

  <h2>Comparisons with other traditions</h2>
  <p>Babaji’s katha includes Vedanta, Yoga, Buddhist and other classical texts. Where the site compares them with Gurbani, it names the tradition and text, explains both the connection and the difference, and keeps Gurmat as the frame. Similar words do not always mean the same thing.</p>

  <h2>Privacy</h2>
  <p>This site sets no cookies and uses no analytics. To remember where you stopped in a recording, your browser keeps your listening positions on your own device; they are never sent anywhere. Videos load from YouTube’s privacy-enhanced domain only when you press play.</p>
  <p><button type="button" class="btn plain" data-forget>Forget my listening history on this device</button></p>

  <h2>Credits</h2>
  <p>Audio recordings are hosted by Gurmatveechar.com. Gurbani text is checked using BaniDB by the Khalis Foundation. Links to read a full Ang open SikhiToTheMax.</p>
</div>"""
    page(ctx, "sources/", "Sources and how this site works", body, "Where Harkhowal Online's material comes from, how it is checked, and how Gurbani, Babaji's katha and editorial writing are distinguished.")


def build_review(ctx):
    """Editorial queue. Not indexed. Generates override JSON for content/editorial/overrides.json."""
    k = ctx["k"]
    links = ctx["links"]
    titles = {}
    for v in k["videos"]:
        titles["yt:" + v["id"]] = ("Video", v["title"], f"https://www.youtube.com/watch?v={v['id']}")
    for s in k["audio"].get("series", []):
        titles["s:" + s["id"]] = ("Series", s["title"], u("listen/" + s["id"] + "/"))
        for t in s["tracks"]:
            titles[t["id"]] = ("Recording", f'{t["t"]} ({s["title"]})', u("listen/" + s["id"] + "/"))
    auto = {}
    for iid, th in links.items():
        for slug, info in th.items():
            if info["via"] in ("curated",):
                continue
            auto.setdefault(slug, []).append({"id": iid, "via": info["via"], "confirmed": info["confirmed"],
                                              "kind": titles.get(iid, ("Item", iid, ""))[0], "title": titles.get(iid, ("", iid, ""))[1],
                                              "url": titles.get(iid, ("", "", ""))[2]})
    untagged = [{"id": "yt:" + v["id"], "title": v["title"], "date": v.get("published", "")} for v in k["videos"][:40] if not links.get("yt:" + v["id"])]
    gb = []
    for gid, line in k["gurbani"].items():
        show, state = K.gurbani_state(line, k["verification"], k["overrides"])
        v = k["verification"].get(gid, {})
        gb.append({"id": gid, "ang": line["source"].get("ang"), "bani": line["source"].get("bani"), "state": state, "shown": show,
                   "reason": v.get("reason", ""), "checked": v.get("checked", ""), "gurmukhi": line["gurmukhi"]})
    data = {
        "overrides": k["overrides"],
        "themes": [{"slug": t["slug"], "title": t["title"], "gurmukhi": t["gurmukhi"], "review": K.theme_review(k, t["slug"])} for t in k["themes"]],
        "topics": [{"slug": t["id"], "title": t["title"] + (" (in depth)" if t["kind"] == "theme" else ""), "gurmukhi": t["gurmukhi"]} for t in k["topics"]],
        "auto": auto, "untagged": untagged, "gurbani": gb,
        "pending": [{"id": i["id"], "title": i["title"], "link": i["link"], "feed": i["feed"], "date": i.get("published", ""), "summary": i.get("summary", "")}
                    for i in K.pending_feed_items(k)],
        "sync": k["sync"], "sources": k["config"].get("sources", []),
        "edit_url": f"https://github.com/{k['config'].get('repository', '')}/edit/main/content/editorial/overrides.json",
    }
    write("review/data.json", json.dumps(data, ensure_ascii=False))
    body = f"""
<section class="page-head"><div class="wrap"><h1>Editorial review</h1>
<p class="lede">For the Dera’s editors. Confirm or remove automatic theme links, approve imported items, check Gurbani verification and record theme reviews. Changes are collected below as a block of text to paste into <code>content/editorial/overrides.json</code> on GitHub; the site rebuilds itself after you save.</p></div></section>
<div class="wrap review" data-review data-src="{u('review/data.json')}"><p class="empty">Loading the review queue…</p></div>"""
    page(ctx, "review/", "Editorial review", body, "Editorial review queue.", noindex=True)


TITLE_DATE = re.compile(r"\b((?:19|20)\d\d)-(\d\d)-(\d\d)\b")
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def latest_items(k):
    """Every recording and video, newest first.

    Recordings are dated by when they were added to Gurmatveechar (they arrive in batches);
    within a batch the later parts come first. Where a title carries the divan's own date,
    it is kept as 'r' and shown alongside.
    """
    items = []
    for s in k["audio"].get("series", []):
        for t in s["tracks"]:
            m = TITLE_DATE.search(t["t"])
            items.append({"k": "a", "t": t["t"], "s": s["title"] + (", " + t["g"] if t.get("g") else ""), "sg": s.get("gurmukhi", ""),
                          "sid": s["id"], "p": t["p"], "d": t.get("d", ""), "r": "-".join(m.groups()) if m else "", "i": t["i"]})
    for v in k["videos"]:
        items.append({"k": "v", "t": v["title"].replace(" || ", ". ").replace("||", ". "), "id": v["id"], "d": v.get("published", ""), "r": "", "i": 0})
    items.sort(key=lambda x: (x["d"], x["k"] == "v", x["r"], x["i"]), reverse=True)
    return items


def latest_row(x):
    if x["k"] == "v":
        lang = "pa" if re.search("[\u0A00-\u0A7F]", x["t"]) else "en"
        return (f'<button type="button" class="row vrow" data-vrow="{e(x["id"])}" aria-expanded="false">'
                f'<span class="vt" aria-hidden="true"><img loading="lazy" alt="" src="https://i.ytimg.com/vi/{e(x["id"])}/mqdefault.jpg" width="320" height="180"></span>'
                f'<span class="t"><b lang="{lang}">{e(x["t"])}</b><span>Video</span></span><span class="d">{fdate(x["d"])}</span></button>')
    t = {"t": x["t"], "p": x["p"], "d": x["d"], "i": x["i"]}
    s = {"title": x["s"], "id": x["sid"], "gurmukhi": x["sg"]}
    sub = x["s"] + (f", divan of {fdate(x['r'])}" if x["r"] else "")
    return track_row(t, s, sub=sub)


def build_latest(ctx):
    k = ctx["k"]
    items = latest_items(k)
    # compact form: a series table, then rows [d, title, video id] or [d, title, series index, path, divan date]
    series = {s["id"]: i for i, s in enumerate(k["audio"].get("series", []))}
    rows_json = [[x["d"], x["t"], x["id"]] if x["k"] == "v" else [x["d"], x["t"], series[x["sid"]], x["p"], x["r"], x["s"]] for x in items]
    write("latest/index.json", json.dumps({"series": [[s["id"], s["title"], s.get("gurmukhi", "")] for s in k["audio"].get("series", [])],
                                           "items": rows_json}, ensure_ascii=False, separators=(",", ":")))
    first, month, rows = items[:60], None, []
    for x in first:
        mlabel = f"{MONTHS_LONG[int(x['d'][5:7]) - 1]} {x['d'][:4]}" if x["d"] else "Undated"
        if mlabel != month:
            month = mlabel
            rows.append(f'<h2 class="month">{e(mlabel)}</h2>')
        rows.append(latest_row(x))
    na = sum(1 for x in items if x["k"] == "a")
    nv = len(items) - na
    body = f"""
<section class="page-head"><div class="wrap">
  <h1>Latest</h1>
  <p class="lede">All of Babaji’s katha as it arrives, newest first: videos from the YouTube channel and recordings added to Gurmatveechar. To search by theme or idea, use <a href="{u('search/')}">Search</a>.</p>
  <div class="latest-tools">
    <div class="seg" role="group" aria-label="Show">
      <button type="button" aria-pressed="true" data-lk="">All <span>{len(items):,}</span></button>
      <button type="button" aria-pressed="false" data-lk="a">Audio <span>{na:,}</span></button>
      <button type="button" aria-pressed="false" data-lk="v">Video <span>{nv:,}</span></button>
    </div>
    <label class="filter"><svg class="icon" aria-hidden="true"><use href="#i-search"/></svg><input id="lq" type="search" placeholder="Filter titles, in English or Gurmukhi" aria-label="Filter titles" autocomplete="off"></label>
  </div>
</div></section>
<div class="wrap latest" data-latest data-src="{u('latest/index.json')}">
  <p class="latest-count" aria-live="polite">Showing the newest {len(first)} of {len(items):,}.</p>
  <div class="rows" data-queue>{''.join(rows)}</div>
  <p class="more"><button type="button" class="btn plain" data-more>Show more</button></p>
</div>"""
    page(ctx, "latest/", "Latest katha, newest first", body,
         "Every katha recording and video by Sant Baba Jagjit Singh Ji Harkhowal Wale, newest first, with a simple filter for audio, video and titles.",
         section="latest")


def build_search(ctx):
    k = ctx["k"]
    links = ctx["links"]
    idx = []

    def add(kind, title, sub, url, text, themes=(), extra=None):
        idx.append([kind, title, sub, url, K.fold(text), " ".join(themes), extra or ""])

    for t in k["themes"]:
        add("theme", f"{t['title']}", t["subtitle"], u("themes/" + t["slug"] + "/"),
            " ".join([t["title"], t["gurmukhi"], t["question"], t["summary"], " ".join(t.get("terms", [])),
                      " ".join(x.lstrip("=") for x in t["match"].get("gurmukhi", []))]), [t["slug"]], t["gurmukhi"])
    for s in k["audio"].get("series", []):
        prof = k["texts"]["profiles"].get(s["id"], {})
        add("series", prof.get("text") or s["title"], f"{len(s['tracks']):,} recordings", u("listen/" + s["id"] + "/"),
            " ".join([s["title"], s.get("gurmukhi", ""), prof.get("text", ""), prof.get("author", ""), prof.get("tradition", "")]),
            links.get("s:" + s["id"], {}).keys(), s.get("gurmukhi", ""))
        for t in s["tracks"]:
            add("rec", t["t"], s["title"] + (", " + t["g"] if t.get("g") else ""), u("listen/" + s["id"] + "/"),
                " ".join([t["t"], t.get("g", ""), s["title"], s.get("gurmukhi", "")]),
                list(links.get(t["id"], {}).keys()) + list(links.get("s:" + s["id"], {}).keys()),
                {"p": t["p"], "sid": s["id"], "s": s["title"], "sg": s.get("gurmukhi", ""), "d": t.get("d", "")})
    for v in k["videos"]:
        add("video", v["title"].replace("||", "."), "Video, " + fdate(v.get("published")), "https://www.youtube.com/watch?v=" + v["id"],
            v["title"] + " " + v.get("description", ""), links.get("yt:" + v["id"], {}).keys(), {"id": v["id"]})
    for x in k["external"]["items"]:
        if x.get("status") == "published":
            add("external", x["title"], x["creator"], ext_url(x), x["title"] + " " + x["creator"], x.get("themes", []))
    add("page", "About Babaji and the Dera", "Sant Jawala Singh Ji, Dera Sant Ghar, lineage", u("about/"),
        "about babaji dera sant ghar harkhowal jawala singh hoti mardan lineage history contact ਹਰਖੋਵਾਲ")
    for tp in k["topics"]:
        if tp["kind"] != "theme":
            add("topic", tp["title"], tp.get("about", ""), topic_url(tp),
                " ".join([tp["title"], tp["gurmukhi"], tp.get("about", "")] + tp.get("aliases", [])), [tp["id"]], tp["gurmukhi"])
    j = k["journey"]
    add("theme", j["title"], j["subtitle"], u("journey/"), " ".join([j["title"], j["gurmukhi"], j["summary"]] + j["terms"]), ["journey"], j["gurmukhi"])
    for i, st in enumerate(j["stages"]):
        add("topic", f"{st['short']}: {st['title']}", f"Step {i + 1} of the journey from manmukh to gurmukh", u("journey/") + "#" + st["id"],
            " ".join([st["title"], st["gurmukhi"], st["short"], st["id"].replace("-", " "), st["source"]]), ["journey"], st["gurmukhi"])
    terms = {tp["id"]: [K.fold(x) for x in [tp["title"], tp["gurmukhi"]] + tp.get("aliases", []) + [g.lstrip("=") for g in tp.get("match", {}).get("gurmukhi", [])]]
             for tp in k["topics"]}
    terms["journey"] = [K.fold(x) for x in [j["title"], j["gurmukhi"]] + j["terms"]]
    write("search/index.json", json.dumps({"items": idx, "themes": terms,
                                           "names": {**{tp["id"]: [tp["title"], tp["gurmukhi"]] for tp in k["topics"]}, "journey": [j["title"], j["gurmukhi"]]}}, ensure_ascii=False, separators=(",", ":")))
    body = f"""
<section class="page-head"><div class="wrap"><h1>Search</h1>
<form class="bigsearch" role="search" data-search-form><label class="sr" for="sq">Search</label>
<svg class="icon" aria-hidden="true"><use href="#i-search"/></svg><input id="sq" name="q" type="search" placeholder="Try ego, ਹੁਕਮ, Japji, Vichar Sagar, 1990" autocomplete="off"></form>
<div class="chips" role="group" aria-label="Filter results" data-kind-filter>
<button type="button" class="chip" aria-pressed="true" data-kind="">Everything</button>
<button type="button" class="chip" aria-pressed="false" data-kind="topic">Topics</button>
<button type="button" class="chip" aria-pressed="false" data-kind="series">Series</button>
<button type="button" class="chip" aria-pressed="false" data-kind="rec">Recordings</button>
<button type="button" class="chip" aria-pressed="false" data-kind="video">Videos</button></div>
</div></section>
<div class="wrap search-results" data-search data-src="{u('search/index.json')}" aria-live="polite"><p class="hint">Search Babaji’s katha, videos and themes in English, Punjabi or transliteration. Searching a topic in any language, such as ‘ego’, ‘ਹੰਕਾਰ’ or ‘Sangrand’, also finds the katha linked to it.</p></div>"""
    page(ctx, "search/", "Search", body, "Search Babaji's katha recordings, videos and themes in English or Gurmukhi.")


REDIRECTS = {
    "shabadguru": "themes/shabad-guru/", "sants-gurmukhs": "about/", "sggs-katha": f"listen/{SGGS}/",
    "srigurpartapsurajgranth": "listen/sri-gurpartap-suraj-parkash-katha/", "nitnem-banis-katha": "listen/nitnem-bani-katha/",
    "bhai-gurdas": "listen/bhai-gurdas-di-vaaran-di-katha/", "misc-katha": "listen/", "babaji-videos": "watch/",
    "jeevan-videos": "watch/", "sikhi-videos": "watch/", "literature": "about/",
}


def build_redirects(ctx):
    """Permanent redirects from the old Wix addresses, in Cloudflare's _redirects format."""
    lines = ["# Old harkhowal.com (Wix) addresses -> their new homes"]
    for old, new in REDIRECTS.items():
        for src in (f"/{old}", f"/{old}/"):
            lines.append(f"{BASE}{src.lstrip('/')} {u(new)} 301")
    lines += ["# The themes index became the topic index", f"{BASE}themes {u('topics/')} 301", f"{BASE}themes/ {u('topics/')} 301"]
    (OUT / "_redirects").write_text("\n".join(lines) + "\n", encoding="utf-8")


# Security headers and caching, in Cloudflare's _headers format. The Content-Security-Policy
# allows exactly what the site uses: its own files, Google Fonts, YouTube thumbnails and the
# privacy-enhanced YouTube player, and audio streamed over HTTPS (Gurmatveechar).
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data: https://i.ytimg.com; media-src https:; "
       "frame-src https://www.youtube-nocookie.com; connect-src 'self'; base-uri 'self'; form-action 'self'; "
       "frame-ancestors 'self'; object-src 'none'")


def build_headers(ctx):
    rules = {
        "/*": ["X-Content-Type-Options: nosniff", "Referrer-Policy: strict-origin-when-cross-origin",
               "Permissions-Policy: camera=(), microphone=(), geolocation=()",
               f"Content-Security-Policy: {CSP}", "Strict-Transport-Security: max-age=31536000"],
        f"{BASE}assets/*": ["Cache-Control: public, max-age=31536000, immutable"],
        f"{BASE}search/index.json": ["Cache-Control: public, max-age=3600"],
        f"{BASE}review/*": ["X-Robots-Tag: noindex, nofollow", "Cache-Control: no-store"],
        # The temporary workers.dev address (and branch previews) stay out of search engines;
        # harkhowal.com, once attached, is indexed normally.
        "https://:worker.:account.workers.dev/*": ["X-Robots-Tag: noindex"],
    }
    text = "".join(f"{path}\n" + "".join(f"  {h}\n" for h in hs) for path, hs in rules.items())
    (OUT / "_headers").write_text(text, encoding="utf-8")


def build_404(ctx):
    body = f"""<section class="page-head"><div class="wrap"><h1>This page isn’t here</h1>
<p class="lede">It may have moved when the site was rebuilt. Try <a href="{u('search/')}">searching</a>, or start from <a href="{u('topics/')}">the topics</a> or <a href="{u('listen/')}">the katha library</a>.</p></div></section>"""
    page(ctx, "404.html", "Page not found", body, "Page not found.", noindex=True)


def build_meta(ctx):
    site = ctx["k"]["config"].get("site_url", "").rstrip("/")
    urls = "".join(f"<url><loc>{e(site + '/' + p)}</loc></url>" for p in ctx["sitemap"])
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nDisallow: {BASE}review/\nSitemap: {site}/sitemap.xml\n", encoding="utf-8")
    build_headers(ctx)
    manifest = json.loads((ROOT / "assets" / "manifest.webmanifest").read_text(encoding="utf-8"))
    manifest["start_url"], manifest["scope"] = BASE, BASE
    for icon in manifest["icons"]:
        icon["src"] = u(icon["src"])
    (OUT / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


def build(out=None):
    global OUT
    if out:
        OUT = Path(out)
    k = K.load_all()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    ver = hashlib.sha1(b"".join((ROOT / "assets" / f).read_bytes() for f in ("site.css", "site.js"))).hexdigest()[:8]
    updated = max([x for x in (k["audio"].get("updated", ""), k["sync"].get("updated", "")[:10]) if x] or [date.today().isoformat()])
    ctx = {"k": k, "links": K.classify_topics(k), "katha_idx": K.katha_index(k["audio"].get("series", [])), "sitemap": [], "ver": ver,
           "updated": fdate(updated), "gurbani_log": {}}
    build_home(ctx)
    build_topics(ctx)
    build_journey(ctx)
    for th in k["themes"]:
        build_theme(ctx, th)
    build_listen(ctx)
    build_watch(ctx)
    build_latest(ctx)
    build_about(ctx)
    build_sources(ctx)
    build_search(ctx)
    build_review(ctx)
    build_redirects(ctx)
    build_404(ctx)
    build_meta(ctx)
    return ctx


if __name__ == "__main__":
    c = build()
    pages = len(c["sitemap"])
    print(f"Built {pages} indexed pages into {OUT} (base {BASE})")
