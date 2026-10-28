"""Focused whole-source and authorship checks for Level 100."""

from __future__ import annotations

import collections
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "parallel_07_level100", ROOT / "Tools/parallel_07_level100_whole_candidate.py")
assert spec is not None and spec.loader is not None
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class Level100WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = converter.build(ROOT)

    def test_pinned_pair_and_complete_pdf_detail(self) -> None:
        c = self.c
        self.assertEqual(c["source_map"]["level"], 100)
        self.assertEqual(c["source_map"]["section"], "XV")
        self.assertIn("pdf_expansion_requires_page_level_conversion_review",
                      c["source_map"]["source_specific_ambiguities"])
        self.assertEqual(len(c["source_archive"]["txt_lines"]), 48)
        self.assertEqual(len(c["source_archive"]["pdf_pages"]), 21)
        self.assertEqual(len(c["pdf_tables"]), 17)
        self.assertEqual(c["declared_workload_total"], 1520)
        self.assertEqual(sum(c["module_workload_declared"].values()), 1520)
        self.assertFalse(c["admission_claim"])

    def test_seed_routes_and_six_printed_variants(self) -> None:
        c = self.c
        tasks = c["tasks"]
        events = c["source_supported_seed_or_contact_events"]
        self.assertEqual(len(tasks), 149)
        self.assertEqual(len(events), 59)
        self.assertEqual(len({t["local_key"] for t in tasks}), len(tasks))
        self.assertEqual(len({e["local_key"] for e in events}), len(events))
        self.assertEqual(dict(collections.Counter(e["kind"] for e in events)),
                         {"seed_degree": 30, "rhythm_contact": 13,
                          "printed_bass_route": 16})
        routes = [t for t in tasks if t["kind"] == "bass_first_design"
                  and t["fields"]["printed_bass_route"]]
        self.assertEqual([t["fields"]["printed_bass_route"] for t in routes],
                         [["C", "B", "A", "G", "F", "E", "D", "G"],
                          ["A", "B", "C", "D", "E", "F", "G", "A"]])
        self.assertEqual(len([t for t in tasks if t["kind"] == "same_melody_harmonization"]), 6)
        self.assertEqual(len([t for t in tasks if t["kind"] == "fixed_harmony_rhythmic_identity"]), 6)
        self.assertEqual(len([x for x in c["source_tensions"] if x.get("pdf_page") in (10, 14)]), 2)

    def test_four_studies_and_blank_thirty_two_bar_authorship(self) -> None:
        c = self.c
        self.assertEqual(len(c["h_studies"]), 4)
        self.assertTrue(all(len(s["passes"]) == 6 for s in c["h_studies"]))
        portfolio = c["portfolio_bar_allocations"]
        self.assertEqual([b["bar"] for b in portfolio], list(range(1, 33)))
        self.assertEqual([b["piece"] for b in portfolio],
                         [f"Piece {letter}" for letter in "ABCD" for _ in range(8)])
        self.assertTrue(all(b["authored_chord"] is None and b["authored_melody"] is None
                            and b["authored_bass"] is None and b["authored_rhythm"] is None
                            for b in portfolio))
        piece_tasks = [t for t in c["tasks"] if t["kind"] == "composition_portfolio_piece"]
        self.assertEqual([t["fields"]["starting_method"] for t in piece_tasks],
                         ["motif-first", "melody-first", "bass-first", "rhythm-first"])
        self.assertEqual(len([t for t in c["tasks"] if t["kind"] == "revision_authorship_question"]), 8)


if __name__ == "__main__":
    unittest.main()
