"""Focused source, prior-slice, and capstone checks for whole Level 94."""

from __future__ import annotations

import collections
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "parallel_07_level094", ROOT / "Tools/parallel_07_level094_whole_candidate.py")
assert spec is not None and spec.loader is not None
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class Level94WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = converter.build(ROOT)

    def test_pinned_pair_and_whole_pdf_expansion(self) -> None:
        c = self.c
        self.assertEqual(c["source_map"]["level"], 94)
        self.assertEqual(c["source_map"]["wbs_owner"], "2.3.1.3.1")
        self.assertIn("pdf_expansion_requires_page_level_conversion_review",
                      c["source_map"]["source_specific_ambiguities"])
        self.assertEqual(len(c["source_archive"]["txt_lines"]), 44)
        self.assertEqual(len(c["source_archive"]["pdf_pages"]), 20)
        self.assertEqual(len(c["pdf_tables"]), 16)
        self.assertEqual(c["declared_workload_total"], 1472)
        self.assertEqual(sum(c["module_workload_declared"].values()), 1472)
        self.assertFalse(c["admission_claim"])

    def test_six_arcs_match_read_only_p06_slice(self) -> None:
        prior = json.loads((ROOT / "Build/parallel-06/2.3-level094-music-r01/candidate-a.json").read_text())
        arcs = [t for t in self.c["tasks"] if t["kind"] == "plain_target_emotional_arc"]
        self.assertEqual(len(arcs), 6)
        self.assertEqual(len(prior["module_a"]["cells"]), 6)
        for whole, narrow in zip(arcs, prior["module_a"]["cells"], strict=True):
            self.assertEqual(whole["fields"]["arc"], narrow["printed_arc"])
            self.assertEqual([w["expression"] for w in whole["fields"]["bar_windows"]],
                             [w["printed_cell"] for w in narrow["ordered_printed_windows"]])
            self.assertTrue(whole["fields"]["no_initial_ornaments"])

    def test_complete_studies_fixed_targets_two_peak_capstone_and_rubric(self) -> None:
        c = self.c
        tasks, markers = c["tasks"], c["bar_or_window_markers"]
        self.assertEqual(len(tasks), 146)
        self.assertEqual(len(markers), 104)
        self.assertEqual(len({t["local_key"] for t in tasks}), len(tasks))
        self.assertEqual(len({m["local_key"] for m in markers}), len(markers))
        self.assertEqual(dict(collections.Counter(m["module"] for m in markers)),
                         {"A": 24, "G": 32, "H": 8, "I": 40})
        self.assertEqual(len(c["g_studies"]), 4)
        self.assertTrue(all(len(s["chords"]) == 8 and len(s["passes"]) == 6
                            for s in c["g_studies"]))
        targets = [m for m in markers if m["module"] == "H"]
        self.assertEqual([m["bar"] for m in targets], list(range(1, 9)))
        self.assertTrue(all(m["target"] in converter.PC for m in targets))
        self.assertEqual([b["bar"] for b in c["capstone_bar_plan"]], list(range(1, 41)))
        self.assertEqual([b["bar"] for b in c["capstone_bar_plan"]
                          if b["arc_role"] == "first peak"], [13, 14, 15, 16])
        self.assertEqual([b["bar"] for b in c["capstone_bar_plan"]
                          if b["arc_role"] == "second peak"], [25, 26, 27, 28])
        self.assertEqual(len([t for t in tasks if t["kind"] == "completion_score_category"]), 8)
        self.assertTrue(all(m["onset_q"] is None and m["duration_q"] is None
                            and m["fret"] is None for m in markers))


if __name__ == "__main__":
    unittest.main()
