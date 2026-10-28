import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level019_schema1_unallocated as proposal


class Level19UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_every_triad_contact_role_quality_and_printed_row(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 858)
        for record, card in zip(self.fields["records"], self.candidate["records"], strict=True):
            events = record["schema1_fields"]["events"]
            self.assertEqual(len(events), 66)
            self.assertEqual(len(record["triad_memberships"]), 22)
            self.assertEqual(record["source_printed_txt"], card["printed_txt"])
            self.assertEqual(record["source_printed_pdf"], card["printed_pdf"])
            notes = [n for t in card["triads"] for n in t["notes"]]
            self.assertEqual([(e["string"], e["fret"], e["midi"], e["spelling"], e["finger"])
                              for e in events],
                             [(proposal.OPEN[n["string"]][0], n["fret"],
                               proposal.OPEN[n["string"]][1] + n["fret"],
                               card["scale_tones"][n["degree"] - 1], int(n["finger_digit"]))
                              for n in notes])
            self.assertEqual([(t["roman"], t["quality"], t["chord_name"])
                              for t in record["triad_memberships"]],
                             [(t["roman"], t["quality"], t["chord_name"])
                              for t in card["triads"]])
            self.assertEqual(events[32]["midi"], events[33]["midi"])
            self.assertEqual(record["triad_memberships"][11]["source_note_roles"],
                             ["fifth", "third", "root"])

    def test_route_spans_and_current659_gap(self):
        route = self.handoff["routes"]["continuous_round_trip"]
        self.assertEqual(len(route), 25)
        self.assertEqual(route.count("L19-rung13"), 1)
        self.assertEqual(route[13:], [f"L19-rung{i:02d}" for i in range(12, 0, -1)])
        self.assertEqual([r["txt"]["ref"] for r in self.handoff["source_map"]],
                         [f"L19-TXT1-{71+28*i}-{95+28*i}" for i in range(13)])
        self.assertEqual(self.fields["current659_level19_records"], 0)
        self.assertFalse(self.fields["current659_level19_workbook_identity"])
        self.assertIsNone(self.fields["representative_collision"])
        self.assertFalse(self.handoff["allocation_allowed"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again, handoff = proposal.build()
        self.assertEqual(proposal.encode(again), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))
        self.assertEqual((proposal.ROOT / proposal.OUT / "field-proposal.json").read_bytes(),
                         proposal.encode(self.fields))
        self.assertEqual((proposal.ROOT / proposal.OUT / "allocation-handoff.json").read_bytes(),
                         proposal.encode(self.handoff))

    def test_missing_changed_card_triad_contact_route_refused(self):
        for mutation in (lambda x: x["records"].pop(),
                         lambda x: x["records"][0]["triads"][0].update(quality="minor"),
                         lambda x: x["records"][0]["triads"][0]["notes"][0].update(fret=6),
                         lambda x: x["neck_route"]["descending_rungs_after_turn"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P09_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)

    def test_identity_timing_triad_and_route_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["triad_memberships"][0]["source_note_roles"] = ["root", "fifth", "third"]
        with self.assertRaisesRegex(proposal.ProposalError, "TRIAD_MEMBERSHIP"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L19-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (514263, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
