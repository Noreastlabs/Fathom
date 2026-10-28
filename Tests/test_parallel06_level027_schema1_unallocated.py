"""Focused Level27 ordered-thirds source and admission checks."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level027_schema1_unallocated as lane  # noqa: E402


class Level27ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.package, cls.registry = lane.read_inputs(ROOT)

    def project(self, candidate=None):
        return lane.project(candidate if candidate is not None else self.candidate,
                            self.package, self.registry)

    def test_exact_rung_pair_contact_parity(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(proposal["records"]), 13)
        self.assertEqual(proposal["counts"]["ordered_third_pairs"], 338)
        self.assertEqual(proposal["counts"]["rung_note_contacts"], 676)
        self.assertEqual(proposal["counts"]["minor_third_pairs"], 208)
        self.assertEqual(proposal["counts"]["major_third_pairs"], 130)
        for projected, source in zip(proposal["records"], self.candidate["records"]):
            fields = projected["schema1_fields"]
            self.assertEqual(projected["source_rung"]["source_refs"], source["source_refs"])
            self.assertEqual([p["source_pair"] for p in projected["source_pairs"]],
                             [p for d in source["directions"] for p in d["pairs"]])
            self.assertEqual(len(projected["source_pairs"]), 26)
            self.assertEqual(len(fields["events"]), 52)
            self.assertEqual([e["source_contact"] for e in fields["events"]],
                             [c for d in source["directions"] for p in d["pairs"] for c in p["contacts"]])
            self.assertEqual(fields["variants"][0]["source_event_ordinals"], list(range(1, 53)))
            for event in fields["events"]:
                contact = event["source_contact"]
                schema = event["schema1_fields"]
                self.assertEqual(schema["midi"], contact["midi_pitch"])
                self.assertEqual(schema["midi"] % 12, lane.PC[schema["spelling"]])
                self.assertIsNone(schema["event_id"])
                self.assertIsNone(schema["onset_q"])
                self.assertIsNone(schema["duration_q"])
        self.assertEqual(handoff["catalog_workbook_id"], "fg:workbook:000027")

    def test_five_source_differences_remain_pending(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(proposal["source_discrepancies"], self.candidate["source_discrepancies"])
        self.assertEqual(handoff["source_differences_pending"], list(lane.DIFFERENCE_IDS))
        self.assertEqual(proposal["source_discrepancies"][0]["txt_ref"]["text"], "A natural minor - octave")
        self.assertEqual(proposal["source_discrepancies"][0]["pdf_ref"]["text"], "A natural minor (octave)")
        self.assertEqual(proposal["pdf_projection_checks"], self.candidate["pdf_projection_checks"])

    def test_route_reuses_rungs_without_new_events(self) -> None:
        proposal, _ = self.project()
        sequence = list(range(1, 14)) + list(range(12, 0, -1))
        self.assertEqual([c["source_rung"] for c in proposal["route_application"]], sequence)
        self.assertEqual(sum(len(c["source_event_ordinals"]) for c in proposal["route_application"]), 1300)
        self.assertEqual(proposal["counts"]["route_new_unique_note_events"], 0)
        self.assertEqual(proposal["sequence_facts"], self.candidate["sequence_facts"])

    def test_nonadmission_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete",
                    "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["admitted"], False)

    def test_changed_difference_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["source_discrepancies"][0]["pdf_ref"]["text"] = "A natural minor - octave"
        with self.assertRaisesRegex(ValueError, "label difference"):
            self.project(changed)

    def test_changed_contact_pitch_tab_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["records"][0]["directions"][0]["pairs"][0]["contacts"][0]["fret"] += 1
        with self.assertRaisesRegex(ValueError, "pitch mismatch"):
            self.project(changed)

    def test_changed_pair_count_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["records"][0]["directions"][0]["pairs"].pop()
        with self.assertRaisesRegex(ValueError, "pair count"):
            self.project(changed)

    def test_changed_admission_and_route_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["scope"]["runtime_eligible"] = True
        with self.assertRaisesRegex(ValueError, "admission"):
            self.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["sequence_facts"]["full_round_trip_instruction"]["instructed_note_count"] += 1
        with self.assertRaisesRegex(ValueError, "route/count"):
            self.project(changed)

    def test_pinned_candidate_refusal_and_output_verify(self) -> None:
        rel = next(iter(lane.INPUTS))
        with patch.object(lane, "INPUTS", {**lane.INPUTS, rel: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.read_inputs(ROOT)
        lane.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
