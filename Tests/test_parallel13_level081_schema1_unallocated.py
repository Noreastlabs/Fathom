"""Focused checks for P13's Level81 count-backed schema projection."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level081_schema1_unallocated as lane  # noqa: E402


class Level81ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sealed = json.loads((ROOT / lane.CANDIDATE).read_text())

    def test_original_replay_and_deterministic_outputs(self) -> None:
        proposal, handoff = lane.derive()
        self.assertEqual(len(proposal["records"]), 86)
        self.assertEqual(proposal["printed_event_allocation"], 1184)
        self.assertEqual(proposal["fully_notated_playable_events"], 0)
        self.assertEqual(handoff["field_proposal_sha256"], lane.sha(lane.encoded(proposal)))
        self.assertEqual((ROOT / lane.OUT / "field-proposal.json").read_bytes(),
                         lane.encoded(proposal))
        self.assertEqual((ROOT / lane.OUT / "allocation-handoff.json").read_bytes(),
                         lane.encoded(handoff))

    def test_every_task_is_count_backed_without_fabricated_events(self) -> None:
        proposal, _ = lane.project(self.sealed)
        self.assertEqual(sum(r["printed_event_allocation"]
                             for r in proposal["records"]), 1184)
        for record in proposal["records"]:
            fields = record["schema1_fields"]
            self.assertEqual(fields["events"], [])
            self.assertIsNone(fields["id"])
            self.assertIsNone(fields["lineage"])
            self.assertIsNone(fields["timing"]["onset_q"])
            self.assertIsNone(fields["timing"]["duration_q"])
            self.assertFalse(fields["runtime_eligible"])
            self.assertEqual(record["playable_event_status"],
                             "unresolved_not_fully_notated")
        self.assertFalse(proposal["admitted"])
        self.assertFalse(proposal["whole_workbook_complete"])

    def test_d_and_f_source_differences_preserved(self) -> None:
        proposal, _ = lane.project(self.sealed)
        d = [r for r in proposal["records"]
             if r["source_local_key"].startswith("L81-D-")]
        self.assertEqual([r["source_anchor_count"] for r in d[-2:]], [16, 15])
        dm = next(v for v in d[5]["source_task"]["voicings"]
                  if v["chord"] == "Dm7/F")
        self.assertEqual(dm["pitch_classes_low_to_high"], [5, 9, 2, 5])
        self.assertNotIn(0, dm["pitch_classes_low_to_high"])
        f = [r for r in proposal["records"]
             if r["source_local_key"].startswith("L81-F-")]
        self.assertEqual([r["source_task"]["chord"] for r in f
                          if r["source_task"]["source_pitch_order_differs_from_fretboard"]],
                         ["Cmaj7", "Cm7", "Dm7"])

    def test_h_i_j_missing_contact_details_remain_explicit(self) -> None:
        proposal, _ = lane.project(self.sealed)
        h4 = next(r for r in proposal["records"]
                  if r["source_local_key"] == "L81-H-04")
        self.assertTrue(all(b["bass_anchor"] is None and
                            len(b["melody_anchors"]) == 1
                            for b in h4["source_task"]["bars"]))
        i = [r for r in proposal["records"]
             if r["source_local_key"].startswith("L81-I-")]
        self.assertEqual(len(i), 24)
        self.assertTrue(all(r["source_anchor_count"] == 2 and
                            r["printed_event_allocation"] == 8
                            for r in i))
        j = [r for r in proposal["records"]
             if r["source_local_key"].startswith("L81-J-")]
        self.assertEqual(len(j), 8)
        self.assertTrue(all(r["source_task"]["recovery_instruction"] and
                            r["schema1_fields"]["events"] == [] for r in j))

    def test_missing_bass_or_f_order_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["modules"]["H"][3]["bars"][0]["bass_anchor"] = "C"
        with self.assertRaisesRegex(lane.ProposalError, "H_ARRANGEMENT"):
            lane.project(changed)
        changed = copy.deepcopy(self.sealed)
        changed["modules"]["F"][0]["actual_fretboard_notes_low_to_high"][1] = "E"
        with self.assertRaisesRegex(lane.ProposalError, "F_PRINTED_ACTUAL_ORDER"):
            lane.project(changed)

    def test_rubric_count_and_admission_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["pdf_only_assessment"]["pass_threshold"] = 13
        with self.assertRaisesRegex(lane.ProposalError, "RUBRIC_HARD_STOP"):
            lane.project(changed)
        changed = copy.deepcopy(self.sealed)
        changed["printed_event_allocation"] = 1185
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_SCOPE"):
            lane.project(changed)
        changed = copy.deepcopy(self.sealed)
        changed["content_admitted"] = True
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_SCOPE"):
            lane.project(changed)

    def test_source_pin_and_original_guidance(self) -> None:
        proposal, _ = lane.project(self.sealed)
        self.assertEqual(len(proposal["txt_source_lines"]), 158)
        self.assertEqual(len(proposal["pdf_source_pages"]), 20)
        self.assertEqual(proposal["pdf_only_assessment"]["pass_threshold"], 14)
        self.assertEqual(len(proposal["source_difference_ledger"]), 3)
        self.assertIsNone(proposal["performed_assessment"])
        fake = dict(lane.PINS)
        fake[lane.CANDIDATE] = "0" * 64
        with patch.object(lane, "PINS", fake):
            with self.assertRaisesRegex(lane.ProposalError, "INPUT_PIN"):
                lane.pins()


if __name__ == "__main__":
    unittest.main()
