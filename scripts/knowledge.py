"""The knowledge model: loading content and data, classification, and Gurbani-to-katha links.

Pure functions over files in content/ and data/; no network. Used by build.py and the tests.
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DATA = ROOT / "data"

# ------------------------------------------------------------------ text normalisation
_GUR_FOLD = {"ਸ਼": "ਸ", "ਖ਼": "ਖ", "ਗ਼": "ਗ", "ਜ਼": "ਜ", "ਫ਼": "ਫ",
             "ਲ਼": "ਲ", "ੰ": "ਂ", "਼": "", "ੱ": "", "ੑ": ""}
_GUR_RE = re.compile("|".join(map(re.escape, _GUR_FOLD)))
_SPLIT = re.compile(r"[^਀-੿a-z0-9]+")


def fold(text):
    """Lower-case, fold Gurmukhi variants (nukta, tippi/bindi, addak) and reduce to space-separated words."""
    t = unicodedata.normalize("NFC", text or "").lower()
    t = _GUR_RE.sub(lambda m: _GUR_FOLD[m.group(0)], t)
    return " ".join(w for w in _SPLIT.split(t) if w)


def term_hits(text_folded, term):
    """'=word' matches a whole word; otherwise the term must start a word. Multi-word terms allowed."""
    padded = " " + text_folded + " "
    if term.startswith("="):
        return (" " + fold(term[1:]) + " ") in padded
    return (" " + fold(term)) in padded


# ------------------------------------------------------------------ content files
def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def parse_doc(path):
    """A content document: a JSON header, a line '---', then sections '## key' in light Markdown."""
    raw = Path(path).read_text(encoding="utf-8")
    head, _, body = raw.partition("\n---\n")
    meta = json.loads(head)
    sections, cur = {}, None
    for line in body.splitlines():
        m = re.match(r"^## ([a-z0-9-]+)\s*$", line)
        if m:
            cur = m.group(1)
            sections[cur] = []
        elif cur:
            sections[cur].append(line)
    meta["sections"] = {k: "\n".join(v).strip() for k, v in sections.items()}
    return meta


def load_themes():
    themes = [parse_doc(p) for p in sorted((CONTENT / "themes").glob("*.md"))]
    return sorted(themes, key=lambda t: t.get("order", 99))


def gurbani_refs(text):
    return re.findall(r"\[\[gurbani:([a-z0-9-]+)\]\]", text)


# ------------------------------------------------------------------ data
def clean_track_title(t):
    t = re.sub(r"\s*–\s*Baba Jagjit Singh \(Harkhowal wale\)\s*–\s*", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def load_all():
    k = {
        "config": read_json(ROOT / "config.json", {}),
        "audio": read_json(DATA / "audio.json", {"series": []}),
        "videos": read_json(DATA / "videos.json", {"videos": []}).get("videos", []),
        "programmes": read_json(DATA / "programmes.json", {"programmes": []}).get("programmes", []),
        "feeds": read_json(DATA / "feeds.json", {"items": []}).get("items", []),
        "sync": read_json(DATA / "sync-status.json", {"sources": {}}),
        "verification": read_json(DATA / "gurbani-verification.json", {"lines": {}}).get("lines", {}),
        "gurbani": {l["id"]: l for l in read_json(CONTENT / "gurbani.json", {"lines": []})["lines"]},
        "themes": load_themes(),
        "graph": read_json(CONTENT / "graph.json", {"edges": []})["edges"],
        "texts": read_json(CONTENT / "texts.json", {"shelves": [], "profiles": {}}),
        "external": read_json(CONTENT / "external.json", {"items": [], "collections": {}}),
        "overrides": read_json(CONTENT / "editorial" / "overrides.json", {}),
        "about": parse_doc(CONTENT / "pages" / "about.md"),
    }
    for s in k["audio"].get("series", []):
        for i, t in enumerate(s["tracks"]):
            t["t"] = clean_track_title(t["t"])
            t["i"] = i
            t["id"] = "a:" + t["p"]
    k["series_by_id"] = {s["id"]: s for s in k["audio"].get("series", [])}
    k["theme_by_slug"] = {t["slug"]: t for t in k["themes"]}
    return k


# ------------------------------------------------------------------ Gurbani display rules
def gurbani_state(line, verification, overrides):
    """Returns (show, label). 'to-verify' lines stay hidden until BaniDB or an editor confirms them."""
    v = verification.get(line["id"], {})
    confirmed = line["id"] in set(overrides.get("gurbani_confirmed", []))
    if v.get("status") == "verified":
        return True, "verified"
    if confirmed:
        return True, "editor-confirmed"
    if v.get("status") == "not-found":
        return False, "failed-check"
    if line.get("confidence") == "high":
        return True, "unchecked"
    return False, "awaiting-check"


# ------------------------------------------------------------------ Ang and pauri index of Babaji's katha
ANG_RE = re.compile(r"\bAng\s*0*(\d{1,4})(?:\s*(?:to|-)\s*0*(\d{1,4}))?", re.I)
PAURI_RE = re.compile(r"Jap\s*Ji.*?Pauri\s*0*(\d{1,2})(?:\s*(?:Part\s*\d+)?\s*to\s*(?:Pauri\s*)?(\d{1,2}|Salok))?", re.I)
MOOL_RE = re.compile(r"Mul\s*Mantar", re.I)


def katha_index(series_list):
    """Map each recording to the Angs (and Japji pauris) it covers, from its title."""
    angs, pauris = [], []
    for s in series_list:
        for t in s["tracks"]:
            title = t["t"]
            m = ANG_RE.search(title)
            if m:
                a = int(m.group(1))
                b = int(m.group(2) or a)
                if 1 <= a <= b <= 1430 and b - a < 40:
                    angs.append((a, b, t, s))
            m = PAURI_RE.search(title + (" " + s["title"] if "Jap" in s["title"] else ""))
            if m and ("Jap" in title or "Jap" in s["title"]):
                a = int(m.group(1))
                b = 39 if (m.group(2) or "").lower() == "salok" else int(m.group(2) or a)
                pauris.append((a, b, t, s))
            elif MOOL_RE.search(title):
                pauris.append((0, 0, t, s))
    return {"angs": angs, "pauris": pauris}


def katha_for_line(line, idx, limit=3):
    """Babaji's recordings covering a Gurbani line: by Japji pauri if known, else by Ang."""
    out = []
    jp = line.get("japji_pauri")
    if jp is not None:
        out += [(t, s) for a, b, t, s in idx["pauris"] if a <= jp <= b]
    ang = line.get("source", {}).get("ang")
    if ang and not out:
        out += [(t, s) for a, b, t, s in idx["angs"] if a <= ang <= b]
    seen, res = set(), []
    for t, s in out:
        if t["p"] not in seen:
            seen.add(t["p"])
            res.append((t, s))
    # prefer the systematic Ang-by-Ang series, then shorter spans
    res.sort(key=lambda ts: (ts[1]["id"] != "sri-guru-granth-sahib-ji-di-lareevar-katha", ts[0]["i"]))
    return res[:limit]


# ------------------------------------------------------------------ classification
ROMAN = {}


def _roman_re(term):
    if term not in ROMAN:
        ROMAN[term] = re.compile(r"\b(?:" + term + r")\b", re.I)
    return ROMAN[term]


def match_theme(theme, text):
    """Return the first matching term, or None. Gurmukhi terms by word, roman terms as regex."""
    folded = fold(text)
    for term in theme.get("match", {}).get("gurmukhi", []):
        if term_hits(folded, term):
            return term.lstrip("=")
    roman = re.sub(r"[_\-–.|]+", " ", text)
    for term in theme.get("match", {}).get("roman", []):
        if _roman_re(term).search(roman):
            return term
    return None


def classify(k):
    """Attach theme links to every video, recording, series and external item.

    Each link records how it was made ('via'), and whether an editor has confirmed it.
    Overrides in content/editorial/overrides.json add, remove or confirm links.
    """
    ov = k["overrides"]
    add, remove, confirmed = ov.get("theme_add", {}), ov.get("theme_remove", {}), ov.get("theme_confirmed", {})
    links = {}  # item id -> {slug: {"via":..., "confirmed": bool}}

    def put(iid, slug, via):
        links.setdefault(iid, {}).setdefault(slug, {"via": via, "confirmed": False})

    for th in k["themes"]:
        series_terms = set(th.get("match", {}).get("series", []))
        for s in k["audio"].get("series", []):
            if s["id"] in series_terms:
                put("s:" + s["id"], th["slug"], "series: listed for this theme")
                continue
            series_hit = match_theme(th, s["title"] + " " + s.get("gurmukhi", ""))
            if series_hit:
                put("s:" + s["id"], th["slug"], f"series title: ‘{series_hit}’")
                continue
            for t in s["tracks"]:
                hit = match_theme(th, t["t"] + " " + t.get("g", ""))
                if hit:
                    put(t["id"], th["slug"], f"title: ‘{hit}’")
        for v in k["videos"]:
            hit = match_theme(th, v["title"])
            if hit:
                put("yt:" + v["id"], th["slug"], f"title: ‘{hit}’")
                continue
            # the channel's descriptions often list the divan's topics; use the part before any hashtags or links
            desc = re.split(r"#|https?://", v.get("description", ""))[0]
            hit = match_theme(th, desc)
            if hit:
                put("yt:" + v["id"], th["slug"], f"description: ‘{hit}’")
        for slug in [th["slug"]]:
            for ex in k["external"].get("items", []):
                if slug in ex.get("themes", []):
                    put(ex["id"], slug, "curated")
    for iid, slugs in add.items():
        for slug in slugs:
            links.setdefault(iid, {})[slug] = {"via": "editor", "confirmed": True}
    for iid, slugs in remove.items():
        for slug in slugs:
            links.get(iid, {}).pop(slug, None)
    for iid, slugs in confirmed.items():
        for slug in slugs:
            if slug in links.get(iid, {}):
                links[iid][slug]["confirmed"] = True
    for ex in k["external"].get("items", []):
        for slug in links.get(ex["id"], {}):
            links[ex["id"]][slug]["confirmed"] = True
    return {iid: v for iid, v in links.items() if v}


def published_feed_items(k):
    ov = k["overrides"]
    approved, rejected = set(ov.get("approve", [])), set(ov.get("reject", []))
    return [i for i in k["feeds"] if i["id"] not in rejected and (i["id"] in approved or i.get("auto_publish"))]


def pending_feed_items(k):
    ov = k["overrides"]
    done = set(ov.get("approve", [])) | set(ov.get("reject", []))
    return [i for i in k["feeds"] if i["id"] not in done and not i.get("auto_publish")]


def theme_review(k, slug):
    th = k["theme_by_slug"][slug]
    r = dict(th.get("review", {}))
    r.update(k["overrides"].get("theme_review", {}).get(slug, {}))
    return r
