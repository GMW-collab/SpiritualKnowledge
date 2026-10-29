"""Babaji's YouTube channel.

Two methods:
  * the public Atom feed (no key; newest 15 uploads). Always used.
  * the YouTube Data API v3 (free key, set as the repository secret
    YOUTUBE_API_KEY). When present, the whole upload history is fetched
    once and then kept up to date. Quota use: about 1 unit per 50 videos.
Captions/transcripts are NOT fetched: the API only allows the channel owner
to download captions (OAuth), so that stays on the roadmap.
"""
import os
import urllib.parse
import xml.etree.ElementTree as ET
import json

from .common import SourceResult, load, request, save, today

NS = {"a": "http://www.w3.org/2005/Atom",
      "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}


def parse_feed(xml_text):
    out = []
    for e in ET.fromstring(xml_text).findall("a:entry", NS):
        vid = e.findtext("yt:videoId", default="", namespaces=NS)
        if not vid:
            continue
        desc = e.findtext("media:group/media:description", default="", namespaces=NS) or ""
        link = e.find("a:link", NS)
        href = link.get("href", "") if link is not None else ""
        out.append({
            "id": vid,
            "title": (e.findtext("a:title", default="", namespaces=NS) or "").strip(),
            "published": (e.findtext("a:published", default="", namespaces=NS) or "")[:10],
            "description": desc.strip()[:400],
            **({"short": True} if "/shorts/" in href else {}),
        })
    return out


def parse_api_page(text):
    data = json.loads(text)
    items = []
    for it in data.get("items", []):
        sn = it.get("snippet", {})
        cd = it.get("contentDetails", {})
        vid = cd.get("videoId") or sn.get("resourceId", {}).get("videoId")
        if not vid or sn.get("title") in ("Private video", "Deleted video"):
            continue
        items.append({
            "id": vid,
            "title": (sn.get("title") or "").strip(),
            "published": (cd.get("videoPublishedAt") or sn.get("publishedAt") or "")[:10],
            "description": (sn.get("description") or "").strip()[:400],
        })
    return items, data.get("nextPageToken")


def fetch_api(channel_id, key, known_ids, fetch=request, max_pages=400, prefix="UU", walk_all=False):
    """Walk an uploads playlist, newest first (UU = all uploads, UUSH = Shorts).

    Until the archive has once been read to the end (walk_all), every page is read;
    after that, the walk stops once a whole page is already known.
    Returns (items, reached_end)."""
    playlist = prefix + channel_id[2:]
    out, token = [], None
    for _ in range(max_pages):
        q = {"part": "snippet,contentDetails", "playlistId": playlist, "maxResults": 50, "key": key}
        if token:
            q["pageToken"] = token
        items, token = parse_api_page(fetch("https://www.googleapis.com/youtube/v3/playlistItems?" + urllib.parse.urlencode(q)))
        out += items
        if not token:
            return out, True
        if not walk_all and items and all(i["id"] in known_ids for i in items):
            return out, False
    return out, False


def feed_urls(channel_id):
    """The channel feed, then the same uploads as a playlist feed. YouTube sometimes answers
    404 to one of them from data-centre addresses (such as GitHub's) while the other works."""
    return [f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
            f"https://www.youtube.com/feeds/videos.xml?playlist_id=UU{channel_id[2:]}"]


def fetch_feed(channel_id, fetch=request):
    errors = []
    for url in feed_urls(channel_id):
        kind = "playlist" if "playlist_id" in url else "channel"
        try:
            items = parse_feed(fetch(url))
            if items:
                return items, errors
            errors.append(f"{kind} feed empty")
        except Exception as e:
            errors.append(f"{kind} feed {e}")
    return [], errors


def run(cfg, source, fetch=request):
    cid = cfg.get("youtube_channel_id")
    if not cid:
        return SourceResult("not-configured", "No youtube_channel_id in config.json")
    old = load("videos.json", {"videos": []})
    by_id = {v["id"]: v for v in old.get("videos", [])}
    notes, got = [], 0
    fresh, errors = fetch_feed(cid, fetch)
    got += len(fresh)
    for v in fresh:
        by_id[v["id"]] = {**by_id.get(v["id"], {}), **v}
    feed_note = "" if fresh else "feed: " + "; ".join(errors)
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    method = "feed"
    complete = bool(old.get("archive_complete"))
    shorts_complete = bool(old.get("shorts_complete"))
    api_ok = False
    if key:
        try:
            api, reached_end = fetch_api(cid, key, set(by_id), fetch=fetch, walk_all=not complete)
            got += len(api)
            method = "feed+api" if fresh else "api"
            api_ok = True
            complete = complete or reached_end
            for v in api:
                by_id[v["id"]] = {**by_id.get(v["id"], {}), **v}
        except Exception as e:
            notes.append(f"api: {e}")
        try:
            known_shorts = {i for i, v in by_id.items() if v.get("short")}
            shorts, reached_end = fetch_api(cid, key, known_shorts, fetch=fetch, prefix="UUSH", walk_all=not shorts_complete)
            shorts_complete = shorts_complete or reached_end
            for v in shorts:
                by_id[v["id"]] = {**by_id.get(v["id"], {}), **v, "short": True}
        except Exception as e:
            notes.append(f"shorts: {e}")
    # The public feed is only a problem when the API is not there to cover for it:
    # YouTube often refuses the feed to GitHub's servers while the API works.
    if feed_note and not api_ok:
        notes.insert(0, feed_note)
    if not got:
        return SourceResult("kept-previous", "; ".join(notes) or "Nothing returned", {"videos": len(by_id)})
    videos = sorted(by_id.values(), key=lambda v: v.get("published", ""), reverse=True)
    save("videos.json", {"updated": today(), "channel_url": cfg.get("youtube_url", ""), "method": method,
                         "archive_complete": complete, "shorts_complete": shorts_complete, "videos": videos})
    n_short = sum(1 for v in videos if v.get("short"))
    state = "ok" if not notes else "partial"
    return SourceResult(state, "; ".join(notes) or f"{got} fetched via {method}" + ("" if complete or not key else ", archive still being read")
                        + (" (public feed unavailable)" if feed_note and api_ok else ""),
                        {"videos": len(videos) - n_short, "shorts": n_short, "fetched": got})
