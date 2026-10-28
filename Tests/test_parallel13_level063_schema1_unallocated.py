"""Focused checks for P13's Level63 source-local picking projection."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level063_schema1_unallocated as lane  # noqa: E402


class Level63ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sealed = json.loads((ROOT / lane.CANDIDATE).read_text())

    def test_original_replay_and_deterministic_outputs(self) -> None:
        proposal, handoff = lane.derive()
        self.assertEqual(len(proposal["records"]), 132)
        self.assertEqual(sum(len(r["schema1_fields"]["events"])
                             for r in proposal["records"]), 1016)
        self.assertEqual(handoff["field_proposal_sha256"], lane.sha(lane.encoded(proposal)))
        self.assertEqual((ROOT / lane.OUT / "field-proposal.json").read_bytes(),
                         lane.encoded(proposal))
        self.assertEqual((ROOT / lane.OUT / "allocation-handoff.json").read_bytes(),
                         lane.encoded(handoff))

    def test_every_attack_retains_printed_pitch_pick_role_and_source(self) -> None:
        proposal, _ = lane.project(self.sealed)
        for record in proposal["records"]:
            source_attacks = record["source_cell"]["attacks"]
            projected = record["schema1_fields"]["events"]
            self.assertEqual(len(source_attacks), len(projected))
            self.assertIsNone(record["schema1_fields"]["id"])
            self.assertIsNone(record["schema1_fields"]["lineage"])
            for original, event in zip(source_attacks, projected, strict=True):
                self.assertEqual(event["source_attack"], original)
                self.assertEqual(event["schema1_fields"]["midi"], original["midi"])
                self.assertEqual(event["schema1_fields"]["string"], original["string"])
                self.assertEqual(event["schema1_fields"]["fret"], original["fret"])
                self.assertEqual(event["printed_pick"], original["printed_pick"])
                self.assertEqual(event["printed_chord_role"], original["printed_role"])
                self.assertIsNone(event["schema1_fields"]["onset_q"])
                self.assertIsNone(event["schema1_fields"]["duration_q"])
        self.assertFalse(proposal["admitted"])
        self.assertFalse(proposal["whole_workbook_complete"])

    def test_txt_h_and_pdf_only_j_accents_are_separate(self) -> None:
        proposal, handoff = lane.project(self.sealed)
        h = [e for r in proposal["records"] if r["source_local_key"].startswith("L63-H-")
             for e in r["schema1_fields"]["events"]]
        j = [e for r in proposal["records"] if r["source_local_key"].startswith("L63-J-")
             for e in r["schema1_fields"]["events"]]
        self.assertEqual(sum(e["printed_chord_role"].startswith(">") for e in h), 36)
        self.assertEqual(sum(e["pdf_only_beat_one_role_accent"] for e in h), 0)
        self.assertEqual(sum(e["pdf_only_beat_one_role_accent"] for e in j), 32)
        self.assertEqual(sum(e["printed_chord_role"].startswith(">") for e in j), 0)
        self.assertEqual(handoff["pdf_only_J_beat_one_role_accents"], 32)
        self.assertEqual(proposal["records"][-1]["source_cell"]["grid"]["pdf_grid_relationship"],
                         "PDF combines four TXT bars")

    def test_source_pitch_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["modules"][0]["cells"][0]["attacks"][0]["midi"] += 1
        with self.assertRaisesRegex(lane.ProposalError, "ATTACK_SOURCE"):
            lane.project(changed)

    def test_pdf_accent_or_count_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["modules"][-1]["cells"][0]["pdf_beat_one_role_accent"] = False
        with self.assertRaisesRegex(lane.ProposalError, "J_PDF_ACCENT"):
            lane.project(changed)
        changed = copy.deepcopy(self.sealed)
        changed["modules"][-1]["cells"][0]["attacks"].pop()
        with self.assertRaisesRegex(lane.ProposalError, "GRID_SOURCE|MODULE_COUNT|ATTACK_SOURCE"):
            lane.project(changed)

    def test_admission_or_source_pin_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.sealed)
        changed["admitted"] = True
        with self.assertRaisesRegex(lane.ProposalError, "SOURCE_SCOPE"):
            lane.project(changed)
        changed_pins = dict(lane.PINS)
        changed_pins[lane.CANDIDATE] = "0" * 64
        with patch.object(lane, "PINS", changed_pins):
            with self.assertRaisesRegex(lane.ProposalError, "INPUT_PIN"):
                lane.pins()

    def test_source_instructions_preserved_without_performance_claim(self) -> None:
        proposal, _ = lane.project(self.sealed)
        self.assertEqual(len(proposal["txt_source_lines"]), 1564)
        self.assertEqual(len(proposal["pdf_source_pages"]), 20)
        self.assertEqual(len(proposal["source_exceptions"]), 4)
        self.assertFalse(proposal["timing_resolved"])
        self.assertFalse(proposal["curriculum_signoff"])
        self.assertEqual(proposal["module_counts"]["G"], {"grids": 32, "attacks": 224})
        self.assertEqual(proposal["module_counts"]["I"], {"grids": 4, "attacks": 128})


if __name__ == "__main__":
    unittest.main()
