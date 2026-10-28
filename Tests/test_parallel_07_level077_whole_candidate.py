"""Focused source and music audits for P07's detached Level 77 candidate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "Tools/parallel_07_level077_whole_candidate.py"
spec = importlib.util.spec_from_file_location("parallel_07_level077", MODULE)
assert spec is not None and spec.loader is not None
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class WholeLevel77CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = converter.build(ROOT)

    def test_source_identity_and_full_printed_coverage(self) -> None:
        c = self.candidate
        self.assertEqual(c["source_map"]["level"], 77)
        self.assertEqual(c["source_map"]["wbs_owner"], "2.3.1.3.1")
        self.assertEqual(len(c["source_archive"]["txt_lines"]), 80)
        self.assertEqual(len(c["source_archive"]["pdf_pages"]), 20)
        self.assertEqual(c["declared_workload_total"], 952)
        self.assertEqual(set(c["module_workload_declared"]), set("ABCDEFGH"))
        self.assertEqual(len(c["pdf_tables"]), 16)
        self.assertEqual(len(c["pdf_tables"]["model_bars"]["rows"]), 16)
        self.assertEqual(len(c["pdf_tables"]["interval_cards"]["rows"]), 24)

    def test_tasks_events_and_source_links_are_distinct_and_honest(self) -> None:
        c = self.candidate
        tasks, events = c["tasks"], c["explicit_pitch_events"]
        self.assertEqual(len(tasks), 206)
        self.assertEqual(len(events), 277)
        self.assertEqual(len({t["local_key"] for t in tasks}), len(tasks))
        self.assertEqual(len({e["local_key"] for e in events}), len(events))
        self.assertTrue(all(1 <= t["source"]["pdf_page"] <= 20 for t in tasks))
        self.assertTrue(all(1 <= e["source"]["pdf_page"] <= 20 for e in events))
        self.assertTrue(all(e["pitch_name"] in converter.PC and e["onset_q"] is None
                            and e["string"] is None and e["fret"] is None for e in events))
        self.assertFalse(c["admission_claim"])
        self.assertEqual(len([t for t in tasks if t["kind"] == "random_function_prompt"]), 18)
        self.assertEqual(len([t for t in tasks if t["kind"] == "model_bar"]), 16)
        self.assertEqual(len([t for t in tasks if t["kind"] == "instructional_method"]), 18)

    def test_source_tensions_preserve_printed_errors(self) -> None:
        c = self.candidate
        anomalies = c["source_tensions"]
        self.assertEqual(len(anomalies), 8)
        card = next(a for a in anomalies if a.get("printed_answer") == "m6")
        self.assertEqual(card["computed_semitones"], 9)
        deck = next(a for a in anomalies if a.get("missing_prompt_numbers"))
        self.assertEqual(deck["missing_prompt_numbers"], [19, 20, 21, 22, 23, 24])
        bar20 = next(t for t in c["tasks"] if t["kind"] == "interval_dictation"
                     and t["source"]["table_row"] == 20)
        self.assertEqual(bar20["fields"]["answer"], "m6")
        self.assertEqual(bar20["fields"]["start"], "B")
        self.assertEqual(bar20["fields"]["destination"], "D")


if __name__ == "__main__":
    unittest.main()
