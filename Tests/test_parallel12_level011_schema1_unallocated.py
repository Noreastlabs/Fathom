import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level011_schema1_unallocated as proposal


class Level11UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, cls.handoff = proposal.build()
        cls.candidate = proposal.p08.build_candidate()

    def test_full_source_order_and_physical_contacts(self):
        self.assertEqual(proposal.verify(self.fields, self.handoff)["events"], 5184)
        self.assertEqual(len(self.fields["records"]), 108)
        for record in self.fields["records"]:
            fields = record["schema1_fields"]
            self.assertEqual(len(fields["events"]), 48)
            self.assertEqual([e["string"] for e in fields["events"][:4]], [1] * 4)
            self.assertEqual([e["string"] for e in fields["events"][24:28]], [6] * 4)
            self.assertTrue(all(e["midi"] == [40, 45, 50, 55, 59, 64][e["string"] - 1] + e["fret"]
                                for e in fields["events"]))
            self.assertEqual([m["landing_event_local_ordinals"][:2]
                              for m in record["variant_memberships"]],
                             [[2, 4], [2, 4], [26, 28], [26, 28]])
            self.assertEqual([len(m["event_local_ordinals"]) for m in record["variant_memberships"]], [24] * 4)
            self.assertFalse(record["schema1_importable"])

    def test_deterministic_source_rebuild(self):
        rebuilt, handoff = proposal.build()
        self.assertEqual(proposal.encode(rebuilt), proposal.encode(self.fields))
        self.assertEqual(proposal.encode(handoff), proposal.encode(self.handoff))

    def test_missing_case_and_fret_source_refused(self):
        missing = copy.deepcopy(self.candidate)
        missing["records"].pop()
        with self.assertRaisesRegex(proposal.ProposalError, "P08_SOURCE_CANDIDATE_DRIFT"):
            proposal.build(candidate_override=missing)
        wrong = copy.deepcopy(self.candidate)
        wrong["records"][0]["directions"][0]["string_routes"][0]["cells"][0]["notes"][0]["fret"] = 12
        with self.assertRaisesRegex(proposal.ProposalError, "P08_SOURCE_CANDIDATE_DRIFT"):
            proposal.build(candidate_override=wrong)

    def test_null_timing_and_identity_refusal(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(proposal.ProposalError, "UNSUPPORTED_TIMING_OR_ID"):
            proposal.verify(changed, self.handoff)
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["schema1_fields"]["id"] = "fg:item:999999"
        with self.assertRaisesRegex(proposal.ProposalError, "INVALID_AUTHORITY"):
            proposal.verify(changed, self.handoff)

    def test_variant_landing_membership_refusal(self):
        changed = copy.deepcopy(self.fields)
        changed["records"][0]["variant_memberships"][0]["landing_event_local_ordinals"][0] = 3
        with self.assertRaisesRegex(proposal.ProposalError, "VARIANT_MEMBERSHIP"):
            proposal.verify(changed, self.handoff)

    def test_input_hash_refusal(self):
        with patch.dict(proposal.PINS, {proposal.CANDIDATE: (3254172, "0" * 64)}):
            with self.assertRaisesRegex(proposal.ProposalError, "INPUT_HASH_DRIFT"):
                proposal.pin()


if __name__ == "__main__":
    unittest.main()
