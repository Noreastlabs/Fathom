import copy
import importlib.util
import json
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/parallel12_level008_schema1_unallocated.py"
spec = importlib.util.spec_from_file_location("parallel12_level008_schema1_unallocated", TOOL)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class Level8UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft = json.loads((pilot.ROOT / pilot.DRAFT).read_text())
        cls.proposal, cls.handoff = pilot.build()

    def test_whole_source_order_and_unallocated_schema_fields(self):
        self.assertEqual(pilot.verify(self.proposal, self.handoff), {"records": 108, "directions": 216, "routes": 1296, "four_note_cells": 2592, "events": 10368, "variant_field_proposals": 432})
        self.assertEqual(len({r["source_local_key"] for r in self.proposal["records"]}), 108)
        for record in self.proposal["records"]:
            fields = record["schema1_fields"]
            self.assertFalse(record["schema1_importable"])
            self.assertEqual([fields[k] for k in ("id", "workbook_id", "module_id", "lineage")], [None] * 4)
            self.assertEqual(len(fields["events"]), 96)
            self.assertEqual([e["string"] for e in fields["events"][:8]], [1] * 8)
            self.assertEqual([e["string"] for e in fields["events"][48:56]], [6] * 8)
            self.assertTrue(all(e["midi"] == [40, 45, 50, 55, 59, 64][e["string"] - 1] + e["fret"] for e in fields["events"]))
            self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for e in fields["events"]))
            self.assertEqual([v["label"] for v in fields["variants"]], ["shift_up-D", "shift_up-U", "shift_down-D", "shift_down-U"])
            self.assertEqual(record["variant_memberships"][1]["event_local_ordinals"], list(range(1, 49)))
            self.assertEqual(record["variant_memberships"][3]["event_local_ordinals"], list(range(49, 97)))

    def test_deterministic_bytes(self):
        proposal, handoff = pilot.build()
        self.assertEqual(pilot.serialized(proposal), pilot.serialized(self.proposal))
        self.assertEqual(pilot.serialized(handoff), pilot.serialized(self.handoff))

    def test_missing_and_duplicate_cases_refused(self):
        missing = copy.deepcopy(self.draft)
        missing["records"].pop()
        with self.assertRaisesRegex(pilot.ProposalError, "DRAFT_COVERAGE"):
            pilot.build(draft_override=missing)
        duplicate = copy.deepcopy(self.draft)
        duplicate["records"][1]["source_local_key"] = duplicate["records"][0]["source_local_key"]
        with self.assertRaisesRegex(pilot.ProposalError, "CASE_MISSING_OR_DUPLICATE"):
            pilot.build(draft_override=duplicate)

    def test_guessed_timing_refused(self):
        guessed = copy.deepcopy(self.draft)
        guessed["records"][0]["directions"][0]["routes"][0]["ordered_notes"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING"):
            pilot.build(draft_override=guessed)
        guessed = copy.deepcopy(self.proposal)
        guessed["records"][0]["schema1_fields"]["events"][0]["duration_q"] = [1, 2]
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING_OR_ID"):
            pilot.verify(guessed, self.handoff)

    def test_false_authority_refused(self):
        claimed = copy.deepcopy(self.draft)
        claimed["records"][0]["canonical_item_id"] = "fg:item:999999"
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING_OR_ID"):
            pilot.build(draft_override=claimed)
        claimed = copy.deepcopy(self.proposal)
        claimed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(pilot.ProposalError, "INVALID_AUTHORITY"):
            pilot.verify(claimed, self.handoff)

    def test_physical_order_and_source_mismatch_refused(self):
        wrong = copy.deepcopy(self.draft)
        wrong["records"][0]["directions"][0]["routes"][0]["ordered_notes"][0]["fret"] = 12
        with self.assertRaisesRegex(pilot.ProposalError, "FINGER_FRET_SOURCE"):
            pilot.build(draft_override=wrong)
        wrong = copy.deepcopy(self.draft)
        wrong["records"][0]["directions"][0]["route_order"][0] = "e"
        with self.assertRaisesRegex(pilot.ProposalError, "DIRECTION_ROUTE"):
            pilot.build(draft_override=wrong)
        wrong = copy.deepcopy(self.draft)
        wrong["records"][0]["source_refs"]["txt"] = wrong["records"][1]["source_refs"]["txt"]
        with self.assertRaisesRegex(pilot.ProposalError, "TXT_HEADING"):
            pilot.build(draft_override=wrong)

    def test_input_hash_refusal(self):
        original = pilot.PINS[pilot.DRAFT]
        try:
            pilot.PINS[pilot.DRAFT] = (original[0], "0" * 64)
            with self.assertRaisesRegex(pilot.ProposalError, "INPUT_HASH_DRIFT"):
                pilot.check_pins()
        finally:
            pilot.PINS[pilot.DRAFT] = original


if __name__ == "__main__":
    unittest.main()
