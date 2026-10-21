"""Babaji's katha folder on Gurmatveechar.com.

Gurmatveechar publishes folder listings as ordinary web pages and serves the
MP3s directly. This adapter reads the listings politely (one page a second,
capped per run), records each file once, and looks up each new file's upload
date once (HTTP HEAD, Last-Modified). Audio is never copied: the site streams
it from Gurmatveechar and credits them.
"""
import html
import re
import time
import urllib.parse
from email.utils import parsedate_to_datetime

from .common import SourceResult, load, request, save, today

GMV = "https://www.gurmatveechar.com"
MAX_PAGES = 150
PAGE_DELAY = 1.0
MAX_HEADS = 3000
HEAD_DELAY = 0.15

FOLDER_RE = re.compile(r'href=["\']?([^"\'\s>]*audio\.php\?q=f&(?:amp;)?f=([^"\'\s>&#]+))', re.I)
MP3_RE = re.compile(r'href=["\']?([^"\'\s>]*?/audios/[^"\'\s>]+?\.mp3)', re.I)


def folder_url(path):
    return f"{GMV}/audio.php?q=f&f={urllib.parse.quote_plus(path)}"


def mp3_url(path):
    return f"{GMV}/audios{urllib.parse.quote(path)}"


def nice(segment):
    s = urllib.parse.unquote_plus(segment)
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip()


def track_title(mp3_path):
    name = urllib.parse.unquote(mp3_path.rsplit("/", 1)[-1])
    name = re.sub(r"\.mp3$", "", name, flags=re.I)
    name = re.sub(r"^(\d+--)?Baba\.Jagjit\.Singh\.\(Harkhowal\.wale\)--", lambda m: (m.group(1) or "").replace("--", " "), name)
    name = name.replace("--", " – ").replace("_", " ").replace(".", " ")
    name = re.sub(r"^(\d+)\s+(?=\S)", r"\1 ", name)
    return re.sub(r"\s+", " ", name).strip()


def parse_listing(page_html, current_path):
    """Return (child_folder_paths, mp3_paths) directly under current_path."""
    page_html = html.unescape(page_html)
    cur = current_path.rstrip("/")
    folders, files = [], []
    for _, enc in FOLDER_RE.findall(page_html):
        p = urllib.parse.unquote_plus(enc)
        if p.startswith(cur + "/") and "/" not in p[len(cur) + 1:] and p not in folders:
            folders.append(p)
    for href in MP3_RE.findall(page_html):
        p = urllib.parse.unquote(urllib.parse.urlparse(href).path)
        rel = p[len("/audios"):] if p.startswith("/audios") else p
        if rel.rsplit("/", 1)[0] == cur and rel not in files:
            files.append(rel)
    return folders, files


class Crawler:
    def __init__(self, fetch=request, delay=PAGE_DELAY, max_pages=MAX_PAGES):
        self.fetch, self.delay, self.max_pages, self.pages = fetch, delay, max_pages, 0

    def crawl(self, path, depth=0):
        if self.pages >= self.max_pages:
            raise RuntimeError("page cap reached")
        self.pages += 1
        if self.pages > 1 and self.delay:
            time.sleep(self.delay)
        folders, files = parse_listing(self.fetch(folder_url(path)), path)
        node = {"path": path, "files": files, "children": []}
        if depth < 3:
            for f in folders:
                node["children"].append(self.crawl(f, depth + 1))
        return node


def flatten(node, group=""):
    items = [(f, group) for f in node["files"]]
    for c in node["children"]:
        g = nice(c["path"].rsplit("/", 1)[-1])
        items += flatten(c, f"{group} · {g}" if group else g)
    return items


def category_for(cfg, path):
    for cat in cfg.get("audio_categories", []):
        if any(m.lower() in path.lower() for m in cat["match"]):
            return cat["name"]
    return "Other"


def upload_date(path, fetch=request):
    try:
        lm = fetch(mp3_url(path), method="HEAD", retries=1).get("Last-Modified")
        return parsedate_to_datetime(lm).strftime("%Y-%m-%d") if lm else ""
    except Exception:
        return ""


def build_series(cfg, root, tree, known, head=upload_date, max_heads=MAX_HEADS, head_delay=HEAD_DELAY):
    gur = cfg.get("series_gurmukhi", {})
    groups = [(c["path"], flatten(c)) for c in tree["children"]]
    if tree["files"]:
        groups.append((root + "/__single", [(f, "") for f in tree["files"]]))
    heads, series = 0, []
    for spath, items in groups:
        seg = spath.rsplit("/", 1)[-1]
        tracks = []
        for full, group in items:
            d = known.get(full, "")
            if not d and heads < max_heads:
                heads += 1
                if head_delay:
                    time.sleep(head_delay)
                d = head(full)
            t = {"p": full[len(root) + 1:], "t": track_title(full), "d": d}
            if group:
                t["g"] = group
            tracks.append(t)
        single = seg == "__single"
        series.append({
            "id": re.sub(r"[^a-z0-9]+", "-", ("single-divans" if single else seg).lower()).strip("-"),
            "title": "Single divans" if single else nice(seg),
            "gurmukhi": gur.get("__single" if single else seg, ""),
            "category": "Single divans" if single else category_for(cfg, spath),
            "page": folder_url(root if single else spath),
            "latest": max((t["d"] for t in tracks), default=""),
            "tracks": tracks,
        })
    return series, heads


def run(cfg, source, fetch=request, crawler=None, head=None):
    root = cfg.get("gurmatveechar_root")
    if not root:
        return SourceResult("not-configured", "No gurmatveechar_root in config.json")
    old = load("audio.json", {"series": []})
    known = {}
    for s in old.get("series", []):
        for t in s.get("tracks", []):
            if "p" in t:
                known[root + "/" + t["p"]] = t.get("d", "")
    cr = crawler or Crawler(fetch=fetch)
    try:
        tree = cr.crawl(root)
    except Exception as e:
        return SourceResult("kept-previous", f"Crawl stopped: {e}", {"recordings": len(known)})
    series, heads = build_series(cfg, root, tree, known, head=head or (lambda p: upload_date(p, fetch)))
    new_total = sum(len(s["tracks"]) for s in series)
    if known and new_total < len(known) * 0.5:
        return SourceResult("kept-previous", f"Only {new_total} of {len(known)} recordings found; kept previous data",
                            {"recordings": len(known)})
    save("audio.json", {"updated": today(), "base": GMV + "/audios" + urllib.parse.quote(root) + "/",
                        "source": folder_url(root), "series": series}, compact=True)
    added = sum(1 for s in series for t in s["tracks"] if root + "/" + t["p"] not in known)
    return SourceResult("ok", f"{len(series)} series, {new_total} recordings, {cr.pages} pages read, {heads} dates looked up",
                        {"series": len(series), "recordings": new_total, "new": added})
