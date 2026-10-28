import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level022_schema1_unallocated as proposal


class Level22UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_all_rungs_contacts_minor_degrees_and_printed_rows(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 390)
        for record, rung in zip(self.fields["records"], self.candidate["rungs"], strict=True):
            events = record["schema1_fields"]["events"]
            self.assertEqual(len(events), 30)
            self.assertEqual(record["source_printed_rows"],
                             {"Deg": rung["source_degree_line"], "Fng": rung["source_finger_line"],
                              "TAB_high_to_low": rung["source_tab_rows_high_to_low"]})
            self.assertEqual(record["source_note_details"], rung["cell_notes"])
            self.assertEqual([(e["string"], e["fret"], e["midi"], e["spelling"], e["finger"])
                              for e in events],
                             [(proposal.OPEN[n["string"]][0], n["fret"],
                               proposal.OPEN[n["string"]][1] + n["fret"], n["pitch_spelling"],
                               n["finger_digit"]) for n in rung["cell_notes"]])
            self.assertEqual(events[14]["midi"], events[15]["midi"])
            self.assertEqual([e["string"] for e in events[:15]].count(4), 3)
            self.assertEqual([e["string"] for e in events[:15]].count(5), 3)

    def test_routes_source_spans_exceptions_and_current659_gap(self):
        route = self.handoff["routes"]
        self.assertEqual(len(route["continuous_round_trip"]), 25)
        self.assertEqual(route["continuous_round_trip"].count("L22-rung13"), 1)
        self.assertEqual(route["down_landmarks"][0], "L22-rung13")
        self.assertEqual(route["down_return"][0], "L22-rung12")
        self.assertTrue(self.fields["source_printed_route"]["down"].startswith("DOWN: A(17)"))
        self.assertEqual([r["txt"]["ref"] for r in self.handoff["source_map"]],
                         [f"L22-TXT1-{55+14*i}-{66+14*i}" for i in range(13)])
        self.assertEqual(self.fields["source_exceptions"], [])
        self.assertEqual(self.fields["current659_level22_records"], 0)
        self.assertFalse(self.fields["current659_level22_workbook_identity"])
        self.assertIsNone(self.fields["representative_collision"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again, handoff = proposal.build()
        self.assertEqual(proposal.encode(again), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))
        self.assertEqual((proposal.ROOT / proposal.OUT / "field-proposal.json").read_bytes(),
                         proposal.encode(self.fields))
        self.assertEqual((proposal.ROOT / proposal.OUT / "allocation-handoff.json").read_bytes(),
                         proposal.encode(self.handoff))

    def test_missing_changed_rung_note_geometry_and_route_refused(self):
        for mutation in (lambda x: x["rungs"].pop(),
                         lambda x: x["rungs"][0]["cell_notes"][0].update(fret=6),
                         lambda x: x["rungs"][0]["cell_notes"][8].update(string="B"),
                         lambda x: x["full_round_trip_route"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_CANDIDATE_DRIFT"):
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
        changed["routes"]["continuous_round_trip"][13] = "L22-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (89655, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
