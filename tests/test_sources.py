"""Source adapters, tested against recorded fixtures. No network access."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from sources import banidb, common, feeds, gurmatveechar, sheet, youtube  # noqa: E402

FIX = HERE / "fixtures"


def fixture(name):
    return (FIX / name).read_text(encoding="utf-8")


class TempData(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._data = common.DATA
        common.DATA = self.tmp

    def tearDown(self):
        common.DATA = self._data
        shutil.rmtree(self.tmp)


class YouTubeTest(TempData):
    def test_parse_feed(self):
        v = youtube.parse_feed(fixture("youtube_feed.xml"))
        self.assertEqual([x["id"] for x in v], ["AAAAAAAAAAA", "BBBBBBBBBBB"])
        self.assertEqual(v[0]["published"], "2026-10-06")
        self.assertIn("ਹੰਕਾਰ", v[0]["description"])

    def test_run_keeps_archive_and_sorts(self):
        common.save("videos.json", {"videos": [{"id": "OLD", "title": "old", "published": "2020-01-01"}]})
        res = youtube.run({"youtube_channel_id": "UCx"}, {}, fetch=lambda url, **k: fixture("youtube_feed.xml"))
        self.assertEqual(res.state, "ok")
        saved = common.load("videos.json", {})
        self.assertEqual([x["id"] for x in saved["videos"]], ["AAAAAAAAAAA", "BBBBBBBBBBB", "OLD"])

    def test_unreachable_feed_keeps_previous(self):
        common.save("videos.json", {"videos": [{"id": "OLD", "title": "old", "published": "2020-01-01"}]})

        def boom(url, **k):
            raise RuntimeError("offline")
        res = youtube.run({"youtube_channel_id": "UCx"}, {}, fetch=boom)
        self.assertEqual(res.state, "kept-previous")
        self.assertEqual(len(common.load("videos.json", {})["videos"]), 1)

    def test_falls_back_to_playlist_feed(self):
        seen = []

        def fetch(url, **k):
            seen.append(url)
            if "channel_id=" in url:
                raise RuntimeError("HTTP Error 404: Not Found")
            return fixture("youtube_feed.xml")
        res = youtube.run({"youtube_channel_id": "UCabc"}, {}, fetch=fetch)
        self.assertEqual(res.state, "ok")
        self.assertIn("playlist_id=UUabc", seen[-1])
        self.assertEqual(len(common.load("videos.json", {})["videos"]), 2)

    def test_parse_feed_marks_shorts(self):
        v = {x["id"]: x for x in youtube.parse_feed(fixture("youtube_feed.xml"))}
        self.assertNotIn("short", v["AAAAAAAAAAA"])
        self.assertTrue(v["BBBBBBBBBBB"]["short"])

    @staticmethod
    def api_page(ids, token=None, day=1):
        return json.dumps({"items": [{"snippet": {"title": "Video " + i, "publishedAt": "2026-01-%02dT00:00:00Z" % day},
                                      "contentDetails": {"videoId": i}} for i in ids], **({"nextPageToken": token} if token else {})})

    def api_fetch(self, uploads, shorts, calls):
        """uploads / shorts: lists of pages (lists of ids); pages chained by tokens p1, p2 ..."""
        def fetch(url, **k):
            calls.append(url)
            if "feeds/videos.xml" in url:
                return fixture("youtube_feed.xml")
            pages = shorts if "playlistId=UUSH" in url else uploads
            n = int(url.split("pageToken=p")[1].split("&")[0]) if "pageToken=" in url else 0
            return self.api_page(pages[n], "p%d" % (n + 1) if n + 1 < len(pages) else None)
        return fetch

    def test_api_pages_shorts_and_key_is_scrubbed(self):
        os.environ["YOUTUBE_API_KEY"] = "SECRET123"
        try:
            calls = []
            fetch = self.api_fetch([["V0", "S1"], ["V2"]], [["S1"]], calls)
            res = youtube.run({"youtube_channel_id": "UCabc"}, {}, fetch=fetch)
            saved = common.load("videos.json", {})
            by = {v["id"]: v for v in saved["videos"]}
            self.assertTrue({"V0", "V2", "S1"} <= set(by))
            self.assertTrue(by["S1"].get("short"))
            self.assertNotIn("short", by["V0"])
            self.assertTrue(saved["archive_complete"] and saved["shorts_complete"])
            self.assertTrue(any("playlistId=UUabc" in c for c in calls))
            self.assertTrue(any("playlistId=UUSHabc" in c for c in calls))
            self.assertEqual(common.scrub("https://x/?key=SECRET123&a=1"), "https://x/?key=***&a=1")
            self.assertEqual(res.state, "ok")
        finally:
            del os.environ["YOUTUBE_API_KEY"]

    def test_incomplete_archive_is_read_to_the_end(self):
        """Known videos on the first page must not stop the walk until the archive has been read once."""
        common.save("videos.json", {"archive_complete": False, "videos": [{"id": "V0", "title": "x", "published": "2026-01-01"}]})
        os.environ["YOUTUBE_API_KEY"] = "K"
        try:
            calls = []
            youtube.run({"youtube_channel_id": "UCabc"}, {}, fetch=self.api_fetch([["V0"], ["OLD"]], [[]], calls))
            self.assertIn("OLD", {v["id"] for v in common.load("videos.json", {})["videos"]})
            # once complete, a known first page ends the walk
            calls.clear()
            youtube.run({"youtube_channel_id": "UCabc"}, {}, fetch=self.api_fetch([["V0"], ["OLDER"]], [[]], calls))
            self.assertNotIn("OLDER", {v["id"] for v in common.load("videos.json", {})["videos"]})
        finally:
            del os.environ["YOUTUBE_API_KEY"]


class GurmatveecharTest(TempData):
    def test_parse_listing_direct_children_only(self):
        folders, files = gurmatveechar.parse_listing(fixture("gmv_root.html"), "/Katha/Root")
        self.assertEqual(folders, ["/Katha/Root/Series_One"])
        self.assertEqual(files, ["/Katha/Root/Baba.Jagjit.Singh.(Harkhowal.wale)--1990-07-02.Katha.mp3"])

    def test_titles(self):
        self.assertEqual(gurmatveechar.track_title("/x/01--Baba.Jagjit.Singh.(Harkhowal.wale)--Bhagti.Te.Prem.mp3"), "01 Bhagti Te Prem")
        self.assertEqual(gurmatveechar.track_title("/x/Baba.Jagjit.Singh.(Harkhowal.wale)--1990-07-02.Katha.mp3"), "1990-07-02 Katha")

    def test_run_builds_series_and_remembers_dates(self):
        pages = {"/Katha/Root": fixture("gmv_root.html"), "/Katha/Root/Series_One": fixture("gmv_series.html")}

        class FakeCrawler(gurmatveechar.Crawler):
            def __init__(self):
                super().__init__(fetch=lambda url, **k: pages[__import__("urllib.parse").parse.parse_qs(url.split("?", 1)[1])["f"][0]], delay=0)
        heads = []
        cfg = {"gurmatveechar_root": "/Katha/Root", "series_gurmukhi": {"Series_One": "ਇੱਕ"},
               "audio_categories": [{"name": "Talks", "match": ["Series"]}]}
        res = gurmatveechar.run(cfg, {}, crawler=FakeCrawler(), head=lambda p: heads.append(p) or "2026-10-01")
        self.assertEqual(res.state, "ok")
        a = common.load("audio.json", {})
        ids = [s["id"] for s in a["series"]]
        self.assertEqual(ids, ["series-one", "single-divans"])
        self.assertEqual(a["series"][0]["gurmukhi"], "ਇੱਕ")
        self.assertEqual(len(heads), 3)
        # second run: dates are remembered, no new lookups
        heads.clear()
        gurmatveechar.run(cfg, {}, crawler=FakeCrawler(), head=lambda p: heads.append(p) or "x")
        self.assertEqual(heads, [])

    def test_shrinking_listing_keeps_previous(self):
        common.save("audio.json", {"series": [{"tracks": [{"p": f"S/{i}.mp3", "d": ""} for i in range(10)]}]})

        class Tiny(gurmatveechar.Crawler):
            def crawl(self, path, depth=0):
                return {"path": path, "files": [path + "/a.mp3"], "children": []}
        res = gurmatveechar.run({"gurmatveechar_root": "/R"}, {}, crawler=Tiny(), head=lambda p: "")
        self.assertEqual(res.state, "kept-previous")


class FeedTest(TempData):
    def test_rss_is_summarised_and_unsafe_links_dropped(self):
        items = feeds.parse(fixture("rss.xml"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "On Hukam")
        self.assertLessEqual(len(items[0]["summary"]), feeds.SUMMARY_CHARS + 1)
        self.assertEqual(items[0]["published"], "2026-10-20")
        self.assertEqual(items[0]["author"], "A. Writer")

    def test_atom(self):
        items = feeds.parse(fixture("youtube_feed.xml"))
        self.assertEqual(items[0]["youtube"], "AAAAAAAAAAA")

    def test_run_imports_without_publishing(self):
        res = feeds.run({}, {"id": "feed:ex", "url": "https://example.org/feed"}, fetch=lambda u, **k: fixture("rss.xml"))
        self.assertEqual(res.counts["new"], 1)
        item = common.load("feeds.json", {})["items"][0]
        self.assertFalse(item["auto_publish"])
        self.assertTrue(item["id"].startswith("f:ex:"))


class FacebookTest(TempData):
    def test_without_secrets_reports_needs_credentials(self):
        from sources import facebook
        os.environ.pop("FACEBOOK_PAGE_TOKEN", None)
        self.assertEqual(facebook.run({}, {"id": "facebook"}).state, "needs-credentials")

    def test_posts_are_imported_for_review(self):
        from sources import facebook
        os.environ["FACEBOOK_PAGE_ID"], os.environ["FACEBOOK_PAGE_TOKEN"] = "123", "TOKEN-xyz"
        try:
            body = json.dumps({"data": [{"id": "1_2", "message": "Katha this Sunday at Sultanpur Lodhi. All welcome.",
                                         "permalink_url": "https://www.facebook.com/1/posts/2", "created_time": "2026-10-20T10:00:00+0000"},
                                        {"id": "1_3", "permalink_url": "https://www.facebook.com/1/posts/3"}]})
            seen = []
            res = facebook.run({"site_name": "Harkhowal Online"}, {"id": "facebook"}, fetch=lambda u, **k: seen.append(u) or body)
            self.assertEqual(res.state, "ok")
            items = common.load("feeds.json", {})["items"]
            self.assertEqual(len(items), 1)
            self.assertFalse(items[0]["auto_publish"])
            self.assertEqual(items[0]["title"], "Katha this Sunday at Sultanpur Lodhi")
            self.assertNotIn("TOKEN-xyz", common.scrub(seen[0]))
        finally:
            del os.environ["FACEBOOK_PAGE_ID"], os.environ["FACEBOOK_PAGE_TOKEN"]


class SheetTest(unittest.TestCase):
    def test_parse(self):
        csv = "Date,End date,Place,Title,Link\n14/11/2026,,Leicester,Katha,javascript:x\n2026-11-01,,Harkhowal,,https://ok.example\n,,,,\n"
        p = sheet.parse(csv)
        self.assertEqual([x["date"] for x in p], ["2026-11-01", "2026-11-14"])
        self.assertEqual(p[1]["link"], "")
        self.assertEqual(p[0]["link"], "https://ok.example")


class BaniDBTest(TempData):
    def test_normalise_ignores_punctuation_and_numbers(self):
        self.assertEqual(banidb.normalise("ਹਉਮੈ ਬੂਝੈ ॥੧॥"), banidb.normalise("ਹਉਮੈਬੂਝੈ"))

    def test_check_line(self):
        page = banidb.collect_unicode(json.loads(fixture("banidb_ang466.json")), [])
        self.assertEqual(banidb.check_line("ਹਉਮੈ ਦੀਰਘ ਰੋਗੁ ਹੈ ਦਾਰੂ ਭੀ ਇਸੁ ਮਾਹਿ ॥", page)[0], "verified")
        self.assertEqual(banidb.check_line("ਹਉਮੈ ਦੀਰਘ ਰੋਗੁ ਨਹੀ ॥", page)[0], "not-found")

    def test_line_on_a_neighbouring_ang_is_reported_and_stays_hidden(self):
        content = self.tmp / "content"
        content.mkdir()
        lines = [{"id": "slip", "gurmukhi": "ਹਉਮੈ ਬੂਝੈ ਤਾ ਦਰੁ ਸੂਝੈ ॥", "source": {"ang": 467}, "confidence": "high"}]
        (content / "gurbani.json").write_text(json.dumps({"lines": lines}), encoding="utf-8")
        old = banidb.CONTENT
        banidb.CONTENT = content
        try:
            pages = {"465": "{}", "466": fixture("banidb_ang466.json"), "467": '{"page": [{"verse": {"unicode": "ਹੋਰ ਬਾਣੀ ॥"}}]}', "468": "{}"}
            res = banidb.run({}, {}, fetch=lambda u, **k: pages[u.split("/angs/")[1].split("/")[0]], delay=0)
            v = common.load("gurbani-verification.json", {})["lines"]["slip"]
            self.assertEqual(v["status"], "wrong-ang")
            self.assertIn("Ang 466", v["reason"])
            self.assertEqual(res.counts["wrong-ang"], 1)
            import knowledge as KN
            self.assertEqual(KN.gurbani_state(lines[0], {"slip": v}, {}), (False, "failed-check"))
        finally:
            banidb.CONTENT = old

    def test_run_checks_each_ang_once_and_caches(self):
        content = self.tmp / "content"
        content.mkdir()
        lines = [{"id": "a", "gurmukhi": "ਹਉਮੈ ਬੂਝੈ ਤਾ ਦਰੁ ਸੂਝੈ ॥", "source": {"ang": 466}},
                 {"id": "b", "gurmukhi": "ਹਉਮੈ ਦੀਰਘ ਰੋਗੁ ਹੈ ਦਾਰੂ ਭੀ ਇਸੁ ਮਾਹਿ ॥", "source": {"ang": 466}},
                 {"id": "c", "gurmukhi": "ਕੁਝ", "source": {}}]
        (content / "gurbani.json").write_text(json.dumps({"lines": lines}), encoding="utf-8")
        old = banidb.CONTENT
        banidb.CONTENT = content
        try:
            calls = []
            res = banidb.run({}, {}, fetch=lambda u, **k: calls.append(u) or fixture("banidb_ang466.json"), delay=0)
            v = common.load("gurbani-verification.json", {})["lines"]
            self.assertEqual(v["a"]["status"], "verified")
            self.assertEqual(v["c"]["status"], "not-applicable")
            self.assertEqual(len(calls), 1)
            self.assertEqual(res.counts["verified"], 2)
            calls.clear()
            banidb.run({}, {}, fetch=lambda u, **k: calls.append(u) or "{}", delay=0)
            self.assertEqual(calls, [], "verified lines are not re-fetched")
        finally:
            banidb.CONTENT = old


if __name__ == "__main__":
    unittest.main()
