import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level018_schema1_unallocated as proposal


class Level18UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_all_printed_pairs_contacts_fingers_and_qualities(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 676)
        for record, card in zip(self.fields["records"], self.candidate["records"], strict=True):
            events = record["schema1_fields"]["events"]
            self.assertEqual(len(events), 52)
            self.assertEqual(len(record["pair_memberships"]), 26)
            self.assertEqual(record["source_printed_rows"],
                             [{"direction": h["direction"], "raw_rows": h["raw_rows"]}
                              for h in card["directions"]])
            notes = [n for h in card["directions"] for n in h["notes"]]
            self.assertEqual([(e["string"], e["fret"], e["midi"], e["spelling"], e["finger"])
                              for e in events],
                             [(6 - proposal.p07.STRINGS_HIGH_TO_LOW.index(n["string"]), n["fret"],
                               proposal.p07.OPEN_MIDI[n["string"]] + n["fret"], n["tone"],
                               n["finger_digit"]) for n in notes])
            self.assertEqual([p["quality"] for p in record["pair_memberships"]],
                             [p["quality"] for h in card["directions"] for p in h["pairs"]])
            self.assertEqual(events[25]["midi"], events[26]["midi"])

    def test_route_source_spans_layout_exception_and_current659_gap(self):
        route = self.handoff["routes"]["continuous_round_trip"]
        self.assertEqual(len(route), 25)
        self.assertEqual(route.count("L18-rung13"), 1)
        self.assertEqual(route[13:], [f"L18-rung{i:02d}" for i in range(12, 0, -1)])
        self.assertEqual([r["txt"]["ref"] for r in self.handoff["source_map"]],
                         [f"L18-TXT1-{72+27*i}-{95+27*i}" for i in range(13)])
        self.assertTrue(all(not r["pdf_card_has_int_row"] for r in self.handoff["source_map"]))
        self.assertEqual(self.fields["source_exceptions"][0]["kind"], "pdf_layout")
        self.assertEqual(self.fields["current659_level18_records"], 0)
        self.assertFalse(self.fields["current659_level18_workbook_identity"])
        self.assertIsNone(self.fields["representative_collision"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again, handoff = proposal.build()
        self.assertEqual(proposal.encode(again), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))
        self.assertEqual((proposal.ROOT / proposal.OUT / "field-proposal.json").read_bytes(),
                         proposal.encode(self.fields))
        self.assertEqual((proposal.ROOT / proposal.OUT / "allocation-handoff.json").read_bytes(),
                         proposal.encode(self.handoff))

    def test_missing_changed_card_pair_contact_route_refused(self):
        for mutation in (lambda x: x["records"].pop(),
                         lambda x: x["records"][0]["directions"][0]["pairs"][0].update(quality="m3"),
                         lambda x: x["records"][0]["directions"][0]["notes"][0].update(fret=6),
                         lambda x: x["routes"]["down_return"]["rungs"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P07_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)

    def test_identity_timing_pair_and_route_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["pair_memberships"][0]["event_local_ordinals"] = [1, 3]
        with self.assertRaisesRegex(proposal.ProposalError, "PAIR_MEMBERSHIP"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L18-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (378374, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
