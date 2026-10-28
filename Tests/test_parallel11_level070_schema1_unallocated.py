"""Focused tests for the detached whole-Level70 schema1 field projection."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel11_level070_schema1_unallocated as lane  # noqa: E402


class Level70UnallocatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c, cls.p06, cls.foundation, cls.registry = lane.read_inputs(ROOT)
        cls.proposal, cls.handoff = lane.project(cls.c, cls.p06, cls.foundation, cls.registry)

    def test_pinned_replay_catalog_and_source_drift_refusal(self) -> None:
        self.assertEqual(self.c["source"]["txt"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".txt"))])
        self.assertEqual(self.c["source"]["pdf"]["sha256"], lane.INPUTS[next(k for k in lane.INPUTS if k.endswith(".pdf"))])
        self.assertEqual(self.handoff["existing_level070_records"], 0)
        self.assertEqual(self.handoff["existing_level070_workbook_entities"], 0)
        bad = copy.deepcopy(self.foundation)
        entry = next(e for e in bad["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000070")
        entry["admitted"] = True
        with self.assertRaisesRegex(ValueError, "source-only catalog drift"):
            lane.identity_boundary(bad, self.registry)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "source.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input drift"):
                lane.pinned(Path(d), "source.txt", "0" * 64)

    def test_all_898_source_contacts_and_p06_independent_parity(self) -> None:
        self.assertEqual(self.proposal["counts"]["module_tones"], lane.COUNTS)
        self.assertEqual(self.proposal["counts"]["printed_sounding_tones"], 898)
        self.assertEqual(self.proposal["counts"]["source_cells"], 43)
        self.assertEqual([r["source_component"] for r in self.proposal["records"]], list("ABCDEFGH"))
        self.assertEqual(sum(len(r["schema1_fields"]["events"]) for r in self.proposal["records"]), 898)
        self.assertEqual(sum(len(r["schema1_fields"]["variants"]) for r in self.proposal["records"]), 43)
        self.assertEqual(self.proposal["p06_read_only_parity"]["ordered_note_string_fret_midi_matches"], 898)
        lane.validate_p06_parity(self.c, self.p06)
        bad = copy.deepcopy(self.p06)
        bad["module_g_blocks"][0]["record_projection"]["events"][0]["fret"] += 1
        with self.assertRaisesRegex(ValueError, "P06 G note/string/fret/midi parity drift"):
            lane.validate_p06_parity(self.c, bad)
        for record in self.proposal["records"]:
            for event in record["schema1_fields"]["events"]:
                source = event["source_tone"]
                fields = event["schema1_fields"]
                self.assertEqual(fields["spelling"], source["note"])
                self.assertEqual(fields["fret"], source["fret"])
                self.assertEqual(fields["midi"], lane.OPEN[source["string"]] + source["fret"])
                self.assertIsNone(fields["event_id"])
                self.assertIsNone(fields["onset_q"])
                self.assertIsNone(fields["duration_q"])
                self.assertIsNone(fields["pick"])
                self.assertIsNone(fields["accent"])

    def test_module_f_both_printed_descents_and_unperformed_choice(self) -> None:
        f = self.proposal["records"][5]
        self.assertEqual(len(f["schema1_fields"]["events"]), 60)
        self.assertEqual(len(f["schema1_fields"]["variants"]), 5)
        for variant in f["schema1_fields"]["variants"]:
            cell = variant["source_cell"]
            self.assertEqual([e["form"] for e in cell["events"]], ["ASC"] * 4 + ["SYM"] * 4 + ["CLS"] * 4)
            self.assertIsNone(variant["performed_pass_count"])
        self.assertIn("choose one of two descending forms", self.proposal["source_ambiguities"][0])
        self.assertTrue(self.proposal["workload"]["module_f_both_descent_forms_written_and_counted"])

    def test_supplemental_boundaries_pdf_parity_and_guidance(self) -> None:
        p = self.proposal
        for key in ("supplemental_seam_second_pass_counted", "supplemental_sequence_translations_counted", "supplemental_capstone_repeat_counted"):
            self.assertFalse(p["workload"][key])
        self.assertEqual(len(p["source_transcription"]["txt_lines"]), 533)
        self.assertEqual(len(p["source_transcription"]["pdf_pages"]), 20)
        self.assertEqual(len(p["mastery"]["txt_lines"]), 33)
        self.assertEqual(p["mastery"]["pdf_page"], 20)
        self.assertEqual(len(p["count_boundaries"]), 3)
        self.assertEqual(len(p["pdf_only_directions"]), 10)
        for letter in "BE":
            record = next(r for r in p["records"] if r["source_component"] == letter)
            self.assertTrue(all(v["source_cell"]["pdf_grid_status"] == "degree_finger_tab_without_note_row"
                                for v in record["schema1_fields"]["variants"]))
        b = p["records"][1]
        self.assertTrue(all(v["source_cell"]["repeat_counted_in_printed_898"] is False
                            for v in b["schema1_fields"]["variants"]))

    def test_rejects_invented_source_and_admission_fields(self) -> None:
        edits = [
            (lambda c: c.update(stable_ids=["invented"]), "source identity/admission drift"),
            (lambda c: c["workload"].update(total_sounding_tones=899), "898-tone source workload drift"),
            (lambda c: c["workload"].update(supplemental_seam_second_pass_counted=True), "supplemental pass count drift"),
            (lambda c: c["modules"]["F"]["cells"][0]["events"][4].update(form="CLS"), "F ASC/SYM/CLS structure drift"),
            (lambda c: c["modules"]["A"]["cells"][0]["events"][0].update(onset_q=0), "source note/TAB/timing drift"),
            (lambda c: c["source_ambiguities"].clear(), "F descent source tension lost"),
        ]
        for edit, message in edits:
            with self.subTest(message=message):
                bad = copy.deepcopy(self.c)
                edit(bad)
                with self.assertRaisesRegex(ValueError, message):
                    lane.validate_candidate(bad)
        self.assertFalse(self.proposal["schema1_importable"])
        self.assertFalse(self.proposal["admitted"])
        self.assertIsNone(self.proposal["mastery_observed"])
        for record in self.proposal["records"]:
            fields = record["schema1_fields"]
            for key in ("id", "workbook_id", "module_id", "content_revision", "lineage"):
                self.assertIsNone(fields[key])
            self.assertIsNone(fields["timing"]["fixed_bpm"])
            self.assertFalse(fields["runtime_eligible"])
            self.assertFalse(fields["admitted"])

    def test_deterministic_products_and_verify(self) -> None:
        a = lane.products(ROOT)
        b = lane.products(ROOT)
        self.assertEqual({k: lane.encoded(v) for k, v in a.items()},
                         {k: lane.encoded(v) for k, v in b.items()})
        lane.run("verify", ROOT)
        self.assertEqual(a["summary.json"]["proposal_sha256"], lane.digest(lane.encoded(a["field-proposal.json"])))


if __name__ == "__main__":
    unittest.main()
