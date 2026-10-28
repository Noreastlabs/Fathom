"""Focused tests for detached whole-Level92 unallocated schema1 fields."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level092_schema1_unallocated as lane  # noqa: E402


class Level92UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c, cls.foundation, cls.registry = lane.read_inputs(ROOT)
        cls.proposal, cls.handoff = lane.project(cls.c, cls.foundation, cls.registry)

    def test_sealed_replay_pins_and_unrelated_numeric_item(self) -> None:
        self.assertEqual(self.c["source"]["txt"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".txt"))])
        self.assertEqual(self.c["source"]["pdf"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".pdf"))])
        self.assertIsNone(self.handoff["existing_level092_representative"])
        self.assertTrue(self.handoff["unrelated_numeric_item_000092_is_level080"])
        self.assertFalse(self.proposal["unrelated_registry_numeric_item_read_only"]["is_level092_identity"])
        bad = copy.deepcopy(self.registry)
        item = next(e for e in bad["entities"] if e.get("id") == "fg:item:000092")
        item["parent"] = "fg:workbook:000092"
        with self.assertRaisesRegex(ValueError, "unrelated lineage drift"):
            lane.identity_boundary(self.foundation, bad)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_104_rows_ten_workloads_and_source_archive(self) -> None:
        p = self.proposal
        self.assertEqual(p["counts"]["printed_task_rows"], 104)
        self.assertEqual(p["counts"]["declared_workload_events"], 1328)
        self.assertEqual(p["counts"]["authored_note_events"], 0)
        self.assertEqual([r["source_component"] for r in p["records"]], list("ABCDEFGHIJ"))
        self.assertEqual(len(p["task_field_proposals"]), 104)
        self.assertEqual(sum(r["printed_task_row_count"] for r in p["records"]), 104)
        self.assertEqual(sum(r["declared_workload_events"] for r in p["records"]), 1328)
        self.assertEqual(len(p["txt_full_lines"]), 44)
        self.assertEqual(len(p["pdf_full_extracted_pages"]), 16)
        self.assertEqual(len(p["symbol_legend"]), 8)
        for r in p["records"]:
            letter = r["source_component"]
            self.assertEqual(r["printed_task_row_count"], lane.ROWS[letter])
            self.assertEqual(r["declared_workload_events"], lane.WORKLOADS[letter])
            self.assertEqual(r["schema1_fields"]["events"], [])
            self.assertEqual(r["schema1_fields"]["variants"], [])
            self.assertIsNone(r["schema1_fields"]["control_scope"]["source_event_count"])
            for t in r["task_proposals"]:
                self.assertTrue(t["source_row"]["pdf_ref"].startswith("L92-PDF-p"))
                self.assertIsNone(t["source_row"]["performed_events"])
                self.assertIsNone(t["source_row"]["declared_events_for_row"])

    def test_capstone_32_chords_five_passes_and_recovery(self) -> None:
        cap = self.proposal["capstone"]
        self.assertEqual((cap["printed_bars"], len(cap["section_blocks"]), len(cap["passes"])), (32, 8, 5))
        self.assertEqual(sum(len(block["semantic"]["chords"]) for block in cap["section_blocks"]), 32)
        self.assertTrue(all(block["semantic"]["note_attacks"] is None and block["semantic"]["voicings"] is None
                            for block in cap["section_blocks"]))
        self.assertEqual(len(self.proposal["records"][-1]["task_proposals"]), 8)
        self.assertTrue(all(t["source_row"]["semantic"]["performed_recovery"] is None
                            for t in self.proposal["records"][-1]["task_proposals"]))

    def test_raw_mastery_gate_and_four_ambiguities_unmapped(self) -> None:
        m = self.proposal["mastery"]
        self.assertEqual((m["required_score"], m["maximum_score"], m["separate_days"]), (14, 16, 2))
        self.assertEqual(m["categories"], lane.SCORED)
        self.assertEqual(m["no_zero_categories"], lane.NO_ZERO)
        self.assertIsNone(m["score_descriptors"])
        self.assertNotIn("target timing", m["categories"])
        self.assertNotIn("harmonic clarity", m["categories"])
        self.assertEqual([x["kind"] for x in self.proposal["source_ambiguities"]], lane.AMBIGUITIES)
        self.assertTrue(all(x["status"] == "pending_curriculum_review" for x in self.proposal["source_ambiguities"]))

    def test_refuses_invented_events_scores_identity_and_gate_mapping(self) -> None:
        edits = [
            (lambda c: c.update(canonical_id="invented"), "invented source performance/identity"),
            (lambda c: c.update(declared_workload_total=1329), "1328 declared workload drift"),
            (lambda c: c["modules"]["A"].update(per_task_event_allocation=[1]), "invented event allocation"),
            (lambda c: c["modules"]["A"]["tables"][0]["rows"][0].update(performed_events=3), "task row drift"),
            (lambda c: c["mastery"].update(score_descriptors={"0": "bad"}), "raw mastery gate/category distinction drift"),
            (lambda c: c["mastery"]["no_zero_categories"].__setitem__(0, "ornament timing"), "raw mastery gate/category distinction drift"),
            (lambda c: c["source_ambiguities"].clear(), "four source ambiguities drift"),
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
            self.assertIsNone(fields["timing"]["fixed_bpm"])
            self.assertIsNone(fields["timing"]["onset_q"])
            self.assertIsNone(fields["timing"]["duration_q"])
            self.assertFalse(fields["runtime_eligible"])

    def test_deterministic_products_and_verify(self) -> None:
        a = lane.products(ROOT)
        b = lane.products(ROOT)
        self.assertEqual({k: lane.encoded(v) for k, v in a.items()},
                         {k: lane.encoded(v) for k, v in b.items()})
        lane.run("verify", ROOT)
        self.assertEqual(a["summary.json"]["proposal_sha256"], lane.digest(lane.encoded(a["field-proposal.json"])))


if __name__ == "__main__":
    unittest.main()
