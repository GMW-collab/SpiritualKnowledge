"""Check every Gurbani line quoted on the site against BaniDB.

For each line in content/gurbani.json that names an Ang of Sri Guru Granth
Sahib Ji, fetch that Ang from the BaniDB API (Khalis Foundation) and confirm
that the quoted Gurmukhi appears on it. Results go to
data/gurbani-verification.json. Lines are re-checked only when their text
changes, so the site makes a handful of requests at most.

Only the verification result is stored. BaniDB's translations are not copied.
"""
import hashlib
import json
import re
import time
import unicodedata

from .common import CONTENT, SourceResult, load, request, save, today

API = "https://api.banidb.com/v2/angs/{ang}/G"
DROP = re.compile(r"[\s॥।੦-੯0-9.,;:'\"‘’“”()\-ੑੵ]")


def normalise(text):
    """Compare Gurmukhi letter sequences only: no spaces, punctuation, verse numbers or optional marks."""
    t = unicodedata.normalize("NFC", text or "")
    t = t.replace("ੰ", "ਂ")  # tippi and bindi are both nasalisation marks
    return DROP.sub("", t)


def collect_unicode(node, out):
    """Pull every Unicode Gurmukhi verse string out of a BaniDB response, whatever its exact shape."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("unicode", "gurmukhiUnicode") and isinstance(v, str):
                out.append(v)
            else:
                collect_unicode(v, out)
    elif isinstance(node, list):
        for v in node:
            collect_unicode(v, out)
    return out


def check_line(gurmukhi, page_texts):
    page = normalise("".join(page_texts))
    parts = [normalise(p) for p in re.split(r"॥", gurmukhi) if normalise(p)]
    if not page:
        return "error", "No Gurmukhi text in the response"
    missing = [p for p in parts if p not in page]
    if not missing:
        return "verified", ""
    return "not-found", f"{len(missing)} of {len(parts)} segment(s) not found on the Ang"


def fingerprint(line):
    return hashlib.sha1((line["gurmukhi"] + "|" + str(line.get("source", {}).get("ang"))).encode("utf-8")).hexdigest()[:12]


def run(cfg, source, fetch=request, delay=1.0):
    lines = json.loads((CONTENT / "gurbani.json").read_text(encoding="utf-8")).get("lines", [])
    store = load("gurbani-verification.json", {"lines": {}})
    results = store.get("lines", {})
    cache, checked, errors = {}, 0, 0
    for line in lines:
        ang = line.get("source", {}).get("ang")
        fp = fingerprint(line)
        prev = results.get(line["id"])
        if not ang:
            results[line["id"]] = {"status": "not-applicable", "reason": "No Ang to check against", "fp": fp, "checked": today()}
            continue
        if prev and prev.get("fp") == fp and prev.get("status") in ("verified", "not-found"):
            continue
        try:
            if ang not in cache:
                if cache and delay:
                    time.sleep(delay)
                cache[ang] = collect_unicode(json.loads(fetch(API.format(ang=ang))), [])
            status, reason = check_line(line["gurmukhi"], cache[ang])
        except Exception as e:
            status, reason = "error", str(e)
            errors += 1
        results[line["id"]] = {"status": status, "reason": reason, "fp": fp, "checked": today(),
                               "against": f"BaniDB, Ang {ang}"}
        checked += 1
    for gone in set(results) - {l["id"] for l in lines}:
        results.pop(gone)
    save("gurbani-verification.json", {"updated": today(), "lines": results})
    counts = {s: sum(1 for r in results.values() if r["status"] == s) for s in ("verified", "not-found", "error")}
    state = "ok" if not errors else ("partial" if errors < max(checked, 1) else "failed")
    return SourceResult(state, f"{checked} line(s) checked", counts)
