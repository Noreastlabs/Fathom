"""Focused Level24 rolling-sequence source and admission checks."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level024_schema1_unallocated as lane  # noqa: E402


class Level24ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.package, cls.registry = lane.read_inputs(ROOT)

    def project(self, candidate=None):
        return lane.project(candidate if candidate is not None else self.candidate,
                            self.package, self.registry)

    def test_exact_rung_group_note_parity(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(proposal["records"]), 13)
        self.assertEqual(proposal["counts"]["rolling_triplet_groups"], 338)
        self.assertEqual(proposal["counts"]["rung_note_contacts"], 1014)
        for projected, source in zip(proposal["records"], self.candidate["records"]):
            fields = projected["schema1_fields"]
            self.assertEqual(projected["source_rung"]["source_refs"], source["source_refs"])
            self.assertEqual([g["source_group"] for g in projected["source_groups"]], source["groups"])
            original_notes = [n for group in source["groups"] for n in group["notes"]]
            self.assertEqual([e["source_note"] for e in fields["events"]], original_notes)
            self.assertEqual(len(fields["events"]), 78)
            self.assertEqual(len(projected["source_groups"]), 26)
            self.assertEqual(fields["variants"][0]["source_event_ordinals"], list(range(1, 79)))
            for event in fields["events"]:
                note = event["source_note"]
                schema = event["schema1_fields"]
                self.assertEqual(schema["spelling"], source["scale_tones"][note["position"] - 1])
                self.assertEqual(schema["midi"] % 12, lane.PC[schema["spelling"]])
                self.assertEqual(schema["fret"], note["fret"])
                self.assertIsNone(schema["event_id"])
                self.assertIsNone(schema["onset_q"])
                self.assertIsNone(schema["duration_q"])
        self.assertEqual(handoff["catalog_workbook_id"], "fg:workbook:000024")

    def test_route_reuses_rungs_without_new_events(self) -> None:
        proposal, _ = self.project()
        sequence = list(range(1, 14)) + list(range(12, 0, -1))
        self.assertEqual([c["source_rung"] for c in proposal["route_application"]], sequence)
        self.assertEqual(sum(len(c["source_event_ordinals"]) for c in proposal["route_application"]), 1950)
        self.assertEqual(proposal["counts"]["route_new_unique_note_events"], 0)
        self.assertEqual(proposal["neck_route"], self.candidate["neck_route"])
        self.assertEqual(proposal["instructions"], self.candidate["instructions"])
        self.assertEqual(proposal["pdf_route_map"], self.candidate["pdf_route_map"])

    def test_nonadmission_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete",
                    "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["admitted"], False)
        self.assertIs(handoff["canonical_ids_allocated"], False)

    def test_changed_admission_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["records"][0]["runtime_eligible"] = True
        with self.assertRaisesRegex(ValueError, "admission"):
            self.project(changed)

    def test_changed_group_count_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["records"][0]["groups"].pop()
        with self.assertRaisesRegex(ValueError, "rung source scope"):
            self.project(changed)

    def test_changed_note_pitch_tab_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["records"][0]["groups"][0]["notes"][0]["fret"] += 1
        with self.assertRaisesRegex(ValueError, "pitch mismatch"):
            self.project(changed)

    def test_changed_route_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["neck_route"]["single_turn_cell_sequence"][-1] = 2
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
