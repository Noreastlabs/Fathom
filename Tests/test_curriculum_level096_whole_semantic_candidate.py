"""Whole Level96 source coverage and semantic refusal checks."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


whole = load("Tools/curriculum_level096_whole_semantic_candidate.py", "level096_whole")
narrow = load("Tools/curriculum_level096_music_candidate.py", "level096_narrow")


class WholeLevel96Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = whole.read_source()
        cls.payload = whole.build_from_source(cls.source)
        cls.modules = {m["module"]: m for m in cls.payload["modules"]}

    def changed(self):
        return copy.deepcopy(self.source)

    def test_complete_module_and_event_declarations(self):
        self.assertEqual(len(self.payload["txt_lines"]), 44)
        self.assertEqual(len(self.payload["pdf_pages"]), 18)
        self.assertEqual(self.payload["module_order"], list("ABCDEFGHIJ"))
        self.assertEqual([m["declared_events"] for m in self.payload["modules"]],
                         [96, 112, 144, 128, 128, 96, 192, 192, 320, 64])
        self.assertEqual(self.payload["declared_total_events"], 1472)
        self.assertEqual(self.payload["extracted_task_rows"], 113)
        self.assertEqual([len(self.modules[x]["tasks"]) for x in "ABCDEFGHIJ"],
                         [8, 15, 14, 14, 16, 12, 12, 7, 8, 7])
        self.assertEqual(len(self.payload["supporting_reference"]["rows"]), 8)

    def test_source_page_relations_and_unknown_task_events(self):
        for module in self.modules.values():
            self.assertIsNone(module["allocated_event_count"])
            self.assertFalse(module["per_task_event_counts_known"])
            for row in module["tasks"]:
                page = row["source"]["page"]
                self.assertEqual(row["source"]["extracted_text_sha256"],
                                 self.payload["pdf_pages"][page-1]["extracted_text_sha256"])
                for field in ("declared_event_count_for_row", "canonical_id", "song_or_recording_finding",
                              "learner_answer", "pitch", "duration", "performed_timing"):
                    self.assertIsNone(row[field])

    def test_module_a_matches_prior_narrow_candidate(self):
        old = narrow.module_a(narrow.read_source())["cells"]
        self.assertEqual([r["fields"]["Prompt"] for r in self.modules["A"]["tasks"]],
                         [r["printed_prompt"] for r in old])
        self.assertEqual([r["fields"]["Decision"] for r in self.modules["A"]["tasks"]],
                         [r["printed_decision_question"] for r in old])
        self.assertEqual(whole.GUIDANCE, narrow.GUIDANCE)

    def test_g_h_i_j_specific_structure(self):
        self.assertEqual([s["study"] for s in self.payload["g_studies"]], [1, 2])
        self.assertEqual([r["fields"]["Pass"] for r in self.modules["G"]["tasks"][0:6]],
                         [str(x) for x in range(1, 7)])
        self.assertEqual(self.modules["H"]["tasks"][0]["fields"],
                         {"Fact": "Length", "Supplied information": "24 bars"})
        self.assertEqual([r["fields"]["Bars"] for r in self.modules["I"]["tasks"]],
                         ["1-4", "5-12", "13-16", "17-24", "25-32", "33-40", "41-44", "45-48"])
        self.assertEqual(self.modules["J"]["tasks"][-1]["fields"]["Question"],
                         "What is tomorrow's first 5-minute task?")
        self.assertEqual(self.payload["mastery"]["protected_zero_domains"],
                         ["form", "groove/style match", "rehearsal planning", "recovery"])

    def test_missing_or_changed_tables_refused(self):
        for page, old, new in [(3, "Tempo shown\n", ""),
                               (7, "form + bass + one landmark\n", ""),
                               (14, "memory performance\n", ""),
                               (17, "45-48\n", "45-49\n"),
                               (18, "What is tomorrow's first 5-minute task?\n", "")]:
            with self.subTest(page=page):
                changed = self.changed()
                changed["pdf"]["content"][page-1] = changed["pdf"]["content"][page-1].replace(old, new, 1)
                with self.assertRaises(whole.SourceError):
                    whole.build_from_source(changed)

    def test_declared_total_and_mastery_drift_refused(self):
        changed = self.changed()
        changed["pdf"]["content"][0] = changed["pdf"]["content"][0].replace("TOTAL\n1472", "TOTAL\n1473", 1)
        with self.assertRaisesRegex(whole.SourceError, "module total"):
            whole.build_from_source(changed)
        changed = self.changed()
        changed["txt"]["content"][39] = "15/16 or better on two separate days."
        with self.assertRaisesRegex(whole.SourceError, "TXT line missing/repeated"):
            whole.build_from_source(changed)

    def test_original_source_pins_and_pending_boundary(self):
        for kind in ("txt", "pdf"):
            rel, size, expected = whole.SOURCE[kind]
            raw = (ROOT / rel).read_bytes()
            self.assertEqual((len(raw), whole.sha(raw)), (size, expected))
            self.assertNotEqual(whole.sha(raw + b"changed"), expected)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertFalse(self.payload["whole_workbook_accepted"])
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["schema1_imported"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertIsNone(self.payload["unresolved"]["per_task_event_counts"])
        self.assertIsNone(self.payload["unresolved"]["actual_song_or_recording"])


if __name__ == "__main__":
    unittest.main()
