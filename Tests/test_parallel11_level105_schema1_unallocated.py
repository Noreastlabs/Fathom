"""Focused tests for the detached Level105 schema1 field projection."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level105_schema1_unallocated as lane  # noqa: E402


class Level105UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate, cls.foundation, cls.registry = lane.read_inputs(ROOT)
        cls.proposal, cls.handoff = lane.project(cls.candidate, cls.foundation, cls.registry)

    def test_source_pins_replay_and_selected_identity_boundary(self) -> None:
        self.assertEqual(self.candidate["source"]["txt"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".txt"))])
        self.assertEqual(self.candidate["source"]["pdf"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".pdf"))])
        self.assertEqual(self.handoff["existing_selected_item_id_read_only"], "fg:item:000013")
        self.assertEqual(self.handoff["existing_selected_record_event_count"], 0)
        bad = copy.deepcopy(self.foundation)
        selected = next(r for r in bad["records"] if r.get("legacy_level") == 105)
        selected["events"] = [{"event_id": "invented"}]
        with self.assertRaisesRegex(ValueError, "selected record boundary"):
            lane.identity_boundary(bad, self.registry)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source.txt"
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_all_modules_rows_workload_and_no_invented_notes(self) -> None:
        p = self.proposal
        self.assertEqual(p["counts"]["declared_workload_events"], 1872)
        self.assertEqual(p["counts"]["printed_module_task_rows"], 151)
        self.assertEqual(p["counts"]["support_table_rows"], 64)
        self.assertEqual(p["counts"]["authored_note_events"], 0)
        self.assertEqual(len(p["source_full_text"]["txt_lines"]), 61)
        self.assertEqual(len(p["source_full_text"]["pdf_extracted_pages"]), 34)
        self.assertEqual([r["source_component"] for r in p["records"]], list("ABCDEFGHIJ"))
        self.assertEqual(sum(r["declared_workload_events"] for r in p["records"]), 1872)
        self.assertEqual(sum(len(t["rows"]) for r in p["records"] for t in r["source_task_tables"]), 151)
        for record in p["records"]:
            fields = record["schema1_fields"]
            self.assertEqual(fields["events"], [])
            self.assertEqual(fields["variants"], [])
            self.assertIsNone(fields["control_scope"]["source_event_count"])
            self.assertIsNone(fields["timing"]["onset_q"])
            self.assertIsNone(fields["timing"]["duration_q"])
            self.assertIsNone(fields["timing"]["fixed_bpm"])
            for table in record["source_task_tables"]:
                self.assertIn(table["page"], record["source_pdf_pages"])
                for row in table["rows"]:
                    self.assertTrue(row["pdf_ref"].startswith("L105-PDF-p"))
                    self.assertIsNone(row["performed_result"])
                    self.assertIsNone(row["declared_events_for_row"])

    def test_fixed_melody_reflection_and_exam_windows(self) -> None:
        b = self.proposal["records"][1]["fixed_melody_reharmonization"]
        self.assertEqual([x["top_note"] for x in b["top_notes"]], ["E", "G", "C", "F#", "Bb", "A"])
        self.assertTrue(all(x["supporting_harmonies"] is None for x in b["top_notes"]))
        j = self.proposal["records"][-1]["reflection"]
        self.assertEqual(len(j["questions"]), 6)
        self.assertTrue(all(q["answer"] is None for q in j["questions"]))
        exam = self.proposal["final_exam"]
        self.assertEqual(len(exam["schedule"]), 8)
        self.assertEqual(sum(len(x["rows"]) for x in exam["detailed_blocks_1_to_7"]), 27)
        self.assertFalse(exam["minute_windows_are_musical_onsets"])
        self.assertIsNone(exam["actual_duration_minutes"])

    def test_rubric_graduation_conflict_and_hard_stop(self) -> None:
        g = self.proposal["graduation"]
        self.assertEqual((g["required_score"], g["maximum_score"], len(g["rubric"])), (24, 30, 10))
        self.assertEqual(set(g["no_zero_domains"]), {"Rhythm/Groove", "Ear/Transcription", "Recovery", "Performance"})
        self.assertEqual(len(g["repeatability_alternatives"]), 2)
        self.assertIsNone(g["recorded_reviewer"])
        self.assertIsNone(g["recorded_scores"])
        self.assertEqual(len(self.proposal["remediation"]), 9)
        self.assertEqual(len(self.proposal["core_path_transformations"]), 12)
        self.assertEqual(len(self.proposal["post_core_tracks"]), 10)
        self.assertIn("condensed core version", json.dumps(self.proposal["final_exam"]["detailed_blocks_1_to_7"]))
        self.assertIn("finished original", json.dumps(g["requirements"]))
        self.assertIn("block7_condensed_core_vs_finished_original", [x["kind"] for x in self.proposal["source_ambiguities"]])
        self.assertFalse(self.proposal["hard_stop"]["level_106_exists"])

    def test_refuses_invented_outcomes_and_changed_source_meaning(self) -> None:
        for edit, expected in [
            (lambda c: c.update(core_complete=True), "invented source outcome"),
            (lambda c: c.update(declared_workload_total=1873), "declared workload drift"),
            (lambda c: c["modules"]["B"].update(per_task_event_allocation=[1]), "invented event allocation"),
            (lambda c: c["modules"]["B"]["fixed_melody_reharmonization"]["top_notes"][0].update(supporting_harmonies=["C"]), "invented reharmonization answer"),
            (lambda c: c["graduation"].update(required_score=23), "graduation rubric drift"),
            (lambda c: c["hard_stop"].update(level_106_exists=True), "Level106 hard stop drift"),
            (lambda c: c["source_ambiguities"].clear(), "p27/p30 original-work ambiguity lost"),
        ]:
            with self.subTest(expected=expected):
                bad = copy.deepcopy(self.candidate)
                edit(bad)
                with self.assertRaisesRegex(ValueError, expected):
                    lane.validate_candidate(bad)

    def test_deterministic_products_and_build_verify(self) -> None:
        first = lane.products(ROOT)
        second = lane.products(ROOT)
        self.assertEqual({k: lane.encoded(v) for k, v in first.items()},
                         {k: lane.encoded(v) for k, v in second.items()})
        lane.run("verify", ROOT)
        self.assertEqual(first["summary.json"]["proposal_sha256"],
                         lane.digest(lane.encoded(first["field-proposal.json"])))
        self.assertFalse(first["field-proposal.json"]["schema1_importable"])
        self.assertFalse(first["field-proposal.json"]["admitted"])
        self.assertIsNone(first["field-proposal.json"]["core_complete"])
        self.assertIsNone(first["field-proposal.json"]["graduated"])
        for record in first["field-proposal.json"]["records"]:
            fields = record["schema1_fields"]
            for key in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
                self.assertIsNone(fields[key])
            self.assertFalse(fields["runtime_eligible"])
            self.assertFalse(fields["admitted"])


if __name__ == "__main__":
    unittest.main()
