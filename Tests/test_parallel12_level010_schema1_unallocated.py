import copy
import importlib.util
import json
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/parallel12_level010_schema1_unallocated.py"
spec = importlib.util.spec_from_file_location("parallel12_level010_schema1_unallocated", TOOL)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class Level10UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aggregate = json.loads((pilot.ROOT / pilot.SOURCE).read_text())
        cls.proposal, cls.handoff = pilot.build()

    def test_whole_source_schema_fields_and_physical_notes(self):
        self.assertEqual(pilot.verify(self.proposal, self.handoff), {"records": 108, "mode_cases": 216, "directions": 432, "routes": 2592, "events": 10368, "variant_field_proposals": 864})
        self.assertEqual(len({r["source_local_key"] for r in self.proposal["records"]}), 108)
        for record in self.proposal["records"]:
            fields = record["schema1_fields"]
            self.assertFalse(record["schema1_importable"])
            self.assertEqual([fields[k] for k in ("id", "workbook_id", "module_id", "lineage")], [None] * 4)
            self.assertEqual(len(fields["events"]), 96)
            self.assertEqual(len(fields["variants"]), 8)
            self.assertEqual([e["string"] for e in fields["events"][:4]], [1] * 4)
            self.assertEqual([e["string"] for e in fields["events"][24:28]], [6] * 4)
            self.assertTrue(all(e["midi"] == [40, 45, 50, 55, 59, 64][e["string"] - 1] + e["fret"] for e in fields["events"]))
            self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for e in fields["events"]))
            self.assertEqual([x["mode"] for x in record["mode_source_refs"]], ["mode_a", "mode_b"])
            self.assertEqual([m["landing_event_local_ordinals"][0] for m in record["variant_memberships"]], [4, 4, 28, 28, 50, 50, 74, 74])

    def test_deterministic_bytes(self):
        proposal, handoff = pilot.build()
        self.assertEqual(pilot.serialized(proposal), pilot.serialized(self.proposal))
        self.assertEqual(pilot.serialized(handoff), pilot.serialized(self.handoff))

    def test_missing_duplicate_case_or_mode_refused(self):
        missing = copy.deepcopy(self.aggregate)
        missing["records"].pop()
        with self.assertRaisesRegex(pilot.ProposalError, "CASE_COVERAGE"):
            pilot.build(aggregate_override=missing)
        duplicate = copy.deepcopy(self.aggregate)
        duplicate["records"][1]["source_local_key"] = duplicate["records"][0]["source_local_key"]
        with self.assertRaisesRegex(pilot.ProposalError, "CASE_MISSING_OR_DUPLICATE"):
            pilot.build(aggregate_override=duplicate)
        missing_mode = copy.deepcopy(self.aggregate)
        missing_mode["records"][0]["modes"].pop()
        with self.assertRaisesRegex(pilot.ProposalError, "MODE_COUNT"):
            pilot.build(aggregate_override=missing_mode)
        duplicate_mode = copy.deepcopy(self.aggregate)
        duplicate_mode["records"][0]["modes"][1]["mode"] = "mode_a"
        with self.assertRaisesRegex(pilot.ProposalError, "MODE_SEMANTICS"):
            pilot.build(aggregate_override=duplicate_mode)

    def test_guessed_timing_refused(self):
        guessed = copy.deepcopy(self.aggregate)
        guessed["records"][0]["modes"][0]["directions"][0]["routes"][0]["notes"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING"):
            pilot.build(aggregate_override=guessed)
        guessed = copy.deepcopy(self.proposal)
        guessed["records"][0]["schema1_fields"]["events"][0]["duration_q"] = [1, 2]
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING_OR_ID"):
            pilot.verify(guessed, self.handoff)
        guessed = copy.deepcopy(self.proposal)
        guessed["records"][0]["fixed_bpm"] = 60
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING"):
            pilot.verify(guessed, self.handoff)

    def test_false_authority_refused(self):
        claimed = copy.deepcopy(self.aggregate)
        claimed["records"][0]["canonical_item_id"] = "fg:item:999999"
        with self.assertRaisesRegex(pilot.ProposalError, "UNSUPPORTED_TIMING_OR_ID"):
            pilot.build(aggregate_override=claimed)
        claimed = copy.deepcopy(self.proposal)
        claimed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(pilot.ProposalError, "INVALID_AUTHORITY"):
            pilot.verify(claimed, self.handoff)

    def test_route_landing_and_source_mismatch_refused(self):
        wrong = copy.deepcopy(self.aggregate)
        wrong["records"][0]["modes"][0]["directions"][0]["routes"][0]["notes"][3]["fret"] = 12
        with self.assertRaisesRegex(pilot.ProposalError, "PHYSICAL_NOTE"):
            pilot.build(aggregate_override=wrong)
        wrong = copy.deepcopy(self.aggregate)
        wrong["records"][0]["modes"][1]["directions"][0]["routes"][0]["notes"][1]["landing"] = False
        with self.assertRaisesRegex(pilot.ProposalError, "LANDING_NOTE"):
            pilot.build(aggregate_override=wrong)
        wrong = copy.deepcopy(self.aggregate)
        wrong["records"][0]["modes"][0]["source_refs"]["txt"] = wrong["records"][1]["modes"][0]["source_refs"]["txt"]
        with self.assertRaisesRegex(pilot.ProposalError, "TXT_HEADING"):
            pilot.build(aggregate_override=wrong)

    def test_input_hash_refusal(self):
        original = pilot.PINS[pilot.SOURCE]
        try:
            pilot.PINS[pilot.SOURCE] = (original[0], "0" * 64)
            with self.assertRaisesRegex(pilot.ProposalError, "INPUT_HASH_DRIFT"):
                pilot.check_pins()
        finally:
            pilot.PINS[pilot.SOURCE] = original


if __name__ == "__main__":
    unittest.main()
