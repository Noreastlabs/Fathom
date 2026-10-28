"""Full Level91 source coverage and refusal checks."""

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


whole = load("Tools/curriculum_level091_whole_semantic_candidate.py", "level091_whole")
narrow = load("Tools/curriculum_level091_music_candidate.py", "level091_narrow")


class WholeLevel91Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = whole.read_source()
        cls.payload = whole.build_from_source(cls.source)
        cls.modules = {m["module"]: m for m in cls.payload["modules"]}

    def changed(self):
        return copy.deepcopy(self.source)

    def test_full_source_and_declared_events(self):
        self.assertEqual(len(self.payload["txt_lines"]), 37)
        self.assertEqual(len(self.payload["pdf_pages"]), 17)
        self.assertEqual(self.payload["module_order"], list("ABCDEFGHIJ"))
        self.assertEqual([m["declared_events"] for m in self.payload["modules"]],
                         [144, 128, 144, 128, 128, 128, 112, 192, 256, 64])
        self.assertEqual(self.payload["declared_total_events"], 1424)
        self.assertEqual(self.payload["txt_total_anchor_line"], 7)
        self.assertEqual(self.payload["extracted_task_rows"], 98)
        self.assertEqual(self.payload["supporting_rows"], 12)

    def test_every_module_task_has_exact_source_and_no_invented_event(self):
        self.assertEqual([len(self.modules[x]["tasks"]) for x in "ABCDEFGHIJ"],
                         [8, 8, 12, 8, 6, 8, 8, 24, 8, 8])
        for module in self.modules.values():
            self.assertIsNone(module["allocated_event_count"])
            self.assertFalse(module["per_task_event_counts_known"])
            for task in module["tasks"]:
                self.assertIn(task["source"]["page"], range(1, 18))
                self.assertEqual(task["source"]["extracted_text_sha256"],
                                 self.payload["pdf_pages"][task["source"]["page"]-1]["extracted_text_sha256"])
                self.assertIsNone(task["declared_event_count_for_row"])
                self.assertIsNone(task["canonical_id"])
                self.assertIsNone(task["pitch"])
                self.assertIsNone(task["duration"])
                self.assertIsNone(task["performed_timing"])

    def test_narrow_module_a_examples_preserved(self):
        old = narrow.module_a(narrow.read_source())["cells"]
        self.assertEqual([x["fields"]["Example"] for x in self.modules["A"]["tasks"]],
                         [x["printed_example"] for x in old])
        self.assertEqual(self.modules["A"]["tasks"][-1]["fields"]["Task"],
                         "half-step + 2-beat hold")

    def test_h_studies_i_ranges_and_j_recovery(self):
        studies = self.modules["H"]["tasks"]
        self.assertEqual([x["study"] for x in studies[0::6]], [1, 2, 3, 4])
        self.assertEqual([x["fields"]["Bars"] for x in self.modules["I"]["tasks"]],
                         [f"{n}-{n+3}" for n in range(1, 33, 4)])
        self.assertEqual(self.modules["I"]["tasks"][-1]["fields"]["Focus"], "resolution/outro")
        self.assertEqual(self.modules["J"]["tasks"][-1]["fields"]["Repair"], "chord tones only")
        self.assertEqual(self.payload["mastery"]["protected_zero_domains"],
                         ["bend intonation", "vibrato control", "pulse", "recovery"])

    def test_supporting_tables_remain_unallocated(self):
        self.assertEqual([(x["page"], len(x["rows"])) for x in self.payload["supporting_tables"]],
                         [(2, 6), (4, 6)])
        self.assertEqual(self.payload["supporting_tables"][1]["relation"],
                         "adjacent_unallocated_timed_arrival_reference")

    def test_missing_or_changed_task_rows_refused(self):
        for page, old, new in [(5, "silent setup after rest\n", ""),
                               (12, "record performance tone\n", ""),
                               (16, "29-32\n", "29-33\n")]:
            with self.subTest(page=page):
                changed = self.changed()
                changed["pdf"]["content"][page-1] = changed["pdf"]["content"][page-1].replace(old, new, 1)
                with self.assertRaises(whole.SourceError):
                    whole.build_from_source(changed)

    def test_module_event_total_and_mastery_drift_refused(self):
        changed = self.changed()
        changed["pdf"]["content"][0] = changed["pdf"]["content"][0].replace("TOTAL\n1424", "TOTAL\n1425", 1)
        with self.assertRaisesRegex(whole.SourceError, "module table/total drift"):
            whole.build_from_source(changed)
        changed = self.changed()
        changed["txt"]["content"][32] = "15/16 or better on two separate days."
        with self.assertRaisesRegex(whole.SourceError, "mastery wording drift"):
            whole.build_from_source(changed)

    def test_original_byte_pins_and_pending_boundary(self):
        for kind in ("txt", "pdf"):
            rel, size, expected = whole.SOURCE[kind]
            raw = (ROOT / rel).read_bytes()
            self.assertEqual((len(raw), whole.sha(raw)), (size, expected))
            self.assertNotEqual(whole.sha(raw + b"changed"), expected)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertFalse(self.payload["whole_workbook_accepted"])
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertFalse(self.payload["schema1_imported"])
        self.assertIsNone(self.payload["unresolved"]["per_task_event_counts"])


if __name__ == "__main__":
    unittest.main()
