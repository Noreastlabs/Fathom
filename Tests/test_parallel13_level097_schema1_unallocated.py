"""Level97 whole-source unallocated schema1 projection and refusal checks."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level097_schema1_unallocated as proposal  # noqa: E402


class Level97ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        proposal.check_pins()
        cls.representative = proposal.foundation_status()
        cls.replayed = proposal.source.build_candidate(ROOT)
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())
        cls.output = proposal.project(cls.candidate, cls.replayed, cls.representative)

    def test_original_replay_and_coverage(self) -> None:
        self.assertEqual(self.candidate, self.replayed)
        self.assertEqual(hashlib.sha256((ROOT / proposal.CANDIDATE).read_bytes()).hexdigest(),
                         proposal.PINS[proposal.CANDIDATE])
        context = self.output["source_context"]
        self.assertEqual(len(context["txt_full_lines"]), 43)
        self.assertEqual(len(context["pdf_full_extracted_pages"]), 19)
        self.assertEqual(len(context["source_ambiguities"]), 4)
        for row in self.output["rows"] + self.output["listening_reference_rows"]:
            page = context["pdf_full_extracted_pages"][row["source_provenance"]["pdf_page"] - 1]
            self.assertEqual(row["source_provenance"]["extracted_page_sha256"],
                             proposal.sha(proposal.encoded(page)))
            self.assertEqual(row["source_provenance"]["pdf_ref"],
                             row["source_row"]["pdf_ref"])

    def test_module_workloads_and_empty_playable_rows(self) -> None:
        self.assertEqual(self.output["module_task_row_count"], 117)
        self.assertEqual(self.output["listening_reference_row_count"], 7)
        self.assertEqual({m["source_module"]: m["declared_events"]
                          for m in self.output["modules"]}, proposal.EVENTS)
        self.assertEqual(self.output["declared_total_events"], 1424)
        self.assertEqual(self.output["playable_event_count"], 0)
        self.assertEqual(len({r["source_local_key"] for r in
                              self.output["rows"] + self.output["listening_reference_rows"]}), 124)
        for row in self.output["rows"] + self.output["listening_reference_rows"]:
            self.assertIsNone(row["printed_event_allocation"])
            fields = row["schema1_fields"]
            self.assertEqual(fields["events"], [])
            self.assertEqual(fields["variants"], [])
            self.assertFalse(fields["runtime_eligible"])
            for key in ("id", "workbook_id", "module_id", "lineage", "content_revision",
                        "pitch", "route", "audio_source", "observed_result"):
                self.assertIsNone(fields[key])
            self.assertEqual(fields["timing"],
                             {"status": "unresolved", "onset_q": None,
                              "duration_q": None, "fixed_bpm": None})

    def test_listening_dependencies_and_distinct_reference(self) -> None:
        refs = self.output["listening_reference_rows"]
        self.assertEqual({r["source_module"] for r in refs}, {None})
        self.assertEqual({r["source_provenance"]["pdf_page"] for r in refs}, {2})
        self.assertEqual(refs[0]["source_row"]["semantic"]["defer"], "exact chords")
        self.assertEqual(refs[-1]["source_row"]["semantic"]["defer"], "micro-details")
        self.assertTrue(any(r["source_row"]["semantic"].get("requires_primary_contact_map")
                            for r in self.output["rows"] if r["source_module"] == "C"))
        self.assertEqual(len([r for r in self.output["rows"] if r["source_module"] == "H"]), 12)

    def test_h_i_j_audio_form_and_mastery(self) -> None:
        context = self.output["source_context"]
        self.assertEqual(len(context["studies"]), 2)
        self.assertNotEqual(context["studies"][0]["brief"], context["studies"][1]["brief"])
        self.assertEqual([len(study["passes"]) for study in context["studies"]], [6, 6])
        self.assertTrue(all(study["audio_supplied"] is False and
                            study["observed_harmony"] is None for study in context["studies"]))
        capstone = context["capstone"]
        self.assertEqual([(r["semantic"]["start_bar"], r["semantic"]["end_bar"])
                          for r in capstone["section_blocks"]],
                         [(1, 4), (5, 12), (13, 16), (17, 24),
                          (25, 32), (33, 40), (41, 44), (45, 48)])
        self.assertEqual(len(capstone["required_deliverables"]), 7)
        self.assertFalse(capstone["source_audio_supplied"])
        self.assertFalse(capstone["chord_chart_allowed"])
        self.assertIsNone(capstone["observed_chords"])
        mastery = context["mastery"]
        self.assertEqual(len(mastery["rubric"]), 8)
        self.assertEqual((mastery["required_score"], mastery["maximum_score"],
                          mastery["unfamiliar_excerpt_count"]), (14, 16, 2))
        self.assertEqual(mastery["no_zero_categories"],
                         ["Form", "Bass/function", "Groove", "Recovery"])
        self.assertIsNone(mastery["observed_scores"])

    def test_selected_representative_stays_read_only_and_distinct(self) -> None:
        rep = self.output["selected_representative_read_only"]
        self.assertEqual(rep["id"], "fg:item:000012")
        self.assertEqual(rep["scope"], "selected_task_reference_only")
        self.assertFalse(rep["whole_workbook_complete"])
        self.assertFalse(rep["runtime_eligible"])
        self.assertEqual(self.output["source_map_representative_status"]["conversion_status"],
                         "converted_candidate_reference")
        self.assertEqual(rep["source_catalog_status"], "not_converted")
        self.assertTrue(all(r["schema1_fields"]["id"] != rep["id"]
                            for r in self.output["rows"] + self.output["listening_reference_rows"]))

    def test_refuse_modified_source_or_admission(self) -> None:
        for mutate in (
            lambda c: c["modules"]["A"]["tables"][0]["rows"][0]["fields"].update(Question="invented"),
            lambda c: c["declared_workload_by_module"].update(A=97),
            lambda c: c["modules"]["I"]["tables"][0]["rows"][0]["semantic"].update(end_bar=5),
            lambda c: c["mastery"].update(required_score=12),
            lambda c: c.update(admitted=True),
            lambda c: c.update(existing_representative_item_id_read_only="fg:item:other"),
        ):
            bad = copy.deepcopy(self.candidate)
            mutate(bad)
            with self.assertRaises(proposal.ProposalError):
                proposal.project(bad, self.replayed, self.representative)

    def test_refuse_representative_collision_and_output_drift(self) -> None:
        bad = copy.deepcopy(self.representative)
        bad["scope"] = "whole_workbook"
        with self.assertRaises(proposal.ProposalError):
            proposal.project(self.candidate, self.replayed, bad)
        altered = copy.deepcopy(self.output)
        altered["rows"][0]["schema1_fields"]["id"] = "fg:item:000012"
        self.assertNotEqual(proposal.encoded(self.output), proposal.encoded(altered))


if __name__ == "__main__":
    unittest.main()
