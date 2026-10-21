"""Babaji's programmes, from a Google Sheet published as CSV (File > Share > Publish to web)."""
import csv
import io
from datetime import datetime

from .common import SourceResult, request, save, today

FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y")


def to_iso(raw):
    for fmt in FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def parse(text):
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        if not (r.get("date") and (r.get("place") or r.get("title"))):
            continue
        link = r.get("link", "")
        if link and not link.lower().startswith(("https://", "http://")):
            link = ""  # never emit javascript: or other schemes from a shared sheet
        end = to_iso(r.get("end date", "")) if r.get("end date") else ""
        out.append({"date": to_iso(r["date"]) or r["date"], "end": end, "place": r.get("place", "")[:160],
                    "title": r.get("title", "")[:160], "link": link})
    out.sort(key=lambda p: p["date"])
    return out


def run(cfg, source, fetch=request):
    url = cfg.get("programmes_csv_url")
    if not url:
        return SourceResult("not-configured", "Add the sheet's published CSV link to programmes_csv_url in config.json")
    try:
        progs = parse(fetch(url))
    except Exception as e:
        return SourceResult("kept-previous", str(e))
    save("programmes.json", {"updated": today(), "programmes": progs})
    return SourceResult("ok", f"{len(progs)} programmes", {"programmes": len(progs)})
