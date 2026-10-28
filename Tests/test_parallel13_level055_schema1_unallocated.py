"""Focused source, harmony and refusal checks for Level55 fields."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level055_schema1_unallocated as proposal  # noqa: E402


class Level55ProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())

    def test_replay_exact_output_and_distinct_workloads(self) -> None:
        fields, handoff = proposal.derive()
        self.assertEqual(proposal.encoded(fields),
                         (ROOT / proposal.OUT / "field-proposal.json").read_bytes())
        self.assertEqual(proposal.encoded(handoff),
                         (ROOT / proposal.OUT / "allocation-handoff.json").read_bytes())
        self.assertEqual(len(fields["records"]), 156)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in fields["records"]), 936)
        self.assertEqual(sum(r["silent_prompt"] is not None for r in fields["records"]), 42)
        self.assertEqual(sum(r["written_prompt"] is not None for r in fields["records"]), 24)
        self.assertEqual(fields["key_foundation"]["circle_order"], ["F", "C", "G", "D", "A", "E"])
        self.assertTrue(all(r["schema1_fields"]["id"] is None and
                            r["schema1_fields"]["lineage"] is None and
                            r["schema1_fields"]["timing"]["onset_q"] is None and
                            r["schema1_fields"]["runtime_eligible"] is False
                            for r in fields["records"]))

    def test_triad_contacts_and_progression_noninvention(self) -> None:
        fields, _ = proposal.project(self.candidate)
        b = next(r for r in fields["records"] if r["source_local_key"] == "L55-B-01")
        events = b["schema1_fields"]["events"]
        self.assertEqual([len(e["sounding_members"]) for e in events], [3, 1, 1, 1])
        self.assertEqual(sorted(m["pitch_class"] for m in events[0]["sounding_members"]),
                         sorted(proposal.source.PC[n] for n in ["C", "E", "G"]))
        c = next(r for r in fields["records"] if r["source_local_key"] == "L55-C-01")
        self.assertEqual(len(c["schema1_fields"]["events"]), 16)
        self.assertTrue(all(e["sounding_members"] == [] and
                            e["pitch_binding"] == "unresolved_voicing_choice" and
                            e["schema1_fields"]["midi"] is None
                            for e in c["schema1_fields"]["events"]))

    def test_voice_alternatives_and_written_answers(self) -> None:
        fields, _ = proposal.project(self.candidate)
        i = next(r for r in fields["records"] if r["source_local_key"] == "L55-I-01")
        self.assertEqual(set(i["source_context"]["unselected_voice_fret_paths"]),
                         {"low", "middle", "top"})
        self.assertEqual(len(i["schema1_fields"]["events"]), 16)
        j = next(r for r in fields["records"] if r["source_local_key"] == "L55-J-01")
        self.assertEqual(j["written_prompt"]["answer_roman"], ["I", "vi", "IV", "V"])
        self.assertEqual(j["schema1_fields"]["events"], [])

    def test_original_source_mutation_refused(self) -> None:
        with self.assertRaisesRegex(proposal.source.CandidateError, "PINNED_INPUT_DRIFT"):
            proposal.source.build_candidate(txt_data=b"altered")

    def test_triad_pitch_and_roman_mutations_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["B"][0]["degrees"][0]["spelling"][0] = "D"
        with self.assertRaisesRegex(proposal.ProposalError, "TRIAD_PITCH"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["C"][0]["bars"][0]["roman"] = "V"
        with self.assertRaisesRegex(proposal.ProposalError, "PROGRESSION_ROMAN"):
            proposal.project(changed)

    def test_silent_written_and_voice_path_mutations_refused(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["A"]["silent_prompts"][0]["sounded_attacks"] = 1
        with self.assertRaisesRegex(proposal.ProposalError, "A_SILENT_ONLY"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["I"][0]["voice_frets"].pop("middle")
        with self.assertRaisesRegex(proposal.ProposalError, "I_VOICE_PATHS"):
            proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["modules"]["J"]["analysis"].pop()
        with self.assertRaisesRegex(proposal.ProposalError, "ITEM_COUNT J"):
            proposal.project(changed)

    def test_timing_admission_and_pdf_mutations_refused(self) -> None:
        for key, value in (("fixed_bpm", 100), ("admitted", True)):
            changed = copy.deepcopy(self.candidate)
            changed[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(proposal.ProposalError, "SOURCE_SCOPE"):
                proposal.project(changed)
        changed = copy.deepcopy(self.candidate)
        changed["pdf_reconciliation"]["discrepancies"] = ["unresolved"]
        with self.assertRaisesRegex(proposal.ProposalError, "SOURCE_RECONCILIATION"):
            proposal.project(changed)


if __name__ == "__main__":
    unittest.main()
