"""Tests for the regulatory change watcher. Stdlib unittest; fixture-backed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regwatch import articles, assessments, audit, diff, extract, mapper, snapshot

FIX = Path(__file__).parent / "fixtures"


class TestExtract(unittest.TestCase):
    def test_eulex_articles(self):
        html = (FIX / "eulex_sample.html").read_text()
        units = extract.extract("eulex_articles", html)
        refs = [u["ref"] for u in units]
        self.assertEqual(refs, ["Article 9", "Article 10", "Article 50", "Annex III"])
        art9 = units[0]
        self.assertIn("Risk management system", art9["title"])
        self.assertEqual(len(art9["paragraphs"]), 2)
        self.assertTrue(art9["paragraphs"][0].startswith("1. A risk management system"))

    def test_generic(self):
        html = (FIX / "generic_sample.html").read_text()
        units = extract.extract("generic", html)
        refs = [u["ref"] for u in units]
        self.assertIn("AI Risk Management Framework", refs)
        self.assertIn("Core Functions", refs)
        # nav crumbs must not leak in
        blob = " ".join(p for u in units for p in u["paragraphs"])
        self.assertNotIn("Home | About", blob)

    def test_generic_fallback_never_empty(self):
        units = extract.extract("generic", "<html><body><p>" + "x" * 100 + "</p></body></html>")
        self.assertTrue(units)


class TestArticles(unittest.TestCase):
    def test_parse_refs(self):
        toks = articles.parse_refs("Article 6(2); Annex III, point 4(a)-(b)")
        self.assertEqual(toks, {"article:6", "annex:III:4"})

    def test_parse_refs_bare_annex(self):
        self.assertEqual(articles.parse_refs("Article 11, Annex IV"),
                         {"article:11", "annex:IV"})

    def test_overlaps_exact(self):
        self.assertTrue(articles.overlaps({"article:9"}, {"article:9", "article:10"}))

    def test_overlaps_paragraph_detail(self):
        # change to Article 9 matches a citation of Article 9(1) and vice versa
        self.assertTrue(articles.overlaps({"article:9"}, {"article:9"}))
        self.assertEqual(articles.ref_label_to_tokens("Article 9(1)"), {"article:9"})

    def test_overlaps_annex_point(self):
        self.assertTrue(articles.overlaps({"annex:III"}, {"annex:III:4"}))
        self.assertTrue(articles.overlaps({"annex:III:4"}, {"annex:III"}))

    def test_no_overlap(self):
        self.assertFalse(articles.overlaps({"article:50"}, {"article:9"}))


class TestDiff(unittest.TestCase):
    def _units(self, name):
        return extract.extract("eulex_articles", (FIX / name).read_text())

    def test_modified_article_detected(self):
        events = diff.diff_units(self._units("eulex_sample.html"),
                                 self._units("eulex_sample_v2.html"))
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["ref"], "Article 9")
        self.assertEqual(ev["change"], "modified")
        self.assertEqual(len(ev["added_paragraphs"]), 1)
        self.assertEqual(len(ev["removed_paragraphs"]), 1)
        self.assertIn("annually", ev["added_paragraphs"][0])

    def test_identical_no_events(self):
        units = self._units("eulex_sample.html")
        self.assertEqual(diff.diff_units(units, units), [])

    def test_added_removed(self):
        old = [{"ref": "Article 1", "title": "t", "paragraphs": ["a"]}]
        new = [{"ref": "Article 2", "title": "t", "paragraphs": ["b"]}]
        events = diff.diff_units(old, new)
        kinds = {(e["ref"], e["change"]) for e in events}
        self.assertEqual(kinds, {("Article 1", "removed"), ("Article 2", "added")})


class TestAssessments(unittest.TestCase):
    def test_from_real_aiact_report(self):
        report = json.loads((FIX / "hire-screen.report.json").read_text())
        rec = assessments.from_aiact_report(report)
        self.assertEqual(rec["instrument"], "eu-ai-act")
        self.assertEqual(rec["risk_tier"], "high-risk")
        toks = set(rec["provision_tokens"])
        self.assertIn("article:9", toks)
        self.assertIn("article:10", toks)
        self.assertIn("annex:III:4", toks)
        self.assertGreaterEqual(len(toks), 10)

    def test_spam_filter_no_provisions(self):
        report = json.loads((FIX / "spam-filter.report.json").read_text())
        rec = assessments.from_aiact_report(report)
        self.assertEqual(rec["provision_tokens"], [])


class TestMapper(unittest.TestCase):
    def _hire(self):
        return assessments.from_aiact_report(
            json.loads((FIX / "hire-screen.report.json").read_text()))

    def _chat(self):
        return assessments.from_aiact_report(
            json.loads((FIX / "support-chatbot.report.json").read_text()))

    def test_changed_article_flags_citing_assessment(self):
        events = {"eu-ai-act": [{"ref": "Article 9", "change": "modified",
                                 "summary": "Article 9 modified"}]}
        flags = mapper.flag_assessments(events, [self._hire(), self._chat()],
                                        {"eu-ai-act": True})
        ids = [f["assessment_id"] for f in flags]
        self.assertIn(self._hire()["id"], ids)
        self.assertNotIn(self._chat()["id"], ids)  # cites only Article 50

    def test_unrelated_change_flags_nothing(self):
        events = {"eu-ai-act": [{"ref": "Article 99", "change": "modified",
                                 "summary": "x"}]}
        flags = mapper.flag_assessments(events, [self._hire(), self._chat()],
                                        {"eu-ai-act": True})
        self.assertEqual(flags, [])

    def _gpai(self):
        return assessments.from_aiact_report(
            json.loads((FIX / "gpai-frontier.report.json").read_text()))

    def test_article50_change_flags_both_citing_assessments(self):
        # hire-screen and the chatbot both cite Article 50 (transparency),
        # so a change there flags both; the GPAI assessment does not cite it.
        events = {"eu-ai-act": [{"ref": "Article 50", "change": "modified",
                                 "summary": "Article 50 modified"}]}
        flags = mapper.flag_assessments(
            events, [self._hire(), self._chat(), self._gpai()], {"eu-ai-act": True})
        ids = [f["assessment_id"] for f in flags]
        self.assertIn(self._hire()["id"], ids)
        self.assertIn(self._chat()["id"], ids)
        self.assertNotIn(self._gpai()["id"], ids)

    def test_gpai_change_flags_only_gpai(self):
        events = {"eu-ai-act": [{"ref": "Article 53", "change": "modified",
                                 "summary": "Article 53 modified"}]}
        flags = mapper.flag_assessments(
            events, [self._hire(), self._chat(), self._gpai()], {"eu-ai-act": True})
        ids = [f["assessment_id"] for f in flags]
        self.assertEqual(ids, [self._gpai()["id"]])

    def test_generic_instrument_whole_watch(self):
        a = assessments.manual_assessment("nist-watch", "RMF watch", "nist-ai-rmf", [])
        events = {"nist-ai-rmf": [{"ref": "Profiles", "change": "modified",
                                   "summary": "Profiles modified"}]}
        flags = mapper.flag_assessments(events, [a], {"nist-ai-rmf": False})
        self.assertEqual(len(flags), 1)


class TestSnapshotAudit(unittest.TestCase):
    def test_snapshot_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            src = {"id": "s1", "name": "S"}
            units = [{"ref": "Article 1", "title": "t", "paragraphs": ["a"]}]
            m1 = snapshot.save_snapshot(base, src, "http://x", units)
            m2 = snapshot.save_snapshot(base, src, "http://x", units)
            self.assertTrue(m2["unchanged"])
            self.assertEqual(len(snapshot.list_snapshots(base, "s1")), 1)
            m3 = snapshot.save_snapshot(
                base, src, "http://x",
                [{"ref": "Article 1", "title": "t", "paragraphs": ["b"]}])
            self.assertFalse(m3["unchanged"])
            self.assertEqual(len(snapshot.list_snapshots(base, "s1")), 2)

    def test_audit_chain_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            audit.append(base, "crawl", {"source": "s1"})
            audit.append(base, "diff", {"changes": 2})
            ok, msg = audit.verify(base)
            self.assertTrue(ok, msg)
            # tamper
            log = base / "audit.jsonl"
            lines = log.read_text().splitlines()
            e = json.loads(lines[0])
            e["details"] = {"source": "evil"}
            lines[0] = json.dumps(e)
            log.write_text("\n".join(lines) + "\n")
            ok, msg = audit.verify(base)
            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
