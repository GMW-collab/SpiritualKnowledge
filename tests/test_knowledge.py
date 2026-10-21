"""The knowledge model: text folding, classification, Ang links and the integrity of the content files."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import knowledge as K  # noqa: E402


class FoldTest(unittest.TestCase):
    def test_gurmukhi_variants_fold_together(self):
        self.assertEqual(K.fold("ਸ਼ਬਦ"), K.fold("ਸਬਦ"))
        self.assertEqual(K.fold("ਸੱਚ"), K.fold("ਸਚ"))
        self.assertEqual(K.fold("Sri_Jap-Ji  Sahib"), "sri jap ji sahib")

    def test_word_matching(self):
        t = K.fold("ਮਨ ਦੀਆਂ ਵਾਸ਼ਨਾਵਾਂ। ਮਨਮੁਖ")
        self.assertTrue(K.term_hits(t, "=ਮਨ"))
        self.assertTrue(K.term_hits(t, "ਵਾਸ਼ਨਾ"))
        self.assertFalse(K.term_hits(K.fold("ਮਨਮੁਖ"), "=ਮਨ"))
        self.assertFalse(K.term_hits(K.fold("ਬ੍ਰਹਮਚਾਰੀ"), "=ਬ੍ਰਹਮ"))


class AngIndexTest(unittest.TestCase):
    def setUp(self):
        self.series = [
            {"id": "sggs", "title": "SGGS", "tracks": [
                {"t": "0006 Sri Jap Ji Sahib Pauri 01", "p": "a", "i": 0},
                {"t": "0032 Sri Jap Ji Sahib Pauri 28 and 29", "p": "b", "i": 1},
                {"t": "0196 Sri Guru Granth Sahib Katha - Ang 0465 to 0467", "p": "c", "i": 2},
                {"t": "Guru Granth Sahib Katha Ang 0887-0888", "p": "d", "i": 3}]},
            {"id": "japji", "title": "Jap Ji Sahib Katha", "tracks": [
                {"t": "Sri Jap Ji Sahib Katha - Pauri 37 to Salok", "p": "e", "i": 0}]}]
        self.idx = K.katha_index(self.series)

    def test_ang_ranges(self):
        line = {"source": {"ang": 466}}
        self.assertEqual([t["p"] for t, s in K.katha_for_line(line, self.idx)], ["c"])
        self.assertEqual([t["p"] for t, s in K.katha_for_line({"source": {"ang": 888}}, self.idx)], ["d"])
        self.assertEqual(K.katha_for_line({"source": {"ang": 1200}}, self.idx), [])

    def test_japji_pauris_and_salok(self):
        self.assertEqual([t["p"] for t, s in K.katha_for_line({"japji_pauri": 28, "source": {"ang": 6}}, self.idx)], ["b"])
        self.assertEqual([t["p"] for t, s in K.katha_for_line({"japji_pauri": 39, "source": {"ang": 8}}, self.idx)], ["e"])


class GurbaniRulesTest(unittest.TestCase):
    def test_display_rules(self):
        hi = {"id": "x", "confidence": "high"}
        tv = {"id": "y", "confidence": "to-verify"}
        self.assertEqual(K.gurbani_state(hi, {}, {}), (True, "unchecked"))
        self.assertEqual(K.gurbani_state(tv, {}, {}), (False, "awaiting-check"))
        self.assertEqual(K.gurbani_state(tv, {"y": {"status": "verified"}}, {}), (True, "verified"))
        self.assertEqual(K.gurbani_state(hi, {"x": {"status": "not-found"}}, {}), (False, "failed-check"))
        self.assertEqual(K.gurbani_state(tv, {}, {"gurbani_confirmed": ["y"]}), (True, "editor-confirmed"))


class ContentIntegrityTest(unittest.TestCase):
    """The rules that keep the site honest, checked on every build."""

    @classmethod
    def setUpClass(cls):
        cls.k = K.load_all()

    def test_every_gurbani_line_is_fully_sourced(self):
        for gid, line in self.k["gurbani"].items():
            src = line["source"]
            for f in ("granth", "bani", "author"):
                self.assertTrue(src.get(f), f"{gid} lacks {f}")
            self.assertIsInstance(src.get("ang"), int, gid)
            self.assertTrue(1 <= src["ang"] <= 1430, gid)
            self.assertRegex(line["gurmukhi"], "[਀-੿]", gid)
            self.assertTrue(line["translit"] and line["rendering"], gid)
            self.assertIn(line["confidence"], ("high", "to-verify"), gid)

    def test_themes_reference_known_gurbani_and_are_labelled(self):
        for th in self.k["themes"]:
            for f in ("slug", "gurmukhi", "title", "question", "summary", "anchor", "review"):
                self.assertTrue(th.get(f), f"{th.get('slug')} lacks {f}")
            for key in ("discover", "understand", "reflect", "practise"):
                self.assertTrue(th["sections"].get(key), f"{th['slug']} lacks section {key}")
            body = "\n".join(th["sections"].values())
            for gid in K.gurbani_refs(body) + [th["anchor"]]:
                self.assertIn(gid, self.k["gurbani"], f"{th['slug']} cites unknown line {gid}")
            self.assertIn(th["review"]["status"], ("awaiting-review", "reviewed", "needs-changes"))

    def test_no_untagged_quotation_of_gurbani_in_prose(self):
        """Gurbani must enter a page through gurbani.json (with its source), never as loose text."""
        lines = {l["gurmukhi"].split("॥")[0].strip() for l in self.k["gurbani"].values()}
        for th in self.k["themes"]:
            body = "\n".join(th["sections"].values())
            for first in lines:
                self.assertNotIn(first, body, f"{th['slug']} quotes Gurbani inline: {first}")

    def test_comparisons_name_their_source(self):
        for th in self.k["themes"]:
            for m in re.finditer(r"^::: compare (.*)$", "\n".join(th["sections"].values()), re.M):
                tradition, _, source = m.group(1).partition("|")
                self.assertTrue(tradition.strip() and source.strip(), f"{th['slug']}: comparison without tradition and source")

    def test_graph_and_shelves_reference_real_things(self):
        slugs = {t["slug"] for t in self.k["themes"]}
        for ed in self.k["graph"]:
            self.assertIn(ed["a"], slugs)
            self.assertIn(ed["b"], slugs)
            self.assertTrue(ed["why"])
            for g in ed.get("gurbani", []):
                self.assertIn(g, self.k["gurbani"])
        for sh in self.k["texts"]["shelves"]:
            for sid in sh["series"]:
                self.assertIn(sid, self.k["texts"]["profiles"], f"shelf {sh['id']} lists {sid} without a profile")
        for sid, p in self.k["texts"]["profiles"].items():
            for t in p.get("themes", []):
                self.assertIn(t, slugs, sid)

    def test_external_items_are_attributed(self):
        for x in self.k["external"]["items"]:
            self.assertTrue(x.get("creator") and x.get("source_note"), x["id"])
            self.assertIn(x["status"], ("published", "review", "rejected"))

    def test_classification_records_how_each_link_was_made(self):
        links = K.classify(self.k)
        self.assertTrue(links)
        for iid, th in links.items():
            for slug, info in th.items():
                self.assertIn(slug, self.k["theme_by_slug"])
                self.assertTrue(info["via"])

    def test_overrides_apply(self):
        k = dict(self.k)
        vid = "yt:" + self.k["videos"][0]["id"]
        k["overrides"] = {"theme_add": {vid: ["seva"]}, "theme_remove": {vid: ["naam"]}, "theme_confirmed": {}}
        links = K.classify(k)
        self.assertIn("seva", links[vid])
        self.assertTrue(links[vid]["seva"]["confirmed"])
        self.assertNotIn("naam", links.get(vid, {}))


if __name__ == "__main__":
    unittest.main()
