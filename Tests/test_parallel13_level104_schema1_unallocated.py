"""Focused Level104 whole-source unallocated schema1 proposal tests."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level104_schema1_unallocated as proposal  # noqa: E402


class Level104ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        proposal.check_pins()
        proposal.foundation_status()
        cls.replayed = proposal.source.make(ROOT)
        cls.candidate = json.loads((ROOT / proposal.CANDIDATE).read_text())
        cls.txt_lines = (ROOT / proposal.source.TXT).read_text().splitlines()
        cls.output = proposal.project(cls.candidate, cls.replayed, cls.txt_lines)

    def test_original_replay_and_full_source_anchors(self) -> None:
        self.assertEqual(self.candidate, self.replayed)
        self.assertEqual(hashlib.sha256((ROOT / proposal.CANDIDATE).read_bytes()).hexdigest(),
                         proposal.PINS[proposal.CANDIDATE])
        context = self.output["source_context"]
        self.assertEqual(len(context["txt_full_lines"]), 47)
        self.assertEqual(len(context["pdf_page_sources"]), 22)
        for page in context["pdf_page_sources"]:
            self.assertEqual(page["extracted_text_sha256"],
                             hashlib.sha256(page["text"].encode()).hexdigest())
        for row in self.output["rows"]:
            provenance = row["source_provenance"]
            page = context["pdf_page_sources"][provenance["pdf_page"] - 1]
            self.assertEqual(provenance["pdf_extracted_text_sha256"],
                             page["extracted_text_sha256"])
            self.assertEqual(provenance["txt_row_detail"], "omitted")

    def test_module_workloads_and_no_playable_events(self) -> None:
        self.assertEqual(self.output["module_task_row_count"], 140)
        self.assertEqual(self.output["production_gate_count"], 9)
        self.assertEqual({m["source_module"]: m["declared_events"]
                          for m in self.output["modules"]}, proposal.source.CLAIMS)
        self.assertEqual({m["source_module"]: len(m["task_keys"])
                          for m in self.output["modules"]}, proposal.source.COUNTS)
        self.assertEqual(self.output["declared_total_events"], 1440)
        self.assertEqual(self.output["playable_event_count"], 0)
        self.assertEqual(len({r["source_local_key"] for r in self.output["rows"]}), 140)
        for row in self.output["rows"]:
            self.assertIsNone(row["printed_event_allocation"])
            fields = row["schema1_fields"]
            self.assertEqual(fields["events"], [])
            self.assertEqual(fields["variants"], [])
            self.assertFalse(fields["runtime_eligible"])
            for key in ("id", "workbook_id", "module_id", "lineage", "content_revision",
                        "pitch", "route", "observed_result"):
                self.assertIsNone(fields[key])
            self.assertEqual(fields["timing"],
                             {"status": "unresolved", "onset_q": None,
                              "duration_q": None, "fixed_bpm": None})

    def test_identity_lock_and_blank_production_evidence(self) -> None:
        context = self.output["source_context"]
        self.assertEqual(len(context["production_gate_sequence_pdf_p2"]), 9)
        self.assertEqual(context["identity_lock"]["required_chosen_elements"], 3)
        self.assertIsNone(context["identity_lock"]["chosen_elements"])
        identity_rows = [r for r in self.output["rows"] if r["source_module"] == "A"
                         and "non_negotiable" in r["source_task"]["fields"]]
        self.assertEqual(len(identity_rows), 7)
        self.assertTrue(all(r["source_task"]["fields"]["non_negotiable"] is None and
                            r["source_task"]["fields"]["why"] is None
                            for r in identity_rows))
        log = [r for r in self.output["rows"] if r["source_kind"] == "blank_recording_evidence_log"]
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["source_task"]["fields"]["visible_blank_row_slots"], 5)
        self.assertEqual(log[0]["source_task"]["fields"]["entries"], [])
        self.assertIsNone(log[0]["source_task"]["fields"]["actual_recording"])
        self.assertEqual(len([r for r in self.output["rows"] if r["source_module"] == "G"]), 6)

    def test_primary_companion_and_source_difference(self) -> None:
        context = self.output["source_context"]
        primary = context["primary_work"]
        companion = context["companion_work"]
        self.assertEqual((primary["bar_min"], primary["bar_max"]), (32, 64))
        self.assertIsNone(primary["actual_bars"])
        self.assertIsNone(primary["final_recording"])
        self.assertEqual((companion["bar_min"], companion["bar_max"]), (16, 32))
        self.assertEqual(companion["minimum_major_contrasting_dimensions"], 4)
        self.assertIsNone(companion["selected_dimensions"])
        self.assertIsNone(companion["final_recording"])
        self.assertEqual(context["companion_length_source_difference"],
                         {"txt_requirement": "16-32 bars",
                          "pdf_page_20_repeats_length": False,
                          "pdf_page_20_minimum_contrast_dimensions": 4})
        self.assertIn("One contrasting 16-32 bar original", "\n".join(context["txt_full_lines"]))
        self.assertNotIn("16-32", context["pdf_page_sources"][19]["text"])

    def test_portfolio_rubric_and_nonadmission(self) -> None:
        context = self.output["source_context"]
        self.assertEqual(context["portfolio"]["printed_item_count"], 8)
        self.assertIsNone(context["portfolio"]["delivered_items"])
        gate = context["mastery_gate"]
        self.assertEqual(len(gate["rubric_0_to_2"]), 8)
        self.assertEqual(gate["threshold"], "14/16 or better")
        self.assertEqual(gate["required_nonzero"],
                         ["Identity", "Form", "Performance", "Finalization"])
        self.assertIsNone(gate["observed_scores"])
        self.assertFalse(self.output["canonical_ids_allocated"])
        self.assertFalse(self.output["schema1_imported"])
        self.assertFalse(self.output["whole_workbook_accepted"])
        self.assertFalse(self.output["runtime_eligible"])

    def test_refuse_source_row_count_blank_or_admission_drift(self) -> None:
        for mutate in (
            lambda c: c["modules"]["A"]["tasks"][0]["fields"].update(field="invented"),
            lambda c: c["modules"]["I"].update(printed_event_claim=353),
            lambda c: c["modules"]["G"]["tasks"][-1]["fields"].update(entries=[{"take": 1}]),
            lambda c: c["identity_lock"].update(chosen_elements=["hook", "riff", "groove"]),
            lambda c: c["companion_work"].update(bar_min=32),
            lambda c: c["mastery_gate"].update(threshold="12/16"),
            lambda c: c.update(admitted=True),
        ):
            bad = copy.deepcopy(self.candidate)
            mutate(bad)
            with self.assertRaises(proposal.ProposalError):
                proposal.project(bad, self.replayed, self.txt_lines)

    def test_refuse_original_txt_or_projection_drift(self) -> None:
        changed = copy.deepcopy(self.txt_lines)
        changed[next(i for i, line in enumerate(changed) if line.startswith("One contrasting 16-32 bar original"))] = "One contrasting 32-bar original"
        with self.assertRaises(proposal.ProposalError):
            proposal.project(self.candidate, self.replayed, changed)
        altered = copy.deepcopy(self.output)
        altered["rows"][0]["schema1_fields"]["events"] = [{"invented": True}]
        self.assertNotEqual(proposal.encoded(self.output), proposal.encoded(altered))


if __name__ == "__main__":
    unittest.main()
