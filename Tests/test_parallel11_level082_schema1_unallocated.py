"""Focused tests for detached whole-Level82 unallocated schema1 fields."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level082_schema1_unallocated as lane  # noqa: E402


class Level82UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c, cls.foundation, cls.registry = lane.read_inputs(ROOT)
        cls.proposal, cls.handoff = lane.project(cls.c, cls.foundation, cls.registry)

    def test_sealed_replay_source_pins_and_catalog_boundary(self) -> None:
        self.assertEqual(self.c["source_pins"]["txt"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".txt"))])
        self.assertEqual(self.c["source_pins"]["pdf"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".pdf"))])
        self.assertEqual(self.handoff["existing_level082_records"], 0)
        self.assertEqual(self.handoff["existing_level082_workbook_entities"], 0)
        bad = copy.deepcopy(self.foundation)
        entry = next(e for e in bad["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000082")
        entry["representative_item_id"] = "invented"
        with self.assertRaisesRegex(ValueError, "source-only catalog drift"):
            lane.identity_boundary(bad, self.registry)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_all_134_tasks_615_pitches_and_1392_declared_workload(self) -> None:
        p = self.proposal
        self.assertEqual(p["counts"], {"provisional_components": 10, "source_tasks": 134,
                                       "explicit_pitch_entries": 615, "declared_workload_events": 1392,
                                       "unassigned_workload_difference": 777})
        self.assertEqual(len(p["records"]), 10)
        self.assertEqual(len(p["task_field_proposals"]), 134)
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in p["records"]), 615)
        self.assertEqual(sum(r["declared_workload_events"] for r in p["records"]), 1392)
        self.assertEqual(sum(r["unassigned_workload_difference"] for r in p["records"]), 777)
        self.assertEqual([r["source_component"] for r in p["records"]], list("ABCDEFGHIJ"))
        for r in p["records"]:
            letter = r["source_component"]
            self.assertEqual(len(r["task_proposals"]), lane.TASK_COUNTS[letter])
            self.assertEqual(r["printed_pitch_entries"], lane.PITCH_COUNTS[letter])
            self.assertEqual(len(r["schema1_fields"]["events"]), lane.PITCH_COUNTS[letter])

    def test_txt_only_a_studies_and_h_i_distinct_structural_occurrences(self) -> None:
        a = [p["source_task"] for p in self.proposal["records"][0]["task_proposals"]
             if p["source_task"]["kind"] == "walking_bass_chord_melody_study"]
        self.assertEqual([t["fields"]["pdf_status"] for t in a], ["exact_printed_study"] * 4 + ["txt_only_study"] * 4)
        h = [p["source_task"] for p in self.proposal["records"][7]["task_proposals"] if p["source_task"]["kind"] == "arrangement_bar"]
        i = [p["source_task"] for p in self.proposal["records"][8]["task_proposals"] if p["source_task"]["kind"] == "capstone_bar"]
        self.assertEqual(len(h), 32)
        self.assertEqual(len(i), 32)
        for left, right in zip(h, i, strict=True):
            self.assertNotEqual(left["local_key"], right["local_key"])
            self.assertEqual(tuple(left["fields"][k] for k in ("chord", "bass", "melody")),
                             tuple(right["fields"][k] for k in ("chord", "bass", "melody")))

    def test_pitch_class_only_f_double_sharp_and_source_guidance(self) -> None:
        p = self.proposal
        self.assertEqual(len(p["source_archive"]["txt_lines"]), 355)
        self.assertEqual(len(p["source_archive"]["pdf_pages"]), 20)
        self.assertEqual(len(p["pdf_tables"]), 7)
        self.assertEqual(len(p["source_tensions"]), 5)
        self.assertEqual(len(p["unresolved_performance_fields"]), 10)
        fdouble = [e for r in p["records"] for e in r["schema1_fields"]["events"]
                   if e["source_pitch"]["pitch_name"] == "F##"]
        self.assertEqual(len(fdouble), 1)
        self.assertEqual(fdouble[0]["schema1_fields"]["pitch_class"], 7)
        for r in p["records"]:
            for event in r["schema1_fields"]["events"]:
                fields = event["schema1_fields"]
                self.assertIsNone(fields["event_id"])
                for key in ("midi", "octave", "string", "fret", "onset_q", "duration_q", "performed"):
                    self.assertIsNone(fields[key])
                self.assertEqual(fields["pitch_class"], lane.PC[fields["spelling"]])

    def test_refuses_invented_counts_identity_and_h_i_merge(self) -> None:
        edits = [
            (lambda c: c.update(admission_claim=True), "source scope/admission drift"),
            (lambda c: c.update(declared_workload_total=1393), "1392 declared workload drift"),
            (lambda c: c["module_count_comparison"]["A"].update(printed_pitch_entries=128), "declared/printed count distinction drift"),
            (lambda c: c["tasks"][0].update(canonical_task_id="invented"), "invented task identity/performance"),
            (lambda c: c["explicit_pitch_events"][0].update(onset_q=0), "invented source pitch binding/timing/performance"),
            (lambda c: c["source_tensions"].clear(), "source tension/performance uncertainty drift"),
            (lambda c: next(t for t in c["tasks"] if t["module"] == "I" and t["kind"] == "capstone_bar")["fields"].update(bass="F"), "H/I structural parity/occurrence drift"),
        ]
        for edit, expected in edits:
            with self.subTest(expected=expected):
                bad = copy.deepcopy(self.c)
                edit(bad)
                with self.assertRaisesRegex(ValueError, expected):
                    lane.validate_candidate(bad)
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])
        self.assertIsNone(self.proposal["mastery_observed"])
        for r in self.proposal["records"]:
            fields = r["schema1_fields"]
            for key in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
                self.assertIsNone(fields[key])
            self.assertFalse(fields["runtime_eligible"])
            self.assertFalse(fields["admitted"])
            self.assertIsNone(fields["timing"]["fixed_bpm"])

    def test_deterministic_products_and_verify(self) -> None:
        a = lane.products(ROOT)
        b = lane.products(ROOT)
        self.assertEqual({k: lane.encoded(v) for k, v in a.items()},
                         {k: lane.encoded(v) for k, v in b.items()})
        lane.run("verify", ROOT)
        self.assertEqual(a["summary.json"]["proposal_sha256"], lane.digest(lane.encoded(a["field-proposal.json"])))


if __name__ == "__main__":
    unittest.main()
