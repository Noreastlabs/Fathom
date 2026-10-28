"""Focused source/authority checks for detached Level83 field proposal."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level83_projection", ROOT / "Tools/parallel_07_level083_schema1_unallocated.py")
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class Level83Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = S.read_inputs(ROOT)
        cls.proposal, cls.handoff = S.project(cls.data)

    def mutated(self) -> dict:
        return copy.deepcopy(self.data)

    def test_written_slot_projection_and_frozen_representative(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["records"]), 10)
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in p["records"]], list(S.COUNTS.values()))
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 1200)
        self.assertEqual(p["frozen_representative_reference"], "fg:item:000011")
        self.assertEqual(self.handoff["existing_level083_representative_records"], 1)
        self.assertEqual(self.handoff["new_canonical_ids_allocated"], False)
        self.assertFalse(p["admitted"] or p["runtime_eligible"] or p["schema1_importable"])
        for record in p["records"]:
            for event in record["schema1_fields"]["events"]:
                self.assertTrue(all(value is None for value in event["schema1_fields"].values()))
                self.assertTrue(all(value is None for key, value in event["source_written_slot"].items() if key != "slot"))

    def test_source_tasks_and_discrepancies_preserved(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["txt"]["lines"]), 59)
        self.assertEqual(len(p["pdf_pages"]), 20)
        self.assertEqual([len(p["pdf_pages"][i]["semantic"][key]) for i, key in ((18, "printed_bar_table"), (19, "rubric"))], [24, 8])
        self.assertEqual([len(r["source_task_groups"]) for r in p["records"]], [8, 8, 1, 1, 1, 1, 1, 4, 1, 1])
        self.assertTrue(all(group["allocation"] == "shared_A_B_unresolved"
                            for record in p["records"][:2] for group in record["source_task_groups"] if 3 <= group["pdf_page"] <= 9))
        self.assertTrue(p["source_reconciliation"]["module_A_B_shared_pdf_pages_without_separate_row_allocation"])
        self.assertTrue(any(x.get("pages") == [19] and "overlaps" in x["observation"] for x in p["visual_review"]))
        self.assertIsNone(p["pdf_pages"][18]["semantic"]["performed_reharmonization"])
        self.assertIsNone(p["pdf_pages"][19]["semantic"]["performed_score"])

    def test_negative_written_count_or_playable_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["modules"][0]["written_event_count"] = 95
        with self.assertRaisesRegex(ValueError, "module written-slot/source-allocation drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["modules"][0]["written_event_slots"][0]["pitch"] = "C"
        with self.assertRaisesRegex(ValueError, "written slot identity/playable drift"):
            S.project(data)

    def test_negative_appendix_cell_parity(self) -> None:
        data = self.mutated()
        data[S.APPENDIX]["pages"][0]["candidate_content"]["rows"][0]["cells"][2]["value"] = "F"
        with self.assertRaisesRegex(ValueError, "literal cell/P09 semantic row divergence"):
            S.project(data)

    def test_negative_shared_ab_ambiguity(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["pdf_pages"][2]["semantic"]["allocation_status"] = "A"
        with self.assertRaisesRegex(ValueError, "shared A/B row-allocation ambiguity lost"):
            S.project(data)

    def test_negative_capstone_mastery_claim(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["pdf_pages"][18]["semantic"]["performed_reharmonization"] = "passed"
        with self.assertRaisesRegex(ValueError, "capstone/mastery source criterion drift"):
            S.project(data)

    def test_negative_representative_or_source_drift(self) -> None:
        data = self.mutated()
        entry = next(x for x in data[S.PACKAGE]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000083")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog boundary drift"):
            S.project(data)
        data = self.mutated()
        data[S.WHOLE]["txt"]["lines"][0]["text"] = "changed"
        with self.assertRaisesRegex(ValueError, "original TXT semantic archive drift"):
            S.project(data)

    def test_sealed_output_replay(self) -> None:
        products = S.products(ROOT)
        for name, value in products.items():
            self.assertEqual((ROOT / S.OUT / name).read_bytes(), S.encoded(value))
        summary = json.loads((ROOT / S.OUT / "summary.json").read_text())
        self.assertEqual(summary["proposal_sha256"], S.sha((ROOT / S.OUT / "field-proposal.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
