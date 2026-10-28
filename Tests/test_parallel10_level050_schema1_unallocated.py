"""Focused source and invented-field refusals for Level50."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))

from parallel10_level050_schema1_unallocated import (  # noqa: E402
    COUNTS, ROOT, digest, encoded, pinned, project, read_inputs,
)


class Level50UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = read_inputs(ROOT)
        cls.proposal, cls.handoff = project(cls.candidate, cls.foundation, cls.registry)

    def test_landings_and_exact_attack_projection(self) -> None:
        proposal = self.proposal
        self.assertEqual(proposal["counts"], {"components": 10, "source_units": 62, "silent_landings": 80,
                                              "notated_attacks": 768, "chord_forms": 10})
        self.assertEqual([r["source_component"] for r in proposal["records"]], list(COUNTS))
        self.assertEqual(len(proposal["records"][0]["silent_landing_tasks"]), 10)
        self.assertEqual(sum(x["silent_landings"] for x in proposal["records"][0]["silent_landing_tasks"]), 80)
        self.assertEqual(proposal["records"][0]["schema1_fields"]["events"], [])
        for record in proposal["records"][1:]:
            module = record["source_component"]
            self.assertEqual(len(record["schema1_fields"]["events"]), COUNTS[module])
            for event in record["schema1_fields"]["events"]:
                fields = event["schema1_fields"]
                self.assertIsNone(fields["event_id"])
                self.assertIsNone(fields["onset_q"])
                self.assertIsNone(fields["duration_q"])
                self.assertIsNone(fields["pitch_binding"])
                self.assertIsNone(event["sounding_member_pitches"])
                self.assertIsNone(event["resolved_fingering"])
        self.assertEqual(self.handoff["existing_level050_records"], 0)
        self.assertEqual(self.handoff["existing_level050_workbook_entities"], 0)
        self.assertFalse(proposal["schema1_importable"])
        self.assertFalse(proposal["admitted"])

    def test_alternate_fingering_h4_and_optional_repeat(self) -> None:
        refs = self.proposal["chord_reference"]
        self.assertEqual(set(refs["alternate"]), {"E-alt", "Em-alt"})
        self.assertNotEqual(refs["standard"]["E"]["fingers_low_to_high"], refs["alternate"]["E-alt"]["fingers_low_to_high"])
        self.assertNotEqual(refs["standard"]["Em"]["fingers_low_to_high"], refs["alternate"]["Em-alt"]["fingers_low_to_high"])
        all_events = [e for r in self.proposal["records"] for e in r["schema1_fields"]["events"]]
        self.assertTrue(any(e["candidate_source_forms"] == ["E", "E-alt"] for e in all_events))
        self.assertTrue(any(e["candidate_source_forms"] == ["Em", "Em-alt"] for e in all_events))
        h4 = self.proposal["records"][7]["schema1_fields"]["events"][-16:]
        self.assertEqual([e["printed_attack_symbol"] for e in h4], ["B", "D", "B", "D"] * 4)
        self.assertTrue(all(e["bass_note_midi"] is None for e in h4))
        self.assertEqual(len(self.proposal["records"][5]["schema1_fields"]["events"]), 96)
        self.assertIsNone(self.candidate["optional_repeat_attack_count"])

    def test_source_hash_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"changed original")
            with self.assertRaisesRegex(ValueError, "input drift"):
                pinned(root, "source.txt", "0" * 64)

    def test_workload_and_invented_voicing_refusals(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["silent_landings"] = 79
        with self.assertRaisesRegex(ValueError, "80/768"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["modules"]["B"][0]["attack_symbols"].pop()
        with self.assertRaisesRegex(ValueError, "source attack/chord count"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["audible_voicing_events"] = [{"invented": True}]
        with self.assertRaisesRegex(ValueError, "invented identity/performance"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["optional_repeat_attack_count"] = 96
        with self.assertRaisesRegex(ValueError, "invented identity/performance"):
            project(candidate, self.foundation, self.registry)
        candidate = copy.deepcopy(self.candidate)
        candidate["chord_reference"]["alternate"]["E-alt"]["sounding_midi"] = [40, 47]
        with self.assertRaisesRegex(ValueError, "invented chord MIDI"):
            project(candidate, self.foundation, self.registry)

    def test_identity_boundary_and_determinism(self) -> None:
        changed = copy.deepcopy(self.foundation)
        changed["records"].append({"legacy_level": 50, "workbook_id": "fg:workbook:000050"})
        with self.assertRaisesRegex(ValueError, "unexpected canonical Level50"):
            project(self.candidate, changed, self.registry)
        changed = copy.deepcopy(self.registry)
        changed["entities"].append({"id": "fg:workbook:000050"})
        with self.assertRaisesRegex(ValueError, "unexpected Level50 registry"):
            project(self.candidate, self.foundation, changed)
        again, handoff = project(self.candidate, self.foundation, self.registry)
        self.assertEqual(encoded(again), encoded(self.proposal))
        self.assertEqual(encoded(handoff), encoded(self.handoff))
        self.assertEqual(digest(encoded(again)), digest(encoded(self.proposal)))


if __name__ == "__main__":
    unittest.main()
