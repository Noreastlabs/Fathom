"""Focused source/authority checks for detached Level100 field proposal."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level100_projection", ROOT / "Tools/parallel_07_level100_schema1_unallocated.py")
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class Level100Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = S.read_inputs(ROOT)
        cls.proposal, cls.handoff = S.project(cls.data)

    def mutated(self) -> dict:
        return copy.deepcopy(self.data)

    def test_tasks_events_portfolio_and_declaration_separate(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["records"]), 10)
        self.assertEqual([len(r["source_tasks"]) for r in p["records"]], list(S.TASKS.values()))
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in p["records"]], list(S.EXPLICIT.values()))
        self.assertEqual(sum(len(r["source_tasks"]) for r in p["records"]), 149)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 59)
        self.assertEqual(len(p["records"][8]["source_portfolio_bars"]), 32)
        self.assertEqual(sum(r["source_declared_workload"] for r in p["records"]), 1520)
        self.assertFalse(p["admitted"] or p["runtime_eligible"] or p["schema1_importable"])
        self.assertIsNone(self.handoff["existing_representative_item_id"])
        for record in p["records"]:
            for event in record["schema1_fields"]["events"]:
                self.assertTrue(all(value is None for value in event["schema1_fields"].values()))

    def test_source_archive_conflicts_and_studies(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["source_archive"]["txt_lines"]), 48)
        self.assertEqual(len(p["source_archive"]["pdf_pages"]), 21)
        self.assertEqual(len(p["pdf_tables"]), 17)
        self.assertEqual(len(p["pdf_tables"]["harmonizations"]["rows"]), 6)
        self.assertEqual(len(p["pdf_tables"]["rhythmic_identities"]["rows"]), 6)
        self.assertEqual([x["pdf_page"] for x in p["source_tensions"][:2]], [10, 14])
        self.assertEqual([len(x["passes"]) for x in p["h_studies"]], [6] * 4)
        bars = p["records"][8]["source_portfolio_bars"]
        self.assertEqual([x["source_portfolio_bar"]["bar"] for x in bars], list(range(1, 33)))
        self.assertEqual({x["source_portfolio_bar"]["starting_method"] for x in bars},
                         {"motif-first", "melody-first", "bass-first", "rhythm-first"})
        self.assertTrue(all(all(value is None for key, value in x["source_portfolio_bar"].items() if key.startswith("authored_")) for x in bars))

    def test_negative_declared_count_or_task_loss(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["declared_workload_total"] = 59
        with self.assertRaisesRegex(ValueError, "table/task/event/allocation/workload drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["tasks"].pop()
        with self.assertRaisesRegex(ValueError, "table/task/event/allocation/workload drift"):
            S.project(data)

    def test_negative_explicit_event_or_authorship_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["source_supported_seed_or_contact_events"].pop()
        with self.assertRaisesRegex(ValueError, "table/task/event/allocation/workload drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["source_supported_seed_or_contact_events"][0]["pitch"] = "C"
        with self.assertRaisesRegex(ValueError, "seed-degree pitch/authorship drift"):
            S.project(data)

    def test_negative_portfolio_authorship(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["portfolio_bar_allocations"][0]["authored_melody"] = "C D E"
        with self.assertRaisesRegex(ValueError, "portfolio bar invented learner authorship"):
            S.project(data)

    def test_negative_conflict_or_study_ladder(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["source_tensions"][0]["resolution"] = "only four"
        with self.assertRaisesRegex(ValueError, "source tension ledger drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["h_studies"][0]["passes"].pop()
        with self.assertRaisesRegex(ValueError, "H study/pass ladder drift"):
            S.project(data)

    def test_negative_catalog_or_original_drift(self) -> None:
        data = self.mutated()
        entry = next(x for x in data[S.PACKAGE]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000100")
        entry["admitted"] = True
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
