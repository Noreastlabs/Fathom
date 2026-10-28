"""Focused source and allocation checks for detached Level98 fields."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level098_schema1_unallocated as lane  # noqa: E402


class Level98ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.package, cls.registry = lane.read_inputs(ROOT)

    def project(self, candidate=None):
        return lane.project(candidate if candidate is not None else self.candidate,
                            self.package, self.registry)

    def test_exact_module_slot_and_task_source_parity(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(proposal["records"]), 10)
        self.assertEqual(proposal["counts"]["by_module"], lane.COUNTS)
        self.assertEqual(proposal["source_txt"], self.candidate["txt"])
        self.assertEqual(proposal["source_pdf_pages"], self.candidate["pdf_pages"])
        for record, source in zip(proposal["records"], self.candidate["modules"]):
            fields = record["schema1_fields"]
            self.assertEqual(record["source_component"], source["module"])
            self.assertEqual(len(fields["events"]), source["written_event_count"])
            self.assertEqual([e["source_slot"] for e in fields["events"]],
                             source["written_event_slots"])
            self.assertEqual(fields["unassigned_source_event_ordinals"],
                             list(range(1, source["written_event_count"] + 1)))
            self.assertEqual(fields["variants"], [])
            self.assertEqual(record["source_task_pages"],
                             [self.candidate["pdf_pages"][n - 1] for n in source["pdf_pages"]])
            for event in fields["events"]:
                for k in ("source_row", "source_bar", "source_pass", "source_version", "performed_result"):
                    self.assertIsNone(event[k])
                for k in ("event_id", "kind", "attack", "spelling", "midi", "string",
                          "fret", "finger", "onset_q", "duration_q", "tie_from"):
                    self.assertIsNone(event["schema1_fields"][k])
        self.assertEqual(handoff["source_described_written_event_slots"], 1528)

    def test_capstone_versions_and_audit_stay_source_only(self) -> None:
        proposal, _ = self.project()
        capstone = proposal["source_pdf_pages"][18]["semantic"]
        self.assertEqual(len(capstone["section_rows"]), 6)
        self.assertEqual(len(capstone["required_versions"]), 3)
        self.assertIsNone(capstone["complete_arrangement_notes"])
        self.assertIsNone(capstone["performed_versions"])
        self.assertIsNone(proposal["source_pdf_pages"][19]["semantic"]["performed_score"])
        self.assertEqual(proposal["visual_review"], self.candidate["visual_review"])
        self.assertEqual(proposal["source_reconciliation"], self.candidate["source_reconciliation"])

    def test_nonadmission_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete",
                    "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["admitted"], False)
        self.assertEqual(proposal["counts"]["slots_allocated_to_rows_bars_passes_versions"], 0)

    def test_changed_admission_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["runtime_eligible"] = True
        with self.assertRaisesRegex(ValueError, "admission"):
            self.project(changed)

    def test_changed_module_count_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"][0]["written_event_count"] += 1
        with self.assertRaisesRegex(ValueError, "module scope"):
            self.project(changed)

    def test_resolved_slot_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"][0]["written_event_slots"][0]["pitch"] = "C"
        with self.assertRaisesRegex(ValueError, "unexpectedly resolved"):
            self.project(changed)

    def test_completed_capstone_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["pdf_pages"][18]["semantic"]["performed_versions"] = ["claimed"]
        with self.assertRaisesRegex(ValueError, "capstone"):
            self.project(changed)

    def test_pinned_candidate_refusal_and_output_verify(self) -> None:
        rel = next(iter(lane.INPUTS))
        with patch.object(lane, "INPUTS", {**lane.INPUTS, rel: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.read_inputs(ROOT)
        lane.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
