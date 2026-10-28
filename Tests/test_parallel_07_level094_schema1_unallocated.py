"""Focused source/authority checks for detached Level94 field proposal."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level94_projection", ROOT / "Tools/parallel_07_level094_schema1_unallocated.py")
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class Level94Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = S.read_inputs(ROOT)
        cls.proposal, cls.handoff = S.project(cls.data)

    def mutated(self) -> dict:
        return copy.deepcopy(self.data)

    def test_tasks_markers_and_declared_workload_separate(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["records"]), 10)
        self.assertEqual([len(r["source_tasks"]) for r in p["records"]], list(S.TASKS.values()))
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in p["records"]], list(S.MARKERS.values()))
        self.assertEqual(sum(len(r["source_tasks"]) for r in p["records"]), 146)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 104)
        self.assertEqual(sum(r["source_declared_workload"] for r in p["records"]), 1472)
        self.assertIsNone(self.handoff["existing_representative_item_id"])
        self.assertFalse(p["admitted"] or p["runtime_eligible"] or p["schema1_importable"])
        for record in p["records"]:
            for marker in record["schema1_fields"]["events"]:
                self.assertTrue(all(value is None for value in marker["schema1_fields"].values()))

    def test_two_peak_plan_studies_and_source_order(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["source_archive"]["txt_lines"]), 44)
        self.assertEqual(len(p["source_archive"]["pdf_pages"]), 20)
        self.assertEqual(len(p["pdf_tables"]), 16)
        self.assertEqual([len(s["passes"]) for s in p["g_studies"]], [6] * 4)
        self.assertEqual([len(s["chords"]) for s in p["g_studies"]], [8] * 4)
        self.assertEqual([x["bar"] for x in p["capstone_bar_plan"] if x["arc_role"] == "first peak"], list(range(13, 17)))
        self.assertEqual([x["bar"] for x in p["capstone_bar_plan"] if x["arc_role"] == "second peak"], list(range(25, 29)))
        tasks = [x for r in p["records"] for x in r["source_tasks"]]
        self.assertEqual(sorted(x["source_global_ordinal"] for x in tasks), list(range(1, 147)))
        self.assertEqual([p["source_task_order"][x["source_global_ordinal"] - 1] for x in tasks],
                         [x["source_task"]["local_key"] for x in tasks])
        self.assertEqual(len(p["pdf_tables"]["completion_rubric"]["rows"]), 8)

    def test_negative_declared_count_or_task_loss(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["declared_workload_total"] = 104
        with self.assertRaisesRegex(ValueError, "table/task/marker/workload drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["tasks"].pop()
        with self.assertRaisesRegex(ValueError, "table/task/marker/workload drift"):
            S.project(data)

    def test_negative_marker_loss_or_fabricated_performance(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["bar_or_window_markers"].pop()
        with self.assertRaisesRegex(ValueError, "table/task/marker/workload drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["bar_or_window_markers"][0]["onset_q"] = 0
        with self.assertRaisesRegex(ValueError, "source marker invented performance"):
            S.project(data)

    def test_negative_narrow_arc_parity(self) -> None:
        data = self.mutated()
        data[S.NARROW]["module_a"]["cells"][0]["ordered_printed_windows"][0]["printed_cell"] = "ff"
        with self.assertRaisesRegex(ValueError, "P06 Module A arc parity drift"):
            S.project(data)

    def test_negative_capstone_or_tension_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["capstone_bar_plan"][12]["arc_role"] = "release"
        with self.assertRaisesRegex(ValueError, "40-bar two-peak capstone drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["source_tensions"][1]["resolution"] = "invent attacks"
        with self.assertRaisesRegex(ValueError, "source tension ledger drift"):
            S.project(data)

    def test_negative_catalog_or_archive_drift(self) -> None:
        data = self.mutated()
        entry = next(x for x in data[S.PACKAGE]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000094")
        entry["representative_item_id"] = "fg:item:999999"
        with self.assertRaisesRegex(ValueError, "source-only catalog boundary drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["source_archive"]["txt_lines"][0]["text"] = "changed"
        with self.assertRaisesRegex(ValueError, "original TXT/archive drift"):
            S.project(data)

    def test_sealed_output_replay(self) -> None:
        products = S.products(ROOT)
        for name, value in products.items():
            self.assertEqual((ROOT / S.OUT / name).read_bytes(), S.encoded(value))
        summary = json.loads((ROOT / S.OUT / "summary.json").read_text())
        self.assertEqual(summary["proposal_sha256"], S.sha((ROOT / S.OUT / "field-proposal.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
