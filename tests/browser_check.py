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
Handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
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
        pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith(URL) else r.abort())
        return pg

    pg = newpage()
    for path in ["", "themes/", "themes/haumai/", "listen/", "listen/sri-guru-granth-sahib-ji-di-lareevar-katha/",
                 "watch/", "search/?q=ego", "about/", "sources/", "review/"]:
        pg.goto(URL + path)
        pg.wait_for_load_state("networkidle")
        check(f"loads without script errors: /{path}", not pg.errors, pg.errors)
        pg.errors.clear()

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
    for path in ["", "themes/maya/", "listen/", "listen/vairaag-shatak/", "watch/", "sources/"]:
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
