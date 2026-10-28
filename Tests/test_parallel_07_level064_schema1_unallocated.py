"""Focused regressions for the detached Level64 schema1 projection."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("level64_projection", ROOT / "Tools/parallel_07_level064_schema1_unallocated.py")
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class Level64Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = S.read_inputs(ROOT)
        cls.proposal, cls.handoff = S.project(cls.data)

    def mutated(self) -> dict:
        return copy.deepcopy(self.data)

    def test_all_positions_and_source_tasks(self) -> None:
        records = self.proposal["records"]
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in records], list(S.COUNTS.values()))
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in records), 640)
        self.assertEqual(sum(len(r["source_slices"]) for r in records), 13)  # H/I share one P01 slice.
        self.assertEqual([len(r["source_slices"]) for r in records], [1, 1, 1, 2, 2, 2, 1, 1, 1, 1])
        self.assertEqual({x["code"] for x in self.proposal["source_discrepancies"]}, S.EXPECTED_DISCREPANCIES)
        self.assertEqual(len(self.proposal["pdf_only_practice_log_fields"]), 7)
        self.assertEqual([x["pdf_page"] for x in self.proposal["source_only_references"]["pdf_page_texts"]], [1, 2, 20])
        self.assertFalse(self.proposal["admitted"] or self.proposal["runtime_eligible"] or self.proposal["schema1_importable"])

    def test_j_order_and_nulls(self) -> None:
        events = self.proposal["records"][9]["schema1_fields"]["events"]
        self.assertEqual([e["source_position"]["path_in_slice"][0] for e in events],
                         ["recovery_cards"] * 24 + ["modulation_bridges"] * 48)
        self.assertTrue(all(e["source_tone"]["printed_tab"] is None for e in events[:24]))
        self.assertTrue(all(e["source_tone"]["printed_tab"] is not None for e in events[24:]))
        for record in self.proposal["records"]:
            for event in record["schema1_fields"]["events"]:
                fields = event["schema1_fields"]
                self.assertTrue(all(fields[key] is None for key in ("event_id", "pick", "pitch_binding", "onset_q", "duration_q")))
                self.assertIsNone(event["source_tone"]["sounding_midi"])
        f_picks = {e["source_position"]["pick_token"] for e in self.proposal["records"][5]["schema1_fields"]["events"]}
        self.assertEqual(f_picks, {"D", "U", "P", "m", "a"})

    def test_negative_position_union_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["modules"]["A"]["positions"][0]["note_token"] = "D"
        with self.assertRaisesRegex(ValueError, "normalized union/order drift"):
            S.project(data)

    def test_negative_source_ref_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["modules"]["F"]["positions"][0]["source_refs"]["note"]["line"] = 1
        with self.assertRaisesRegex(ValueError, "position TXT ref outside slice"):
            S.project(data)

    def test_negative_j_card_and_order_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["modules"]["J"]["positions"][0]["source_tab"] = {"string_label": "B", "fret_token": "8"}
        with self.assertRaisesRegex(ValueError, "J recovery card invented TAB"):
            S.project(data)
        data = self.mutated()
        j = data[S.WHOLE]["modules"]["J"]["positions"]
        j[0], j[24] = j[24], j[0]
        with self.assertRaisesRegex(ValueError, "position token/order drift|J printed ordering drift"):
            S.project(data)

    def test_negative_discrepancy_and_index_drift(self) -> None:
        data = self.mutated()
        data[S.WHOLE]["source_discrepancies"].pop()
        with self.assertRaisesRegex(ValueError, "source discrepancy ledger drift"):
            S.project(data)
        data = self.mutated()
        data[S.INDEX]["module_candidate_union"][0]["candidate_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "P01 slice pin drift"):
            S.project(data)

    def test_negative_catalog_admission_drift(self) -> None:
        data = self.mutated()
        entry = next(x for x in data[S.PACKAGE]["workbook_catalog"]["entries"] if x["workbook_id"] == "fg:workbook:000064")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog boundary drift"):
            S.project(data)

    def test_sealed_output_replay(self) -> None:
        products = S.products(ROOT)
        for name, value in products.items():
            self.assertEqual((ROOT / S.OUT / name).read_bytes(), S.encoded(value))
        summary = json.loads((ROOT / S.OUT / "summary.json").read_text())
        self.assertEqual(summary["proposal_sha256"], S.sha((ROOT / S.OUT / "field-proposal.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
