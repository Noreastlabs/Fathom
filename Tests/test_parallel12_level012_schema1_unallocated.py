import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level012_schema1_unallocated as proposal


class Level12UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_thirteen_keyed_cells_pitch_and_routes(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 208)
        self.assertEqual(len(self.fields["records"]), 13)
        self.assertEqual([r["key"] for r in self.fields["records"]],
                         ["A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A"])
        for record in self.fields["records"]:
            fields = record["schema1_fields"]
            self.assertEqual(len(fields["events"]), 16)
            self.assertEqual([e["finger"] for e in fields["events"]], proposal.FINGERS)
            self.assertEqual(fields["events"][7]["midi"], fields["events"][8]["midi"])
            self.assertTrue(all(e["midi"] == [40, 45, 50][e["string"] - 1] + e["fret"]
                                for e in fields["events"]))
            self.assertTrue(all(proposal.pitch_class(e["spelling"]) == e["midi"] % 12
                                for e in fields["events"]))
            self.assertFalse(record["schema1_importable"])
        self.assertEqual(self.handoff["routes"]["continuous_round_trip"].count("L12-rung13"), 1)
        self.assertEqual(len(self.handoff["routes"]["continuous_round_trip"]), 25)

    def test_existing_revision_three_overlap_and_decision(self):
        overlap = self.fields["existing_rung01_reconciliation"]
        self.assertEqual(overlap["existing_workbook_id"], "fg:workbook:000012")
        self.assertEqual(overlap["existing_item_id"], "fg:item:000003")
        self.assertEqual(overlap["existing_content_revision"], 3)
        self.assertTrue(overlap["physical_note_tuple_match"])
        self.assertEqual(len(overlap["remaining_source_keys"]), 12)
        self.assertEqual(overlap["exact_source_ref_key_overlap"], [])
        self.assertEqual(overlap["overlapping_txt_line_spans"][0]["shared_lines"], [42, 52])
        self.assertIsNone(overlap["selected_choice"])
        self.assertFalse(self.handoff["allocation_allowed"])

    def test_deterministic_bytes(self):
        fields, handoff = proposal.build()
        self.assertEqual(proposal.encode(fields), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))

    def test_missing_rung_and_wrong_pitch_refused(self):
        missing = copy.deepcopy(self.candidate)
        missing["records"].pop()
        with self.assertRaisesRegex(proposal.ProposalError, "P07_SOURCE_CANDIDATE_DRIFT"):
            proposal.build(candidate_override=missing)
        wrong = copy.deepcopy(self.candidate)
        wrong["records"][0]["notes"][0]["fret"] = 6
        with self.assertRaisesRegex(proposal.ProposalError, "P07_SOURCE_CANDIDATE_DRIFT"):
            proposal.build(candidate_override=wrong)

    def test_invented_timing_identity_and_route_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["duration_q"] = [1, 2]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_ID"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L12-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (76983, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_HASH_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
