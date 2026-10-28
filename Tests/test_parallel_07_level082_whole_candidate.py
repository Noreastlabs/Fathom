"""Focused whole-source coverage and musical checks for Level 82."""

from __future__ import annotations

import collections
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "parallel_07_level082", ROOT / "Tools/parallel_07_level082_whole_candidate.py")
assert spec is not None and spec.loader is not None
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class Level82WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c = converter.build(ROOT)

    def test_pinned_sources_and_workload_boundaries(self) -> None:
        c = self.c
        self.assertEqual(c["source_map"]["level"], 82)
        self.assertEqual(c["source_map"]["wbs_owner"], "2.3.1.3.1")
        self.assertEqual(len(c["source_archive"]["txt_lines"]), 355)
        self.assertEqual(len(c["source_archive"]["pdf_pages"]), 20)
        self.assertEqual(len(c["pdf_tables"]), 7)
        self.assertEqual(c["declared_workload_total"], 1392)
        self.assertEqual(sum(c["module_workload_declared"].values()), 1392)
        self.assertFalse(c["admission_claim"])

    def test_every_authored_study_and_capstone_occurrence(self) -> None:
        c = self.c
        tasks, events = c["tasks"], c["explicit_pitch_events"]
        self.assertEqual(len(tasks), 134)
        self.assertEqual(len(events), 615)
        self.assertEqual(len({t["local_key"] for t in tasks}), len(tasks))
        self.assertEqual(len({e["local_key"] for e in events}), len(events))
        self.assertEqual(dict(collections.Counter(t["module"] for t in tasks)),
                         {"A": 9, "B": 9, "C": 11, "D": 9, "E": 7, "F": 7,
                          "G": 7, "H": 33, "I": 33, "J": 9})
        a = [t for t in tasks if t["kind"] == "walking_bass_chord_melody_study"]
        self.assertEqual(len(a), 8)
        self.assertEqual([t["fields"]["pdf_status"] for t in a],
                         ["exact_printed_study"] * 4 + ["txt_only_study"] * 4)
        h = [t for t in tasks if t["kind"] == "arrangement_bar"]
        i = [t for t in tasks if t["kind"] == "capstone_bar"]
        self.assertEqual(len(h), len(i))
        self.assertEqual(len(i), 32)
        self.assertEqual([(t["fields"]["chord"], t["fields"]["bass"],
                           t["fields"]["melody"]) for t in h],
                         [(t["fields"]["chord"], t["fields"]["bass"],
                           t["fields"]["melody"]) for t in i])

    def test_printed_pitch_spelling_and_unresolved_timing(self) -> None:
        c = self.c
        events = c["explicit_pitch_events"]
        self.assertTrue(any(e["pitch_name"] == "F##" for e in events))
        self.assertEqual(converter.PC["F##"], converter.PC["G"])
        self.assertTrue(all(e["pitch_name"] in converter.PC for e in events))
        self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None
                            and e["string"] is None and e["fret"] is None for e in events))
        self.assertEqual(len([t for t in c["tasks"] if t["kind"] == "no_restart_repair"]), 8)
        self.assertEqual(len([t for t in c["tasks"] if t["kind"] == "instructional_method"]), 10)


if __name__ == "__main__":
    unittest.main()
