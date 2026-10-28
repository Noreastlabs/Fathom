"""Focused source and semantic checks for P13's Level58 detached fields."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level058_schema1_unallocated as lane  # noqa: E402


class Level58ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads((ROOT / lane.WHOLE).read_text())
        cls.narrow = json.loads((ROOT / lane.NARROW).read_text())

    def test_replay_pins_and_deterministic_outputs(self) -> None:
        proposal, handoff = lane.derive()
        self.assertEqual(len(proposal["records"]), 74)
        self.assertEqual(sum(len(r["schema1_fields"]["events"])
                             for r in proposal["records"]), 1018)
        self.assertEqual(handoff["field_proposal_sha256"], lane.sha(lane.encoded(proposal)))
        self.assertEqual((ROOT / lane.OUT / "field-proposal.json").read_bytes(),
                         lane.encoded(proposal))
        self.assertEqual((ROOT / lane.OUT / "allocation-handoff.json").read_bytes(),
                         lane.encoded(handoff))

    def test_slot_contact_bijection_and_unpitched_dead(self) -> None:
        proposal, _ = lane.project(self.source, self.narrow)
        for record in proposal["records"]:
            slots = record["source_unit"]["slots"]
            events = record["schema1_fields"]["events"]
            self.assertEqual([e["source_slot_ordinal"] for e in events],
                             [i for i, s in enumerate(slots, 1)
                              if s["sound_symbol"] in "Px"])
            for event in events:
                slot = slots[event["source_slot_ordinal"] - 1]
                self.assertEqual(event["source_attack"]["sound_symbol"],
                                 slot["sound_symbol"])
                self.assertEqual(event["schema1_fields"]["midi"], None)
                self.assertEqual(event["schema1_fields"]["onset_q"], None)
                self.assertEqual(event["schema1_fields"]["duration_q"], None)
                if slot["sound_symbol"] == "x":
                    self.assertEqual(event["pitch_binding"], "unpitched_dead_contact")
            self.assertIsNone(record["schema1_fields"]["id"])
            self.assertIsNone(record["schema1_fields"]["lineage"])
            self.assertFalse(record["schema1_fields"]["runtime_eligible"])

    def test_h_conflict_and_capstone_remain_explicit(self) -> None:
        proposal, handoff = lane.project(self.source, self.narrow)
        self.assertEqual([r["source_unit"]["contact_count"] for r in proposal["records"]
                          if r["source_local_key"].startswith("L58-H-")],
                         [32, 24, 32, 28])
        self.assertEqual(handoff["H_conflict"]["printed_headline_contacts"], 128)
        self.assertEqual(handoff["H_conflict"]["mask_contacts"], 116)
        self.assertEqual(proposal["module_counts"]["I"]["contact_events"], 209)
        self.assertEqual([r["source_unit"]["last_bar"] for r in proposal["records"]
                          if r["source_local_key"].startswith("L58-I-")][-1], 32)
        self.assertFalse(proposal["admitted"])
        self.assertFalse(proposal["whole_workbook_complete"])

    def test_p01_module_a_parity_refuses_changed_mask(self) -> None:
        changed = copy.deepcopy(self.narrow)
        changed["records"][0]["sound_mask_bar_source"] = "P---P---P---P--x"
        with self.assertRaisesRegex(lane.ProposalError, "A_PARITY"):
            lane.project(self.source, changed)

    def test_air_contact_inflation_refused(self) -> None:
        changed = copy.deepcopy(self.source)
        slot = changed["modules"]["A"]["units"][0]["slots"][1]
        slot["sound_symbol"] = "P"
        slot["kind"] = "pitched contact"
        with self.assertRaisesRegex(lane.ProposalError, "A_PARITY|UNIT_CONTACTS"):
            lane.project(changed, self.narrow)

    def test_h_count_and_admission_refused(self) -> None:
        changed = copy.deepcopy(self.source)
        changed["H_mask_derived_count"] = 128
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_SCOPE"):
            lane.project(changed, self.narrow)
        changed = copy.deepcopy(self.source)
        changed["admitted"] = True
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_SCOPE"):
            lane.project(changed, self.narrow)

    def test_source_pin_refuses_drift(self) -> None:
        changed = dict(lane.PINS)
        changed[lane.WHOLE] = "0" * 64
        with patch.object(lane, "PINS", changed):
            with self.assertRaisesRegex(lane.ProposalError, "INPUT_PIN"):
                lane.pins()

    def test_source_guidance_and_e_pair_selection_remain_unresolved(self) -> None:
        proposal, _ = lane.project(self.source, self.narrow)
        self.assertEqual(len(proposal["reference_voicings"]), 17)
        self.assertEqual(len(proposal["printed_guidance"]["pdf_extracted_pages"]), 20)
        self.assertEqual([r["source_unit"]["pair"] for r in proposal["records"]
                          if r["source_local_key"] in
                          {f"L58-E-{i:02d}" for i in range(9, 13)}], [None] * 4)
        self.assertEqual({e["code"] for e in proposal["source_exceptions"]},
                         {"H_COUNT_CONFLICT", "D_PDF_ACCENT_ROW",
                          "PDF_ONLY_PROTOCOL_AND_CAPSTONE_REPAIR",
                          "E_PUSH_PAIR_UNSPECIFIED", "TXT_PDF_LAYOUT_AND_PALETTE"})


if __name__ == "__main__":
    unittest.main()
