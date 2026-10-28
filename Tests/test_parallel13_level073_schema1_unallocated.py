"""Focused checks for P13's Level73 modulation source projection."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level073_schema1_unallocated as lane  # noqa: E402


class Level73ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sealed = json.loads((ROOT / lane.CANDIDATE).read_text())

    def test_original_replay_and_deterministic_outputs(self) -> None:
        proposal, handoff = lane.derive()
        self.assertEqual(len(proposal["records"]), 61)
        self.assertEqual(sum(len(r["schema1_fields"]["events"])
                             for r in proposal["records"]), 652)
        self.assertEqual(handoff["field_proposal_sha256"], lane.sha(lane.encoded(proposal)))
        self.assertEqual((ROOT / lane.OUT / "field-proposal.json").read_bytes(),
                         lane.encoded(proposal))
        self.assertEqual((ROOT / lane.OUT / "allocation-handoff.json").read_bytes(),
                         lane.encoded(handoff))

    def test_printed_pitch_source_positions_and_null_timing(self) -> None:
        proposal, _ = lane.project(self.sealed)
        for record in proposal["records"]:
            self.assertIsNone(record["schema1_fields"]["id"])
            self.assertIsNone(record["schema1_fields"]["lineage"])
            self.assertFalse(record["schema1_fields"]["runtime_eligible"])
            for event in record["schema1_fields"]["events"]:
                raw = event["source_attack"]
                self.assertEqual(event["printed_note"], raw["note"])
                self.assertEqual(event["schema1_fields"]["midi"],
                                 lane.source.OPEN[raw["string"]] + raw["fret"])
                self.assertIsNone(event["schema1_fields"]["onset_q"])
                self.assertIsNone(event["schema1_fields"]["duration_q"])
        self.assertFalse(proposal["admitted"])
        self.assertFalse(proposal["whole_workbook_complete"])

    def test_c_two_voices_share_source_bar_without_performance_order(self) -> None:
        proposal, _ = lane.project(self.sealed)
        sheets = [r for r in proposal["records"]
                  if r["source_local_key"].startswith("L73-C-")]
        self.assertEqual(len(sheets), 6)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in sheets), 48)
        for record in sheets:
            events = record["schema1_fields"]["events"]
            for bar in range(1, 5):
                same_bar = [e for e in events if e["source_bar"] == bar]
                self.assertEqual({e["source_voice"] for e in same_bar}, {1, 2})
                self.assertEqual({e["simultaneity_group"] for e in same_bar},
                                 {f"bar-{bar}"})
                self.assertTrue(all(e["execution_order"] is None for e in same_bar))

    def test_three_barline_conflicts_preserved_without_ties(self) -> None:
        proposal, handoff = lane.project(self.sealed)
        self.assertEqual([a["printed_barline_notes"] for a in handoff["A_pdf_barline_conflicts"]],
                         [["G", "E"], ["G", "C"], ["D", "B"]])
        self.assertTrue(all(a["status"] == "pending_curriculum_review"
                            for a in proposal["source_ambiguities"]))
        a = [r for r in proposal["records"]
             if r["source_local_key"].startswith("L73-A-")]
        self.assertEqual(sum(not r["source_unit"]["barline_repeats_note"] for r in a), 3)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in a), 64)

    def test_note_or_chord_role_drift_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["modules"]["A"][0]["events"][0]["fret"] += 1
        with self.assertRaisesRegex(lane.ProposalError, "EVENT_PITCH"):
            lane.project(changed)
        changed = copy.deepcopy(self.sealed)
        changed["modules"]["B"][0]["events"][0]["role_slot_raw"] = "b7--"
        with self.assertRaisesRegex(lane.ProposalError, "CHORD_ROLE"):
            lane.project(changed)

    def test_ambiguity_count_and_admission_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["source_ambiguities"].pop()
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_GUIDANCE_AMBIGUITY"):
            lane.project(changed)
        changed = copy.deepcopy(self.sealed)
        changed["admitted"] = True
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_SCOPE"):
            lane.project(changed)

    def test_pin_and_guidance_preservation(self) -> None:
        proposal, _ = lane.project(self.sealed)
        self.assertEqual(len(proposal["guidance"]["txt_full_lines"]), 668)
        self.assertEqual(len(proposal["guidance"]["pdf_full_extracted_pages"]), 20)
        self.assertEqual(proposal["module_counts"]["G"]["printed_tones"], 128)
        self.assertEqual(proposal["module_counts"]["H"]["printed_tones"], 64)
        self.assertFalse(proposal["timing_resolved"])
        changed_pins = dict(lane.PINS)
        changed_pins[lane.CANDIDATE] = "0" * 64
        with patch.object(lane, "PINS", changed_pins):
            with self.assertRaisesRegex(lane.ProposalError, "INPUT_PIN"):
                lane.pins()


if __name__ == "__main__":
    unittest.main()
