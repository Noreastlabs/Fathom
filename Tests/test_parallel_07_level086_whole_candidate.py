"""Focused PDF expansion checks for detached Level 86 groove conversion."""

from __future__ import annotations

import collections
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "parallel_07_level086", ROOT / "Tools/parallel_07_level086_whole_candidate.py")
assert spec is not None and spec.loader is not None
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class Level86WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = converter.build(ROOT)

    def test_pinned_index_and_expanded_pdf_coverage(self) -> None:
        c = self.c
        self.assertEqual(c["source_map"]["level"], 86)
        self.assertEqual(c["source_map"]["wbs_owner"], "2.3.1.3.1")
        self.assertIn("pdf_expansion_requires_page_level_conversion_review",
                      c["source_map"]["source_specific_ambiguities"])
        self.assertEqual(len(c["source_archive"]["txt_lines"]), 43)
        self.assertEqual(len(c["source_archive"]["pdf_pages"]), 15)
        self.assertEqual(len(c["pdf_tables"]), 11)
        self.assertEqual(c["declared_workload_total"], 1504)
        self.assertEqual(sum(c["module_workload_declared"].values()), 1504)
        self.assertFalse(c["admission_claim"])

    def test_grid_slots_keep_sixteenth_hierarchy_without_pitch_invention(self) -> None:
        c = self.c
        slots = c["grid_slots"]
        self.assertEqual(len(slots), 252)
        self.assertEqual(len({s["local_key"] for s in slots}), len(slots))
        self.assertEqual(dict(collections.Counter(s["module"] for s in slots)),
                         {"A": 96, "B": 28, "E": 128})
        self.assertTrue(all(s["symbol"] in converter.SLOT_MEANING and s["pitch"] is None
                            and s["onset_q"] is None and s["duration_q"] is None
                            for s in slots))
        first = [s for s in slots if s["module"] == "A" and s["source"]["row"] == 1]
        self.assertEqual([s["symbol"] for s in first], list("Pggg" * 4))
        self.assertEqual([s["beat"] for s in first], [b for b in range(1, 5) for _ in range(4)])

    def test_studies_capstone_and_recovery_are_complete(self) -> None:
        c = self.c
        tasks, events = c["tasks"], c["contact_or_bar_events"]
        self.assertEqual(len(tasks), 104)
        self.assertEqual(len(events), 88)
        self.assertEqual(len({t["local_key"] for t in tasks}), len(tasks))
        self.assertEqual(len({e["local_key"] for e in events}), len(events))
        self.assertEqual(len(c["h_studies"]), 4)
        self.assertTrue(all(len(s["chords"]) == 8 and len(s["passes"]) == 6
                            for s in c["h_studies"]))
        self.assertEqual([b["bar"] for b in c["capstone_bar_plan"]], list(range(1, 33)))
        self.assertEqual(len([t for t in tasks if t["kind"] == "pocket_recovery"]), 8)
        self.assertEqual(len([t for t in tasks if t["kind"] == "instructional_method"]), 7)
        self.assertTrue(all(e["pitch"] is None for e in events))


if __name__ == "__main__":
    unittest.main()
