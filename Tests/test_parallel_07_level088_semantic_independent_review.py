"""Bounded independent parity checks for parked Level88 review."""

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("p07_level088_review", ROOT / "Tools/parallel_07_level088_semantic_independent_review.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Level88IndependentReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tool.read_inputs(ROOT)

    def changed(self):
        return copy.deepcopy(self.data)

    def test_all_fifteen_pages_and_seventy_task_units(self):
        verdict = tool.review(self.data)
        self.assertEqual(verdict["parity"], "pass")
        self.assertEqual([x["page"] for x in verdict["task_page_checks"]], list(range(1,16)))
        self.assertEqual(verdict["source_task_units"], 70)
        self.assertEqual(verdict["declared_events_unmapped"], 1536)

    def test_task_row_mismatch_is_rejected(self):
        d = self.changed()
        d["candidate"]["modules"][0]["task_rows"][0]["fields"]["grid_literal"] = "M M"
        with self.assertRaisesRegex(ValueError, "page 3"):
            tool.review(d, replay=False)

    def test_page14_event_mapping_and_time_signature_stay_unresolved(self):
        d = self.changed()
        d["candidate"]["capstone_order_relation"]["event_mapping"] = {"per_bar": 8}
        with self.assertRaisesRegex(ValueError, "page 14"):
            tool.review(d, replay=False)
        d = self.changed()
        d["pages"][13].append("Time signature: 4/4")
        with self.assertRaisesRegex(ValueError, "page 14"):
            tool.review(d, replay=False)

    def test_page15_scoring_allocation_stays_null(self):
        d = self.changed()
        d["candidate"]["mastery_comparison"]["scoring_allocation"] = {"pulse": 4}
        with self.assertRaisesRegex(ValueError, "page 15"):
            tool.review(d, replay=False)

    def test_review_only_output_replay(self):
        self.assertEqual(tool.encoded(tool.review(self.data)),
                         (ROOT / tool.OUT / "review.json").read_bytes())
        self.assertFalse((ROOT / tool.OUT / "field-proposal.json").exists())
        tool.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
