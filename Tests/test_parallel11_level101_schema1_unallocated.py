"""Focused tests for detached whole-Level101 unallocated schema1 fields."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level101_schema1_unallocated as lane  # noqa: E402


class Level101UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c, cls.map_row, cls.foundation, cls.registry = lane.read_inputs(ROOT)
        cls.proposal, cls.handoff = lane.project(cls.c, cls.map_row, cls.foundation, cls.registry)

    def test_sealed_replay_original_pins_and_source_only_catalog(self) -> None:
        self.assertEqual(self.c["source_identities"]["txt"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".txt"))])
        self.assertEqual(self.c["source_identities"]["pdf"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".pdf"))])
        self.assertEqual(self.map_row["conversion_status"], "not_converted")
        self.assertEqual(self.handoff["existing_level101_records"], 0)
        self.assertEqual(self.handoff["existing_level101_workbook_entities"], 0)
        bad = copy.deepcopy(self.foundation)
        entry = next(e for e in bad["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000101")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog drift"):
            lane.identity_boundary(bad, self.registry)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_118_tasks_1584_declared_and_all_source_text(self) -> None:
        p = self.proposal
        self.assertEqual(p["counts"], {"provisional_components": 10, "printed_task_rows": 118,
                                       "supporting_reference_rows": 8, "declared_workload_events": 1584,
                                       "authored_note_events": 0, "energy_map_blank_cells": 12})
        self.assertEqual([r["source_component"] for r in p["records"]], list("ABCDEFGHIJ"))
        self.assertEqual(len(p["task_field_proposals"]), 118)
        self.assertEqual(sum(len(r["task_proposals"]) for r in p["records"]), 118)
        self.assertEqual(sum(r["declared_workload_events"] for r in p["records"]), 1584)
        self.assertEqual(len(p["supporting_reference"]["rows"]), 8)
        self.assertEqual(len(p["txt_lines"]), 51)
        self.assertEqual(len(p["pdf_pages"]), 21)
        for r in p["records"]:
            letter = r["source_component"]
            self.assertEqual(r["declared_workload_events"], lane.WORKLOADS[letter])
            self.assertEqual(r["printed_task_row_count"], lane.ROWS[letter])
            self.assertEqual(r["schema1_fields"]["events"], [])
            self.assertEqual(r["schema1_fields"]["variants"], [])
            self.assertIsNone(r["schema1_fields"]["control_scope"]["source_event_count"])
            for task in r["task_proposals"]:
                self.assertIsNone(task["source_task"]["declared_event_count_for_row"])
                self.assertIsNone(task["source_task"]["recorded_take"])
                self.assertEqual(task["schema1_fields"]["events"], [])

    def test_sparse_energy_map_four_h_studies_and_i_32_bar_form(self) -> None:
        g = self.proposal["records"][6]
        energy = [t["source_task"] for t in g["task_proposals"] if t["source_task"]["source"]["page"] == 15]
        self.assertEqual([t["fields"]["Energy 1-5"] for t in energy], ["2", "3", "4-5", "2-4"])
        self.assertEqual(sum(t["fields"][k] is None for t in energy for k in ("Density", "Register", "Cadence")), 12)
        self.assertTrue(all(t["blank_cells_verified_from_render"] for t in energy))
        h = [t["source_task"] for t in self.proposal["records"][7]["task_proposals"]]
        self.assertEqual(len(self.proposal["h_studies"]), 4)
        self.assertEqual([sum(t["study"] == i for t in h) for i in range(1, 5)], [6, 6, 6, 6])
        i = [t["source_task"]["fields"] for t in self.proposal["records"][8]["task_proposals"]]
        self.assertEqual([t["Bars"] for t in i], ["1-8", "9-16", "17-24", "25-32"])
        self.assertEqual([t["Section"] for t in i], ["A", "B", "Bridge", "A'"])

    def test_literal_capstone_wording_and_raw_mastery(self) -> None:
        deliverables = self.proposal["capstone_deliverables"]
        self.assertEqual(deliverables["wording_equivalence_review"], "Pending")
        self.assertNotEqual(deliverables["txt"], deliverables["pdf"])
        self.assertIn("motif,", deliverables["txt"])
        self.assertIn("motif statement", deliverables["pdf"])
        self.assertIn("recorded take", deliverables["txt"])
        self.assertIn("recorded take", deliverables["pdf"])
        self.assertEqual(self.proposal["mastery"]["minimum"], "14/16 or better")
        self.assertEqual(self.proposal["mastery"]["protected_zero_domains"], ["identity", "form", "thematic return", "performance"])
        self.assertIsNone(self.proposal["recorded_take_observed"])
        self.assertIsNone(self.proposal["mastery_observed"])

    def test_refuses_invented_counts_blank_cells_take_and_admission(self) -> None:
        edits = [
            (lambda c: c.update(schema1_imported=True), "source scope/admission drift"),
            (lambda c: c.update(declared_total_events=1585), "1584/118 module source total drift"),
            (lambda c: c["modules"][0]["tasks"][0].update(declared_event_count_for_row=8), "invented task event/performance"),
            (lambda c: next(t for t in c["modules"][6]["tasks"] if t["source"]["page"] == 15)["fields"].update(Density="high"), "G twelve blank cells were filled"),
            (lambda c: c["modules"][8]["tasks"][0]["fields"].update(Bars="2-9"), "I 32-bar coverage drift"),
            (lambda c: c["capstone_deliverables"].update(wording_equivalence_review="Accepted"), "TXT/PDF capstone wording distinction drift"),
            (lambda c: c["unresolved"].update(recorded_take=True), "source unresolved claims drift"),
        ]
        for edit, expected in edits:
            with self.subTest(expected=expected):
                bad = copy.deepcopy(self.c)
                edit(bad)
                with self.assertRaisesRegex(ValueError, expected):
                    lane.validate_candidate(bad)
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])
        for record in self.proposal["records"]:
            fields = record["schema1_fields"]
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
