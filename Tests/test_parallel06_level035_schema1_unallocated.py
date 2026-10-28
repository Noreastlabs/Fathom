"""Focused Level35 horizontal-lane source and nonadmission checks."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level035_schema1_unallocated as lane  # noqa: E402


class Level35ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.package, cls.registry = lane.read_inputs(ROOT)

    def project(self, candidate=None):
        return lane.project(candidate if candidate is not None else self.candidate,
                            self.package, self.registry)

    def test_exact_items_events_and_pitch_geometry(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(proposal["records"]), 4)
        self.assertEqual(proposal["counts"]["source_items"], 48)
        self.assertEqual(proposal["counts"]["by_module"], lane.COUNTS)
        for record in proposal["records"]:
            module = record["source_component"]
            fields = record["schema1_fields"]
            self.assertEqual(len(fields["variants"]), len(self.candidate["modules"][module]))
            self.assertEqual(len(fields["events"]), lane.COUNTS[module]["sounding"])
            self.assertEqual([e["source_event"] for e in fields["events"]],
                             [e for item in self.candidate["modules"][module] for e in item["events"]])
            for event in fields["events"]:
                source = event["source_event"]
                schema = event["schema1_fields"]
                self.assertEqual(schema["spelling"], source["note"])
                self.assertEqual(schema["midi"] % 12, lane.PITCH_CLASS[source["note"]])
                self.assertEqual(schema["fret"], source["fret"])
                self.assertIsNone(schema["event_id"])
                self.assertIsNone(schema["onset_q"])
                self.assertIsNone(schema["duration_q"])
        self.assertEqual(handoff["catalog_workbook_id"], "fg:workbook:000035")

    def test_picked_attacks_and_unpicked_slide_arrivals(self) -> None:
        proposal, _ = self.project()
        events = [e for r in proposal["records"] for e in r["schema1_fields"]["events"]]
        self.assertEqual(sum(e["source_event"]["pick_attack"] for e in events), 336)
        self.assertEqual(sum(not e["source_event"]["pick_attack"] for e in events), 48)
        self.assertEqual({e["source_event"]["articulation"] for e in events if not e["source_event"]["pick_attack"]},
                         {"slide_up_arrival", "slide_down_arrival"})
        self.assertTrue(all(e["schema1_fields"]["attack"] is None for e in events if not e["source_event"]["pick_attack"]))
        self.assertEqual(proposal["source_picking"], self.candidate["picking"])

    def test_module_guidance_and_turn_retained(self) -> None:
        proposal, _ = self.project()
        self.assertEqual(proposal["source_lanes"], self.candidate["lanes"])
        self.assertEqual(proposal["source_guidance"], self.candidate["guidance"])
        self.assertEqual(proposal["source_discrepancies"], [])
        d = proposal["records"][-1]["schema1_fields"]["events"]
        self.assertEqual([(e["source_event"]["string"], e["source_event"]["fret"]) for e in d[35:37]],
                         [("e", 5), ("e", 5)])
        self.assertEqual([v["source_item"]["route"] for v in proposal["records"][-1]["schema1_fields"]["variants"]],
                         ["forward"] * 6 + ["reverse"] * 6)

    def test_nonadmission_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete",
                    "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["admitted"], False)
        self.assertIsNone(proposal["source_timing"]["numeric_onset"])

    def test_changed_note_geometry_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["A"][0]["events"][0]["fret"] += 1
        with self.assertRaisesRegex(ValueError, "pitch mismatch"):
            self.project(changed)

    def test_changed_slide_attack_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["B"][0]["events"][2]["pick_attack"] = True
        with self.assertRaisesRegex(ValueError, "articulation"):
            self.project(changed)

    def test_changed_module_count_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["C"][0]["events"].pop()
        with self.assertRaisesRegex(ValueError, "target/mirror"):
            self.project(changed)

    def test_changed_timing_and_admission_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["timing"]["numeric_onset"] = 0
        with self.assertRaisesRegex(ValueError, "timing"):
            self.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["admitted"] = True
        with self.assertRaisesRegex(ValueError, "admission"):
            self.project(changed)

    def test_pinned_candidate_refusal_and_output_verify(self) -> None:
        rel = next(iter(lane.INPUTS))
        with patch.object(lane, "INPUTS", {**lane.INPUTS, rel: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.read_inputs(ROOT)
        lane.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
