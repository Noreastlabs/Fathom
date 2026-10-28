import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level016_schema1_unallocated as proposal


class Level16UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_all_rungs_four_note_groups_and_contacts(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 520)
        self.assertEqual(len(self.fields["records"]), 13)
        for row, source in zip(self.fields["records"], self.candidate["records"], strict=True):
            events = row["schema1_fields"]["events"]
            self.assertEqual(len(events), 40)
            self.assertEqual(len(row["group_memberships"]), 10)
            self.assertEqual([(e["string"], e["fret"], e["finger"], e["spelling"]) for e in events],
                             [(proposal.OPEN_MIDI[n["string"]][0], n["fret"], n["finger_digit"], n["tone"])
                              for group in source["groups"] for n in group["notes"]])
            self.assertEqual(events[19]["midi"], events[20]["midi"])
            self.assertEqual(len(row["schema1_fields"]["variants"]), 2)
            self.assertFalse(row["schema1_importable"])

    def test_route_spans_and_current659_gap(self):
        route = self.handoff["routes"]["continuous_round_trip"]
        self.assertEqual(len(route), 25)
        self.assertEqual(route.count("L16-rung13"), 1)
        self.assertEqual(route[13:], [f"L16-rung{i:02d}" for i in range(12, 0, -1)])
        self.assertEqual([r["txt"]["ref"] for r in self.handoff["source_map"]],
                         [f"L16-TXT1-{62+14*i}-{73+14*i}" for i in range(13)])
        self.assertEqual(self.fields["current659_level16_records"], 0)
        self.assertFalse(self.fields["current659_level16_workbook_identity"])
        self.assertFalse(self.handoff["allocation_allowed"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again, handoff = proposal.build()
        self.assertEqual(proposal.encode(again), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))
        self.assertEqual((proposal.ROOT / proposal.OUT / "field-proposal.json").read_bytes(),
                         proposal.encode(self.fields))

    def test_source_missing_rung_note_printed_group_and_route_refused(self):
        for mutation in (lambda x: x["records"].pop(),
                         lambda x: x["records"][0]["groups"][0]["notes"][0].update(fret=6),
                         lambda x: x["records"][0]["groups"][0].update(printed_deg_cell="0--2--3--4--"),
                         lambda x: x["round_trip_rung_order"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P11_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)

    def test_identity_timing_group_and_route_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["duration_q"] = [1, 4]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["group_memberships"][0]["event_local_ordinals"] = [1, 2, 3, 5]
        with self.assertRaisesRegex(proposal.ProposalError, "GROUP_MEMBERSHIP"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L16-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (359420, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_HASH_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
