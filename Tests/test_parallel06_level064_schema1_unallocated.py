"""Focused Level64 whole-source projection and nonadmission checks."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level064_schema1_unallocated as lane  # noqa: E402


class Level64ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.whole, cls.index, cls.package, cls.registry, cls.slice_pins = lane.read_inputs(ROOT)

    def project(self, whole=None, index=None):
        return lane.project(whole if whole is not None else self.whole,
                            index if index is not None else self.index,
                            self.package, self.registry)

    def test_exact_modules_slices_positions_and_source_paths(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(self.slice_pins), 12)
        self.assertEqual([r["source_component"] for r in proposal["records"]], list(lane.COUNTS))
        self.assertEqual(proposal["counts"]["by_module"], lane.COUNTS)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in proposal["records"]), 640)
        # The one shared H-I source slice is projected once under each module.
        self.assertEqual(sum(len(r["schema1_fields"]["variants"]) for r in proposal["records"]), 13)
        for record in proposal["records"]:
            module = record["source_component"]
            self.assertEqual(len(record["schema1_fields"]["events"]), lane.COUNTS[module])
            self.assertEqual([e["source_position"] for e in record["schema1_fields"]["events"]],
                             self.whole["modules"][module]["positions"])
            self.assertEqual(record["source_slices"], self.whole["modules"][module]["slices"])
        self.assertEqual(handoff["catalog_workbook_id"], "fg:workbook:000064")

    def test_tokens_tab_and_frozen_degree_shape(self) -> None:
        proposal, _ = self.project()
        for record in proposal["records"]:
            for contact in record["schema1_fields"]["events"]:
                source, fields = contact["source_position"], contact["schema1_fields"]
                self.assertEqual(fields["spelling"], source["note_token"])
                self.assertEqual(contact["source_role_token"], source["role_token"])
                self.assertEqual(contact["source_pick_token"], source["pick_token"])
                self.assertEqual(contact["source_tab"], source["source_tab"])
                self.assertEqual(fields["degree_contexts"], {})
                self.assertIsInstance(fields["degree_contexts"], dict)
                self.assertIsNone(fields["midi"])
                self.assertIsNone(fields["string"])
                self.assertIsNone(fields["fret"])
                self.assertIsNone(fields["onset_q"])
                self.assertIsNone(fields["duration_q"])
                self.assertIsNone(fields["event_id"])
                self.assertTrue(source["source_refs"])

    def test_j_cards_bridges_and_printed_order(self) -> None:
        proposal, _ = self.project()
        j = proposal["records"][-1]["schema1_fields"]["events"]
        self.assertEqual([e["source_position"]["path_in_slice"][0] for e in j],
                         ["recovery_cards"] * 24 + ["modulation_bridges"] * 48)
        self.assertTrue(all(e["source_tab"] is None for e in j[:24]))
        self.assertTrue(all(e["source_tab"] is not None for e in j[24:]))
        self.assertEqual(proposal["counts"]["j_recovery_note_role_positions_without_tab"], 24)

    def test_ambiguities_discrepancies_and_source_only_pages(self) -> None:
        proposal, _ = self.project()
        self.assertEqual(proposal["source_discrepancies"], self.whole["source_discrepancies"])
        self.assertEqual(proposal["source_coverage_exceptions"], self.index["coverage_exceptions"])
        self.assertEqual(proposal["source_other_limits"], self.whole["other_source_limits"])
        self.assertEqual(proposal["source_only_reference_pages"], [1, 2, 20])
        self.assertEqual(proposal["source_txt_document_text"], self.whole["txt_document_text"])
        self.assertEqual(proposal["source_pdf_page_texts"], self.whole["pdf_page_texts"])
        f = next(r for r in proposal["records"] if r["source_component"] == "F")
        exception = next(s["structured_source_candidate"]["source_token_exception"]
                         for s in f["source_slices"] if s["slice_key"] == "F-page-12")
        self.assertEqual(exception["code"], "LEVEL64_F6_ROLE_A_LITERAL")
        self.assertEqual(exception["status"], "pending")
        b = next(r for r in proposal["records"] if r["source_component"] == "B")
        self.assertIn("pdf_visual_limit", b["source_slices"][0]["structured_source_candidate"])

    def test_nonadmission_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete",
                    "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["admitted"], False)
        self.assertTrue(all(e["schema1_fields"]["midi"] is None
                            for r in proposal["records"] for e in r["schema1_fields"]["events"]))

    def test_count_and_order_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["modules"]["A"]["positions"].pop()
        with self.assertRaisesRegex(ValueError, "module position count"):
            self.project(changed)
        changed = copy.deepcopy(self.whole)
        changed["modules"]["G"]["positions"][0]["source_order"] = 2
        with self.assertRaisesRegex(ValueError, "token/order"):
            self.project(changed)

    def test_tab_and_j_authorship_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["modules"]["A"]["positions"][0]["source_tab"]["string_label"] = "X"
        with self.assertRaisesRegex(ValueError, "TAB token"):
            self.project(changed)
        changed = copy.deepcopy(self.whole)
        changed["modules"]["J"]["positions"][0]["source_tab"] = {"string_label": "E", "fret_token": "5"}
        with self.assertRaisesRegex(ValueError, "card invented TAB"):
            self.project(changed)

    def test_exception_timing_and_admission_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["source_discrepancies"].pop()
        with self.assertRaisesRegex(ValueError, "coverage/exception"):
            self.project(changed)
        changed = copy.deepcopy(self.whole)
        changed["modules"]["H"]["positions"][0]["onset_q"] = 0
        with self.assertRaisesRegex(ValueError, "identity/timing/pitch"):
            self.project(changed)
        changed = copy.deepcopy(self.whole)
        changed["admitted"] = True
        with self.assertRaisesRegex(ValueError, "admission"):
            self.project(changed)

    def test_pinned_input_and_byte_exact_output(self) -> None:
        with patch.object(lane, "INPUTS", {**lane.INPUTS, lane.WHOLE: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.read_inputs(ROOT)
        lane.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
