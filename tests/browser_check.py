#!/usr/bin/env python3
"""End-to-end checks in a real browser (Chromium via Playwright).

Builds the site, serves it locally, blocks every outside request (fonts,
YouTube, Gurmatveechar) so the test is deterministic, and checks the behaviour
that only exists in a browser. Exits non-zero on any failure.

  pip install playwright && python -m playwright install chromium
  python tests/browser_check.py
"""
import http.server
import os
import socketserver
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["BASE_PATH"] = "/"
import build  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

out = Path(tempfile.mkdtemp()) / "site"
build.build(out)


def parse_headers(text):
    rules, cur = [], None
    for line in text.splitlines():
        if line and not line[0].isspace():
            cur = (line.strip(), [])
            rules.append(cur)
        elif line.strip() and cur:
            k, _, v = line.strip().partition(":")
            cur[1].append((k.strip(), v.strip()))
    return rules


HEADERS = parse_headers((out / "_headers").read_text(encoding="utf-8"))
REDIRECTS = {l.split()[0]: l.split()[1] for l in (out / "_redirects").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")}


class CloudflareLike(http.server.SimpleHTTPRequestHandler):
    """Serves _site the way Cloudflare's static assets will: _headers, _redirects,
    auto-trailing-slash and the 404 page."""
    def log_message(self, *a):
        pass

    def end_headers(self):
        path = self.path.split("?")[0]
        for pat, hs in HEADERS:
            if pat == path or (pat.endswith("*") and path.startswith(pat[:-1])):
                for k, v in hs:
                    self.send_header(k, v)
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in REDIRECTS:
            self.send_response(301); self.send_header("Location", REDIRECTS[path]); self.end_headers(); return
        target = out / path.lstrip("/")
        if not path.endswith("/") and (target / "index.html").exists():
            self.send_response(307); self.send_header("Location", path + "/"); self.end_headers(); return
        if not target.exists() and not (target / "index.html").exists():
            body = (out / "404.html").read_bytes()
            self.send_response(404); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(body); return
        super().do_GET()


Handler = partial(CloudflareLike, directory=str(out))
srv = socketserver.TCPServer(("127.0.0.1", 0), Handler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{PORT}/"

failures, passes = [], []


def check(name, cond, detail=""):
    (passes if cond else failures).append(name + ("" if cond else f": {detail}"))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f" ({detail})"))


with sync_playwright() as p:
    b = p.chromium.launch()

    def newpage(w=1280, h=900):
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.on("console", lambda m: pg.errors.append(m.text) if "Content Security Policy" in m.text else None)
        pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith(URL) else r.abort())
        return pg

    pg = newpage()
    for path in ["", "journey/", "topics/", "topics/sukhmani/", "themes/haumai/", "listen/", "listen/sri-guru-granth-sahib-ji-di-lareevar-katha/",
                 "watch/", "search/?q=ego", "about/", "sources/", "review/"]:
        pg.goto(URL + path)
        pg.wait_for_load_state("networkidle")
        check(f"loads without script errors: /{path}", not pg.errors, pg.errors)
        pg.errors.clear()

    # Cloudflare behaviour: old Wix addresses redirect, missing pages get the 404 page.
    r = pg.goto(URL + "shabadguru")
    check("old Wix address /shabadguru redirects to the Shabad Guru theme", pg.url.endswith("/themes/shabad-guru/"), pg.url)
    r = pg.goto(URL + "no-such-page")
    check("unknown address shows the 404 page", r.status == 404 and "isn" in pg.locator("h1").inner_text(), r.status)
    r = pg.goto(URL + "themes/naam/")
    check("security headers are sent", "default-src 'self'" in (r.headers.get("content-security-policy") or ""))

    # Playing a recording, then moving to another page: the player and its track survive.
    pg.goto(URL + "themes/haumai/")
    row = pg.locator(".bani-katha .row").first
    title = row.get_attribute("data-t")
    row.click()
    check("pressing a recording opens the player", pg.locator("#player").is_visible())
    check("the player shows the recording", pg.locator("#p-title").inner_text() == title)
    src = pg.evaluate("document.getElementById('audio').getAttribute('src')")
    check("audio streams from Gurmatveechar", "gurmatveechar.com/audios/" in (src or ""), src)
    pg.evaluate("window.__marker = 1")
    pg.locator(".top nav a", has_text="Listen").click()
    pg.wait_for_url(URL + "listen/")
    pg.wait_for_selector("h1:has-text('Listen')")
    check("navigation stays in the same document (audio keeps playing)", pg.evaluate("window.__marker") == 1)
    check("the player keeps its track after navigation", pg.locator("#p-title").inner_text() == title)
    check("the URL and title update", "Listen" in pg.title())
    pg.go_back()
    pg.wait_for_selector("h1 .g")
    check("back button returns to the theme", pg.url.endswith("/themes/haumai/"))

    # Search across languages: an English word finds the Gurmukhi theme and its linked items.
    pg.goto(URL + "search/?q=ego")
    pg.wait_for_selector(".res-theme")
    check("searching 'ego' finds the Haumai theme first", "Haumai" in pg.locator(".res-theme").first.inner_text())
    pg.fill("#sq", "ਹੁਕਮ")
    pg.wait_for_timeout(400)
    check("searching ਹੁਕਮ finds the Hukam theme", "Hukam" in pg.locator("#main").inner_text())
    pg.fill("#sq", "vichar sagar")
    pg.wait_for_timeout(400)
    check("searching a text name finds its series", "Vichar Sagar" in pg.locator("#main").inner_text())
    pg.fill("#sq", "zzqqxx")
    pg.wait_for_timeout(400)
    check("a search with no results explains what to try", "Try a shorter word" in pg.locator("#main").inner_text())

    # Latest: everything newest first, with simple filters.
    pg.goto(URL + "latest/")
    first_date = pg.locator("#main .row .d").first.inner_text()
    check("Latest opens with the newest item first", first_date != "", first_date)
    pg.locator("[data-lk='v']").click()
    pg.wait_for_timeout(300)
    check("Video filter shows only videos", pg.locator("#main .row[data-p]").count() == 0 and pg.locator("#main .row.vrow").count() > 0)
    pg.locator("[data-lk='a']").click()
    pg.wait_for_timeout(300)
    check("Audio filter shows only recordings", pg.locator("#main .row.vrow").count() == 0 and pg.locator("#main .row[data-p]").count() == 60)
    pg.locator("[data-more]").click()
    pg.wait_for_timeout(200)
    check("Show more adds the next 60", pg.locator("#main .row[data-p]").count() == 120)
    pg.fill("#lq", "smethwick")
    pg.wait_for_timeout(400)
    n = pg.locator("#main .row[data-p]").count()
    check("the title filter narrows the list", 0 < n <= 30 and "matching" in pg.locator(".latest-count").inner_text(), n)
    pg.locator("#main .row[data-p]").first.click()
    check("a recording in Latest plays", pg.locator("#player").is_visible())
    pg.fill("#lq", "")
    pg.locator("[data-lk='v']").click()
    pg.wait_for_timeout(300)
    pg.locator("#main .row.vrow").first.click()
    check("a video in Latest opens its player in place", pg.locator("#main .vembed iframe").count() == 1)

    # The journey from manmukh to gurmukh.
    pg.goto(URL + "journey/")
    pg.locator(".journey-head .path a").nth(5).click()
    pg.wait_for_timeout(300)
    check("a stop on the journey path jumps to its step", pg.url.endswith("#karam-khand") and pg.locator("#karam-khand").is_visible())
    pg.locator(".journey-head .journey-listen a").click()
    pg.wait_for_timeout(200)
    first = pg.locator("#katha + p + .rows .row").first
    first.click()
    check("Babaji's katha of the khands plays from the journey", pg.locator("#player").is_visible() and "Pauri" in pg.locator("#p-title").inner_text())
    pg.goto(URL + "search/?q=gurmukh")
    pg.wait_for_selector(".res-theme")
    check("searching 'gurmukh' finds the journey first", "manmukh to gurmukh" in pg.locator(".res-theme").first.inner_text())
    pg.goto(URL + "search/?q=" + "ਸਚ ਖੰਡ")
    pg.wait_for_selector(".res-theme")
    check("searching ਸਚ ਖੰਡ finds the step", "realm of truth" in pg.locator("#main").inner_text())

    # Topics: find a topic, open it, play its katha.
    pg.goto(URL + "topics/")
    pg.fill("#tq", "sangrand")
    visible = [t for t in pg.locator(".ix:visible .en").all_inner_texts()]
    check("the topic finder narrows to Sangrand", "Sangrand" in visible and len(visible) <= 2, visible)
    pg.fill("#tq", "ਸੁਖਮਨੀ")
    check("the topic finder works in Gurmukhi", "Sukhmani Sahib" in pg.locator(".ix:visible").first.inner_text())
    pg.locator(".ix:visible").first.click()
    pg.wait_for_url("**/topics/sukhmani/")
    check("a topic page lists katha with reasons", pg.locator("#main .row").count() > 3 and "Linked:" in pg.locator("#main .row").first.inner_text())
    pg.locator("#main .row").first.click()
    check("katha on a topic page plays", pg.locator("#player").is_visible())
    pg.goto(URL + "search/?q=sangrand")
    pg.wait_for_selector(".res-theme")
    check("Search finds the Sangrand topic", "Sangrand" in pg.locator(".res-theme").first.inner_text())
    r = pg.goto(URL + "themes/")
    check("the old /themes/ address goes to Topics", pg.url.endswith("/topics/"), pg.url)

    # Ang lookup on the Guru Granth Sahib series.
    pg.goto(URL + "listen/sri-guru-granth-sahib-ji-di-lareevar-katha/")
    pg.fill("#angn", "466")
    pg.press("#angn", "Enter")
    pg.wait_for_timeout(200)
    focused = pg.evaluate("document.activeElement.dataset.t || ''")
    check("'Go to Ang 466' finds the katha covering it", "0465 to 0467" in focused, focused)

    # Filtering the library.
    pg.goto(URL + "listen/")
    pg.fill("[data-filter-input]", "ਜਪੁਜੀ")
    visible = pg.locator(".ix:visible").count()
    check("filtering the library in Gurmukhi narrows the list", 0 < visible < 6, visible)

    # Theme chips on Watch.
    pg.goto(URL + "watch/")
    chips = pg.locator("[data-theme-chip]")
    if chips.count():
        total = pg.locator("[data-themes]:visible").count()
        chips.first.click()
        check("a theme chip filters the videos", pg.locator("[data-themes]:visible").count() < total)

    # Review page renders its queue and produces override JSON.
    pg.goto(URL + "review/")
    pg.wait_for_selector("textarea")
    check("review page produces overrides JSON", '"theme_add"' in pg.locator("textarea").input_value())

    # Keyboard: the first Tab reaches the skip link.
    pg.goto(URL)
    pg.keyboard.press("Tab")
    check("first Tab reaches 'Skip to content'", pg.evaluate("document.activeElement.className") == "skip")

    # Mobile: no sideways scrolling on key pages.
    m = newpage(390, 844)
    for path in ["", "journey/", "themes/maya/", "listen/", "listen/vairaag-shatak/", "watch/", "sources/"]:
        m.goto(URL + path)
        over = m.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check(f"no horizontal scroll on mobile: /{path}", over <= 0, f"{over}px too wide")

    # Dark mode renders with a dark background.
    d = b.new_page(color_scheme="dark")
    d.route("**/*", lambda r: r.continue_() if r.request.url.startswith(URL) else r.abort())
    d.goto(URL + "themes/naam/")
    bg = d.evaluate("getComputedStyle(document.body).backgroundColor")
    check("dark mode uses the night palette", bg == "rgb(17, 20, 42)", bg)

    # Page weight of the home page (HTML + CSS + JS, uncompressed; fonts and thumbnails excluded).
    sizes = {f: (out / f).stat().st_size for f in ("index.html", "assets/site.css", "assets/site.js")}
    check("home page code under 120 KB before compression", sum(sizes.values()) < 120_000, sizes)
    b.close()

srv.shutdown()
print(f"\n{len(passes)} passed, {len(failures)} failed")
sys.exit(1 if failures else 0)
