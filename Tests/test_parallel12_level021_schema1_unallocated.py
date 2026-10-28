import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level021_schema1_unallocated as proposal


class Level21UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_all_rungs_contacts_minor_degrees_and_printed_rows(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 208)
        for record, rung in zip(self.fields["records"], self.candidate["rungs"], strict=True):
            events = record["schema1_fields"]["events"]
            self.assertEqual(len(events), 16)
            self.assertEqual(record["source_printed_rows"], rung["txt_rows"])
            self.assertEqual(record["source_note_details"], rung["notes"])
            self.assertEqual([(e["string"], e["fret"], e["midi"], e["spelling"], e["finger"])
                              for e in events],
                             [(proposal.p10.STRINGS.index(n["string"]) + 1, n["fret"], n["midi"],
                               n["source_tone"], n["finger"]) for n in rung["notes"]])
            self.assertEqual([next(iter(e["degree_contexts"].values()))["alteration"] for e in events[:8]],
                             [0, 0, -1, 0, 0, -1, -1, 0])
            self.assertEqual(events[7]["midi"], events[8]["midi"])

    def test_routes_source_spans_exceptions_and_current659_gap(self):
        route = self.handoff["routes"]
        self.assertEqual(len(route["continuous_round_trip"]), 25)
        self.assertEqual(route["continuous_round_trip"].count("L21-rung13"), 1)
        self.assertEqual(route["down_landmarks"][0], "L21-rung13")
        self.assertEqual(route["down_return"][0], "L21-rung12")
        self.assertTrue(self.fields["source_printed_route"]["down"].startswith("DOWN: A(17)"))
        self.assertEqual([r["txt"]["ref"] for r in self.handoff["source_map"]],
                         [f"L21-TXT1-{45+14*i}-{56+14*i}" for i in range(13)])
        self.assertEqual(self.fields["source_exceptions"], [])
        self.assertEqual(self.fields["current659_level21_records"], 0)
        self.assertFalse(self.fields["current659_level21_workbook_identity"])
        self.assertIsNone(self.fields["representative_collision"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again, handoff = proposal.build()
        self.assertEqual(proposal.encode(again), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))
        self.assertEqual((proposal.ROOT / proposal.OUT / "field-proposal.json").read_bytes(),
                         proposal.encode(self.fields))
        self.assertEqual((proposal.ROOT / proposal.OUT / "allocation-handoff.json").read_bytes(),
                         proposal.encode(self.handoff))

    def test_missing_changed_rung_note_degree_and_route_refused(self):
        for mutation in (lambda x: x["rungs"].pop(),
                         lambda x: x["rungs"][0]["notes"][0].update(fret=6),
                         lambda x: x["rungs"][0]["notes"][2].update(degree="3"),
                         lambda x: x["ladder"]["down_rungs"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P10_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)

    def test_identity_timing_note_and_route_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][2]["degree_contexts"]["A-natural-minor"]["alteration"] = 0
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L21-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (42349, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
