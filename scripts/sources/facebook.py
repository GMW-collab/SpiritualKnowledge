"""Facebook Page posts, through Meta's Graph API.

Needs two repository secrets, created by a Page admin (see docs/SOURCES.md):
  FACEBOOK_PAGE_ID     the numeric Page id
  FACEBOOK_PAGE_TOKEN  a long-lived Page access token with pages_read_engagement
Without them the source reports 'needs-credentials' and nothing is fetched.

Posts are stored with the feed items and wait on the Review page for approval,
because Page posts often repeat YouTube uploads or are notices not meant to last.
Only the text (shortened), date and permalink are kept; images are not copied.
"""
import hashlib
import json
import os
import urllib.parse

from .common import SourceResult, load, request, save, today
from .feeds import plain, safe_link


def parse(text):
    data = json.loads(text)
    out = []
    for p in data.get("data", []):
        msg = plain(p.get("message", ""), 280)
        link = safe_link(p.get("permalink_url", ""))
        if not (msg and link):
            continue
        first = msg.split(". ")[0]
        out.append({"guid": p.get("id", link), "title": (first if len(first) <= 120 else first[:117] + "…"), "link": link,
                    "published": (p.get("created_time") or "")[:10], "author": "", "summary": msg, "youtube": ""})
    return out


def run(cfg, source, fetch=request):
    page = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
    token = os.environ.get("FACEBOOK_PAGE_TOKEN", "").strip()
    if not (page and token):
        return SourceResult("needs-credentials", "Add FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN as repository secrets (docs/SOURCES.md).")
    version = source.get("graph_version", "v21.0")
    q = urllib.parse.urlencode({"fields": "message,permalink_url,created_time", "limit": 25, "access_token": token})
    try:
        posts = parse(fetch(f"https://graph.facebook.com/{version}/{urllib.parse.quote(page)}/posts?{q}"))
    except Exception as e:
        return SourceResult("kept-previous", str(e))
    store = load("feeds.json", {"items": []})
    by_id = {i["id"]: i for i in store.get("items", [])}
    new = 0
    for it in posts:
        iid = "f:facebook:" + hashlib.sha1(it["guid"].encode("utf-8")).hexdigest()[:12]
        if iid not in by_id:
            new += 1
            by_id[iid] = {"id": iid, "feed": source["id"], "first_seen": today(), "auto_publish": False,
                          "creator": cfg.get("site_name", ""), **{k: v for k, v in it.items() if k != "guid"}}
        by_id[iid]["last_seen"] = today()
    save("feeds.json", {"updated": today(), "items": sorted(by_id.values(), key=lambda i: i.get("published", ""), reverse=True)})
    return SourceResult("ok", f"{len(posts)} posts read, {new} new (awaiting review)", {"new": new})
