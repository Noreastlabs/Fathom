"""Focused source and nonadmission checks for the detached Level78 proposal."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level078_schema1_unallocated as lane  # noqa: E402


class Level78ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.whole, cls.package, cls.registry = lane.read_inputs(ROOT)

    def project(self, whole=None):
        return lane.project(whole if whole is not None else self.whole,
                            self.package, self.registry)

    def test_exact_task_and_slot_parity(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(proposal["records"]), 8)
        self.assertEqual(proposal["counts"]["tasks_by_module"], lane.TASK_COUNTS)
        self.assertEqual(proposal["counts"]["events_by_module"], lane.COUNTS)
        for projected in proposal["records"]:
            module = projected["source_component"]
            source = self.whole["modules"][module]
            fields = projected["schema1_fields"]
            self.assertEqual(len(fields["variants"]), len(source["records"]))
            self.assertEqual(len(fields["events"]), source["written_event_count"])
            self.assertEqual([v["source_task"] for v in fields["variants"]], source["records"])
            self.assertEqual([e["source_slot"] for e in fields["events"]],
                             [s for s in self.whole["written_event_slots"] if s["module"] == module])
            self.assertEqual(sum(len(v["source_event_ordinals"]) for v in fields["variants"]),
                             source["written_event_count"] - (64 if module == "H" else 0))
            for event in fields["events"]:
                schema = event["schema1_fields"]
                for key in ("event_id", "kind", "attack", "spelling", "midi", "string",
                            "fret", "finger", "onset_q", "duration_q", "tie_from"):
                    self.assertIsNone(schema[key])
                self.assertIsNone(event["performed_result"])
        self.assertEqual(handoff["catalog_workbook_id"], "fg:workbook:000078")

    def test_h_ambiguity_and_pdf_guidance_preserved(self) -> None:
        proposal, handoff = self.project()
        h = proposal["records"][-1]["schema1_fields"]
        self.assertEqual(h["unassigned_source_event_ordinals"], list(range(65, 129)))
        self.assertEqual(proposal["source_count_ambiguities"], self.whole["source_count_ambiguities"])
        self.assertEqual(proposal["pdf_visual_limits"], self.whole["pdf_visual_limits"])
        self.assertEqual(proposal["capstone"], self.whole["capstone"])
        self.assertEqual(len(proposal["capstone"]["five_performance_passes"]), 5)
        self.assertEqual(handoff["module_h_unassigned_written_slots"], 64)
        self.assertIs(proposal["capstone"]["five_passes_are_written_event_multiplier"], False)

    def test_nonadmission_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete",
                    "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["canonical_ids_allocated"], False)
        self.assertIs(handoff["admitted"], False)

    def test_changed_admission_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["runtime_eligible"] = True
        with self.assertRaisesRegex(ValueError, "admission"):
            self.project(changed)

    def test_resolved_slot_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["written_event_slots"][0]["printed_note"] = "F"
        with self.assertRaisesRegex(ValueError, "unexpectedly resolved"):
            self.project(changed)

    def test_h_unassigned_count_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["written_event_slots"][-1]["family"] = "capstone_form"
        with self.assertRaisesRegex(ValueError, "unassigned 64-slot"):
            self.project(changed)

    def test_pinned_candidate_refusal(self) -> None:
        rel = next(iter(lane.INPUTS))
        with patch.object(lane, "INPUTS", {**lane.INPUTS, rel: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.read_inputs(ROOT)

    def test_built_outputs_verify(self) -> None:
        lane.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
