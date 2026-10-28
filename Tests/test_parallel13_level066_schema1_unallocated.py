"""Focused checks for P13's Level66 unallocated harmonic-minor fields."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level066_schema1_unallocated as lane  # noqa: E402


class Level66ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sealed = json.loads((ROOT / lane.CANDIDATE).read_text())
        cls.narrow = json.loads((ROOT / lane.NARROW).read_text())

    def test_original_replay_and_deterministic_outputs(self) -> None:
        proposal, handoff = lane.derive()
        self.assertEqual(len(proposal["records"]), 48)
        self.assertEqual(sum(len(r["schema1_fields"]["events"])
                             for r in proposal["records"]), 898)
        self.assertEqual(handoff["field_proposal_sha256"], lane.sha(lane.encoded(proposal)))
        self.assertEqual((ROOT / lane.OUT / "field-proposal.json").read_bytes(),
                         lane.encoded(proposal))
        self.assertEqual((ROOT / lane.OUT / "allocation-handoff.json").read_bytes(),
                         lane.encoded(handoff))

    def test_all_events_preserve_authored_note_and_unresolved_timing(self) -> None:
        proposal, _ = lane.project(self.sealed, self.narrow)
        for record in proposal["records"]:
            self.assertIsNone(record["schema1_fields"]["id"])
            self.assertIsNone(record["schema1_fields"]["lineage"])
            self.assertFalse(record["schema1_fields"]["runtime_eligible"])
            for event in record["schema1_fields"]["events"]:
                raw = event["source_attack"]
                self.assertEqual(event["printed_note"], raw["note"])
                self.assertEqual(event["printed_degree"], raw["degree"])
                self.assertEqual(event["printed_finger"], raw.get("finger"))
                self.assertEqual(event["printed_chord_role"], raw.get("role"))
                self.assertEqual(event["schema1_fields"]["midi"],
                                 lane.whole.OPEN[raw["string"]] + raw["fret"])
                self.assertIsNone(event["schema1_fields"]["onset_q"])
                self.assertIsNone(event["schema1_fields"]["duration_q"])
        self.assertFalse(proposal["admitted"])
        self.assertFalse(proposal["whole_workbook_complete"])

    def test_seam_repeat_remains_instruction_outside_898(self) -> None:
        proposal, handoff = lane.project(self.sealed, self.narrow)
        seams = [r for r in proposal["records"]
                 if r["source_local_key"].startswith("L66-B-")]
        self.assertEqual(len(seams), 4)
        self.assertEqual([len(r["schema1_fields"]["events"]) for r in seams], [42] * 4)
        self.assertEqual(handoff["supplemental_seam_repeat_tones_not_counted"], 168)
        self.assertTrue(all(r["source_cell"]["repeat_twice_instruction"] for r in seams))
        self.assertTrue(all(not r["source_cell"]["repeat_counted_in_printed_898"]
                            for r in seams))
        self.assertEqual(proposal["module_counts"]["H"],
                         {"cells": 4, "printed_tones": 64})

    def test_p09_module_a_parity_refuses_note_or_finger_drift(self) -> None:
        changed = copy.deepcopy(self.narrow)
        changed["records"][0]["routes"]["ascending"][0]["printed_note"] = "B"
        with self.assertRaisesRegex(lane.ProposalError, "A_PARITY"):
            lane.project(self.sealed, changed)
        changed = copy.deepcopy(self.narrow)
        changed["records"][0]["routes"]["ascending"][0]["printed_finger"] = 4
        with self.assertRaisesRegex(lane.ProposalError, "A_PARITY"):
            lane.project(self.sealed, changed)

    def test_pitch_or_count_inflation_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["modules"]["A"]["cells"][0]["events"][0]["fret"] += 1
        with self.assertRaisesRegex(lane.ProposalError, "A_PARITY"):
            lane.project(changed, self.narrow)
        changed = copy.deepcopy(self.sealed)
        changed["modules"]["B"]["cells"][0]["repeat_counted_in_printed_898"] = True
        with self.assertRaisesRegex(lane.ProposalError, "SEAM_COUNT"):
            lane.project(changed, self.narrow)

    def test_admission_and_input_pin_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["admitted"] = True
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_SCOPE"):
            lane.project(changed, self.narrow)
        fake = dict(lane.PINS)
        fake[lane.CANDIDATE] = "0" * 64
        with patch.object(lane, "PINS", fake):
            with self.assertRaisesRegex(lane.ProposalError, "INPUT_PIN"):
                lane.pins()

    def test_source_guidance_and_capstone_retained(self) -> None:
        proposal, _ = lane.project(self.sealed, self.narrow)
        self.assertEqual(len(proposal["source_transcription"]["txt_lines"]), 503)
        self.assertEqual(len(proposal["source_transcription"]["pdf_pages"]), 20)
        self.assertEqual(len(proposal["count_boundaries"]), 3)
        self.assertEqual(proposal["module_counts"]["A"]["printed_tones"], 180)
        self.assertEqual(proposal["module_counts"]["G"]["printed_tones"], 64)
        self.assertFalse(proposal["timing_resolved"])
        self.assertFalse(proposal["curriculum_signoff"])


if __name__ == "__main__":
    unittest.main()
