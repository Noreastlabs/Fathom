"""Focused source and admission checks for the detached Level72 projection."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel06_level072_schema1_unallocated as lane  # noqa: E402


class Level72ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.whole, cls.index, cls.package, cls.registry, _ = lane.read_inputs(ROOT)

    def project(self, whole=None, index=None):
        return lane.project(whole or self.whole, index or self.index,
                            self.package, self.registry)

    def test_exact_whole_parity_and_event_fields(self) -> None:
        proposal, handoff = self.project()
        self.assertEqual(len(proposal["records"]), 73)
        self.assertEqual(proposal["counts"]["by_module"], lane.COUNTS)
        pairs = zip(proposal["records"], self.whole["records"])
        for projected, original in pairs:
            self.assertEqual(projected["qualified_source_key"], original["qualified_source_key"])
            events = projected["schema1_fields"]["events"]
            self.assertEqual(len(events), original["contact_count"])
            for event, source in zip(events, original["contacts"]):
                self.assertEqual(event["printed_note"], source["printed_note"])
                self.assertEqual(event["printed_role_or_degree"], source["printed_role_or_degree"])
                self.assertEqual(event["printed_pick"], source["printed_pick"])
                self.assertEqual(event["source_string"], source["string"])
                self.assertEqual(event["source_fret"], source["fret"])
                self.assertEqual(event["source_refs"], source["source_refs"])
                fields = event["schema1_fields"]
                self.assertEqual(fields["midi"] % 12, lane.PC[source["printed_note"]])
                self.assertIsNone(fields["event_id"])
                self.assertIsNone(fields["onset_q"])
                self.assertIsNone(fields["duration_q"])
                self.assertIsNone(event["performed_result"])
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in proposal["records"]), 640)
        self.assertEqual(handoff["catalog_workbook_id"], "fg:workbook:000072")

    def test_nonadmission_and_guidance_boundary(self) -> None:
        proposal, handoff = self.project()
        for key in ("canonical_ids_allocated", "schema1_importable", "whole_workbook_complete", "runtime_eligible", "admitted"):
            self.assertIs(proposal[key], False)
        self.assertIs(handoff["admitted"], False)
        self.assertEqual(proposal["source_differences"], self.whole["source_differences"])
        self.assertEqual(proposal["three_pass_capstone"], self.whole["three_pass_capstone"])
        self.assertEqual(proposal["pdf_only_practice_log"], self.whole["pdf_only_practice_log"])
        self.assertEqual(proposal["counts"]["distinct_printed_contacts"], 640)

    def test_source_admission_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["runtime_eligible"] = True
        with self.assertRaisesRegex(ValueError, "admission"):
            self.project(whole=changed)

    def test_source_order_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["records"][0], changed["records"][1] = changed["records"][1], changed["records"][0]
        with self.assertRaisesRegex(ValueError, "source order"):
            self.project(whole=changed)

    def test_source_count_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["records"][0]["contacts"].pop()
        with self.assertRaisesRegex(ValueError, "record coverage"):
            self.project(whole=changed)

    def test_printed_note_tab_conflict_refused(self) -> None:
        changed = copy.deepcopy(self.whole)
        changed["records"][0]["contacts"][0]["printed_note"] = "E"
        with self.assertRaisesRegex(ValueError, "pitch mismatch"):
            self.project(whole=changed)

    def test_pinned_source_refusal(self) -> None:
        rel = next(iter(lane.INPUTS))
        wrong = {**lane.INPUTS, rel: "0" * 64}
        with patch.object(lane, "INPUTS", wrong):
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.read_inputs(ROOT)

    def test_built_outputs_verify(self) -> None:
        lane.run("verify", ROOT)


if __name__ == "__main__":
    unittest.main()
