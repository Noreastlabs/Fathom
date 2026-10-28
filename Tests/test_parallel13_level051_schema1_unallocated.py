"""Source, musical and refusal checks for the Level51 unallocated proposal."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level051_schema1_unallocated as proposal  # noqa: E402


class Level51ProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())

    def test_replayed_source_and_exact_output(self) -> None:
        fields, handoff = proposal.derive()
        self.assertEqual(proposal.encoded(fields),
                         (ROOT / proposal.OUT / "field-proposal.json").read_bytes())
        self.assertEqual(proposal.encoded(handoff),
                         (ROOT / proposal.OUT / "allocation-handoff.json").read_bytes())
        self.assertEqual(len(fields["records"]), 109)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in fields["records"]), 996)
        self.assertEqual(sum(len(r["source_silent_landings"]) for r in fields["records"]), 56)
        self.assertTrue(all(r["schema1_fields"]["id"] is None and
                            r["schema1_fields"]["lineage"] is None and
                            r["schema1_fields"]["timing"]["onset_q"] is None and
                            r["schema1_fields"]["runtime_eligible"] is False
                            for r in fields["records"]))

    def test_chord_and_partial_contacts(self) -> None:
        fields, _ = proposal.project(self.candidate)
        first = fields["records"][0]
        self.assertEqual([x["phase"] for x in first["source_silent_landings"]],
                         ["full", "partial"])
        self.assertEqual([len(x["voicing"]["members"]) for x in first["source_silent_landings"]],
                         [6, 4])
        c = next(r for r in fields["records"] if r["source_local_key"] == "L51-C-01")
        self.assertEqual(len(c["schema1_fields"]["events"]), 12)
        self.assertEqual(c["schema1_fields"]["events"][0]["schema1_fields"]["midi"], 41)
        self.assertEqual(len(c["schema1_fields"]["events"][0]["sounding_members"]), 1)
        self.assertEqual(len(c["schema1_fields"]["events"][0]["possible_voicing_members"]), 6)
        j4 = next(r for r in fields["records"] if r["source_local_key"] == "L51-J-04")
        self.assertEqual(len(j4["schema1_fields"]["events"]), 16)
        self.assertTrue(all(e["schema1_fields"]["string"] is None and
                            len(e["sounding_members"]) == 0 and
                            len(e["possible_voicing_members"]) == 4 and
                            e["schema1_fields"]["kind"] == "arpeggio_pick_string_unresolved"
                            for e in j4["schema1_fields"]["events"]))
        self.assertEqual(len(fields["pdf_only"]["partial_diagrams"]), 4)
        self.assertIn(20, fields["pdf_only"]["guidance_pages"])

    def test_original_source_mutation_refused(self) -> None:
        with self.assertRaisesRegex(proposal.source.CandidateError, "PINNED_INPUT_DRIFT"):
            proposal.source.build_candidate(txt_data=b"changed source")

    def test_pitch_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["C"][0]["notes_by_string"][0] = "F#"
        with self.assertRaisesRegex(proposal.ProposalError, "PITCH_CONTACT"):
            proposal.project(changed)

    def test_silent_landing_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["A"]["natural_calls"][0]["silent_partial_landing"] = 0
        with self.assertRaisesRegex(proposal.ProposalError, "SILENT_SOURCE"):
            proposal.project(changed)

    def test_major_v_mutation_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["I"][4]["bars"][2]["chord"] += "m"
        changed["modules"]["I"][4]["bars"][2]["quality"] = "minor"
        with self.assertRaisesRegex(proposal.ProposalError, "MINOR_ROUTE_MAJOR_V"):
            proposal.project(changed)

    def test_timing_and_admission_mutations_refused(self) -> None:
        for key, value in (("fixed_bpm", 90), ("admitted", True)):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.candidate)
                changed[key] = value
                with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_SCOPE"):
                    proposal.project(changed)

    def test_pdf_and_attack_count_mutations_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["pdf_reconciliation"]["discrepancies"] = ["missing diagram"]
        with self.assertRaisesRegex(proposal.ProposalError, "PDF_SCOPE"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["pdf_reconciliation"]["partial_diagram_examples"][0]["frets"]["D"] += 1
        with self.assertRaisesRegex(proposal.ProposalError, "PDF_DIAGRAM"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["E"][0]["attack_count"] = 7
        with self.assertRaisesRegex(proposal.ProposalError, "GRID_COUNT"):
            proposal.project(changed)


if __name__ == "__main__":
    unittest.main()
