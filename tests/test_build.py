"""Build the whole site into a temporary folder and check what visitors and search engines receive."""
import html.parser
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.imgs_without_alt, self.ids, self.buttons_unnamed, self.h1 = [], 0, set(), 0, 0
        self._btn = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag == "img" and "alt" not in a:
            self.imgs_without_alt += 1
        if tag == "h1":
            self.h1 += 1
        if tag == "button":
            self._btn = [a.get("aria-label") or "", ""]

    def handle_data(self, data):
        if self._btn is not None:
            self._btn[1] += data

    def handle_endtag(self, tag):
        if tag == "button" and self._btn is not None:
            if not (self._btn[0].strip() or self._btn[1].strip()):
                self.buttons_unnamed += 1
            self._btn = None


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp()) / "site"
        os.environ["BASE_PATH"] = "/"
        import build
        cls.ctx = build.build(cls.out)
        cls.pages = sorted(p for p in cls.out.rglob("*.html"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out.parent)

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    def test_expected_pages_exist(self):
        k = self.ctx["k"]
        for rel in ["index.html", "topics/index.html", "listen/index.html", "watch/index.html", "search/index.html",
                    "about/index.html", "sources/index.html", "review/index.html", "404.html", "sitemap.xml", "robots.txt",
                    "search/index.json", "review/data.json", "assets/site.css", "assets/site.js"]:
            self.assertTrue((self.out / rel).exists(), rel)
        for th in k["themes"]:
            self.assertTrue((self.out / "themes" / th["slug"] / "index.html").exists())
        for s in k["audio"]["series"]:
            self.assertTrue((self.out / "listen" / s["id"] / "index.html").exists(), s["id"])

    def test_every_internal_link_resolves(self):
        broken = []
        for p in self.pages:
            parser = Links()
            parser.feed(p.read_text(encoding="utf-8"))
            for h in parser.hrefs:
                if h.startswith(("http", "mailto:", "#")):
                    continue
                path = h.split("#")[0].split("?")[0]
                target = self.out / path.lstrip("/")
                if path.endswith("/") or not target.suffix:
                    target = target / "index.html"
                if not target.exists():
                    broken.append(f"{p.relative_to(self.out)} -> {h}")
        self.assertEqual(broken, [])

    def test_accessibility_basics(self):
        for p in self.pages:
            parser = Links()
            txt = p.read_text(encoding="utf-8")
            parser.feed(txt)
            rel = p.relative_to(self.out)
            self.assertEqual(parser.imgs_without_alt, 0, f"{rel}: image without alt")
            self.assertEqual(parser.buttons_unnamed, 0, f"{rel}: button without a name")
            self.assertEqual(parser.h1, 1, f"{rel}: should have exactly one h1")
            self.assertIn('<html lang="', txt)
            self.assertIn('class="skip"', txt)

    def test_unique_titles_and_descriptions(self):
        titles, descs = {}, {}
        for p in self.pages:
            txt = p.read_text(encoding="utf-8")
            if 'noindex' in txt:
                continue
            t = re.search(r"<title>(.*?)</title>", txt).group(1)
            d = re.search(r'<meta name="description" content="(.*?)"', txt).group(1)
            self.assertNotIn(t, titles, f"duplicate title {t}: {p} and {titles.get(t)}")
            titles[t] = p
            self.assertTrue(d)
            self.assertIn('rel="canonical"', txt)

    def test_theme_pages_label_provenance(self):
        for th in self.ctx["k"]["themes"]:
            txt = self.read(f"themes/{th['slug']}/index.html")
            self.assertIn("Editorial introduction", txt)
            self.assertIn("Not Gurbani and not Babaji’s words", txt)
            self.assertIn("Babaji’s katha", txt)
            for layer in ("discover", "understand", "explore", "reflect", "deeper"):
                self.assertIn(f'id="{layer}"', txt, f"{th['slug']} lacks layer {layer}")
            if th.get("review", {}).get("status") != "reviewed":
                self.assertIn("Awaiting review", txt)

    def test_gurbani_blocks_carry_source_and_labelled_translation(self):
        n = 0
        for th in self.ctx["k"]["themes"]:
            txt = self.read(f"themes/{th['slug']}/index.html")
            for block in re.findall(r'<figure class="bani".*?</figure>', txt, re.S):
                n += 1
                self.assertIn("Ang", block)
                self.assertIn("Translation, editorial", block)
                self.assertIn('lang="pa"', block)
        self.assertGreater(n, 15)

    def test_unverified_lines_are_hidden(self):
        k = self.ctx["k"]
        for gid, line in k["gurbani"].items():
            if line["confidence"] == "to-verify" and k["verification"].get(gid, {}).get("status") != "verified" \
                    and gid not in k["overrides"].get("gurbani_confirmed", []):
                for th in k["themes"]:
                    self.assertNotIn(line["gurmukhi"], self.read(f"themes/{th['slug']}/index.html"), gid)

    def test_gurbani_lines_link_to_babajis_katha(self):
        txt = self.read("themes/haumai/index.html")
        block = re.search(r'<figure class="bani" id="g-haumai-rog".*?</figure>', txt, re.S).group(0)
        self.assertIn("Ang 0465 to 0467", block)

    def test_latest_is_newest_first_and_complete(self):
        d = json.loads(self.read("latest/index.json"))
        k = self.ctx["k"]
        n_rec = sum(len(s["tracks"]) for s in k["audio"]["series"])
        self.assertEqual(len(d["items"]), n_rec + len(k["videos"]))
        dates = [r[0] for r in d["items"]]
        self.assertEqual(dates, sorted(dates, reverse=True))
        for r in d["items"]:
            if len(r) == 6:
                self.assertLess(r[2], len(d["series"]))
                if r[4]:
                    self.assertRegex(r[4], r"^\d{4}-\d\d-\d\d$")
        page = self.read("latest/index.html")
        self.assertIn('class="month"', page)
        self.assertGreaterEqual(page.count('class="row'), 60)
        self.assertIn('href="/latest/"', self.read("index.html"))

    def test_topic_pages_explain_every_link(self):
        k = self.ctx["k"]
        for tp in k["topics"]:
            if tp["kind"] == "theme":
                continue
            page = self.read(f"topics/{tp['id']}/index.html")
            self.assertIn("How this page is made", page)
            rows = page.count('class="row"')
            self.assertEqual(rows, page.count("Linked: "), f"{tp['id']}: a recording without a reason")
            if tp.get("match", {}).get("angs"):
                self.assertIn("sikhitothemax.org/ang?ang=", page, tp["id"])
        sidh = self.read("topics/sidh-gosht/index.html")
        self.assertIn("katha covers Ang", sidh)
        self.assertIn('href="/themes/shabad-guru/"', sidh)
        # places named after Gurus are not katha about the Gurus
        self.assertNotIn("Leicester", self.read("topics/guru-tegh-bahadur/index.html"))
        self.assertNotIn("Smethwick", self.read("topics/guru-nanak/index.html"))

    def test_topics_are_searchable(self):
        d = json.loads(self.read("search/index.json"))
        kinds = {i[0] for i in d["items"]}
        self.assertIn("topic", kinds)
        self.assertIn("sangrand", d["themes"])
        self.assertIn("ego", d["themes"]["haumai"])

    def test_sitemap_and_robots(self):
        root = ET.parse(self.out / "sitemap.xml").getroot()
        locs = [e.text for e in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertGreater(len(locs), 50)
        self.assertFalse(any("/review/" in l for l in locs))
        self.assertIn("Disallow: /review/", self.read("robots.txt"))

    def test_old_wix_urls_redirect_to_real_pages(self):
        lines = [l.split() for l in self.read("_redirects").splitlines() if l and not l.startswith("#")]
        sources = {l[0] for l in lines}
        for old in ("/shabadguru", "/sggs-katha/", "/sants-gurmukhs", "/literature"):
            self.assertIn(old, sources)
        for src, dest, code in lines:
            self.assertEqual(code, "301")
            self.assertTrue((self.out / dest.lstrip("/") / "index.html").exists(), dest)
            self.assertFalse((self.out / src.strip("/") / "index.html").exists(), f"{src} would be shadowed by a page")
        self.assertIn("/themes/ /topics/ 301", self.read("_redirects"))

    def test_cloudflare_headers(self):
        h = self.read("_headers")
        self.assertIn("Content-Security-Policy:", h)
        self.assertIn("/assets/*", h)
        self.assertIn("X-Robots-Tag: noindex", h)
        # the CSP has no 'unsafe-inline', so pages must carry no inline scripts or style attributes
        for p in self.pages:
            txt = p.read_text(encoding="utf-8")
            self.assertNotIn(' style="', txt, p)
            for m in re.finditer(r"<script(?![^>]*\bsrc=)([^>]*)>", txt):
                self.assertIn("application/ld+json", m.group(1), f"inline script in {p}")

    def test_wrangler_config_points_at_the_build(self):
        cfg = (ROOT / "wrangler.jsonc").read_text(encoding="utf-8")
        cfg = json.loads(re.sub(r"^\s*//.*$", "", cfg, flags=re.M))
        self.assertEqual(cfg["assets"]["directory"], "./_site")
        self.assertIn("scripts/build.py", cfg["build"]["command"])
        self.assertEqual(cfg["assets"]["not_found_handling"], "404-page")

    def test_search_index(self):
        d = json.loads(self.read("search/index.json"))
        kinds = {i[0] for i in d["items"]}
        self.assertTrue({"theme", "series", "rec", "video"} <= kinds)
        self.assertIn("ego", d["themes"]["haumai"])
        self.assertTrue(any("ਹਕਮ" in t or "ਹੁਕਮ" in t for t in d["themes"]["hukam"]))

    def test_no_unescaped_template_leaks(self):
        for p in self.pages:
            txt = p.read_text(encoding="utf-8")
            for bad in ("{e(", "None</", ">None<", "[[gurbani:", "undefined"):
                self.assertNotIn(bad, txt, f"{p.relative_to(self.out)} contains {bad!r}")


if __name__ == "__main__":
    unittest.main()
