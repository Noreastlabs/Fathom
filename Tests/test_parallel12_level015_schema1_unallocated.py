import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level015_schema1_unallocated as proposal


class Level15UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_thirteen_rungs_all_groups_contacts_and_spellings(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 1014)
        self.assertEqual(len(self.fields["records"]), 13)
        for row, source in zip(self.fields["records"], self.candidate["records"], strict=True):
            events = row["schema1_fields"]["events"]
            self.assertEqual(len(events), 78)
            self.assertEqual(len(row["group_memberships"]), 26)
            self.assertEqual([(e["string"], e["fret"], e["finger"]) for e in events],
                             [(proposal.OPEN_MIDI[n["string"]][0], n["fret"], int(n["finger_digit"]))
                              for group in source["groups"] for n in group["notes"]])
            self.assertEqual((events[38]["string"], events[38]["fret"], events[38]["midi"]),
                             (events[39]["string"], events[39]["fret"], events[39]["midi"]))
            self.assertTrue(all(proposal.pitch_class(e["spelling"]) == e["midi"] % 12 for e in events))
            self.assertEqual(len(row["schema1_fields"]["variants"]), 4)
            self.assertFalse(row["schema1_importable"])

    def test_route_and_existing_revision_three_overlap(self):
        route = self.handoff["routes"]["continuous_round_trip"]
        self.assertEqual(len(route), 25)
        self.assertEqual(route.count("L15-rung13"), 1)
        self.assertEqual(route[13:], [f"L15-rung{i:02d}" for i in range(12, 0, -1)])
        overlap = self.fields["existing_selected_illustration_reconciliation"]
        self.assertEqual(overlap["existing_workbook_id"], "fg:workbook:000015")
        self.assertEqual(overlap["existing_item_id"], "fg:item:000004")
        self.assertEqual(overlap["existing_content_revision"], 3)
        self.assertEqual(overlap["existing_timing_status"], "source_defined")
        self.assertEqual(overlap["overlapping_txt_line_spans"][0]["shared_lines"], [70, 81])
        self.assertEqual(overlap["exact_source_ref_key_overlap"], [])
        self.assertTrue(overlap["physical_first_triplet_tuple_match"])
        self.assertIsNone(overlap["selected_choice"])
        self.assertFalse(self.handoff["allocation_allowed"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again, handoff = proposal.build()
        self.assertEqual(proposal.encode(again), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))
        self.assertEqual((proposal.ROOT / proposal.OUT / "field-proposal.json").read_bytes(),
                         proposal.encode(self.fields))

    def test_source_missing_rung_degree_tab_and_route_refused(self):
        for mutation in (lambda x: x["records"].pop(),
                         lambda x: x["records"][0]["groups"][0]["notes"][0].update(degree=2),
                         lambda x: x["records"][0]["groups"][0]["notes"][0].update(fret=6),
                         lambda x: x["neck_route"]["single_turn_cell_sequence"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P08_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)

    def test_identity_timing_group_route_and_overlap_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["duration_q"] = [1, 3]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["group_memberships"][0]["event_local_ordinals"] = [1, 2, 4]
        with self.assertRaisesRegex(proposal.ProposalError, "GROUP_MEMBERSHIP"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L15-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)
        changed = copy.deepcopy(self.fields)
        changed["existing_selected_illustration_reconciliation"]["selected_choice"] = "retain"
        with self.assertRaisesRegex(proposal.ProposalError, "EXISTING_SELECTED_RECONCILIATION"):
            proposal.verify(changed, self.handoff)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (559471, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_HASH_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
