"""Focused source, musical and refusal checks for Level54 field projection."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level054_schema1_unallocated as proposal  # noqa: E402


class Level54ProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())

    def test_replay_exact_output_and_counts(self) -> None:
        fields, handoff = proposal.derive()
        self.assertEqual(proposal.encoded(fields),
                         (ROOT / proposal.OUT / "field-proposal.json").read_bytes())
        self.assertEqual(proposal.encoded(handoff),
                         (ROOT / proposal.OUT / "allocation-handoff.json").read_bytes())
        self.assertEqual(len(fields["records"]), 120)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in fields["records"]), 558)
        self.assertEqual(sum(r["silent_formation"] is not None for r in fields["records"]), 45)
        self.assertTrue(all(r["schema1_fields"]["id"] is None and
                            r["schema1_fields"]["lineage"] is None and
                            r["schema1_fields"]["timing"]["onset_q"] is None and
                            r["schema1_fields"]["runtime_eligible"] is False
                            for r in fields["records"]))

    def test_blocked_attack_and_distinct_roots(self) -> None:
        fields, _ = proposal.project(self.candidate)
        b = next(r for r in fields["records"] if r["source_local_key"] == "L54-B-03")
        self.assertEqual(len(b["schema1_fields"]["events"]), 14)
        first = b["schema1_fields"]["events"][0]
        self.assertEqual(first["schema1_fields"]["kind"], "blocked_full_form")
        self.assertEqual(len(first["sounding_members"]), 6)
        self.assertEqual(first["schema1_fields"]["midi"], None)
        picked = b["schema1_fields"]["events"][4]
        self.assertEqual(len(picked["sounding_members"]), 1)
        self.assertIn({"fret": 8, "string": "e"}, b["source_unit"]["full_form_root_contacts"])
        self.assertNotIn({"fret": 8, "string": "e"}, b["source_unit"]["fragment_root_contacts"])

    def test_triad_and_d_form_scale(self) -> None:
        fields, _ = proposal.project(self.candidate)
        c = next(r for r in fields["records"] if r["source_local_key"] == "L54-C-01")
        events = c["schema1_fields"]["events"]
        self.assertEqual([len(e["sounding_members"]) for e in events], [3, 1, 1, 1])
        d_form = next(r for r in fields["records"] if r["source_local_key"] == "L54-I-05")
        scale = d_form["schema1_fields"]["events"][4:]
        self.assertEqual([e["sounding_members"][0]["degree"] for e in scale],
                         ["5", "6", "7", "1", "2", "3", "4", "5"])

    def test_source_identity_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["source"]["pdf"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_IDENTITY"):
            proposal.project(changed)

    def test_workout_and_pitch_mutations_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["B"][0]["workout"]["full_string_audit_attacks"] += 1
        with self.assertRaisesRegex(proposal.ProposalError, "B_WORKOUT"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["C"][0]["triad"]["notes"][0] = "D"
        with self.assertRaisesRegex(proposal.ProposalError, "PITCH_CONTACT"):
            proposal.project(changed)

    def test_third_and_silent_mutations_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["D"][0]["moving_string"] = "A"
        with self.assertRaisesRegex(proposal.ProposalError, "D_THIRD"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["A"]["natural_root_form_prompts"][0]["sound"] = True
        with self.assertRaisesRegex(proposal.ProposalError, "A_SILENT_ONLY"):
            proposal.project(changed)

    def test_d_form_scale_and_admission_mutations_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["I"][4]["scale_degrees"][0] = 1
        with self.assertRaisesRegex(proposal.ProposalError, "I_PATTERN"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["content_admitted"] = True
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_SCOPE"):
            proposal.project(changed)


if __name__ == "__main__":
    unittest.main()
