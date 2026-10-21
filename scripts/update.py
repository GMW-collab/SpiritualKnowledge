#!/usr/bin/env python3
"""Daily content update for Harkhowal Online.

Pulls:
  * latest videos from the YouTube channel's public feed (no API key)
  * Babaji's katha series and recordings from gurmatveechar.com, with each
    file's upload date (read once per file, then remembered)
  * optionally, Babaji's programmes from a published Google Sheet (CSV)

Writes data/videos.json, data/audio.json and data/programmes.json.
Standard library only. If a source can't be reached, the previous data is
kept, so a bad day never empties the website.
"""
import csv, io, json, re, sys, time, html
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
GMV = "https://www.gurmatveechar.com"
UA = "HarkhowalOnline-updater/1.1 (+https://www.harkhowal.com; once-daily)"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d")
MAX_PAGES = 150     # Gurmatveechar folder pages per run
PAGE_DELAY = 1.0
MAX_HEADS = 3000    # upload-date lookups per run (only for files we haven't dated yet)
HEAD_DELAY = 0.15

_pages = 0


def request(url, method="GET", retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace") if method == "GET" else r.headers
        except Exception as e:
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def save(name, obj, compact=False):
    DATA.mkdir(exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if compact \
        else json.dumps(obj, ensure_ascii=False, indent=1)
    (DATA / name).write_text(txt + "\n", encoding="utf-8")


# ---------------------------------------------------------------- YouTube
def parse_youtube_feed(xml_text):
    ns = {"a": "http://www.w3.org/2005/Atom",
          "yt": "http://www.youtube.com/xml/schemas/2015",
          "media": "http://search.yahoo.com/mrss/"}
    out = []
    for e in ET.fromstring(xml_text).findall("a:entry", ns):
        vid = e.findtext("yt:videoId", default="", namespaces=ns)
        if not vid:
            continue
        desc = e.findtext("media:group/media:description", default="", namespaces=ns) or ""
        out.append({
            "id": vid,
            "title": (e.findtext("a:title", default="", namespaces=ns) or "").strip(),
            "published": (e.findtext("a:published", default="", namespaces=ns) or "")[:10],
            "description": desc.strip()[:400],
        })
    return out


def update_youtube():
    cid = CONFIG.get("youtube_channel_id")
    if not cid:
        return
    old = load("videos.json", {"videos": []})
    try:
        fresh = parse_youtube_feed(request(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
    except Exception as e:
        print(f"YouTube: kept previous data ({e})", file=sys.stderr)
        return
    by_id = {v["id"]: v for v in old.get("videos", [])}   # the feed holds 15; keep the archive growing
    for v in fresh:
        by_id[v["id"]] = v
    videos = sorted(by_id.values(), key=lambda v: v.get("published", ""), reverse=True)
    save("videos.json", {"updated": NOW, "channel_url": CONFIG.get("youtube_url", ""), "videos": videos})
    print(f"YouTube: {len(fresh)} in feed, {len(videos)} total")


# ---------------------------------------------------------- Gurmatveechar
# Links on Gurmatveechar are sometimes quoted and sometimes not, so accept both.
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
    name = re.sub(r"^Baba\.Jagjit\.Singh\.\(Harkhowal\.wale\)--", "", name)
    name = name.replace("--", " – ").replace("_", " ").replace(".", " ")
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


def crawl(path, depth=0):
    global _pages
    if _pages >= MAX_PAGES:
        raise RuntimeError("page cap reached")
    _pages += 1
    if _pages > 1:
        time.sleep(PAGE_DELAY)
    folders, files = parse_listing(request(folder_url(path)), path)
    node = {"path": path, "files": files, "children": []}
    if depth < 3:
        for f in folders:
            node["children"].append(crawl(f, depth + 1))
    return node


def flatten(node, group=""):
    items = [(f, group) for f in node["files"]]
    for c in node["children"]:
        g = nice(c["path"].rsplit("/", 1)[-1])
        items += flatten(c, f"{group} · {g}" if group else g)
    return items


def category_for(path):
    for cat in CONFIG.get("audio_categories", []):
        if any(m.lower() in path.lower() for m in cat["match"]):
            return cat["name"]
    return "Other"


def upload_date(path):
    try:
        lm = request(mp3_url(path), method="HEAD", retries=1).get("Last-Modified")
        return parsedate_to_datetime(lm).strftime("%Y-%m-%d") if lm else ""
    except Exception:
        return ""


def update_audio():
    root = CONFIG.get("gurmatveechar_root")
    if not root:
        return
    old = load("audio.json", {"series": []})
    known = {}  # full path -> upload date, remembered between runs
    for s in old.get("series", []):
        for t in s.get("tracks", []):
            if "p" in t:
                known[root + "/" + t["p"]] = t.get("d", "")

    try:
        tree = crawl(root)
    except Exception as e:
        print(f"Gurmatveechar: kept previous data ({e})", file=sys.stderr)
        return

    gur = CONFIG.get("series_gurmukhi", {})
    groups = [(c["path"], flatten(c)) for c in tree["children"]]
    if tree["files"]:
        groups.append((root + "/__single", [(f, "") for f in tree["files"]]))

    heads = 0
    series = []
    for spath, items in groups:
        seg = spath.rsplit("/", 1)[-1]
        tracks = []
        for full, group in items:
            d = known.get(full, "")
            if not d and heads < MAX_HEADS:
                heads += 1
                time.sleep(HEAD_DELAY)
                d = upload_date(full)
            t = {"p": full[len(root) + 1:], "t": track_title(full), "d": d}
            if group:
                t["g"] = group
            tracks.append(t)
        single = seg == "__single"
        series.append({
            "id": re.sub(r"[^a-z0-9]+", "-", ("single-divans" if single else seg).lower()).strip("-"),
            "title": "Single divans" if single else nice(seg),
            "gurmukhi": gur.get("__single" if single else seg, ""),
            "category": "Single divans" if single else category_for(spath),
            "page": folder_url(root if single else spath),
            "latest": max((t["d"] for t in tracks), default=""),
            "tracks": tracks,
        })

    new_total = sum(len(s["tracks"]) for s in series)
    old_total = sum(len(s.get("tracks", [])) or s.get("count", 0) for s in old.get("series", []))
    if old_total and new_total < old_total * 0.5:
        print(f"Gurmatveechar: only {new_total} of {old_total} recordings found, kept previous data", file=sys.stderr)
        return
    save("audio.json", {"updated": NOW, "base": GMV + "/audios" + urllib.parse.quote(root) + "/",
                        "source": folder_url(root), "series": series}, compact=True)
    print(f"Gurmatveechar: {len(series)} series, {new_total} recordings, {_pages} pages, {heads} dates looked up")


# ------------------------------------------------- Programmes (Google Sheet)
def update_programmes():
    url = CONFIG.get("programmes_csv_url")
    if not url:
        return
    try:
        rows = list(csv.DictReader(io.StringIO(request(url))))
    except Exception as e:
        print(f"Programmes: kept previous data ({e})", file=sys.stderr)
        return
    out = []
    for r in rows:
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        if not (r.get("date") and (r.get("place") or r.get("title"))):
            continue
        raw = r["date"]
        iso = ""
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
            try:
                iso = datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                pass
        out.append({"date": iso or raw, "end": r.get("end date", ""), "place": r.get("place", ""),
                    "title": r.get("title", ""), "link": r.get("link", "")})
    out.sort(key=lambda p: p["date"])
    save("programmes.json", {"updated": NOW, "programmes": out})
    print(f"Programmes: {len(out)}")


if __name__ == "__main__":
    for step in (update_youtube, update_audio, update_programmes):
        try:
            step()
        except Exception as e:
            print(f"{step.__name__} failed: {e}", file=sys.stderr)
