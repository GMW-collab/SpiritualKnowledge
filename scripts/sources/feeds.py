"""Generic RSS 2.0 / Atom feeds: other channels, blogs, publications.

Add a source to config.json like:
  {"id": "feed:example", "adapter": "feed", "title": "Example", "url": "https://example.org/feed.xml",
   "auto_publish": false, "creator": "Name of the teacher or publisher", "terms": "how we may use it"}

Imported items are never published automatically unless auto_publish is true.
They wait on the Review page until an editor approves them (content/editorial/overrides.json).
Only the title, link, date, author and a short plain-text summary are kept;
the site links to the original rather than copying it.
"""
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .common import SourceResult, load, request, save, today

ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"
SUMMARY_CHARS = 280


def plain(s, limit=SUMMARY_CHARS):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", html.unescape(s)).strip()
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def date_of(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    if re.match(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except Exception:
        return ""


def safe_link(u):
    u = (u or "").strip()
    return u if u.lower().startswith(("https://", "http://")) else ""


def parse(xml_text):
    root = ET.fromstring(xml_text)
    items = []
    if root.tag == ATOM + "feed":
        for e in root.findall(ATOM + "entry"):
            link = ""
            for l in e.findall(ATOM + "link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
            yt = e.findtext(YT + "videoId")
            items.append({
                "guid": e.findtext(ATOM + "id") or link,
                "title": plain(e.findtext(ATOM + "title"), 200),
                "link": safe_link(link),
                "published": date_of(e.findtext(ATOM + "published") or e.findtext(ATOM + "updated")),
                "author": plain(e.findtext(f"{ATOM}author/{ATOM}name"), 120),
                "summary": plain(e.findtext(ATOM + "summary") or e.findtext(ATOM + "content")
                                 or e.findtext("{http://search.yahoo.com/mrss/}group/{http://search.yahoo.com/mrss/}description")),
                "youtube": yt or "",
            })
    else:
        ch = root.find("channel")
        for e in (ch.findall("item") if ch is not None else []):
            link = e.findtext("link") or ""
            items.append({
                "guid": e.findtext("guid") or link,
                "title": plain(e.findtext("title"), 200),
                "link": safe_link(link),
                "published": date_of(e.findtext("pubDate")),
                "author": plain(e.findtext("author") or e.findtext("{http://purl.org/dc/elements/1.1/}creator"), 120),
                "summary": plain(e.findtext("description")),
                "youtube": "",
            })
    return [i for i in items if i["title"] and i["link"]]


def item_id(feed_id, guid):
    return f"f:{feed_id.split(':', 1)[-1]}:{hashlib.sha1(guid.encode('utf-8')).hexdigest()[:12]}"


def run(cfg, source, fetch=request):
    url = source.get("url")
    if not url:
        return SourceResult("not-configured", "No url for this feed")
    store = load("feeds.json", {"items": []})
    by_id = {i["id"]: i for i in store.get("items", [])}
    try:
        fresh = parse(fetch(url))
    except Exception as e:
        return SourceResult("kept-previous", str(e))
    new = 0
    for it in fresh:
        iid = item_id(source["id"], it["guid"])
        if iid not in by_id:
            new += 1
            by_id[iid] = {"id": iid, "feed": source["id"], "first_seen": today(),
                          "auto_publish": bool(source.get("auto_publish")),
                          "creator": source.get("creator", ""), **{k: v for k, v in it.items() if k != "guid"}}
        else:
            by_id[iid].update({k: v for k, v in it.items() if k != "guid"})
        by_id[iid]["last_seen"] = today()
    items = sorted(by_id.values(), key=lambda i: i.get("published", ""), reverse=True)
    save("feeds.json", {"updated": today(), "items": items})
    return SourceResult("ok", f"{len(fresh)} in feed, {new} new", {"items": sum(1 for i in items if i['feed'] == source['id']), "new": new})
