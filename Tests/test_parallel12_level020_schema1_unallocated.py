import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level020_schema1_unallocated as proposal


class Level20UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = json.loads((proposal.ROOT / proposal.CANDIDATE).read_text())

    def test_all_modules_groups_contacts_and_source_rows(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 4186)
        for rung_index, rung in enumerate(self.candidate["rungs"], 1):
            for module_index, module in enumerate(rung["modules"], 1):
                record = self.fields["records"][(rung_index - 1) * 5 + module_index - 1]
                events = record["schema1_fields"]["events"]
                self.assertEqual(record["source_printed_rows"], module["source_rows"])
                self.assertEqual(len(events), module["contact_count"])
                self.assertEqual(len(record["group_memberships"]), len(module["groups"]))
                self.assertEqual([(e["string"], e["fret"], e["midi"], e["spelling"], e["finger"])
                                  for e in events],
                                 [(proposal.OPEN[n["string"]][0], n["fret"],
                                   proposal.OPEN[n["string"]][1] + n["fret"],
                                   n["printed_note_spelling"], n["printed_finger"])
                                  for n in module["contacts"]])
                self.assertEqual([g["event_local_ordinals"] for g in record["group_memberships"]],
                                 [g["contact_ordinals"] for g in module["groups"]])

    def test_circuit_boundaries_high_root_and_route(self):
        self.assertEqual(len(self.fields["circuits"]), 13)
        for rung_index, circuit in enumerate(self.fields["circuits"], 1):
            self.assertEqual([b["last_circuit_contact"] for b in circuit["module_boundaries"]],
                             [30, 108, 204, 256, 322])
            records = self.fields["records"][(rung_index - 1) * 5:rung_index * 5]
            self.assertEqual(records[0]["schema1_fields"]["events"][14]["midi"],
                             records[0]["schema1_fields"]["events"][15]["midi"])
            for before, after in zip(records, records[1:]):
                self.assertEqual(before["schema1_fields"]["events"][-1]["midi"],
                                 after["schema1_fields"]["events"][0]["midi"])
        route = self.handoff["routes"]["continuous_round_trip"]
        self.assertEqual(len(route), 25)
        self.assertEqual(route.count("L20-rung13"), 1)
        self.assertEqual(route[13:], [f"L20-rung{i:02d}" for i in range(12, 0, -1)])
        self.assertEqual(self.fields["counts"]["round_trip_contact_traversals"], 8050)
        self.assertEqual(self.fields["current659_level20_records"], 0)
        self.assertFalse(self.fields["current659_level20_workbook_identity"])

    def test_deterministic_bytes_and_saved_outputs(self):
        again, handoff = proposal.build()
        self.assertEqual(proposal.encode(again), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))
        self.assertEqual((proposal.ROOT / proposal.OUT / "field-proposal.json").read_bytes(),
                         proposal.encode(self.fields))
        self.assertEqual((proposal.ROOT / proposal.OUT / "allocation-handoff.json").read_bytes(),
                         proposal.encode(self.handoff))

    def test_missing_or_altered_source_rung_module_contact_route_refused(self):
        for mutation in (lambda x: x["rungs"].pop(),
                         lambda x: x["rungs"][0]["modules"].pop(),
                         lambda x: x["rungs"][0]["modules"][0]["contacts"][0].update(fret=6),
                         lambda x: x["printed_guidance"]["route_rung_indices"].pop()):
            changed = copy.deepcopy(self.candidate)
            mutation(changed)
            with self.assertRaisesRegex(proposal.ProposalError, "P05_SOURCE_CANDIDATE_DRIFT"):
                proposal.build(candidate_override=changed)

    def test_identity_timing_group_and_route_refused(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_NOTE"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["group_memberships"][0]["event_local_ordinals"] = [2]
        with self.assertRaisesRegex(proposal.ProposalError, "GROUP_MEMBERSHIP"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.handoff)
        changed["routes"]["continuous_round_trip"][13] = "L20-rung13"
        with self.assertRaisesRegex(proposal.ProposalError, "ROUTE_OR_CASE_ORDER"):
            proposal.verify(self.fields, changed)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (3758457, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
